"""Run Mission 29 schedule behavior against committed independent IANA evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from astroscope import schedule as schedule_module
from astroscope.planner import ObservationPlanEntry, ObservationPlanResult

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"


class ScheduleIntervalValidationError(ValueError):
    """Raised when committed interval evidence is malformed or inconsistent."""


def _path(value: str | Path) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _payload_sha(payload: dict[str, Any], key: str) -> str:
    copy = dict(payload)
    copy.pop(key, None)
    return hashlib.sha256(
        json.dumps(copy, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_verified_inputs(manifest_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(_path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ScheduleIntervalValidationError("Unsupported schedule interval manifest schema.")
    if _payload_sha(manifest, "manifest_payload_sha256") != manifest.get("manifest_payload_sha256"):
        raise ScheduleIntervalValidationError("Schedule interval manifest payload digest failed.")
    fixture_path = _path(manifest["fixture_path"])
    if _sha256(fixture_path) != manifest["fixture_sha256"]:
        raise ScheduleIntervalValidationError("Schedule interval fixture digest failed.")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != SCHEMA_VERSION or len(fixture.get("cases", ())) != 37:
        raise ScheduleIntervalValidationError("Expected exactly 37 schema-v1 interval cases.")
    ids = [case.get("id") for case in fixture["cases"]]
    if len(set(ids)) != 37:
        raise ScheduleIntervalValidationError("Schedule interval case IDs must be unique.")
    schedule_path = ROOT / manifest["system_under_validation"]["schedule_source_path"]
    if (
        _git_blob_sha(schedule_path)
        != manifest["system_under_validation"]["schedule_source_blob_sha"]
    ):
        raise ScheduleIntervalValidationError(
            "schedule.py does not match the approved Mission 29 blob."
        )
    return manifest, fixture


def _endpoint(value: list[Any]) -> schedule_module.ScheduleCivilEndpoint:
    local, fold = value
    parsed = datetime.fromisoformat(local)
    return schedule_module.ScheduleCivilEndpoint(parsed.date(), parsed.time(), fold)


def _request(case: dict[str, Any]) -> schedule_module.ScheduleIntervalRequest:
    return schedule_module.ScheduleIntervalRequest(
        timezone_name=case["timezone"], start=_endpoint(case["start"]), end=_endpoint(case["end"])
    )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _recommendation() -> ObservationPlanEntry:
    return ObservationPlanEntry(
        "fixture-target",
        "catalog",
        60.0,
        180.0,
        "S",
        1.2,
        90.0,
        "observable",
        36.0,
        18.0,
        20.0,
        15.0,
        89.0,
        "excellent",
        True,
    )


def _plan(recommended: bool) -> ObservationPlanResult:
    entries = (_recommendation(),) if recommended else ()
    return ObservationPlanResult(
        entries, -20.0, len(entries), len(entries), "2026-01-01T00:00:00+00:00"
    )


def _run_occupancy(
    case: dict[str, Any], interval: schedule_module.ResolvedScheduleInterval
) -> dict[str, Any]:
    original = schedule_module.calculate_observation_plan
    call_count = 0

    def deterministic_plan(**_: Any) -> ObservationPlanResult:
        nonlocal call_count
        call_count += 1
        return _plan(case.get("occupancy") != "sentinel_only" or call_count > 2)

    schedule_module.calculate_observation_plan = deterministic_plan
    try:
        result = schedule_module.calculate_observation_schedule_strict(
            0.0, 0.0, 0.0, interval, interval_minutes=60, include_solar_system_targets=False
        )
    finally:
        schedule_module.calculate_observation_plan = original
    return {
        "scheduled_minutes": result.scheduled_minutes,
        "block_count": len(result.schedule_blocks),
    }


def execute_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute exactly one evidence case and normalize its outcome."""

    try:
        if case.get("operation") == "legacy":
            start = datetime.fromisoformat(case["start"][0])
            end = datetime.fromisoformat(case["end"][0])
            grid = schedule_module.create_local_time_grid(
                start.date(), start.time(), end.time(), case["timezone"], 60
            )
            actual = {
                "start_utc": _iso(grid[0]),
                "end_utc": _iso(grid[-1]),
                "elapsed_seconds": (
                    grid[-1].astimezone(UTC) - grid[0].astimezone(UTC)
                ).total_seconds(),
            }
        else:
            interval = schedule_module.resolve_schedule_interval(_request(case))
            actual = {
                "start_utc": _iso(interval.start_utc),
                "end_utc": _iso(interval.end_utc),
                "elapsed_seconds": interval.elapsed.total_seconds(),
            }
            if "grid_minutes" in case:
                grid = schedule_module.create_resolved_schedule_time_grid(
                    interval, case["grid_minutes"]
                )
                actual["grid_utc"] = [_iso(value) for value in grid]
                actual["local_folds"] = [value.fold for value in grid]
            if "occupancy" in case:
                actual.update(_run_occupancy(case, interval))
        if case["category"] != "passed":
            return {
                "id": case["id"],
                "category": "failed",
                "detail": "Expected rejection was accepted.",
            }
        expected = {
            key: case[key]
            for key in (
                "start_utc",
                "end_utc",
                "elapsed_seconds",
                "grid_utc",
                "local_folds",
                "scheduled_minutes",
            )
            if key in case
        }
        mismatch = {
            key: {"expected": value, "actual": actual.get(key)}
            for key, value in expected.items()
            if actual.get(key) != value
        }
        return {
            "id": case["id"],
            "category": "passed" if not mismatch else "failed",
            "actual": actual,
            "mismatch": mismatch,
        }
    except Exception as error:  # expected scientific rejection is fixture-owned
        if case["category"] == "expected_rejection" and type(error).__name__ == case["error"]:
            return {
                "id": case["id"],
                "category": "expected_rejection",
                "error": type(error).__name__,
            }
        return {"id": case["id"], "category": "failed", "error": f"{type(error).__name__}: {error}"}


