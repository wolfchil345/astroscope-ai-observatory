"""Run the offline strict civil-time resolution validation benchmark."""

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

from astroscope.observer import (
    CivilTimeClassification,
    CivilTimeResolutionError,
    classify_local_datetime,
    resolve_local_datetime,
)

SCHEMA_VERSION = "1.0"
EXPECTED_TZDATA_VERSION = "2026.3"
EXPECTED_IANA_VERSION = "2026c"
EXPECTED_MANIFEST_FILE_SHA256 = "a041cfdd5494b858354d2b028abc4c888ad79ff71be3265750bbc9cba1e617a2"
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
    """Verify the committed manifest and fixture before returning them."""

    resolved_manifest = _repository_path(manifest_path)
    manifest_bytes = resolved_manifest.read_bytes()
    actual_manifest_file_sha256 = _sha256_bytes(manifest_bytes)
    if actual_manifest_file_sha256 != EXPECTED_MANIFEST_FILE_SHA256:
        raise ValidationInputError("Manifest file SHA-256 verification failed.")
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValidationInputError("Manifest root must be a JSON object.")

    expected_payload_sha256 = manifest.get("manifest_payload_sha256")
    if not isinstance(expected_payload_sha256, str) or not SHA256_PATTERN.fullmatch(
        expected_payload_sha256
    ):
        raise ValidationInputError("Manifest payload SHA-256 is absent or malformed.")
    actual_payload_sha256 = _canonical_payload_sha256(
        manifest,
        "manifest_payload_sha256",
    )
    if actual_payload_sha256 != expected_payload_sha256:
        raise ValidationInputError("Manifest payload SHA-256 verification failed.")

    fixture_path_value = manifest.get("fixture_path")
    expected_fixture_sha256 = manifest.get("fixture_sha256")
    if not isinstance(fixture_path_value, str):
        raise ValidationInputError("Manifest fixture_path must be a string.")
    if not isinstance(expected_fixture_sha256, str) or not SHA256_PATTERN.fullmatch(
        expected_fixture_sha256
    ):
        raise ValidationInputError("Fixture SHA-256 is absent or malformed.")
    fixture_bytes = _repository_path(fixture_path_value).read_bytes()
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
            "manifest_payload_sha256": actual_payload_sha256,
            "fixture_sha256": actual_fixture_sha256,
        },
    )


def _parse_local_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValidationInputError("Fixture local_datetime values must be timezone-naive.")
    return parsed


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat(timespec="microseconds")


def _classification_record(classification: CivilTimeClassification) -> dict[str, Any]:
    return {
        "status": classification.status.value,
        "candidates": [
            {
                "fold": candidate.fold,
                "utc": _iso(candidate.utc_datetime),
                "utc_offset_seconds": int(candidate.utc_offset.total_seconds()),
                "roundtrip_local": _iso(candidate.roundtrip_local_datetime),
                "roundtrip_fold": candidate.roundtrip_fold,
                "roundtrip_matches": candidate.roundtrip_matches,
            }
            for candidate in classification.candidates
        ],
        "previous_valid_local": _iso(classification.previous_valid_local),
        "next_valid_local": _iso(classification.next_valid_local),
    }


def _classification_matches(
    case: dict[str, Any],
    classification: CivilTimeClassification,
) -> tuple[bool, dict[str, Any]]:
    actual = _classification_record(classification)
    expected = case["expected_classification"]
    return actual == expected, actual


def _resolution_record(
    local_datetime: datetime,
    timezone_name: str,
    requested_fold: int | None,
    expected_classification: dict[str, Any],
) -> dict[str, Any]:
    try:
        utc_datetime = resolve_local_datetime(
            local_date=local_datetime.date(),
            local_time=local_datetime.timetz().replace(tzinfo=None),
            timezone_name=timezone_name,
            fold=requested_fold,
        )
    except CivilTimeResolutionError as error:
        return {
            "outcome": "error",
            "type": type(error).__name__,
            "message": str(error),
            "requested_fold": error.requested_fold,
            "classification_matches": error.classification is not None
            and _classification_record(error.classification) == expected_classification,
        }
    return {"outcome": "resolved", "utc": _iso(utc_datetime)}


