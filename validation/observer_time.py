"""Run the reproducible observer civil-time validation benchmark."""

from __future__ import annotations

import argparse
import hashlib
import importlib
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
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, reset_tzpath

from astroscope.observer import local_datetime_to_utc

SCHEMA_VERSION = "1.0"
EXPECTED_TZDATA_VERSION = "2026.3"
EXPECTED_IANA_VERSION = "2026c"
EXPECTED_MANIFEST_FILE_SHA256 = "314fcdb8a2a25ec9a32c381b68efc9f71e836d290a68c82b592a1e1a7df7d1aa"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class ValidationInputError(ValueError):
    """Raised when committed validation inputs fail integrity checks."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_payload_sha256(payload: dict[str, Any], omitted_key: str) -> str:
    canonical_payload = dict(payload)
    canonical_payload.pop(omitted_key, None)
    encoded = json.dumps(
        canonical_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _repository_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPOSITORY_ROOT / candidate


def load_verified_inputs(
    manifest_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Verify manifest and fixture integrity before returning scientific cases."""

    resolved_manifest = _repository_path(manifest_path)
    manifest_bytes = resolved_manifest.read_bytes()
    actual_manifest_file_sha256 = _sha256_bytes(manifest_bytes)
    if actual_manifest_file_sha256 != EXPECTED_MANIFEST_FILE_SHA256:
        raise ValidationInputError("Manifest file SHA-256 verification failed.")
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValidationInputError("Manifest root must be a JSON object.")

    expected_manifest_payload_sha256 = manifest.get("manifest_payload_sha256")
    if not isinstance(expected_manifest_payload_sha256, str) or not SHA256_PATTERN.fullmatch(
        expected_manifest_payload_sha256
    ):
        raise ValidationInputError("Manifest payload SHA-256 is absent or malformed.")
    actual_manifest_payload_sha256 = _canonical_payload_sha256(
        manifest,
        "manifest_payload_sha256",
    )
    if actual_manifest_payload_sha256 != expected_manifest_payload_sha256:
        raise ValidationInputError("Manifest payload SHA-256 verification failed.")

    fixture_path_value = manifest.get("fixture_path")
    expected_fixture_sha256 = manifest.get("fixture_sha256")
    if not isinstance(fixture_path_value, str):
        raise ValidationInputError("Manifest fixture_path must be a string.")
    if not isinstance(expected_fixture_sha256, str) or not SHA256_PATTERN.fullmatch(
        expected_fixture_sha256
    ):
        raise ValidationInputError("Fixture SHA-256 is absent or malformed.")

    resolved_fixture = _repository_path(fixture_path_value)
    fixture_bytes = resolved_fixture.read_bytes()
    actual_fixture_sha256 = _sha256_bytes(fixture_bytes)
    if actual_fixture_sha256 != expected_fixture_sha256:
        raise ValidationInputError("Fixture SHA-256 verification failed.")

    fixture = json.loads(fixture_bytes)
    if not isinstance(fixture, dict):
        raise ValidationInputError("Fixture root must be a JSON object.")

    return (
        manifest,
        fixture,
        {
            "manifest_file_sha256": actual_manifest_file_sha256,
            "manifest_payload_sha256": actual_manifest_payload_sha256,
            "fixture_sha256": actual_fixture_sha256,
        },
    )


def _parse_local_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValidationInputError("Fixture local_datetime values must be timezone-naive.")
    return parsed


def classify_local_datetime(local_datetime: datetime, timezone_name: str) -> dict[str, Any]:
    """Classify a civil time through both PEP 495 fold candidates."""

    if local_datetime.tzinfo is not None:
        raise ValueError("Classification requires a timezone-naive local datetime.")
    timezone = ZoneInfo(timezone_name)
    candidates: list[dict[str, Any]] = []

    for fold in (0, 1):
        aware_local = local_datetime.replace(tzinfo=timezone, fold=fold)
        utc_datetime = aware_local.astimezone(UTC)
        roundtrip = utc_datetime.astimezone(timezone)
        roundtrip_matches = roundtrip.replace(tzinfo=None) == local_datetime
        offset = aware_local.utcoffset()
        if offset is None:
            raise RuntimeError(f"No UTC offset available for {timezone_name}.")
        candidates.append(
            {
                "fold": fold,
                "utc": utc_datetime.isoformat(timespec="seconds"),
                "utc_offset_seconds": int(offset.total_seconds()),
                "roundtrip_local": roundtrip.isoformat(timespec="seconds"),
                "roundtrip_fold": roundtrip.fold,
                "roundtrip_matches": roundtrip_matches,
            }
        )

    real_candidates = [candidate for candidate in candidates if candidate["roundtrip_matches"]]
    real_utc_values = {candidate["utc"] for candidate in real_candidates}
    offsets = {candidate["utc_offset_seconds"] for candidate in candidates}

    if len(real_utc_values) == 1 and len(offsets) == 1:
        classification = "normal"
    elif len(real_candidates) == 2 and len(real_utc_values) == 2:
        classification = "ambiguous"
    elif not real_candidates:
        classification = "nonexistent"
    else:
        classification = "unexpected"

    return {"classification": classification, "candidates": candidates}


