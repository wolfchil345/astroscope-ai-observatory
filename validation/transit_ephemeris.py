"""Mission 35 Stage B: offline comparison against frozen independent references."""

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
from collections import Counter
from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path

from astroscope import transit_scheduler as production

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "validation/manifests/transit_ephemeris_v1.json"
FIXTURE = "validation/fixtures/transit_ephemeris_v1.json"
POLICY = "validation/manifests/transit_ephemeris_policy_v1.json"
EXPECTED_MANIFEST_SHA256 = "41c3059129eaf8278091e78535c548d60614101ada958f4c75d4a616c3de9900"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(root: Path = ROOT) -> tuple[dict, dict, dict]:
    if sha(root / MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        if sha(root / name) != digest:
            raise ValueError(f"Input checksum mismatch: {name}")
    fixture = json.loads((root / FIXTURE).read_text(encoding="utf-8"))
    for group, count in manifest["counts"].items():
        if len(fixture[group]) != count:
            raise ValueError(f"Invalid count: {group}")
        if group != "covariance_diagnostics":
            ids = [row["id"] for row in fixture[group]]
            if len(set(ids)) != len(ids):
                raise ValueError(f"Duplicate IDs: {group}")
    return manifest, json.loads((root / POLICY).read_text(encoding="utf-8")), fixture


def make_ephemeris(e: dict) -> production.TransitEphemeris:
    values = {f.name: e[f.name] for f in fields(production.TransitEphemeris)}
    return production.TransitEphemeris(
        **{k: v if k == "planet_name" or v is None else float(v) for k, v in values.items()}
    )


def difference_seconds(actual: float, expected: str, seconds_per_unit: int) -> float:
    if not math.isfinite(actual):
        return math.inf
    with localcontext() as context:
        context.prec = 60
        return float((Decimal.from_float(actual) - Decimal(expected)) * seconds_per_unit)


def check_event(case: dict, e: dict, policy: dict) -> dict:
    event = production.build_transit_event(
        make_ephemeris(e), case["cycle"], **{k: float(v) for k, v in case["options"].items()}
    )
    metrics = {}
    limits = policy["limits"]
    for name, expected in case["expected"].items():
        actual = getattr(event, name)
        scale = 3600 if name.endswith("hours") else 86400
        error = difference_seconds(actual, expected, scale)
        if name.startswith("timing_uncertainty"):
            bound = max(
                limits["uncertainty_absolute_seconds"],
                abs(float(expected) * scale) * limits["uncertainty_relative"],
            )
        elif name == "observation_window_hours":
            bound = limits["window_duration_seconds"]
        else:
            bound = limits["absolute_time_seconds"]
        metrics[name] = {
            "actual": actual if math.isfinite(actual) else None,
            "reference": expected,
            "error_seconds": error if math.isfinite(error) else None,
            "bound_seconds": bound,
            "passed": math.isfinite(error) and abs(error) <= bound,
        }
    identity = event.transit_number == case["cycle"] and event.planet_name == e["planet_name"]
    return {
        "id": case["id"],
        "cycle": case["cycle"],
        "ephemeris_id": e["id"],
        "uncertainty_status": e["uncertainty_status"],
        "metrics": metrics,
        "identity_passed": identity,
        "status": "passed" if identity and all(m["passed"] for m in metrics.values()) else "failed",
    }


def _check_range(case: dict, e: dict) -> dict:
    ephemeris = make_ephemeris(e)
    start, end = float(case["start_jd"]), float(case["end_jd"])
    events = production.predict_transits(ephemeris, start, end)
    actual = [event.transit_number for event in events]
    after = production.calculate_transit_number_on_or_after(ephemeris, start)
    before = production.calculate_transit_number_on_or_before(ephemeris, end)
    exact = (
        actual == case["expected_cycles"]
        and after == case["expected_after"]
        and before == case["expected_before"]
    )
    # Guarded cases still reject gross errors, unordered/duplicate cycles and endpoint escape.
    guard_days = float(case["boundary_guard_seconds"]) / 86400
    bounded = (
        set(case["certain_cycles"]) <= set(actual) <= set(case["possible_cycles"])
        and actual == sorted(set(actual))
        and abs(after - case["expected_after"]) <= 1
        and abs(before - case["expected_before"]) <= 1
        and all(start - guard_days <= ev.mid_transit_jd <= end + guard_days for ev in events)
    )
    passed = exact if case["eligible"] else bounded
    return {
        "id": case["id"],
        "ephemeris_id": e["id"],
        "start_jd": case["start_jd"],
        "end_jd": case["end_jd"],
        "expected_cycles": case["expected_cycles"],
        "actual_cycles": actual,
        "expected_after": case["expected_after"],
        "actual_after": after,
        "expected_before": case["expected_before"],
        "actual_before": before,
        "eligible": case["eligible"],
        "exact_topology_agreement": exact,
        "guard_passed": bounded,
        "status": "failed"
        if not passed
        else "passed"
        if case["eligible"]
        else "boundary_indeterminate",
    }


def check_range(case: dict, e: dict) -> dict:
    """Unexpected production rejection is a benchmark failure, with retained evidence."""
    try:
        return _check_range(case, e)
    except (production.TransitSchedulerError, ArithmeticError) as error:
        return {
            "id": case["id"],
            "ephemeris_id": e["id"],
            "eligible": case["eligible"],
            "exact_topology_agreement": False,
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
        }


def rejection_cases() -> list[dict]:
    """Software input contracts, kept distinct from independent numerical evidence."""
    cases = []
    for field in [
        "orbital_period_days",
        "transit_duration_hours",
        "reference_mid_transit_jd",
        "period_uncertainty_days",
        "reference_epoch_uncertainty_days",
    ]:
        values = ["nan", "inf", "-inf"]
        if field != "reference_mid_transit_jd":
            values += ["-1"]
        if field in ["orbital_period_days", "transit_duration_hours"]:
            values += ["0"]
        for value in values:
            cases.append(
                {
                    "id": f"ephemeris:{field}:{value}",
                    "kind": "ephemeris",
                    "field": field,
                    "value": value,
                }
            )
    for field in ["baseline_before_hours", "baseline_after_hours", "uncertainty_sigma_multiplier"]:
        for value in ["-1", "nan", "inf"]:
            cases.append(
                {"id": f"event:{field}:{value}", "kind": "option", "field": field, "value": value}
            )
    for method in ["calculate_mid_transit_jd", "calculate_timing_uncertainty_days"]:
        for value in [True, 1.5, "1"]:
            cases.append(
                {
                    "id": f"cycle:{method}:{value!r}",
                    "kind": "cycle",
                    "method": method,
                    "value": value,
                }
            )
    for value in [True, 0, -1, 1.5, 2]:
        cases.append({"id": f"capacity:{value!r}", "kind": "capacity", "value": value})
    cases.append({"id": "interval:reversed", "kind": "reversed"})
    cases.append({"id": "ephemeris:blank_name", "kind": "blank_name"})
    for field in ["start_jd", "end_jd"]:
        for value in ["nan", "inf", "-inf"]:
            cases.append(
                {
                    "id": f"interval:{field}:{value}",
                    "kind": "endpoint",
                    "field": field,
                    "value": value,
                }
            )
    return cases


def check_rejection(case: dict, e: dict) -> dict:
    values = {
        f.name: getattr(make_ephemeris(e), f.name) for f in fields(production.TransitEphemeris)
    }
    try:
        kind = case["kind"]
        if kind == "ephemeris":
            values[case["field"]] = float(case["value"])
            production.TransitEphemeris(**values)
        elif kind == "blank_name":
            values["planet_name"] = "  "
            production.TransitEphemeris(**values)
        elif kind == "option":
            production.build_transit_event(
                make_ephemeris(e), 0, **{case["field"]: float(case["value"])}
            )
        elif kind == "cycle":
            getattr(production, case["method"])(make_ephemeris(e), case["value"])
        else:
            ep = make_ephemeris(e)
            start, end = ep.reference_mid_transit_jd, ep.reference_mid_transit_jd + 4
            options = {"start_jd": start, "end_jd": end}
            if kind == "capacity":
                options["maximum_events"] = case["value"]
            elif kind == "reversed":
                options.update(start_jd=end, end_jd=start)
            else:
                options[case["field"]] = float(case["value"])
            production.predict_transits(ep, **options)
    except production.TransitSchedulerError as error:
        return {"id": case["id"], "status": "expected_rejection", "message": str(error)}
    return {"id": case["id"], "status": "failed", "message": "Invalid input accepted"}


def metric_summary(events: list[dict]) -> dict:
    result = {}
    for metric in events[0]["metrics"]:
        rows = [(r["id"], r["metrics"][metric]) for r in events]
        errors = [abs(m["error_seconds"]) for _, m in rows if m["error_seconds"] is not None]
        worst = max(
            rows,
            key=lambda row: (
                abs(row[1]["error_seconds"]) if row[1]["error_seconds"] is not None else math.inf
            ),
        )
        result[metric] = {
            "count": len(rows),
            "finite_count": len(errors),
            "passed": sum(m["passed"] for _, m in rows),
            "mae_seconds": statistics.mean(errors) if errors else None,
            "median_seconds": statistics.median(errors) if errors else None,
            "rms_seconds": math.sqrt(statistics.mean(x * x for x in errors)) if errors else None,
            "max_seconds": max(errors) if errors else None,
            "worst_case": worst[0],
        }
    return result


def provenance(manifest: dict) -> dict:
    def git(*args: str) -> str | None:
        run = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
        return run.stdout.strip() if run.returncode == 0 else None

    head, status = git("rev-parse", "HEAD"), git("status", "--porcelain")
    paths = [
        "src/astroscope/transit_scheduler.py",
        "validation/transit_ephemeris.py",
        "src/astroscope/transit_schedule_application.py",
        "src/astroscope/transit_visibility.py",
        "src/astroscope/transit_schedule_exports.py",
        "validation/requirements-transit.txt",
    ]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "implementation_commit": os.environ.get("ASTROSCOPE_IMPLEMENTATION_COMMIT", head),
        "checkout_commit": os.environ.get("ASTROSCOPE_CHECKOUT_COMMIT", head),
        "git_dirty": bool(status) if status is not None else None,
        "project_version": importlib.metadata.version("astroscope-ai-observatory"),
        "dependencies": sorted(
            (d.metadata["Name"], d.version) for d in importlib.metadata.distributions()
        ),
        "source_sha256": {p: sha(ROOT / p) for p in paths},
        "input_sha256": {**manifest["files"], MANIFEST: sha(ROOT / MANIFEST)},
        "runtime_reference_imports": False,
        "network_required": False,
        "randomness": "none",
        "ephemeris_iers_policy": "not used by scalar benchmark",
    }


