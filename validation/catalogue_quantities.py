"""Offline Mission 60 catalogue baseline; scientific acceptance and replay are distinct."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

from astroscope import exoplanet_catalog as exo
from astroscope import gaia_catalog as gaia
from astroscope.exoplanet_visuals import calculate_trapezoid_transit_flux
from astroscope.gaia_visuals import calculate_local_offsets_deg

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "validation/fixtures/catalogue_quantities_v1.json"
POLICY = "validation/manifests/catalogue_quantities_policy_v1.json"
MANIFEST = "validation/manifests/catalogue_quantities_v1.json"
OBSERVATIONS = "validation/fixtures/catalogue_quantities_observed_v1.json"
SOURCE_PATHS = [
    "src/astroscope/gaia_catalog.py",
    "src/astroscope/gaia_visuals.py",
    "src/astroscope/exoplanet_catalog.py",
    "src/astroscope/exoplanet_visuals.py",
    "validation/catalogue_quantities.py",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_inputs():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    fixture = json.loads((ROOT / FIXTURE).read_text())
    ids = [c["id"] for c in fixture["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs")
    return json.loads((ROOT / POLICY).read_text()), fixture


def decode(value):
    return None if value is None else float(value)


def csv_text(row):
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(row))
    writer.writeheader()
    writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return stream.getvalue()


def source_at(ra, dec):
    values = dict.fromkeys(f.name for f in fields(gaia.GaiaSource))
    values.update(
        source_id=1, designation="synthetic", ra_deg=ra, dec_deg=dec, angular_distance_deg=0
    )
    return gaia.GaiaSource(**values)


def call_production(case):
    family, inputs = case["family"], case["inputs"]
    scalar_functions = {
        "distance": gaia.estimate_naive_distance_parsecs,
        "absolute_g": gaia.calculate_absolute_g_magnitude,
        "density": exo.calculate_planet_density_g_cm3,
        "depth": exo.calculate_transit_depth_ppm,
        "probability": exo.calculate_transit_probability_percent,
        "screen": exo.classify_temperate_candidate,
    }
    if family in scalar_functions:
        return scalar_functions[family](*map(decode, inputs))
    if family == "gaia_row":
        row = dict(source_id="1", ra="0", dec="60", angular_distance_deg="0", **inputs)
        obj = gaia.parse_gaia_csv(csv_text(row))[0]
        return {k: getattr(obj, k) for k in case["expected"]}
    if family == "exoplanet_row":
        row = dict(pl_name="synthetic b", hostname="synthetic", **inputs)
        obj = exo.parse_exoplanet_csv(csv_text(row))[0]
        return {k: getattr(obj, k) for k in case["expected"]}
    if family == "offsets":
        ra, dec, cra, cdec = map(decode, inputs)
        return list(
            calculate_local_offsets_deg(source_at(ra, dec), center_ra_deg=cra, center_dec_deg=cdec)
        )
    if family == "trapezoid":
        return list(
            calculate_trapezoid_transit_flux(
                list(map(decode, inputs["times"])),
                depth_ppm=decode(inputs["depth"]),
                duration_hours=decode(inputs["duration"]),
                ingress_fraction=decode(inputs["ingress"]),
            )
        )
    if family == "constant":
        return getattr(exo, inputs[0])
    if family == "radius_coherence":
        # Compare implied SI radii from the two separate production conversions.
        depth_radius = Decimal(str(exo.EARTH_RADIUS_IN_SOLAR_RADII)) * Decimal("695700000")
        probability_radius = Decimal(str(exo.EARTH_RADIUS_IN_AU)) * Decimal("149597870700")
        return float(depth_radius - probability_radius)
    raise ValueError(f"Unknown family: {family}")


def serializable(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, (tuple, list)):
        return [serializable(x) for x in value]
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    return value


def matches(actual, expected, *, atol, rtol):
    """Recursive finite comparison; booleans/labels/unknowns are never numeric tolerances."""
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and actual.keys() == expected.keys()
            and all(matches(actual[k], v, atol=atol, rtol=rtol) for k, v in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, (list, tuple))
            and len(actual) == len(expected)
            and all(
                matches(a, b, atol=atol, rtol=rtol) for a, b in zip(actual, expected, strict=True)
            )
        )
    if isinstance(actual, bool) or isinstance(expected, bool) or expected is None:
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)):
        try:
            reference = float(expected)
        except (TypeError, ValueError):
            return False
        return (
            math.isfinite(actual)
            and math.isfinite(reference)
            and abs(actual - reference) <= (atol + rtol * abs(reference))
        )
    return actual == expected


def assess(case, actual, exception, policy):
    requirement, family = case["requirement"], case["family"]
    controlled_rejection = exception is not None and issubclass(exception, ValueError)
    if requirement == "reject":
        return controlled_rejection
    if requirement == "reject_or_null":
        return controlled_rejection or (exception is None and actual is None)
    if requirement == "value_or_reject" and controlled_rejection:
        return True
    if exception is not None:
        return False
    atol = float(case.get("absolute_tolerance", policy["numeric_absolute_tolerance"]))
    rtol = policy["numeric_relative_tolerance"]
    if "absolute_tolerance" in case:
        rtol = 0
    elif family == "offsets":
        atol, rtol = policy["offset_absolute_tolerance_deg"], 0
    elif family == "trapezoid":
        atol, rtol = policy["flux_absolute_tolerance"], 0
    return matches(actual, case["expected"], atol=atol, rtol=rtol)


def evaluate(case, policy):
    actual, exception = None, None
    try:
        actual = call_production(case)
    except (ValueError, OverflowError, ZeroDivisionError, TypeError) as error:
        exception = type(error)
    row = {
        "id": case["id"],
        "family": case["family"],
        "group": case["group"],
        "actual": serializable(actual),
        "exception": None if exception is None else exception.__name__,
        "expected": case["expected"],
        "requirement": case["requirement"],
        "passed": assess(case, actual, exception, policy),
    }
    if "diagnostic" in case:
        ref = case["diagnostic"]["spherical_log_map_deg"]
        valid = exception is None and all(math.isfinite(x) for x in actual)
        row["projection_diagnostic"] = dict(
            case["diagnostic"],
            error_arcsec=math.hypot(actual[0] - ref[0], actual[1] - ref[1]) * 3600
            if valid
            else None,
        )
    if "exterior_circular_orbit" in case:
        row["exterior_circular_orbit"] = case["exterior_circular_orbit"]
    return row


def summarize_projection(rows):
    grouped = defaultdict(list)
    for row in rows:
        if "projection_diagnostic" in row:
            d = row["projection_diagnostic"]
            grouped[(d["radius_deg"], abs(d["center_dec_deg"]))].append(
                (d["error_arcsec"], row["id"])
            )
    return [
        {
            "cone_radius_deg": key[0],
            "absolute_center_declination_deg": key[1],
            "case_count": len(values),
            "maximum_sampled_error_arcsec": max(values)[0],
            "worst_case_id": max(values)[1],
            "continuous_bound": False,
        }
        for key, values in sorted(grouped.items())
    ]


def run_benchmark():
    policy, fixture = load_inputs()
    rows = [evaluate(c, policy) for c in fixture["cases"]]
    return {
        "mission": 60,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(rows),
        "failed_cases": sum(not r["passed"] for r in rows),
        "failed_case_ids": [r["id"] for r in rows if not r["passed"]],
        "overall_passed": all(r["passed"] for r in rows),
        "family_counts": dict(Counter(r["family"] for r in rows)),
        "family_failure_counts": dict(Counter(r["family"] for r in rows if not r["passed"])),
        "projection_summary": summarize_projection(rows),
        "independent_definition_diagnostics": fixture["independent_definition_diagnostics"],
        "capped_non_exterior_probability_cases": sum(
            r.get("exterior_circular_orbit") is False for r in rows
        ),
        "physical_arrival_qualification_changed": False,
        "observational_calibration_established": False,
        "phase_2_exit_approved": False,
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "versions": {x: importlib.metadata.version(x) for x in ["astropy", "numpy", "plotly"]},
            "source_sha256": {p: sha(ROOT / p) for p in SOURCE_PATHS},
            "input_sha256": {p: sha(ROOT / p) for p in [FIXTURE, POLICY, MANIFEST]},
            "network_required": False,
            "randomness": "none",
        },
        "results": rows,
    }


def audit_observations(result):
    """Compare ALL successes, failures and diagnostics to one observed baseline.

    This is a reproducibility check; its tolerance never changes scientific goals.
    """
    baseline = json.loads((ROOT / OBSERVATIONS).read_text())
    current = {key: result[key] for key in baseline["observations"]}
    passed = matches(current, baseline["observations"], atol=2e-9, rtol=2e-12)
    expected_inputs = baseline["input_sha256"]
    passed = passed and all(sha(ROOT / p) == h for p, h in expected_inputs.items())
    return {
        "passed": passed,
        "baseline_sha256": sha(ROOT / OBSERVATIONS),
        "meaning": "Full-record regression reproduction, NOT scientific acceptance",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--audit-known-discrepancies",
        action="store_true",
        help="Exit on complete observation reproduction; retain scientific failures",
    )
    args = parser.parse_args()
    result = run_benchmark()
    if args.audit_known_discrepancies:
        result["observation_audit"] = audit_observations(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ["case_count", "failed_cases", "overall_passed"]}))
    if args.audit_known_discrepancies:
        print(json.dumps(result["observation_audit"]))
        return 0 if result["observation_audit"]["passed"] else 1
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
