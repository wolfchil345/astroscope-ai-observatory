"""Offline Mission 54 window and sampling validation with frozen independent references."""

import argparse
import importlib.metadata
import json
import math
import os
import platform
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import ObserverSite, TransitTarget, analyze_transit_visibility
from validation.celestial_coordinates import sha
from validation.solar_lunar_twilight import frozen_environment

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "validation/fixtures/visibility_sampling_v1.json"
POLICY = "validation/manifests/visibility_sampling_policy_v1.json"
MANIFEST = "validation/manifests/visibility_sampling_v1.json"


def load_inputs():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    fixture = json.loads((ROOT / FIXTURE).read_text())
    if len(fixture["windows"]) != 16 or len({w["id"] for w in fixture["windows"]}) != 16:
        raise ValueError("Unexpected window corpus")
    return json.loads((ROOT / POLICY).read_text()), fixture


def classification_bounds(grid, policy):
    """Independent lower/upper sample-count fractions with angular boundary guards."""
    a = policy["minimum_altitude_degrees"]
    d = policy["darkness_sun_altitude_degrees"]
    ea = policy["tolerances_degrees"]["target_altitude_degrees"]
    ed = policy["tolerances_degrees"]["sun_altitude_degrees"]
    alt = grid["target_altitude_degrees"]
    sun = grid["sun_altitude_degrees"]
    n = len(alt)
    sure_a = [x > a + ea for x in alt]
    possible_a = [x >= a - ea for x in alt]
    sure_d = [x < d - ed for x in sun]
    possible_d = [x <= d + ed for x in sun]
    return {
        name: [sum(lo) / n, sum(hi) / n]
        for name, lo, hi in [
            ("altitude", sure_a, possible_a),
            ("dark", sure_d, possible_d),
            (
                "observable",
                [a and b for a, b in zip(sure_a, sure_d, strict=True)],
                [a and b for a, b in zip(possible_a, possible_d, strict=True)],
            ),
        ]
    }


def nominal_fraction(grid, policy, event_only=None):
    indices = [
        i
        for i, jd in enumerate(grid["jd"])
        if event_only is None or event_only[0] <= jd <= event_only[1]
    ]
    return (
        sum(
            grid["target_altitude_degrees"][i] >= policy["minimum_altitude_degrees"]
            and grid["sun_altitude_degrees"][i] <= policy["darkness_sun_altitude_degrees"]
            for i in indices
        )
        / len(indices)
        if indices
        else None
    )


def evaluate(window, count, policy):
    event = TransitEvent(**window["event"])
    result = analyze_transit_visibility(
        event,
        ObserverSite(**window["site"]),
        TransitTarget(**window["target"]),
        sample_count=count,
        minimum_altitude_degrees=policy["minimum_altitude_degrees"],
        darkness_sun_altitude_degrees=policy["darkness_sun_altitude_degrees"],
    )
    ref = window["grids"][str(count)]
    errors = {
        key: [abs(getattr(s, key) - v) for s, v in zip(result.samples, ref[key], strict=True)]
        for key in policy["tolerances_degrees"]
    }
    contracts = {
        "grid": [s.julian_date for s in result.samples] == ref["jd"],
        "nearest_midpoint": result.midpoint_sample
        == min(result.samples, key=lambda s: abs(s.julian_date - event.mid_transit_jd)),
        "sample_flags": all(
            s.target_above_minimum_altitude
            == (s.target_altitude_degrees >= policy["minimum_altitude_degrees"])
            and s.is_astronomical_dark
            == (s.sun_altitude_degrees <= policy["darkness_sun_altitude_degrees"])
            for s in result.samples
        ),
        "full_sample_flag": result.full_observation_window_visible
        == all(s.is_observable for s in result.samples),
        "extrema": result.minimum_target_altitude_degrees
        == min(s.target_altitude_degrees for s in result.samples)
        and result.maximum_target_altitude_degrees
        == max(s.target_altitude_degrees for s in result.samples),
        "moon_minimum": result.minimum_moon_separation_degrees
        == min(s.moon_separation_degrees for s in result.samples),
        "maximum_airmass": result.maximum_airmass
        == max((s.airmass for s in result.samples if s.airmass is not None), default=None),
    }
    bounds = classification_bounds(ref, policy)
    fractions = {key: getattr(result, key + "_sample_fraction") for key in bounds}
    for key, (lo, hi) in bounds.items():
        contracts[key + "_reference_fraction"] = lo <= fractions[key] <= hi
    dense = window["grids"][str(policy["dense_reference_count"])]
    passed = all(contracts.values()) and all(
        math.isfinite(x) and x <= policy["tolerances_degrees"][key]
        for key, values in errors.items()
        for x in values
    )
    return {
        "id": window["id"],
        "sample_count": count,
        "passed": passed,
        "errors_degrees": errors,
        "contracts": contracts,
        "fraction_bounds": bounds,
        "fractions": fractions,
        "samples": [asdict(s) for s in result.samples],
        "nearest_midpoint_offset_seconds": (
            result.midpoint_sample.julian_date - event.mid_transit_jd
        )
        * 86400,
        "dense_reference_observable_fraction": nominal_fraction(dense, policy),
        "sample_minus_dense_fraction": fractions["observable"] - nominal_fraction(dense, policy),
        "dense_reference_event_fraction": nominal_fraction(
            dense, policy, (event.ingress_jd, event.egress_jd)
        ),
        "continuous_coverage_certified": False,
    }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    policy, fixture = load_inputs()
    with frozen_environment():
        rows = [evaluate(w, n, policy) for w in fixture["windows"] for n in policy["sample_counts"]]
    sources = [
        "src/astroscope/transit_visibility.py",
        "src/astroscope/transit_timing.py",
        "src/astroscope/transit_scheduler.py",
        "validation/visibility_sampling.py",
        "validation/solar_lunar_twilight.py",
        "validation/celestial_coordinates.py",
    ]
    return {
        "mission": 54,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(rows),
        "sample_count": sum(r["sample_count"] for r in rows),
        "failed_cases": sum(not r["passed"] for r in rows),
        "overall_passed": all(r["passed"] for r in rows),
        "policy": policy,
        "physical_arrival_qualification_changed": False,
        "continuous_coverage_certified": False,
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {
                p: importlib.metadata.version(p)
                for p in ("astropy", "numpy", "pyerfa", "astropy-iers-data")
            },
            "source_sha256": {p: sha(ROOT / p) for p in sources},
            "input_sha256": {p: sha(ROOT / p) for p in (FIXTURE, POLICY, MANIFEST)},
            "network_required": False,
            "reference_imports_required": False,
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
    print(json.dumps({k: result[k] for k in ("case_count", "failed_cases", "overall_passed")}))
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
