"""Mission 53 offline planetary validation against frozen independent references."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from astroscope.solar_system import calculate_solar_system_body
from validation.celestial_coordinates import circular_error, direction_error, sha
from validation.solar_lunar_twilight import frozen_environment

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "validation/manifests/planetary_positions_v1.json"
FIXTURE = "validation/fixtures/planetary_positions_v1.json"
POLICY = "validation/manifests/planetary_positions_policy_v1.json"
EOP = "validation/fixtures/solar_lunar_eop_v1.json"
GENERATOR = "validation/reference_generation/planetary_positions.py"
EXPECTED_MANIFEST_SHA256 = "cea2d25e82f965e88ac0cfbafa8083385f3370c67354bc1a5694a148db4a17d8"
PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune")


def validate_fixture(fixture, manifest, rows):
    cases = fixture["cases"]
    if len(cases) != manifest["case_count"] or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Invalid count or duplicate IDs")
    if dict(Counter(c["body"] for c in cases)) != manifest["body_counts"]:
        raise ValueError("Planet coverage mismatch")
    if set(manifest["body_counts"]) != set(PLANETS):
        raise ValueError("Unsupported planet inventory")
    days = {r["MJD"] for r in rows}
    if any(b["MJD"] - a["MJD"] != 1 for a, b in zip(rows[:-1], rows[1:], strict=True)):
        raise ValueError("Nonconsecutive IERS rows")
    for case in cases:
        dt = datetime.fromisoformat(case["utc"])
        if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0 or dt.year != 2024:
            raise ValueError("Reference date outside UTC 2024 scope")
        day = math.floor(40587 + dt.timestamp() / 86400)
        if day not in days or day + 1 not in days:
            raise ValueError("Reference date lacks bracketing IERS rows")
        if not all(math.isfinite(v) for v in case["reference"].values()):
            raise ValueError("Nonfinite reference")


def load_inputs(root=ROOT):
    if sha(root / MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads((root / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(root / path) != digest:
            raise ValueError(f"Input checksum mismatch: {path}")
    fixture = json.loads((root / FIXTURE).read_text())
    validate_fixture(fixture, manifest, json.loads((root / EOP).read_text())["rows"])
    return manifest, json.loads((root / POLICY).read_text()), fixture


def body_at(case):
    dt = datetime.fromisoformat(case["utc"])
    site = case["site"]
    return calculate_solar_system_body(
        case["body"],
        site["latitude_deg"],
        site["longitude_deg"],
        site["elevation_m"],
        "UTC",
        dt.date(),
        dt.time(),
        20,
    )


def sexagesimal(text, hours=False):
    sign = -1 if text.startswith("-") else 1
    a, b, c = map(float, text.lstrip("+-").split(":"))
    return sign * (a + b / 60 + c / 3600) * (15 if hours else 1)


def evaluate(case, policy):
    result = body_at(case)
    actual = asdict(result)
    ref = case["reference"]
    bound = policy["direction_arcsec"][case["body"]]
    solar = ref["solar_elongation_degrees"] < policy["solar_exclusion_deg"]
    metrics = {}
    exclusions = {}

    def metric(name, error, limit, reason=None):
        finite = math.isfinite(error)
        metrics[name] = {
            "absolute_error": abs(error) if finite else None,
            "bound": limit,
            "eligible": reason is None,
            "passed": finite and (reason is not None or abs(error) <= limit),
        }
        if reason:
            exclusions[name] = reason

    angular_reason = "solar_proximity" if solar else None
    metric(
        "equatorial_direction_arcsec",
        direction_error(
            result.declination_degrees,
            result.right_ascension_degrees,
            ref["dec_degrees"],
            ref["ra_degrees"],
        ),
        bound,
        angular_reason,
    )
    metric(
        "horizontal_direction_arcsec",
        direction_error(
            result.altitude_degrees,
            result.azimuth_degrees,
            ref["altitude_degrees"],
            ref["azimuth_degrees"],
        ),
        bound,
        angular_reason,
    )
    metric(
        "declination_arcsec",
        (result.declination_degrees - ref["dec_degrees"]) * 3600,
        bound,
        angular_reason,
    )
    metric(
        "right_ascension_arcsec",
        circular_error(result.right_ascension_degrees, ref["ra_degrees"], 360) * 3600,
        bound / max(math.cos(math.radians(ref["dec_degrees"])), math.cos(math.radians(85))),
        angular_reason or ("equatorial_pole" if abs(ref["dec_degrees"]) > 85 else None),
    )
    metric(
        "altitude_arcsec",
        (result.altitude_degrees - ref["altitude_degrees"]) * 3600,
        bound,
        angular_reason,
    )
    metric(
        "azimuth_arcsec",
        circular_error(result.azimuth_degrees, ref["azimuth_degrees"], 360) * 3600,
        bound * policy["azimuth_projection_factor"],
        angular_reason
        or (
            "zenith_nadir"
            if abs(ref["altitude_degrees"]) > policy["azimuth_excluded_abs_altitude_deg"]
            else None
        ),
    )
    for key, extra in [
        ("solar_elongation_degrees", "sun_separation_additional_arcsec"),
        ("moon_separation_degrees", "moon_separation_additional_arcsec"),
    ]:
        metric(
            key.replace("_degrees", "_arcsec"),
            (actual[key] - ref[key]) * 3600,
            bound + policy[extra],
            angular_reason,
        )
    metric(
        "distance_km", result.distance_km - ref["distance_km"], policy["distance_km"][case["body"]]
    )
    metric(
        "distance_au",
        result.distance_au - ref["distance_au"],
        policy["distance_km"][case["body"]] / policy["au_km"],
    )
    metric(
        "au_km_consistency_relative",
        result.distance_km / (result.distance_au * policy["au_km"]) - 1,
        policy["distance_unit_relative_tolerance"],
    )
    metric(
        "ra_format_arcsec",
        circular_error(
            sexagesimal(result.right_ascension_hms, True), result.right_ascension_degrees, 360
        )
        * 3600,
        policy["ra_format_arcsec"],
    )
    metric(
        "dec_format_arcsec",
        (sexagesimal(result.declination_dms) - result.declination_degrees) * 3600,
        policy["dec_format_arcsec"],
    )
    expected_horizon = ref["altitude_degrees"] > 0
    expected_status = (
        "below_horizon"
        if ref["altitude_degrees"] <= 0
        else "low_altitude"
        if ref["altitude_degrees"] < 20
        else "observable"
    )
    actual_status = (
        "below_horizon"
        if result.altitude_degrees <= 0
        else "low_altitude"
        if result.altitude_degrees < 20
        else "observable"
    )
    directions = (
        "north",
        "northeast",
        "east",
        "southeast",
        "south",
        "southwest",
        "west",
        "northwest",
    )
    expected_cardinal = directions[int((ref["azimuth_degrees"] + 22.5) // 45) % 8]
    actual_cardinal = directions[int((result.azimuth_degrees + 22.5) // 45) % 8]
    guard = bound / 3600
    classes = {}
    for name, uncertain, agrees in [
        (
            "horizon",
            abs(ref["altitude_degrees"]) <= guard,
            result.is_above_horizon == expected_horizon,
        ),
        (
            "visibility",
            min(abs(ref["altitude_degrees"]), abs(ref["altitude_degrees"] - 20)) <= guard,
            result.status == expected_status,
        ),
        (
            "cardinal",
            abs(ref["altitude_degrees"]) > 85
            or min(circular_error(ref["azimuth_degrees"], 22.5 + i * 45, 360) for i in range(8))
            <= guard * 12,
            result.cardinal_direction == expected_cardinal,
        ),
    ]:
        classes[name] = {
            "status": "excluded_solar"
            if solar
            else "boundary_indeterminate"
            if uncertain
            else "agrees"
            if agrees
            else "failed",
            "raw_agreement": agrees,
        }
    contracts = {
        "body_identity": result.body_key == case["body"],
        "ephemeris": result.ephemeris_name == "builtin",
        "utc": result.utc_datetime_iso
        == datetime.fromisoformat(case["utc"]).isoformat(timespec="seconds"),
        "horizon_internal": result.is_above_horizon == (result.altitude_degrees > 0),
        "visibility_internal": result.status == actual_status,
        "cardinal_internal": result.cardinal_direction == actual_cardinal,
        "valid_ranges": all(
            math.isfinite(actual[k])
            for k in (
                "right_ascension_degrees",
                "declination_degrees",
                "altitude_degrees",
                "azimuth_degrees",
                "distance_au",
                "distance_km",
                "solar_elongation_degrees",
                "moon_separation_degrees",
                "moon_illumination_fraction",
            )
        )
        and 0 <= result.right_ascension_degrees < 360
        and -90 <= result.declination_degrees <= 90
        and -90 <= result.altitude_degrees <= 90
        and 0 <= result.azimuth_degrees < 360
        and result.distance_au > 0
        and result.distance_km > 0
        and 0 <= result.solar_elongation_degrees <= 180
        and 0 <= result.moon_separation_degrees <= 180
        and 0 <= result.moon_illumination_fraction <= 1,
    }
    passed = (
        all(m["passed"] for m in metrics.values())
        and all(contracts.values())
        and all(c["status"] != "failed" for c in classes.values())
    )
    return {
        "id": case["id"],
        "body": case["body"],
        "category": case["category"],
        "actual": actual,
        "reference": ref,
        "metrics": metrics,
        "exclusions": exclusions,
        "classifications": classes,
        "contracts": contracts,
        "passed": passed,
    }


def summarize(rows):
    summary = {}
    for key in rows[0]["metrics"]:
        admitted = [(r["id"], r["metrics"][key]) for r in rows if r["metrics"][key]["eligible"]]
        pairs = [(i, m["absolute_error"]) for i, m in admitted if m["absolute_error"] is not None]
        values = [v for _, v in pairs]
        worst = max(pairs, key=lambda item: item[1]) if pairs else (None, None)
        summary[key] = {
            "eligible_count": len(admitted),
            "finite_count": len(values),
            "excluded_count": len(rows) - len(admitted),
            "failed_count": sum(not m["passed"] for _, m in admitted),
            "maximum": worst[1],
            "worst_case": worst[0],
            "median": statistics.median(values) if values else None,
            "rms": math.sqrt(sum(v * v for v in values) / len(values)) if values else None,
        }
    return summary


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    manifest, policy, fixture = load_inputs()
    with frozen_environment():
        rows = [evaluate(c, policy) for c in fixture["cases"]]
    sources = [
        "src/astroscope/solar_system.py",
        "src/astroscope/observer.py",
        "src/astroscope/visibility.py",
        "validation/planetary_positions.py",
        "validation/celestial_coordinates.py",
        "validation/solar_lunar_twilight.py",
    ]
    return {
        "schema_version": "1.0",
        "mission": 53,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(rows),
        "failed_cases": sum(not r["passed"] for r in rows),
        "overall_passed": all(r["passed"] for r in rows),
        "policy": policy,
        "body_counts": dict(Counter(r["body"] for r in rows)),
        "category_counts": dict(Counter(r["category"] for r in rows)),
        "summary": summarize(rows),
        "summary_by_body": {b: summarize([r for r in rows if r["body"] == b]) for b in PLANETS},
        "classification_counts": dict(
            Counter(c["status"] for r in rows for c in r["classifications"].values())
        ),
        "environment": {
            "implementation_commit": os.environ.get(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.environ.get(
                "ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")
            ),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "versions": {
                p: importlib.metadata.version(p)
                for p in ("astropy", "pyerfa", "numpy", "scipy", "astropy-iers-data", "tzdata")
            },
            "source_sha256": {p: sha(ROOT / p) for p in sources},
            "input_sha256": {**manifest["files"], MANIFEST: sha(ROOT / MANIFEST)},
            "network_required": False,
            "runtime_reference_imports": False,
            "randomness": "none",
        },
        "scientific_status": "Bounded UTC-2024 planner-scale cross-model comparison; "
        "no covariance or universal accuracy guarantee",
        "physical_arrival_qualification_changed": False,
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
