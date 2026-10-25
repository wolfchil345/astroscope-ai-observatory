"""Same-library diagnostic only; independent evidence remains the exact phase oracle."""

import argparse
import json
import warnings
from pathlib import Path

from astropy.timeseries import BoxLeastSquares

from validation.celestial_coordinates import sha
from validation.light_curve_campaign import ROOT, load_inputs, processed
from validation.light_curve_references import exact_box_snr


def diagnose(record):
    policy, fixture = load_inputs()
    cases = {c["id"]: c for c in fixture["cases"]}
    rows = []
    for row in record["results"]:
        if row["algorithm"] != "bls" or row["passed"]:
            continue
        curve = processed(cases[row["id"]], row["stage"], policy)
        t = [p.time for p in curve.points]
        y = [p.value for p in curve.points]
        e = [p.uncertainty for p in curve.points]
        best = row["best_candidate"]
        exact = exact_box_snr(t, y, e, best["period"], best["duration"])
        model = BoxLeastSquares(t, y, dy=e)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            slow = model.power(
                [best["period"]], [best["duration"]], method="slow", oversample=100, objective="snr"
            )
            fast = model.power(
                [best["period"]], [best["duration"]], method="fast", oversample=100, objective="snr"
            )
        rows.append(
            {
                "id": row["id"],
                "warnings": [str(w.message) for w in caught],
                "stage": row["stage"],
                "period": best["period"],
                "duration": best["duration"],
                "production_snr": best["depth_snr"],
                "independent_exact_snr": exact,
                "slow_100_snr": float(slow.depth_snr[0]),
                "fast_100_snr": float(fast.depth_snr[0]),
                "slow_within_independent_bound": float(slow.depth_snr[0]) <= exact + 1e-5,
            }
        )
    return {
        "mission": 56,
        "execution_target": "historical pre-Mission-58 fast search; not current production",
        "campaign_environment": record["environment"],
        "diagnostic_source_sha256": sha(ROOT / "validation/light_curve_bls_diagnostic.py"),
        "independent_oracle": "validation.light_curve_references.exact_box_snr",
        "same_library_diagnostic_not_independent_reference": True,
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            diagnose(json.loads(args.record.read_text())), indent=2, sort_keys=True, allow_nan=False
        )
        + "\n"
    )
