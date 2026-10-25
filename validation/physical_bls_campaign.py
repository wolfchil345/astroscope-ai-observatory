"""Mission 58 current-production replay of the frozen Mission 56 science policy."""

import argparse
import json
import time
from pathlib import Path

from astroscope.light_curve_transit_search import search_box_least_squares
from validation.celestial_coordinates import sha
from validation.light_curve_campaign import ROOT, run_benchmark

POLICY = "validation/manifests/physical_bls_policy_v1.json"
LEGACY = "validation/historical/mission57_light_curve_transit_search.py"


def run():
    start = time.monotonic()
    result = run_benchmark(bls_search=search_box_least_squares)
    result["runtime_seconds"] = time.monotonic() - start
    result["physical_search_policy"] = json.loads((ROOT / POLICY).read_text())
    result["environment"]["input_sha256"][POLICY] = sha(ROOT / POLICY)
    result["environment"]["source_sha256"]["validation/physical_bls_campaign.py"] = sha(
        Path(__file__)
    )
    if sha(ROOT / LEGACY) != "daa92537c91274c774379385de85dfce3862fda73ccd891c2001054ecd2fd55a":
        raise ValueError("Historical implementation was modified")
    prior = json.loads(
        (ROOT / "validation/results/light_curve_campaign_reference_run.json").read_text()
    )
    old = {(r["id"], r["stage"], r["algorithm"]): r for r in prior["results"]}
    result["previously_failed_trials"] = [
        {
            "id": r["id"],
            "stage": r["stage"],
            "algorithm": r["algorithm"],
            "previous_snr": old[(r["id"], r["stage"], r["algorithm"])]["best_candidate"][
                "depth_snr"
            ],
            "current_snr": r["best_candidate"]["depth_snr"] if r["best_candidate"] else None,
            "current_passed": r["passed"],
        }
        for r in result["results"]
        if not old[(r["id"], r["stage"], r["algorithm"])]["passed"]
    ]
    result["all_nine_previous_failures_pass"] = len(
        result["previously_failed_trials"]
    ) == 9 and all(r["current_passed"] for r in result["previously_failed_trials"])
    result["environment"]["input_sha256"][
        "validation/results/light_curve_campaign_reference_run.json"
    ] = sha(ROOT / "validation/results/light_curve_campaign_reference_run.json")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "trial_count",
                    "failed_trials",
                    "overall_passed",
                    "all_nine_previous_failures_pass",
                ]
            }
        )
    )
    return 0 if result["overall_passed"] and result["all_nine_previous_failures_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
