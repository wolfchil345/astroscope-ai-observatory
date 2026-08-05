"""Run Mission 29 schedule behavior against committed independent IANA evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.resources
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
import zoneinfo
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, reset_tzpath

from astroscope import schedule as schedule_module
from astroscope.planner import ObservationPlanEntry, ObservationPlanResult

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
EXPECTED_TZDATA_VERSION = "2026.3"
EXPECTED_IANA_VERSION = "2026c"
ZONES = ("Asia/Tokyo", "America/New_York", "Europe/London", "Australia/Lord_Howe")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
SHA1_PATTERN = re.compile(r"[0-9a-f]{40}")


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


def _input_hashes(manifest_path: str | Path, manifest: dict[str, Any]) -> dict[str, str]:
    fixture_path = _path(manifest["fixture_path"])
    return {
        "manifest_file_sha256": _sha256(_path(manifest_path)),
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "fixture_sha256": _sha256(fixture_path),
    }


def load_verified_inputs(manifest_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the committed manifest and fixture before returning them."""

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
    if len(set(ids)) != 37 or any(not isinstance(case_id, str) for case_id in ids):
        raise ScheduleIntervalValidationError("Schedule interval case IDs must be unique strings.")
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
        if "expected_block_count" in case:
            expected["block_count"] = case["expected_block_count"]
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


def calculate_benchmark_input_digest(manifest: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """Hash manifest-declared committed benchmark inputs deterministically."""

    algorithm = manifest.get("benchmark_input_digest_algorithm")
    if algorithm != "sha256-path-null-file-sha256-v1":
        raise ScheduleIntervalValidationError(
            f"Unsupported benchmark input digest algorithm: {algorithm}"
        )
    input_files = manifest.get("benchmark_input_files")
    if not isinstance(input_files, list) or not input_files:
        raise ScheduleIntervalValidationError("benchmark_input_files must be a non-empty list.")
    if any(not isinstance(item, str) for item in input_files):
        raise ScheduleIntervalValidationError("Every benchmark input path must be a string.")
    if input_files != sorted(input_files) or len(input_files) != len(set(input_files)):
        raise ScheduleIntervalValidationError("benchmark_input_files must be unique and sorted.")
    aggregate = hashlib.sha256()
    records: list[dict[str, str]] = []
    for relative_path in input_files:
        file_sha256 = _sha256(_path(relative_path))
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(file_sha256))
        records.append({"path": relative_path, "sha256": file_sha256})
    return aggregate.hexdigest(), records


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit_value(name: str, fallback: str) -> str:
    value = os.environ.get(name, fallback)
    if not SHA1_PATTERN.fullmatch(value):
        raise ScheduleIntervalValidationError(f"{name} must be a complete Git SHA.")
    return value


def _source_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def _tzif_hashes() -> dict[str, str]:
    zoneinfo_root = importlib.resources.files("tzdata.zoneinfo")
    return {
        zone: hashlib.sha256(zoneinfo_root.joinpath(*zone.split("/")).read_bytes()).hexdigest()
        for zone in sorted(ZONES)
    }