def execute_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one independently evidenced strict civil-time fixture case."""

    category = case["category"]
    base_result = {
        "id": case["id"],
        "category": category,
        "timezone": case["timezone"],
        "local_datetime": case["local_datetime"],
    }
    local_datetime = _parse_local_datetime(case["local_datetime"])

    if category == "invalid_input":
        try:
            classify_local_datetime(
                local_date=local_datetime.date(),
                local_time=local_datetime.time(),
                timezone_name=case["timezone"],
            )
        except ValueError as error:
            matched = (
                type(error).__name__ == case["expected_error_type"]
                and str(error) == case["expected_error"]
            )
            return {
                **base_result,
                "status": "invalid_input" if matched else "failed",
                "actual_error_type": type(error).__name__,
                "actual_error": str(error),
            }
        return {**base_result, "status": "failed", "actual_error": None}

    try:
        classification = classify_local_datetime(
            local_date=local_datetime.date(),
            local_time=local_datetime.time(),
            timezone_name=case["timezone"],
        )
    except Exception as error:
        return {
            **base_result,
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }

    classification_matches, actual_classification = _classification_matches(case, classification)
    transition_width_matches = True
    if "transition_width_seconds" in case:
        previous = classification.previous_valid_local
        next_value = classification.next_valid_local
        if previous is None or next_value is None:
            transition_width_matches = False
        else:
            transition_width_matches = (
                int((next_value.utcoffset() - previous.utcoffset()).total_seconds())
                == case["transition_width_seconds"]
            )
    resolution_results = [
        {
            "fold": expectation["fold"],
            **_resolution_record(
                local_datetime,
                case["timezone"],
                expectation["fold"],
                case["expected_classification"],
            ),
        }
        for expectation in case["resolution_expectations"]
    ]
    expected_resolutions = [
        {"fold": expectation["fold"], **expectation["expected"]}
        for expectation in case["resolution_expectations"]
    ]
    resolutions_match = resolution_results == expected_resolutions

    expected_status = {
        "normal_resolution": "passed",
        "ambiguous_resolution": "passed",
        "ambiguous_rejection": "expected_rejection",
        "nonexistent_rejection": "expected_rejection",
    }[category]
    return {
        **base_result,
        "status": (
            expected_status
            if classification_matches and transition_width_matches and resolutions_match
            else "failed"
        ),
        "classification": actual_classification,
        "transition_width_matches": transition_width_matches,
        "resolution_results": resolution_results,
    }


def calculate_benchmark_input_digest(
    manifest: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    """Hash manifest-declared committed benchmark inputs deterministically."""

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
        file_sha256 = _sha256_file(_repository_path(relative_path))
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


def _tzif_hashes(zones: list[str]) -> list[dict[str, str]]:
    zoneinfo_root = importlib.resources.files("tzdata.zoneinfo")
    return [
        {
            "zone": zone,
            "sha256": _sha256_bytes(
                zoneinfo_root.joinpath(*zone.split("/")).read_bytes()
            ),
        }
        for zone in sorted(zones)
    ]


def _environment_record(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def record_check(name: str, passed: bool, actual: Any, expected: Any) -> None:
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "failed",
                "actual": actual,
                "expected": expected,
            }
        )

    python_tzpath = os.environ.get("PYTHONTZPATH")
    reset_tzpath()
    ZoneInfo.clear_cache()
    captured_tzpath = list(zoneinfo.TZPATH)
    tzdata_version = importlib.metadata.version("tzdata")
    tzdata_module = __import__("tzdata")
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
                "tzdata_distribution": tzdata_version,
                "tzdata_iana": tzdata_iana_version,
            },
            "timezone_database": {
                "pythontzpath": python_tzpath,
                "zoneinfo_tzpath": captured_tzpath,
                "tzif_files": _tzif_hashes(fixture["zones"]),
            },
            "git": {
                "implementation_commit": implementation_commit,
                "checked_out_commit": checked_out_commit,
                "tracked_worktree_clean_before_output": tracked_status == "",
            },
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
    """Run the benchmark and write a non-canonical structured run record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "civil-time-validation-v2",
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
            "manifest": {"path": str(Path(manifest_path)), **input_hashes},
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
    summary = {
        "passed": sum(result["status"] == "passed" for result in case_results),
        "expected_rejection": sum(
            result["status"] == "expected_rejection" for result in case_results
        ),
        "invalid_input": sum(result["status"] == "invalid_input" for result in case_results),
        "failed": sum(result["status"] == "failed" for result in case_results),
        "total": len(case_results),
    }
    aggregate_passed = summary == manifest["expected_summary"]
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