def _benchmark_inputs(manifest: dict[str, Any]) -> dict[str, Any]:
    files = []
    for relative in manifest["benchmark_input_files"]:
        files.append({"path": relative, "sha256": _sha256(ROOT / relative)})
    digest = hashlib.sha256(
        "".join(f"{item['path']}\0{item['sha256']}\0" for item in files).encode()
    ).hexdigest()
    return {
        "digest_algorithm": manifest["benchmark_input_digest_algorithm"],
        "benchmark_input_sha256": digest,
        "files": files,
    }


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    manifest, fixture = load_verified_inputs(manifest_path)
    results = [execute_case(case) for case in fixture["cases"]]
    summary = {
        category: sum(result["category"] == category for result in results)
        for category in ("passed", "expected_rejection", "invalid_input", "failed")
    }
    summary["total"] = len(results)
    record = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": manifest["benchmark_id"],
        "aggregate_status": "passed" if summary == manifest["expected_summary"] else "failed",
        "summary": summary,
        "cases": results,
        "fixture_sha256": manifest["fixture_sha256"],
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "benchmark_inputs": _benchmark_inputs(manifest),
        "reference_provenance": manifest["reference_provenance_id"],
        "system_under_validation": manifest["system_under_validation"],
        "execution": {
            "implementation_commit": os.environ.get(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", _git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.environ.get(
                "ASTROSCOPE_CHECKOUT_COMMIT", _git("rev-parse", "HEAD")
            ),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "source_package_version": "0.2.0",
            "installed_package_version": metadata.version("astroscope-ai-observatory"),
            "tzdata_distribution": metadata.version("tzdata"),
            "network_required": False,
        },
    }
    _path(output_path).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    return 0 if run_benchmark(args.manifest, args.output)["aggregate_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