def _environment_record(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, actual: Any, expected: Any) -> None:
        checks.append(
            {
                "name": name,
                "status": "passed" if actual == expected else "failed",
                "actual": actual,
                "expected": expected,
            }
        )

    pythontzpath = os.environ.get("PYTHONTZPATH")
    reset_tzpath()
    ZoneInfo.clear_cache()
    captured_tzpath = list(zoneinfo.TZPATH)
    tzdata_distribution = importlib.metadata.version("tzdata")
    tzdata_module = __import__("tzdata")
    tzdata_iana = getattr(tzdata_module, "IANA_VERSION", None)
    source_version = _source_version()
    installed_version = importlib.metadata.version("astroscope-ai-observatory")
    git_head = _git("rev-parse", "HEAD")
    implementation_commit = _commit_value("ASTROSCOPE_IMPLEMENTATION_COMMIT", git_head)
    checkout_commit = _commit_value("ASTROSCOPE_CHECKOUT_COMMIT", git_head)
    expected_origin = manifest["system_under_validation"]["implementation_origin_commit"]
    expected_tzif_hashes = manifest["expected_tzif_sha256"]
    actual_tzif_hashes = _tzif_hashes()
    check("PYTHONTZPATH", pythontzpath, "")
    check("zoneinfo.TZPATH", captured_tzpath, [])
    check("tzdata distribution version", tzdata_distribution, EXPECTED_TZDATA_VERSION)
    check("tzdata IANA version", tzdata_iana, EXPECTED_IANA_VERSION)
    check("source and installed package versions", source_version, installed_version)
    check("Mission 29 origin commit format", bool(SHA1_PATTERN.fullmatch(expected_origin)), True)
    for zone in sorted(ZONES):
        check(
            f"TZif SHA-256 for {zone}",
            actual_tzif_hashes.get(zone),
            expected_tzif_hashes.get(zone),
        )
    return (
        {
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "executable": sys.executable,
            },
            "operating_system": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
            },
            "architecture": platform.machine(),
            "package_versions": {
                "source_pyproject": source_version,
                "installed_distribution": installed_version,
                "tzdata_distribution": tzdata_distribution,
                "tzdata_iana": tzdata_iana,
            },
            "timezone_database": {
                "pythontzpath": pythontzpath,
                "zoneinfo_tzpath": captured_tzpath,
                "tzif_sha256": {
                    "expected": expected_tzif_hashes,
                    "actual": actual_tzif_hashes,
                },
            },
            "git": {
                "mission_29_origin_commit": expected_origin,
                "approved_schedule_source_blob_sha": manifest["system_under_validation"][
                    "schedule_source_blob_sha"
                ],
                "implementation_commit": implementation_commit,
                "checkout_commit": checkout_commit,
            },
            "network_required": False,
        },
        checks,
    )


def _write_record(output_path: str | Path, record: dict[str, Any]) -> None:
    resolved_output = _path(output_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_benchmark(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Run the benchmark and write a canonical, environment-pinned record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "schedule-interval-validation-v1",
        "aggregate_status": "failed",
    }
    try:
        manifest, fixture = load_verified_inputs(manifest_path)
        benchmark_digest, benchmark_inputs = calculate_benchmark_input_digest(manifest)
        environment, environment_checks = _environment_record(manifest)
    except Exception as error:
        record["failure"] = {
            "category": "input_or_environment",
            "type": type(error).__name__,
            "message": str(error),
        }
        _write_record(output_path, record)
        return record
    record.update(
        {
            "manifest": {
                "path": str(Path(manifest_path)),
                **_input_hashes(manifest_path, manifest),
            },
            "reference": manifest["reference_toolchain"],
            "benchmark_inputs": {
                "digest_algorithm": manifest["benchmark_input_digest_algorithm"],
                "benchmark_input_sha256": benchmark_digest,
                "files": benchmark_inputs,
            },
            "environment": environment,
            "environment_checks": environment_checks,
            "scientific_context": manifest["scientific_context"],
        }
    )
    if any(check["status"] != "passed" for check in environment_checks):
        record["failure"] = {
            "category": "environment",
            "message": "One or more canonical environment checks failed.",
        }
        record["cases"] = []
        _write_record(output_path, record)
        return record
    cases = [execute_case(case) for case in fixture["cases"]]
    summary = {
        category: sum(case["category"] == category for case in cases)
        for category in ("passed", "expected_rejection", "invalid_input", "failed")
    }
    summary["total"] = len(cases)
    record["cases"] = cases
    record["summary"] = summary
    record["aggregate_status"] = "passed" if summary == manifest["expected_summary"] else "failed"
    if record["aggregate_status"] == "failed":
        record["failure"] = {
            "category": "scientific_or_classification",
            "message": "Observed case totals do not match the manifest contract.",
        }
    _write_record(output_path, record)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    return 0 if run_benchmark(args.manifest, args.output)["aggregate_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
