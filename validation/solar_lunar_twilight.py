"""Offline validation of existing Solar System and visibility APIs (Mission 34)."""

from __future__ import annotations

import argparse
import functools
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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import astropy.units as u
import numpy as np
from astropy.coordinates import solar_system_ephemeris
from astropy.table import QTable
from astropy.utils import iers
from scipy.optimize import brentq, minimize_scalar

from astroscope.planner import calculate_darkness_score
from astroscope.solar_system import calculate_solar_system_body
from astroscope.transit_visibility import ObserverSite, TransitTarget, sample_transit_visibility
from validation.celestial_coordinates import (
    circular_error,
    direction_error,
    json_safe,
    sha,
    summarize,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation/manifests/solar_lunar_twilight_v1.json"
FIXTURE = ROOT / "validation/fixtures/solar_lunar_twilight_v1.json"
EOP = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
POLICY = ROOT / "validation/manifests/solar_lunar_twilight_policy_v1.json"
EXPECTED_MANIFEST_SHA256 = "f5938576fd0fc445e117b61c7e8fb0587911f272a39afd9cca95c7c937847041"
GENERATOR = ROOT / "validation/reference_generation/solar_lunar_twilight.py"


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads(MANIFEST.read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Input checksum mismatch: {path}")
    if sha(GENERATOR) != manifest["generator_sha256"]:
        raise ValueError("Generator checksum mismatch")
    fixture = json.loads(FIXTURE.read_text())
    for key, count in [("cases", manifest["case_count"]), ("windows", manifest["window_count"])]:
        if len(fixture[key]) != count or len({c["id"] for c in fixture[key]}) != count:
            raise ValueError("Invalid count or duplicate identifiers")
    rows = json.loads(EOP.read_text())["rows"]
    first, last = rows[0]["MJD"], rows[-1]["MJD"]
    if any(b["MJD"] - a["MJD"] != 1 for a, b in zip(rows[:-1], rows[1:], strict=True)):
        raise ValueError("IERS rows are not consecutive")
    for c in [*fixture["cases"], *fixture["windows"]]:
        for key in ["utc", "start_utc", "end_utc"]:
            if key in c:
                dt = datetime.fromisoformat(c[key])
                if dt.utcoffset().total_seconds() != 0:
                    raise ValueError("Fixture timestamps must be UTC")
                if not first <= 40587 + dt.timestamp() / 86400 < last:
                    raise ValueError("Fixture timestamp outside frozen IERS range")
    return json.loads(POLICY.read_text()), fixture


@contextmanager
def frozen_environment() -> Iterator[None]:
    rows = json.loads(EOP.read_text())["rows"]
    table = QTable()
    for key, unit in [("MJD", u.day), ("UT1_UTC", u.s), ("PM_x", u.arcsec), ("PM_y", u.arcsec)]:
        table[key] = [r[key] for r in rows] * unit
    with (
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("iers_degraded_accuracy", "error"),
        iers.earth_orientation_table.set(iers.IERS(table)),
        solar_system_ephemeris.set("builtin"),
    ):
        yield


def body_at(site: dict[str, Any], dt: datetime, body: str):
    return calculate_solar_system_body(
        body=body,
        latitude_deg=site["latitude_deg"],
        longitude_deg=site["longitude_deg"],
        elevation_m=site["elevation_m"],
        timezone_name="UTC",
        local_date=dt.date(),
        local_time=dt.time(),
    )


def evaluate_snapshot(case: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    dt, site, ref = datetime.fromisoformat(case["utc"]), case["site"], case["reference"]
    bodies = {name: body_at(site, dt, name) for name in ["sun", "moon"]}
    errors: dict[str, float] = {}
    exclusions: dict[str, str] = {}
    classes: dict[str, str] = {}
    failures = []
    actual: dict[str, Any] = {}
    for name, body in bodies.items():
        alt, az = body.altitude_degrees, body.azimuth_degrees
        actual[name] = {
            "altitude": alt,
            "azimuth": az,
            "above_horizon": body.is_above_horizon,
            "status": body.status,
            "solar_elongation": body.solar_elongation_degrees,
            "moon_separation": body.moon_separation_degrees,
            "illumination": body.moon_illumination_fraction,
        }
        errors[f"{name}_altitude_arcsec"] = abs(alt - ref[f"{name}_altitude"]) * 3600
        errors[f"{name}_azimuth_arcsec"] = circular_error(az, ref[f"{name}_azimuth"], 360) * 3600
        errors[f"{name}_direction_arcsec"] = direction_error(
            alt, az, ref[f"{name}_altitude"], ref[f"{name}_azimuth"]
        )
        if (
            abs(ref[f"{name}_altitude"])
            > policy["conditioning"]["azimuth_excluded_above_absolute_altitude_degrees"]
        ):
            exclusions[f"{name}_azimuth_arcsec"] = "ill_conditioned_azimuth; direction still gated"
        guard = policy["tolerances"][f"{name}_direction_arcsec"] / 3600
        for threshold in [0.0, 20.0]:
            label = f"{name}_above_{threshold}"
            if abs(ref[f"{name}_altitude"] - threshold) <= guard:
                classes[label] = "boundary_indeterminate"
            else:
                classes[label] = "reference_compared"
                if (alt > threshold) != (ref[f"{name}_altitude"] > threshold):
                    failures.append(label)
        if body.is_above_horizon != (alt > 0):
            failures.append(f"{name}_horizon_consistency")
        status = "below_horizon" if alt <= 0 else "low_altitude" if alt < 20 else "observable"
        if body.status != status or not (
            math.isfinite(alt) and -90 <= alt <= 90 and math.isfinite(az) and 0 <= az < 360
        ):
            failures.append(f"{name}_status_or_range")
        if body.utc_datetime_iso != dt.isoformat(timespec="seconds"):
            failures.append(f"{name}_utc")
    errors["sun_moon_separation_arcsec"] = (
        abs(bodies["sun"].moon_separation_degrees - ref["sun_moon_separation"]) * 3600
    )
    errors["solar_elongation_arcsec"] = (
        abs(bodies["moon"].solar_elongation_degrees - ref["sun_moon_separation"]) * 3600
    )
    fraction = bodies["moon"].moon_illumination_fraction
    errors["illumination_model_absolute"] = abs(fraction - ref["illumination_model"])
    errors["illumination_physical_absolute"] = abs(fraction - ref["illumination_physical"])
    actual["illumination_relative_error"] = (
        errors["illumination_physical_absolute"] / ref["illumination_physical"]
        if ref["illumination_physical"]
        >= policy["conditioning"]["illumination_relative_excluded_below_fraction"]
        else None
    )
    if (
        not math.isfinite(fraction)
        or not 0 <= fraction <= 1
        or abs(bodies["sun"].solar_elongation_degrees) > 1e-10
        or abs(bodies["moon"].moon_separation_degrees) > 1e-10
    ):
        failures.append("fraction_range_or_self_separation")
    # Configurable threshold is part of the existing transit visibility API.
    threshold = [-6.0, -12.0, -18.0][int(case["id"].rsplit("_", 1)[1]) % 3]
    observer = ObserverSite(
        site["name"], site["latitude_deg"], site["longitude_deg"], site["elevation_m"]
    )
    sample = sample_transit_visibility(
        observer,
        TransitTarget("fixed star", 90.0, 20.0),
        2440587.5 + dt.timestamp() / 86400,
        darkness_sun_altitude_degrees=threshold,
    )
    actual["transit"] = {
        "sun_altitude": sample.sun_altitude_degrees,
        "moon_altitude": sample.moon_altitude_degrees,
        "illumination": sample.moon_illumination_fraction,
        "dark": sample.is_astronomical_dark,
        "observable": sample.is_observable,
        "darkness_threshold": threshold,
    }
    for name in ["sun", "moon"]:
        errors[f"transit_{name}_altitude_arcsec"] = (
            abs(getattr(sample, f"{name}_altitude_degrees") - ref[f"{name}_altitude"]) * 3600
        )
    errors["transit_illumination_model_absolute"] = abs(
        sample.moon_illumination_fraction - ref["illumination_model"]
    )
    sun_guard = policy["tolerances"]["sun_direction_arcsec"] / 3600
    if (
        abs(ref["sun_altitude"] - threshold) <= sun_guard
        or abs(ref["target_altitude"] - 20) <= 2 / 3600
    ):
        classes["transit_darkness_observability"] = "boundary_indeterminate"
    else:
        classes["transit_darkness_observability"] = "reference_compared"
        dark = ref["sun_altitude"] <= threshold
        if sample.is_astronomical_dark != dark or sample.is_observable != (
            dark and ref["target_altitude"] >= 20
        ):
            failures.append("transit_darkness_observability")
    if sample.is_astronomical_dark != (sample.sun_altitude_degrees <= threshold):
        failures.append("darkness_internal_consistency")
    expected_score = 15 * min(1, max(0, -ref["sun_altitude"] / 18))
    actual["darkness_score"] = calculate_darkness_score(bodies["sun"].altitude_degrees)
    errors["darkness_score_absolute"] = abs(actual["darkness_score"] - expected_score)
    tolerances = all_tolerances(policy)
    failures.extend(
        k
        for k, v in errors.items()
        if k not in exclusions and (not math.isfinite(v) or v > tolerances[k])
    )
    return {
        "id": case["id"],
        "scenario": {"site": site, "utc": case["utc"], "category": case["category"]},
        "reference": ref,
        "actual": actual,
        "errors": errors,
        "excluded_metrics": exclusions,
        "classifications": classes,
        "failures": failures,
        "status": "failed" if failures else "passed",
    }


def all_tolerances(policy: dict[str, Any]) -> dict[str, float]:
    t = dict(policy["tolerances"])
    t.update(
        {
            f"transit_{name}_altitude_arcsec": t[f"{name}_altitude_arcsec"]
            for name in ["sun", "moon"]
        }
    )
    t["transit_illumination_model_absolute"] = t["illumination_model_absolute"]
    return t


def search_events(altitude, threshold: float, policy: dict[str, Any]) -> dict[str, Any]:
    """Validation-only independent search: hourly grid, extrema, then Brent roots.

    Searches only this 24h window; no claim of a general-purpose rise/set API.
    """
    step = policy["event_search"]["production_grid_seconds"]
    grid = list(np.arange(0, 86400 + step / 2, step))
    values = [altitude(float(t)) for t in grid]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite event altitude")
    extrema = []
    for i in range(1, len(grid) - 1):
        for sign in [1.0, -1.0]:
            if (
                sign * values[i] <= sign * values[i - 1]
                and sign * values[i] <= sign * values[i + 1]
            ):
                result = minimize_scalar(
                    lambda x, sign=sign: sign * altitude(float(x)),
                    bounds=(grid[i - 1], grid[i + 1]),
                    method="bounded",
                    options={"xatol": 0.01},
                )
                if not result.success or not math.isfinite(result.fun):
                    raise ValueError("Event extremum search failed")
                extrema.append(float(result.x))
    knots = sorted(set([*grid, *extrema]))
    heights = [altitude(float(x)) for x in knots]
    events = []
    for a, b, fa, fb in zip(knots[:-1], knots[1:], heights[:-1], heights[1:], strict=True):
        if fa == threshold:
            if (
                a > 0
                and (altitude(float(a - 1)) - threshold) * (altitude(float(a + 1)) - threshold) >= 0
            ):
                continue  # A tangent touch is not a rising/setting crossing.
            root = float(a)
        elif (fa - threshold) * (fb - threshold) < 0:
            root = float(
                brentq(
                    lambda x: altitude(x) - threshold,
                    a,
                    b,
                    xtol=policy["event_search"]["production_root_precision_seconds"],
                )
            )
        else:
            continue
        slope = altitude(min(86400.0, root + 1)) - altitude(max(0.0, root - 1))
        event = {"seconds": root, "direction": "rising" if slope > 0 else "setting"}
        if root < 86400 and (not events or abs(root - events[-1]["seconds"]) > 0.02):
            events.append(event)
    low, high = min(heights), max(heights)
    state = (
        "crossings"
        if events
        else "always_above"
        if low > threshold
        else "always_below"
        if high < threshold
        else "grazing_indeterminate"
    )
    return {"events": events, "state": state, "minimum_altitude": low, "maximum_altitude": high}


def evaluate_window(window, policy, cached_body) -> dict[str, Any]:
    start = datetime.fromisoformat(window["start_utc"])

    def altitude(seconds):
        return cached_body(
            window["body"], start + timedelta(seconds=float(seconds))
        ).altitude_degrees

    actual = search_events(altitude, window["threshold"], policy)
    ref = window["reference"]
    failures = []
    events = []
    metric = f"{window['body']}_event_seconds"
    if actual["state"] != ref["state"] or len(actual["events"]) != len(ref["events"]):
        failures.append("event_topology")
    for i, (expected, observed) in enumerate(zip(ref["events"], actual["events"], strict=False)):
        ill = (
            abs(expected["slope_arcsec_per_second"])
            < policy["conditioning"]["minimum_event_slope_arcsec_per_second"]
        )
        error = abs(observed["seconds"] - expected["seconds"])
        failed = observed["direction"] != expected["direction"] or (
            not ill and error > policy["tolerances"][metric]
        )
        if failed:
            failures.append(f"event_{i}")
        events.append(
            {
                "id": f"{window['id']}_{i}",
                "scenario": {
                    "site": window["site"],
                    "start_utc": window["start_utc"],
                    "threshold": window["threshold"],
                    "body": window["body"],
                    "direction": expected["direction"],
                },
                "expected": expected,
                "actual": observed,
                "errors": {metric: error},
                "excluded_metrics": {metric: "ill_conditioned_crossing"} if ill else {},
                "status": "failed" if failed else "passed",
            }
        )
    guard = policy["tolerances"][f"{window['body']}_direction_arcsec"] / 3600
    proximity = min(
        abs(ref["minimum_altitude"] - window["threshold"]),
        abs(ref["maximum_altitude"] - window["threshold"]),
    )
    return {
        "id": window["id"],
        "scenario": {k: window[k] for k in ["site", "body", "threshold", "start_utc", "end_utc"]},
        "reference": ref,
        "actual": actual,
        "event_comparisons": events,
        "no_event_conditioning": "near_tangent" if proximity <= guard else "well_separated",
        "failures": failures,
        "status": "failed" if failures else "passed",
    }


def run_benchmark(output: Path) -> dict[str, Any]:
    policy, fixture = load_inputs()
    started = time.perf_counter()
    with frozen_environment():
        results = [evaluate_snapshot(case, policy) for case in fixture["cases"]]
        windows = []
        # Cache body evaluations across the four solar thresholds in each window.
        for site_name in dict.fromkeys(w["site"]["name"] for w in fixture["windows"]):
            subset = [w for w in fixture["windows"] if w["site"]["name"] == site_name]
            site = subset[0]["site"]

            @functools.cache
            def cached_body(body, dt, site=site):
                return body_at(site, dt, body)

            for window in subset:
                windows.append(evaluate_window(window, policy, cached_body))
            print(f"Validated event windows: {site_name}", flush=True)
    event_results = [e for w in windows for e in w["event_comparisons"]]
    summary = summarize([*results, *event_results], all_tolerances(policy))
    event_groups = {}
    for body, threshold in [
        ("sun", 0.0),
        ("sun", -6.0),
        ("sun", -12.0),
        ("sun", -18.0),
        ("moon", 0.0),
    ]:
        group = [
            e
            for w in windows
            if w["scenario"]["body"] == body and w["scenario"]["threshold"] == threshold
            for e in w["event_comparisons"]
        ]
        metric = f"{body}_event_seconds"
        event_groups[f"{body}_{threshold}"] = summarize(
            group, {metric: policy["tolerances"][metric]}
        )[metric]
    failed = sum(r["status"] == "failed" for r in results)
    failed_windows = sum(w["status"] == "failed" for w in windows)
    relative = [
        r["actual"]["illumination_relative_error"]
        for r in results
        if r["actual"]["illumination_relative_error"] is not None
    ]
    sources = [
        "src/astroscope/solar_system.py",
        "src/astroscope/transit_visibility.py",
        "src/astroscope/planner.py",
        "src/astroscope/observer.py",
        "src/astroscope/visibility.py",
        "validation/celestial_coordinates.py",
        "validation/solar_lunar_twilight.py",
        "validation/reference_generation/solar_lunar_twilight.py",
        "validation/manifests/solar_lunar_twilight_v1.json",
        "validation/requirements-celestial.txt",
    ]
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    record = {
        "schema_version": "1.0",
        "benchmark_id": "solar-lunar-twilight-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "aggregate_status": "failed" if failed or failed_windows else "passed",
        "case_count": len(results),
        "failed_cases": failed,
        "window_count": len(windows),
        "failed_windows": failed_windows,
        "event_count": len(event_results),
        "expected_event_count": sum(len(w["reference"]["events"]) for w in fixture["windows"]),
        "native_event_api_status": "unsupported: all event times are validation-derived crossings",
        "event_summary_by_threshold": event_groups,
        "summary": summary,
        "illumination_relative_diagnostic": {
            "count": len(relative),
            "excluded_near_new": len(results) - len(relative),
            "mean": statistics.mean(relative),
            "maximum": max(relative),
            "claim": "Diagnostic only; absolute error is the acceptance metric",
        },
        "classification_counts": {
            k: sum(v == k for r in results for v in r["classifications"].values())
            for k in ["reference_compared", "boundary_indeterminate"]
        },
        "window_state_counts": {
            k: sum(w["reference"]["state"] == k for w in windows)
            for k in ["crossings", "always_above", "always_below", "grazing_indeterminate"]
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "git_commit": git,
            "git_dirty": dirty,
            "implementation_commit": os.environ.get("ASTROSCOPE_IMPLEMENTATION_COMMIT"),
            "checkout_commit": os.environ.get("ASTROSCOPE_CHECKOUT_COMMIT"),
            "installed_dependencies": sorted(
                [
                    {"name": d.metadata["Name"], "version": d.version}
                    for d in importlib.metadata.distributions()
                ],
                key=lambda x: x["name"].lower(),
            ),
            "iers_auto_download": False,
            "production_ephemeris": "builtin",
        },
        "input_sha256": {
            **json.loads(MANIFEST.read_text())["files"],
            **{p: sha(ROOT / p) for p in sources},
        },
        "reference": fixture["reference"],
        "policy": policy,
        "runtime_seconds": time.perf_counter() - started,
        "results": results,
        "windows": windows,
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
        f"{record['aggregate_status']}: {record['case_count']} snapshots, "
        f"{record['window_count']} windows, {record['event_count']} matched events"
    )
    return 0 if record["aggregate_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