def run_benchmark() -> dict:
    manifest, policy, fixture = load_inputs()
    ephs = {e["id"]: e for e in fixture["ephemerides"]}
    events = [check_event(c, ephs[c["ephemeris_id"]], policy) for c in fixture["events"]]
    ranges = [check_range(c, ephs[c["ephemeris_id"]]) for c in fixture["ranges"]]
    rejections = [check_rejection(c, fixture["ephemerides"][0]) for c in rejection_cases()]
    counts = dict(Counter(r["status"] for r in [*events, *ranges, *rejections]))
    return {
        "schema_version": "1.0",
        "mission": 35,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "environment": provenance(manifest),
        "policy": policy,
        "counts": counts,
        "metrics": metric_summary(events),
        "overall_passed": counts.get("failed", 0) == 0,
        "scientific_status": "bounded_arithmetic_only; barycentric_to_UTC_unsupported",
        "range_topology": {
            "eligible": sum(r["eligible"] for r in ranges),
            "indeterminate": sum(not r["eligible"] for r in ranges),
            "indeterminate_disagreements": sum(
                not r["eligible"] and not r["exact_topology_agreement"] for r in ranges
            ),
        },
        "events": events,
        "ranges": ranges,
        "input_contracts": rejections,
        "covariance_diagnostics": fixture["covariance_diagnostics"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"counts": result["counts"], "overall_passed": result["overall_passed"]}))
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
