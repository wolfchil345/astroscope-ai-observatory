"""Tests for the offline observer-time validation benchmark."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import zoneinfo
from collections.abc import Generator
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, reset_tzpath

import pytest

from validation.observer_time import (
    calculate_benchmark_input_digest,
    execute_case,
    load_verified_inputs,
    run_benchmark,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "validation/manifests/observer_time_v1.json"
MANIFEST, FIXTURE, INPUT_HASHES = load_verified_inputs(MANIFEST_PATH)
SUPPORTED_CASES = [case for case in FIXTURE["cases"] if case["category"] == "supported"]
UNSUPPORTED_CASES = [case for case in FIXTURE["cases"] if case["category"] == "unsupported"]
INVALID_CASES = [case for case in FIXTURE["cases"] if case["category"] == "invalid_input"]


@pytest.fixture(autouse=True)
def pinned_python_tzdata(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    original_tzpath = zoneinfo.TZPATH
    monkeypatch.setenv("PYTHONTZPATH", "")
    reset_tzpath()
    ZoneInfo.clear_cache()
    try:
        yield
    finally:
        reset_tzpath(original_tzpath)
        ZoneInfo.clear_cache()


@pytest.mark.parametrize("case", SUPPORTED_CASES, ids=lambda case: case["id"])
def test_supported_reference_conversion(case: dict[str, Any]) -> None:
    result = execute_case(case)

    assert result["status"] == "passed"
    assert result["actual_utc"] == case["expected_utc"]
    assert result["actual_classification"] == case["expected_classification"]
    if case["expected_classification"] == "ambiguous":
        assert result["fold"] == case["fold"]
        assert len({candidate["utc"] for candidate in result["candidates"]}) == 2


@pytest.mark.parametrize("case", UNSUPPORTED_CASES, ids=lambda case: case["id"])
def test_nonexistent_time_is_characterized_as_unsupported(case: dict[str, Any]) -> None:
    result = execute_case(case)

    assert result["status"] == "unsupported"
    assert result["actual_classification"] == "nonexistent"
    assert all(not candidate["roundtrip_matches"] for candidate in result["candidates"])
    assert result["candidates"] == case["expected_candidates"]


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda case: case["id"])
def test_invalid_timezone_preserves_validation_error(case: dict[str, Any]) -> None:
    result = execute_case(case)

    assert result["status"] == "invalid_input"
    assert result["actual_error"] == case["expected_error"]


def test_manifest_contract_is_explicit_and_counted() -> None:
    assert MANIFEST["schema_version"] == "1.0"
    assert FIXTURE["schema_version"] == "1.0"
    assert MANIFEST["iana_release"] == "2026c"
    assert MANIFEST["python_tzdata_release"] == "2026.3"
    assert MANIFEST["expected_tzdata_iana_version"] == "2026c"
    assert len(SUPPORTED_CASES) == MANIFEST["expected_supported_case_count"] == 9
    assert len(UNSUPPORTED_CASES) == MANIFEST["expected_unsupported_case_count"] == 2
    assert len(INVALID_CASES) == MANIFEST["expected_invalid_input_case_count"] == 1
    assert len(FIXTURE["cases"]) == 12
    for context in MANIFEST["scientific_context"].values():
        assert context["status"] == "not_applicable"
        assert isinstance(context["reason"], str) and context["reason"]


def test_committed_checksums_and_provenance_verify() -> None:
    manifest, fixture, hashes = load_verified_inputs(MANIFEST_PATH)
    benchmark_digest, input_files = calculate_benchmark_input_digest(manifest)

    assert hashes == INPUT_HASHES
    assert all(len(value) == 64 for value in hashes.values())
    assert len(benchmark_digest) == 64
    assert [item["path"] for item in input_files] == manifest["benchmark_input_files"]
    assert fixture["reference"]["version_file_contents"] == "2026c"
    assert fixture["reference"]["tool_versions"] == {
        "zdump": "zdump (tzcode) 2026c",
        "zic": "zic (tzcode) 2026c",
    }
    assert all(
        len(archive["sha256"]) == 64
        for archive in manifest["reference_toolchain"]["archives"]
    )


def test_run_record_schema_and_fresh_environment_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_tzpath = zoneinfo.TZPATH

    def deny_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("Observer-time validation attempted network socket creation.")

    monkeypatch.setenv("PYTHONTZPATH", "")
    monkeypatch.setattr(socket, "socket", deny_socket)
    monkeypatch.setattr(socket, "create_connection", deny_socket)
    output_path = tmp_path / "observer-time-run.json"
    try:
        record = run_benchmark(MANIFEST_PATH, output_path)
    finally:
        reset_tzpath(original_tzpath)

    assert record["schema_version"] == "1.0"
    assert record["aggregate_status"] == "passed"
    assert record["summary"] == {
        "supported_passed": 9,
        "expected_unsupported": 2,
        "expected_invalid_input": 1,
        "failed": 0,
        "total": 12,
    }
    environment = record["environment"]
    assert environment["package_versions"]["source_pyproject"] == "0.2.0"
    assert environment["package_versions"]["installed_distribution"] == "0.2.0"
    assert environment["package_versions"]["tzdata_distribution"] == "2026.3"
    assert environment["package_versions"]["tzdata_iana"] == "2026c"
    assert environment["timezone_database"]["zoneinfo_tzpath"] == []
    assert [
        item["zone"] for item in environment["timezone_database"]["tzif_files"]
    ] == sorted(FIXTURE["zones"])
    dependencies = environment["installed_dependencies"]
    assert dependencies == sorted(
        dependencies,
        key=lambda dependency: (dependency["name"].casefold(), dependency["version"]),
    )
    assert environment["iers"]["status"] == "not_applicable"
    assert environment["ephemeris"]["status"] == "not_applicable"
    assert json.loads(output_path.read_text(encoding="utf-8")) == record


def test_cli_runs_offline_with_committed_inputs(
    tmp_path: Path,
) -> None:
    guard_directory = tmp_path / "offline-guard"
    guard_directory.mkdir()
    (guard_directory / "sitecustomize.py").write_text(
        "import socket\n"
        "class OfflineSocket(socket.socket):\n"
        "    def __new__(cls, *args, **kwargs):\n"
        "        raise RuntimeError('network disabled by observer-time validation test')\n"
        "def deny_connection(*args, **kwargs):\n"
        "    raise RuntimeError('network disabled by observer-time validation test')\n"
        "socket.socket = OfflineSocket\n"
        "socket.create_connection = deny_connection\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "offline-run.json"
    environment = os.environ.copy()
    environment["PYTHONTZPATH"] = ""
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(guard_directory), str(REPOSITORY_ROOT), environment.get("PYTHONPATH", "")]
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.observer_time",
            "--manifest",
            "validation/manifests/observer_time_v1.json",
            "--output",
            str(output_path),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    record = json.loads(output_path.read_text(encoding="utf-8"))
    assert record["aggregate_status"] == "passed"
    assert record["environment"]["timezone_database"]["zoneinfo_tzpath"] == []
