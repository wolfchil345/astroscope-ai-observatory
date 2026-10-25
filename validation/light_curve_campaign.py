"""Offline LS/BLS recovery and false-positive campaign; all outcomes retained."""

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import warnings
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from astroscope.light_curve import LightCurveError, LightCurveMetadata, build_light_curve
from astroscope.light_curve_period import analyze_lomb_scargle
from astroscope.light_curve_processing import (
    detrend_light_curve,
    normalize_light_curve,
    sigma_clip_light_curve,
)
from astroscope.light_curve_transit_search import search_box_least_squares
from validation.celestial_coordinates import sha
from validation.light_curve_references import exact_box_snr, ls_power, raw_checksum, wilson

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "validation/fixtures/light_curve_campaign_v1.json"
POLICY = "validation/manifests/light_curve_campaign_policy_v1.json"
MANIFEST = "validation/manifests/light_curve_campaign_v1.json"


def load_inputs():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    fixture = json.loads((ROOT / FIXTURE).read_text())
    assert len(fixture["cases"]) == 42 and len({c["id"] for c in fixture["cases"]}) == 42
    published = fixture["cases"][-1]
    raw = (ROOT / "validation/fixtures/published/kplr006922244-2010078095331_llc.fits").read_bytes()
    spans = published["provenance"]["hdu_integrity"]
    assert spans[0]["start"] == 0 and spans[-1]["end"] == len(raw)
    for span in spans:
        if raw_checksum(raw[span["start"] : span["end"]]) != 0xFFFFFFFF:
            raise ValueError("Raw FITS HDU checksum mismatch")
    return json.loads((ROOT / POLICY).read_text()), fixture


def build(case):
    return build_light_curve(
        metadata=LightCurveMetadata(case["id"], "flux", case["time_standard"]),
        times=case["times"],
        values=case["values"],
        uncertainties=case["uncertainties"],
    )


def processed(case, stage, policy):
    curve = normalize_light_curve(build(case)).light_curve
    if stage == "linear_detrended":
        curve = detrend_light_curve(curve, degree=1).light_curve
    elif stage == "sigma_clipped":
        curve = sigma_clip_light_curve(curve, sigma=policy["sigma_clip"]).light_curve
    return curve


def classify_period(period, truth, goal):
    if truth is None:
        return "no_periodic_truth"
    if abs(period / truth - 1) <= goal:
        return "fundamental"
    for label, candidate in [
        ("half_period", truth / 2),
        ("double_period", truth * 2),
        ("daily_alias", 1 / abs(1 / truth - 1)),
        ("daily_alias", 1 / (1 / truth + 1)),
    ]:
        if abs(period / candidate - 1) <= goal:
            return label
    return "other"


