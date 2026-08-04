"""Tests for the offline strict civil-time validation benchmark."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import zoneinfo
from collections.abc import Generator
from pathlib import Path
from zoneinfo import ZoneInfo, reset_tzpath

import pytest

from validation.civil_time import (
    calculate_benchmark_input_digest,
    execute_case,
    load_verified_inputs,
    run_benchmark,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "validation/manifests/civil_time_v2.json"
MANIFEST, FIXTURE, INPUT_HASHES = load_verified_inputs(MANIFEST_PATH)


@pytest.fixture(autouse=True)
def pinned_python_tzdata(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Use only the pinned Python tzdata distribution during benchmark tests."""

    original_tzpath = zoneinfo.TZPATH
    monkeypatch.setenv("PYTHONTZPATH", "")
    reset_tzpath()
    ZoneInfo.clear_cache()
    try:
        yield
    finally:
        reset_tzpath(original_tzpath)
        ZoneInfo.clear_cache()


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["id"])
def test_strict_civil_time_reference_case(case: dict[str, object]) -> None:
    result = execute_case(case)
    expected_status = {
        "normal_resolution": "passed",
        "ambiguous_resolution": "passed",
        "ambiguous_rejection": "expected_rejection",
        "nonexistent_rejection": "expected_rejection",
        "invalid_input": "invalid_input",
    }[case["category"]]

    assert result["status"] == expected_status


def test_fixture_manifest_contract_and_independent_reference_provenance() -> None:
    assert MANIFEST["schema_version"] == FIXTURE["schema_version"] == "1.0"
    assert MANIFEST["iana_release"] == "2026c"
    assert MANIFEST["python_tzdata_release"] == "2026.3"
    assert FIXTURE["provenance_id"] == MANIFEST["reference_toolchain"]["reference_provenance_id"]
    assert len(FIXTURE["cases"]) == 16
    assert MANIFEST["expected_summary"] == {
        "passed": 10,
        "expected_rejection": 5,
        "invalid_input": 1,
        "failed": 0,
        "total": 16,
    }
    assert all(
        archive["source_url"].endswith(archive["filename"])
        for archive in MANIFEST["reference_toolchain"]["archives"]
    )
    assert "Python ZoneInfo" in MANIFEST["reference_toolchain"]["generation_method"]


def test_fixture_manifest_and_benchmark_input_digests_verify() -> None:
    manifest, fixture, hashes = load_verified_inputs(MANIFEST_PATH)
    benchmark_digest, input_files = calculate_benchmark_input_digest(manifest)

    assert fixture == FIXTURE
    assert hashes == INPUT_HASHES
    assert all(len(value) == 64 for value in hashes.values())
    assert len(benchmark_digest) == 64
    assert [item["path"] for item in input_files] == manifest["benchmark_input_files"]


def test_run_record_and_provenance_schema_contract(tmp_path: Path) -> None:
    output_path = tmp_path / "civil-time-run.json"
    record = run_benchmark(MANIFEST_PATH, output_path)

    assert record["schema_version"] == "1.0"
    assert record["benchmark_id"] == "civil-time-validation-v2"
    assert record["aggregate_status"] == "passed"
    assert record["summary"] == MANIFEST["expected_summary"]
    assert record["reference"] == MANIFEST["reference_toolchain"]
    assert record["environment"]["timezone_database"]["zoneinfo_tzpath"] == []
    assert json.loads(output_path.read_text(encoding="utf-8")) == record


def test_benchmark_runs_offline_in_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("Civil-time validation attempted network socket creation.")

    monkeypatch.setattr(socket, "socket", deny_socket)
    monkeypatch.setattr(socket, "create_connection", deny_socket)
    record = run_benchmark(MANIFEST_PATH, tmp_path / "offline-run.json")

    assert record["aggregate_status"] == "passed"


def test_benchmark_cli_runs_offline(tmp_path: Path) -> None:
    guard_directory = tmp_path / "offline-guard"
    guard_directory.mkdir()
    (guard_directory / "sitecustomize.py").write_text(
        "import socket\n"
        "class OfflineSocket(socket.socket):\n"
        "    def __new__(cls, *args, **kwargs):\n"
        "        raise RuntimeError('network disabled by civil-time validation test')\n"
        "def deny_connection(*args, **kwargs):\n"
        "    raise RuntimeError('network disabled by civil-time validation test')\n"
        "socket.socket = OfflineSocket\n"
        "socket.create_connection = deny_connection\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "offline-cli-run.json"
    environment = os.environ.copy()
    environment["PYTHONTZPATH"] = ""
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(guard_directory),
            str(REPOSITORY_ROOT / "src"),
            environment.get("PYTHONPATH", ""),
        ]
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.civil_time",
            "--manifest",
            "validation/manifests/civil_time_v2.json",
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
    assert json.loads(output_path.read_text(encoding="utf-8"))["aggregate_status"] == "passed"