def execute_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one committed observer-time validation case."""

    case_id = case["id"]
    category = case["category"]
    timezone_name = case["timezone"]
    local_datetime = _parse_local_datetime(case["local_datetime"])
    base_result: dict[str, Any] = {
        "id": case_id,
        "category": category,
        "timezone": timezone_name,
        "local_datetime": case["local_datetime"],
    }

    if category == "invalid_input":
        try:
            local_datetime_to_utc(
                local_date=local_datetime.date(),
                local_time=local_datetime.time(),
                timezone_name=timezone_name,
            )
        except ValueError as error:
            actual_error = str(error)
            passed = actual_error == case["expected_error"]
            return {
                **base_result,
                "status": "invalid_input" if passed else "failed",
                "expected_error": case["expected_error"],
                "actual_error": actual_error,
            }
        return {
            **base_result,
            "status": "failed",
            "expected_error": case["expected_error"],
            "actual_error": None,
        }

    try:
        classification = classify_local_datetime(local_datetime, timezone_name)
    except ZoneInfoNotFoundError as error:
        return {**base_result, "status": "failed", "error": str(error)}

    expected_classification = case["expected_classification"]
    classification_matches = classification["classification"] == expected_classification

    if category == "unsupported":
        expected_candidates = case["expected_candidates"]
        candidates_match = classification["candidates"] == expected_candidates
        status = "unsupported" if classification_matches and candidates_match else "failed"
        return {
            **base_result,
            "status": status,
            "reason": case["reason"],
            "expected_classification": expected_classification,
            "actual_classification": classification["classification"],
            "candidates": classification["candidates"],
            "expected_candidates": expected_candidates,
        }

    fold = case["fold"]
    production_time = time(
        local_datetime.hour,
        local_datetime.minute,
        local_datetime.second,
        local_datetime.microsecond,
        fold=fold,
    )
    actual_utc = local_datetime_to_utc(
        local_date=local_datetime.date(),
        local_time=production_time,
        timezone_name=timezone_name,
    ).isoformat(timespec="seconds")
    expected_utc = case["expected_utc"]
    status = "passed" if classification_matches and actual_utc == expected_utc else "failed"
    return {
        **base_result,
        "status": status,
        "fold": fold,
        "expected_classification": expected_classification,
        "actual_classification": classification["classification"],
        "expected_utc": expected_utc,
        "actual_utc": actual_utc,
        "candidates": classification["candidates"],
    }


def calculate_benchmark_input_digest(
    manifest: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    """Hash the committed benchmark inputs with the manifest-declared algorithm."""

    algorithm = manifest.get("benchmark_input_digest_algorithm")
    if algorithm != "sha256-path-null-file-sha256-v1":
        raise ValidationInputError(f"Unsupported benchmark input digest algorithm: {algorithm}")
    input_files = manifest.get("benchmark_input_files")
    if not isinstance(input_files, list) or not input_files:
        raise ValidationInputError("benchmark_input_files must be a non-empty list.")
    if input_files != sorted(input_files) or len(input_files) != len(set(input_files)):
        raise ValidationInputError("benchmark_input_files must be unique and sorted.")

    aggregate = hashlib.sha256()
    file_records: list[dict[str, str]] = []
    for relative_path in input_files:
        if not isinstance(relative_path, str):
            raise ValidationInputError("Every benchmark input path must be a string.")
        resolved_path = _repository_path(relative_path)
        file_sha256 = _sha256_file(resolved_path)
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(file_sha256))
        file_records.append({"path": relative_path, "sha256": file_sha256})
    return aggregate.hexdigest(), file_records


def _git_output(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_value(environment_name: str, fallback: str) -> str:
    value = os.environ.get(environment_name, fallback)
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValidationInputError(f"{environment_name} must be a complete Git SHA.")
    return value


def _source_version() -> str:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]["version"]


def _installed_dependencies() -> list[dict[str, str]]:
    dependencies = [
        {
            "name": distribution.metadata.get("Name", "<unknown>"),
            "version": distribution.version,
        }
        for distribution in importlib.metadata.distributions()
    ]
    return sorted(
        dependencies,
        key=lambda dependency: (dependency["name"].casefold(), dependency["version"]),
    )


def _tzif_hashes(zones: list[str]) -> list[dict[str, str]]:
    zoneinfo_root = importlib.resources.files("tzdata.zoneinfo")
    hashes = []
    for zone in sorted(zones):
        zone_resource = zoneinfo_root.joinpath(*zone.split("/"))
        hashes.append({"zone": zone, "sha256": _sha256_bytes(zone_resource.read_bytes())})
    return hashes


def _environment_record(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def record_check(name: str, passed: bool, actual: Any, expected: Any) -> None:
        checks.append(
            {"name": name, "status": "passed" if passed else "failed", "actual": actual,
             "expected": expected}
        )

    python_tzpath = os.environ.get("PYTHONTZPATH")
    reset_tzpath()
    ZoneInfo.clear_cache()
    captured_tzpath = list(zoneinfo.TZPATH)
    tzdata_version = importlib.metadata.version("tzdata")
    tzdata_module = importlib.import_module("tzdata")
    tzdata_iana_version = getattr(tzdata_module, "IANA_VERSION", None)
    source_version = _source_version()
    installed_version = importlib.metadata.version("astroscope-ai-observatory")
    git_head = _git_output("rev-parse", "HEAD")
    tracked_status = _git_output("status", "--porcelain", "--untracked-files=no")
    implementation_commit = _commit_value("ASTROSCOPE_IMPLEMENTATION_COMMIT", git_head)
    checked_out_commit = _commit_value("ASTROSCOPE_CHECKOUT_COMMIT", git_head)

    record_check("PYTHONTZPATH", python_tzpath == "", python_tzpath, "")
    record_check("zoneinfo.TZPATH", captured_tzpath == [], captured_tzpath, [])
    record_check(
        "tzdata distribution version",
        tzdata_version == EXPECTED_TZDATA_VERSION,
        tzdata_version,
        EXPECTED_TZDATA_VERSION,
    )
    record_check(
        "tzdata IANA version",
        tzdata_iana_version == EXPECTED_IANA_VERSION,
        tzdata_iana_version,
        EXPECTED_IANA_VERSION,
    )
    record_check(
        "source and installed package versions",
        source_version == installed_version,
        {"source": source_version, "installed": installed_version},
        "equal",
    )

    astropy = importlib.import_module("astropy")
    iers = importlib.import_module("astropy.utils.iers")
    coordinates = importlib.import_module("astropy.coordinates")
    dependencies = _installed_dependencies()
    zones = fixture["zones"]

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
            "astropy_version": astropy.__version__,
            "package_versions": {
                "source_pyproject": source_version,
                "installed_distribution": installed_version,
                "tzdata_distribution": tzdata_version,
                "tzdata_iana": tzdata_iana_version,
            },
            "timezone_database": {
                "pythontzpath": python_tzpath,
                "zoneinfo_tzpath": captured_tzpath,
                "tzif_files": _tzif_hashes(zones),
            },
            "git": {
                "implementation_commit": implementation_commit,
                "checked_out_commit": checked_out_commit,
                "tracked_worktree_clean_before_output": tracked_status == "",
            },
            "iers": {
                "status": "not_applicable",
                "reason": "Civil-time UTC-offset mapping does not consume Earth-orientation data.",
                "configuration": {
                    "auto_download": bool(iers.conf.auto_download),
                    "auto_max_age": iers.conf.auto_max_age,
                },
            },
            "ephemeris": {
                "status": "not_applicable",
                "reason": (
                    "Civil-time UTC-offset mapping does not calculate solar-system positions."
                ),
                "configuration": {
                    "solar_system_ephemeris": coordinates.solar_system_ephemeris.get()
                },
            },
            "installed_dependencies": dependencies,
        },
        checks,
    )


def _write_record(output_path: str | Path, record: dict[str, Any]) -> None:
    resolved_output = _repository_path(output_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_benchmark(manifest_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Run the committed benchmark and write its structured evidence record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "observer-time-validation-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "aggregate_status": "failed",
    }
    try:
        manifest, fixture, input_hashes = load_verified_inputs(manifest_path)
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValidationInputError("Unsupported manifest schema_version.")
        if fixture.get("schema_version") != SCHEMA_VERSION:
            raise ValidationInputError("Unsupported fixture schema_version.")
        benchmark_digest, benchmark_inputs = calculate_benchmark_input_digest(manifest)
        environment, environment_checks = _environment_record(fixture)
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
                **input_hashes,
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

    case_results = [execute_case(case) for case in fixture["cases"]]
    supported_passed = sum(
        result["status"] == "passed" and result["category"] == "supported"
        for result in case_results
    )
    expected_unsupported = sum(result["status"] == "unsupported" for result in case_results)
    expected_invalid = sum(result["status"] == "invalid_input" for result in case_results)
    failed = sum(result["status"] == "failed" for result in case_results)
    summary = {
        "supported_passed": supported_passed,
        "expected_unsupported": expected_unsupported,
        "expected_invalid_input": expected_invalid,
        "failed": failed,
        "total": len(case_results),
    }
    aggregate_passed = (
        supported_passed == manifest["expected_supported_case_count"]
        and expected_unsupported == manifest["expected_unsupported_case_count"]
        and expected_invalid == manifest["expected_invalid_input_case_count"]
        and failed == 0
    )
    record["cases"] = case_results
    record["summary"] = summary
    record["aggregate_status"] = "passed" if aggregate_passed else "failed"
    if not aggregate_passed:
        record["failure"] = {
            "category": "scientific_or_classification",
            "message": "Observed case totals do not match the manifest contract.",
        }
    _write_record(output_path, record)
    return record


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Repository-relative manifest path.")
    parser.add_argument("--output", required=True, help="Path for the structured run record.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return nonzero for any failed benchmark aggregate."""

    arguments = _argument_parser().parse_args(argv)
    record = run_benchmark(arguments.manifest, arguments.output)
    return 0 if record["aggregate_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