def evaluate(case, stage, algorithm, policy):
    required = stage != "sigma_clipped" and (
        (
            case["regime"] == "uniform"
            and (case["kind"], algorithm) in [("sine", "ls"), ("box", "bls")]
        )
        or (case["kind"] == "published_transit" and algorithm == "bls")
    )
    row = {
        "id": case["id"],
        "kind": case["kind"],
        "regime": case["regime"],
        "stage": stage,
        "algorithm": algorithm,
        "required_recovery": required,
        "input_count": len(case["times"]),
        "truth_period": case.get("injected_period") or case.get("published_period"),
        "passed": False,
        "exception": None,
        "best_candidate": None,
        "recovered": False,
        "threshold_flag": False,
        "reference": {},
        "warnings": [],
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            curve = processed(case, stage, policy)
            times = [p.time for p in curve.points]
            values = [p.value for p in curve.points]
            errors = [p.uncertainty for p in curve.points]
            row["retained_count"] = len(times)
            row["removed_count"] = len(case["times"]) - len(times)
            row["time_standard"] = curve.metadata.time_standard
            kwargs = dict(
                minimum_period=policy["minimum_period_days"],
                maximum_period=policy["maximum_period_days"],
                candidate_count=5,
            )
            if algorithm == "ls":
                result = analyze_lomb_scargle(
                    curve, **kwargs, samples_per_peak=policy["ls_samples_per_peak"]
                )
                best = result.best_candidate
                reference = ls_power(times, values, errors, best.frequency)
                residual = None if reference is None else abs(best.power - reference)
                row["reference"] = {
                    "direct_weighted_power": reference,
                    "absolute_power_error": residual,
                }
                numeric_ok = reference is None or residual <= policy["ls_power_absolute_goal"]
                row["threshold_flag"] = (
                    best.false_alarm_probability is not None
                    and best.false_alarm_probability < policy["ls_fap_flag_threshold"]
                )
            else:
                result = search_box_least_squares(
                    curve,
                    **kwargs,
                    durations=policy["bls_durations_days"],
                    objective="snr",
                    oversample=policy["bls_oversample"],
                    frequency_factor=policy["bls_frequency_factor"],
                )
                best = result.best_candidate
                exact = exact_box_snr(times, values, errors, best.period, best.duration)
                row["reference"] = {
                    "exact_fixed_period_duration_snr": exact,
                    "reported_minus_exact_snr": best.depth_snr - exact,
                    "phase_search_efficiency": best.depth_snr / exact if exact > 0 else None,
                }
                numeric_ok = best.depth_snr <= exact + policy["bls_exact_snr_upper_slack"]
                row["threshold_flag"] = best.depth_snr >= policy["bls_snr_flag_threshold"]
                row["depth_to_injected_ratio"] = (
                    best.depth / case["injected_depth"] if case.get("injected_depth") else None
                )
            row["best_candidate"] = asdict(best)
            row["candidates"] = [asdict(c) for c in result.candidates]
            row["grid_count"] = len(result.samples)
            row["period_outcome"] = classify_period(
                best.period, row["truth_period"], policy["relative_period_goal"]
            )
            row["recovered"] = row["period_outcome"] == "fundamental"
            row["numeric_reference_passed"] = numeric_ok
            row["passed"] = numeric_ok and (not required or row["recovered"])
            if case["kind"] == "constant":
                row["threshold_flag"] = False
        except LightCurveError as error:
            row["exception"] = {"type": type(error).__name__, "message": str(error)}
            row["passed"] = case["kind"] == "constant"
        row["warnings"] = [str(w.message) for w in caught]
    return row


def summarize_nulls(rows):
    summaries = []
    for kind in ["white_null", "red_null"]:
        for stage in ["normalized", "linear_detrended", "sigma_clipped"]:
            for algorithm in ["ls", "bls"]:
                admitted = [
                    r
                    for r in rows
                    if (r["kind"], r["stage"], r["algorithm"]) == (kind, stage, algorithm)
                ]
                k = sum(r["threshold_flag"] for r in admitted)
                summaries.append(
                    {
                        "kind": kind,
                        "stage": stage,
                        "algorithm": algorithm,
                        "flagged": k,
                        "total": len(admitted),
                        "exceptions": sum(r["exception"] is not None for r in admitted),
                        "fraction": k / len(admitted),
                        "wilson_95": wilson(k, len(admitted)),
                    }
                )
    return summaries


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    policy, fixture = load_inputs()
    rows = [
        evaluate(c, stage, algorithm, policy)
        for c in fixture["cases"]
        for stage in policy["stages"]
        for algorithm in ["ls", "bls"]
    ]
    sources = [
        "src/astroscope/" + p + ".py"
        for p in [
            "light_curve",
            "light_curve_period",
            "light_curve_transit_search",
            "light_curve_processing",
        ]
    ]
    sources += [
        "validation/light_curve_campaign.py",
        "validation/light_curve_references.py",
        "validation/celestial_coordinates.py",
    ]
    return {
        "mission": 56,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "input_case_count": 42,
        "trial_count": len(rows),
        "failed_trials": sum(not r["passed"] for r in rows),
        "overall_passed": all(r["passed"] for r in rows),
        "required_recovery_count": sum(r["required_recovery"] for r in rows),
        "required_recovery_successes": sum(r["required_recovery"] and r["recovered"] for r in rows),
        "period_outcomes": dict(Counter(r.get("period_outcome", "rejected") for r in rows)),
        "null_summary": summarize_nulls(rows),
        "policy": policy,
        "physical_arrival_qualification_changed": False,
        "universal_fap_calibration_established": False,
        "published_provenance": fixture["cases"][-1]["provenance"],
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {x: importlib.metadata.version(x) for x in ["astropy", "numpy", "scipy"]},
            "source_sha256": {x: sha(ROOT / x) for x in sources},
            "input_sha256": {x: sha(ROOT / x) for x in [FIXTURE, POLICY, MANIFEST]},
            "network_required": False,
        },
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ["trial_count", "failed_trials", "overall_passed"]}))
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
