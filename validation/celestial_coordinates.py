"""Offline Mission 33 validation of public APIs against frozen independent references."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import astropy.units as u
from astropy.table import QTable
from astropy.utils import iers

from astroscope.coordinates import create_icrs_coordinate
from astroscope.observer import calculate_astronomical_time, create_earth_location
from astroscope.visibility import calculate_horizontal_coordinates

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation/manifests/celestial_coordinates_v1.json"
FIXTURE = ROOT / "validation/fixtures/celestial_coordinates_v1.json"
EOP = ROOT / "validation/fixtures/celestial_eop_v1.json"
EXPECTED_MANIFEST_SHA256 = "d9a5d2c37cea081243c6ea9a3267408d323ae662af77d5e35be1d59fdfff39e8"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads(MANIFEST.read_text())
    for name, digest in manifest["files"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Input checksum mismatch: {name}")
    fixture = json.loads(FIXTURE.read_text())
    for key, count_key in [
        ("cases", "expected_case_count"),
        ("invalid_inputs", "expected_invalid_input_count"),
    ]:
        cases = fixture[key]
        if len(cases) != manifest[count_key] or len({c["id"] for c in cases}) != len(cases):
            raise ValueError("Invalid case count or duplicate identifiers")
    generator = ROOT / "validation/reference_generation/celestial_coordinates.py"
    if sha(generator) != fixture["reference"]["generator_sha256"]:
        raise ValueError("Reference generator checksum mismatch")
    rows = json.loads(EOP.read_text())["rows"]
    days = {r["MJD"] for r in rows}
    for case in fixture["cases"]:
        dt = datetime.fromisoformat(case["utc"])
        if dt.utcoffset().total_seconds() != 0:
            raise ValueError("Fixture instants must be UTC")
        day = math.floor(40587 + dt.timestamp() / 86400)
        if day not in days or day + 1 not in days:
            raise ValueError("Observation instant lacks consecutive bracketing IERS rows")
    return manifest, fixture


@contextmanager
def fixed_earth_orientation() -> Iterator[None]:
    """Install committed observations without downloads, restoring state even on error."""
    rows = json.loads(EOP.read_text())["rows"]
    table = QTable()
    for key, unit in [("MJD", u.day), ("UT1_UTC", u.s), ("PM_x", u.arcsec), ("PM_y", u.arcsec)]:
        table[key] = [r[key] for r in rows] * unit
    with (
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("iers_degraded_accuracy", "error"),
        iers.earth_orientation_table.set(iers.IERS(table)),
    ):
        yield


def circular_error(actual: float, expected: float, period: float) -> float:
    return abs((actual - expected + period / 2) % period - period / 2)


def direction_error(alt: float, az: float, ref_alt: float, ref_az: float) -> float:
    """Stable great-circle separation, including near zenith; never mask NaN."""
    if not all(math.isfinite(v) for v in [alt, az, ref_alt, ref_az]):
        return math.nan
    a, b = math.radians(alt), math.radians(ref_alt)
    h = (
        math.sin((a - b) / 2) ** 2
        + math.cos(a) * math.cos(b) * math.sin(math.radians(az - ref_az) / 2) ** 2
    )
    return math.degrees(2 * math.asin(math.sqrt(min(1, max(0, h))))) * 3600


def case_arguments(case: dict[str, Any]) -> dict[str, Any]:
    dt = datetime.fromisoformat(case["utc"])
    return {
        **{k: case[k] for k in ["latitude_deg", "longitude_deg", "elevation_m"]},
        "timezone_name": "UTC",
        "local_date": dt.date(),
        "local_time": dt.time(),
    }


def evaluate_case(case: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    args = case_arguments(case)
    coord = calculate_horizontal_coordinates(
        right_ascension=case["right_ascension"],
        declination=case["declination"],
        **args,
    )
    parsed = create_icrs_coordinate(case["right_ascension"], case["declination"])
    instant = calculate_astronomical_time(**args)
    site = create_earth_location(case["latitude_deg"], case["longitude_deg"], case["elevation_m"])
    xyz = [float(v.to_value(u.m)) for v in site.geocentric]
    ref = case["expected"]
    actual = {
        "observer_xyz_m": xyz,
        "altitude_deg": coord.altitude_degrees,
        "azimuth_deg": coord.azimuth_degrees,
        "lst_hours": instant.local_sidereal_time_hours,
        "jd_utc": instant.julian_date,
        "mjd_utc": instant.modified_julian_date,
        "ra_deg": float(parsed.ra.deg),
        "dec_deg": float(parsed.dec.deg),
        "airmass": coord.airmass,
        "above_horizon": coord.is_above_horizon,
        "visibility_status": coord.status,
        "utc": coord.utc_datetime_iso,
    }
    errors = {
        "observer_metres": max(abs(a - b) for a, b in zip(xyz, ref["observer_xyz_m"], strict=True)),
        "altitude_arcsec": abs(actual["altitude_deg"] - ref["altitude_deg"]) * 3600,
        "azimuth_arcsec": circular_error(actual["azimuth_deg"], ref["azimuth_deg"], 360) * 3600,
        "direction_arcsec": direction_error(
            actual["altitude_deg"], actual["azimuth_deg"], ref["altitude_deg"], ref["azimuth_deg"]
        ),
        "lst_seconds": circular_error(actual["lst_hours"], ref["lst_hours"], 24) * 3600,
        "jd_seconds": abs(actual["jd_utc"] - ref["jd_utc"]) * 86400,
        "mjd_seconds": abs(actual["mjd_utc"] - ref["mjd_utc"]) * 86400,
        "ra_input_arcsec": circular_error(actual["ra_deg"], case["ra_hours"] * 15, 360) * 3600,
        "dec_input_arcsec": abs(actual["dec_deg"] - case["dec_degrees"]) * 3600,
    }
    exclusions: dict[str, str] = {}
    if abs(ref["altitude_deg"]) > manifest["azimuth_component_excluded_above_abs_altitude_deg"]:
        exclusions["azimuth_arcsec"] = "ill_conditioned_near_zenith; direction bound still enforced"
    failures = []
    if not all(math.isfinite(v) for v in xyz):
        failures.append("nonfinite_observer_position")
    horizon_eligible = abs(ref["altitude_deg"]) * 3600 > manifest["horizon_ambiguity_arcsec"]
    if horizon_eligible and coord.is_above_horizon != ref["above_horizon"]:
        failures.append("reference_horizon_classification")
    if coord.is_above_horizon != (coord.altitude_degrees > 0):
        failures.append("horizon_internal_consistency")
    expected_status = (
        "below_horizon"
        if coord.altitude_degrees <= 0
        else "low_altitude"
        if coord.altitude_degrees < 20
        else "observable"
    )
    if coord.status != expected_status:
        failures.append("visibility_status_consistency")
    expected_utc = datetime.fromisoformat(case["utc"]).isoformat(timespec="seconds")
    if coord.utc_datetime_iso != expected_utc or instant.utc_datetime_iso != expected_utc:
        failures.append("utc_instant")
    if ref["secz"] is None:
        airmass_regime = "unsupported_below_5_degrees"
        if coord.airmass is not None:
            failures.append("unsupported_airmass_not_none")
    else:
        high = ref["altitude_deg"] >= manifest["airmass_scientific_minimum_altitude_deg"]
        metric = "airmass_relative" if high else "low_altitude_secz_relative"
        airmass_regime = "plane_parallel_approximation" if high else "low_altitude_model_only"
        errors[metric] = (
            abs(coord.airmass - ref["secz"]) / ref["secz"]
            if coord.airmass is not None
            else math.nan
        )
    for metric, error in errors.items():
        if metric not in exclusions and (
            not math.isfinite(error) or error > manifest["tolerances"][metric]
        ):
            failures.append(metric)
    for key in ["altitude_deg", "azimuth_deg", "lst_hours", "jd_utc", "mjd_utc"]:
        if not math.isfinite(actual[key]):
            failures.append(f"nonfinite_{key}")
    if not 0 <= coord.azimuth_degrees < 360 or not -90 <= coord.altitude_degrees <= 90:
        failures.append("coordinate_output_range")
    return {
        "id": case["id"],
        "category": case["category"],
        "scenario": {
            k: case[k]
            for k in [
                "site",
                "utc",
                "latitude_deg",
                "longitude_deg",
                "elevation_m",
                "right_ascension",
                "declination",
            ]
        },
        "expected": ref,
        "actual": actual,
        "errors": errors,
        "excluded_metrics": exclusions,
        "horizon_comparison": (
            "independent_reference"
            if horizon_eligible
            else "boundary_indeterminate_within_coordinate_tolerance"
        ),
        "airmass_regime": airmass_regime,
        "failures": failures,
        "status": "failed" if failures else "passed",
    }


def evaluate_invalid(case: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    args = {**case_arguments(baseline), "right_ascension": "6h", "declination": "+30d"}
    args[case["field"]] = case["value"]
    try:
        calculate_horizontal_coordinates(**args)
    except Exception as exc:
        actual = type(exc).__name__
    else:
        actual = None
    return {
        **case,
        "actual_error": actual,
        "status": "passed" if actual == case["error"] else "failed",
    }


def summarize(results: list[dict[str, Any]], tolerances: dict[str, float]) -> dict[str, Any]:
    summary = {}
    for metric, tolerance in tolerances.items():
        eligible = [
            r for r in results if metric in r["errors"] and metric not in r["excluded_metrics"]
        ]
        values = [r["errors"][metric] for r in eligible]
        finite = all(math.isfinite(v) for v in values)
        passed = sum(math.isfinite(v) and v <= tolerance for v in values)
        worst = max(
            eligible,
            key=lambda r: r["errors"][metric] if math.isfinite(r["errors"][metric]) else math.inf,
            default=None,
        )
        summary[metric] = {
            "mean": statistics.mean(values) if values and finite else None,
            "median": statistics.median(values) if values and finite else None,
            "maximum": max(values) if values and finite else None,
            "rms": math.sqrt(statistics.mean(v * v for v in values)) if values and finite else None,
            "tolerance": tolerance,
            "count": len(values),
            "inside_tolerance": passed,
            "inside_tolerance_percent": 100 * passed / len(values) if values else None,
            "excluded_count": sum(metric in r["excluded_metrics"] for r in results),
            "not_applicable_count": sum(metric not in r["errors"] for r in results),
            "nonfinite_count": sum(not math.isfinite(v) for v in values),
            "worst_case": {"id": worst["id"], **worst["scenario"]} if worst else None,
        }
    return summary


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def run_benchmark(output: Path) -> dict[str, Any]:
    manifest, fixture = load_inputs()
    started = time.perf_counter()
    with fixed_earth_orientation():
        results = [evaluate_case(c, manifest) for c in fixture["cases"]]
        invalid = [evaluate_invalid(c, fixture["cases"][0]) for c in fixture["invalid_inputs"]]
    failed = sum(r["status"] == "failed" for r in results)
    invalid_failed = sum(r["status"] == "failed" for r in invalid)
    sources = [
        "pyproject.toml",
        "src/astroscope/observer.py",
        "src/astroscope/visibility.py",
        "src/astroscope/coordinates.py",
        "validation/celestial_coordinates.py",
        "validation/manifests/celestial_coordinates_v1.json",
        "validation/reference_generation/celestial_coordinates.py",
        "validation/requirements-celestial.txt",
    ]
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    )
    record = {
        "schema_version": "1.0",
        "benchmark_id": manifest["benchmark_id"],
        "aggregate_status": "failed" if failed or invalid_failed else "passed",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(results),
        "failed_cases": failed,
        "case_pass_percent": 100 * (len(results) - failed) / len(results),
        "input_contract_count": len(invalid),
        "failed_input_contracts": invalid_failed,
        "runtime_seconds": time.perf_counter() - started,
        "summary": summarize(results, manifest["tolerances"]),
        "classification_summary": {
            "horizon_reference_compared": sum(
                r["horizon_comparison"] == "independent_reference" for r in results
            ),
            "horizon_boundary_indeterminate": sum(
                r["horizon_comparison"] != "independent_reference" for r in results
            ),
            "airmass_regimes": {
                k: sum(r["airmass_regime"] == k for r in results)
                for k in [
                    "plane_parallel_approximation",
                    "low_altitude_model_only",
                    "unsupported_below_5_degrees",
                ]
            },
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "installed_dependencies": sorted(
                [
                    {"name": d.metadata["Name"], "version": d.version}
                    for d in importlib.metadata.distributions()
                ],
                key=lambda d: d["name"].lower(),
            ),
            "git_commit": git.stdout.strip() if git.returncode == 0 else None,
            "git_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
            "implementation_commit": os.environ.get("ASTROSCOPE_IMPLEMENTATION_COMMIT"),
            "checkout_commit": os.environ.get("ASTROSCOPE_CHECKOUT_COMMIT"),
            "iers_auto_download": False,
            "eop": "committed IERS B snapshot",
            "production_ephemeris": "Astropy builtin ERFA epv00",
        },
        "input_sha256": {**manifest["files"], **{p: sha(ROOT / p) for p in sources}},
        "reference": fixture["reference"],
        "results": results,
        "input_contract_results": invalid,
    }
    record = json_safe(record)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = run_benchmark(args.output)
    print(
        f"{record['aggregate_status']}: {record['case_count']} cases; "
        f"{record['failed_cases']} failures; {record['failed_input_contracts']} input failures"
    )
    return 0 if record["aggregate_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
