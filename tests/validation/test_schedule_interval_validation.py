"""Distinct contracts for independent Mission 32 schedule evidence."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import zoneinfo
from collections.abc import Generator
from pathlib import Path
from zoneinfo import ZoneInfo, reset_tzpath

import pytest

from validation import schedule_interval
from validation.reference_generation import generate_schedule_interval_fixture as generator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = "validation/manifests/schedule_interval_v1.json"
MANIFEST = ROOT / MANIFEST_PATH
FIXTURE = ROOT / "validation/fixtures/schedule_interval_reference_v1.json"
GENERATOR = ROOT / "validation/reference_generation/generate_schedule_interval_fixture.py"
WORKFLOW = ROOT / ".github/workflows/quality-gate.yml"
MANIFEST_DATA, FIXTURE_DATA = schedule_interval.load_verified_inputs(MANIFEST_PATH)


@pytest.fixture(autouse=True)
def pinned_python_tzdata(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Run Stage B in its canonical tzdata-only environment."""

    original_tzpath = zoneinfo.TZPATH
    monkeypatch.setenv("PYTHONTZPATH", "")
    reset_tzpath()
    ZoneInfo.clear_cache()
    try:
        yield
    finally:
        reset_tzpath(original_tzpath)
        ZoneInfo.clear_cache()


# 37 direct evidence contracts: each fixture case remains independently executed.
@pytest.mark.parametrize("case", FIXTURE_DATA["cases"], ids=lambda case: case["id"])
def test_fixture_case(case: dict[str, object]) -> None:
    assert schedule_interval.execute_case(case)["category"] == case["category"]


# Eight integrity/schema contracts.
def test_manifest_schema_version() -> None:
    assert MANIFEST_DATA["schema_version"] == "1.0"


def test_fixture_schema_and_case_count() -> None:
    assert FIXTURE_DATA["schema_version"] == "1.0"
    assert len(FIXTURE_DATA["cases"]) == 37


def test_fixture_case_ids_are_unique_strings() -> None:
    identifiers = [case["id"] for case in FIXTURE_DATA["cases"]]
    assert len(identifiers) == len(set(identifiers)) == 37
    assert all(isinstance(identifier, str) for identifier in identifiers)


def test_fixture_file_digest_matches_manifest() -> None:
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == MANIFEST_DATA["fixture_sha256"]


def test_manifest_payload_digest_matches_content() -> None:
    assert (
        schedule_interval._payload_sha(MANIFEST_DATA, "manifest_payload_sha256")
        == MANIFEST_DATA["manifest_payload_sha256"]
    )


def test_reference_archives_are_the_pinned_2026c_inputs() -> None:
    archives = MANIFEST_DATA["reference_toolchain"]["archives"]
    assert [archive["filename"] for archive in archives] == [
        "tzcode2026c.tar.gz",
        "tzdata2026c.tar.gz",
    ]
    assert [archive["sha256"] for archive in archives] == [
        generator.TZCODE_SHA256,
        generator.TZDATA_SHA256,
    ]


def test_schedule_blob_matches_approved_mission_29_source() -> None:
    source = ROOT / MANIFEST_DATA["system_under_validation"]["schedule_source_path"]
    assert (
        schedule_interval._git_blob_sha(source)
        == MANIFEST_DATA["system_under_validation"]["schedule_source_blob_sha"]
    )


def test_benchmark_input_file_declaration_is_sorted_and_complete() -> None:
    paths = MANIFEST_DATA["benchmark_input_files"]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == 7


# Six independent provenance and generator-safety contracts.
def test_captured_zdump_transformation_reproduces_all_37_committed_cases() -> None:
    assert generator.canonical_fixture_bytes(generator.CAPTURED_ZDUMP_2026C) == FIXTURE.read_bytes()


def test_captured_zdump_parser_contains_evidence_for_all_four_zones() -> None:
    parsed = generator.parse_zdump_transition_evidence(generator.CAPTURED_ZDUMP_2026C)
    assert tuple(parsed) == generator.ZONES
    assert all(len(samples) >= 2 for samples in parsed.values())


def test_archive_layout_requires_root_level_iana_contents(tmp_path: Path) -> None:
    code_dir = tmp_path / "tzcode"
    data_dir = tmp_path / "tzdata"
    nested_code = code_dir / "unexpected-wrapper"
    nested_data = data_dir / "unexpected-wrapper"
    nested_code.mkdir(parents=True)
    nested_data.mkdir(parents=True)
    for filename in generator.REQUIRED_CODE_FILES:
        (nested_code / filename).touch()
    for filename in generator.REQUIRED_DATA_FILES:
        (nested_data / filename).touch()
    with pytest.raises(ValueError, match="archive root"):
        generator.require_root_level_archive_layout(code_dir, data_dir)
    for filename in generator.REQUIRED_CODE_FILES:
        (code_dir / filename).touch()
    for filename in generator.REQUIRED_DATA_FILES:
        (data_dir / filename).touch()
    generator.require_root_level_archive_layout(code_dir, data_dir)


def test_generator_ast_inspection_detects_direct_and_from_imports() -> None:
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert not any(name == "astroscope" or name.startswith("astroscope.") for name in imported)
    assert not any(name == "zoneinfo" or name.startswith("zoneinfo.") for name in imported)


def test_generator_has_no_network_client_import() -> None:
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    names = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        for alias in (node.names if isinstance(node, ast.Import) else ())
    }
    names.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert names.isdisjoint({"requests", "urllib", "http", "socket", "httpx"})


def test_generator_requires_both_archives_unless_capture_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        generator.main(["--output", str(tmp_path / "fixture.json")])


# Four benchmark/result-model contracts.
def test_benchmark_passes_with_the_canonical_environment(tmp_path: Path) -> None:
    record = schedule_interval.run_benchmark(MANIFEST_PATH, tmp_path / "record.json")
    assert record["aggregate_status"] == "passed"
    assert record["summary"] == MANIFEST_DATA["expected_summary"]


def test_failed_environment_pin_fails_the_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PYTHONTZPATH", raising=False)
    reset_tzpath()
    record = schedule_interval.run_benchmark(MANIFEST_PATH, tmp_path / "failed-environment.json")
    assert record["aggregate_status"] == "failed"
    assert record["failure"]["category"] == "environment"


def test_benchmark_record_includes_cases_summary_and_reference(tmp_path: Path) -> None:
    record = schedule_interval.run_benchmark(MANIFEST_PATH, tmp_path / "schema.json")
    assert len(record["cases"]) == 37
    assert record["reference"] == MANIFEST_DATA["reference_toolchain"]
    assert record["benchmark_inputs"]["digest_algorithm"] == "sha256-path-null-file-sha256-v1"
    continuity = next(case for case in record["cases"] if case["id"] == "utc-continuity")
    assert continuity["actual"]["block_count"] == 1
    assert continuity["mismatch"] == {}


def test_benchmark_record_written_to_disk_matches_return_value(tmp_path: Path) -> None:
    output = tmp_path / "persisted.json"
    record = schedule_interval.run_benchmark(MANIFEST_PATH, output)
    assert json.loads(output.read_text(encoding="utf-8")) == record


# Four environment/version contracts.
def test_source_package_version_is_read_from_pyproject() -> None:
    assert schedule_interval._source_version() == importlib.metadata.version(
        "astroscope-ai-observatory"
    )
    assert (
        '"0.2.0"' not in schedule_interval.__file__
        and "0.2.0" not in (ROOT / "validation/schedule_interval.py").read_text()
    )


def test_tzdata_distribution_and_iana_release_are_pinned() -> None:
    assert importlib.metadata.version("tzdata") == "2026.3"
    assert __import__("tzdata").IANA_VERSION == "2026c"


def test_tzif_hashes_cover_all_tested_zones() -> None:
    hashes = schedule_interval._tzif_hashes()
    assert hashes == MANIFEST_DATA["expected_tzif_sha256"]


def test_canonical_timezone_environment_records_empty_tzpath() -> None:
    environment, checks = schedule_interval._environment_record(MANIFEST_DATA)
    assert environment["timezone_database"]["pythontzpath"] == ""
    assert environment["timezone_database"]["zoneinfo_tzpath"] == []
    assert all(check["status"] == "passed" for check in checks)


# Four reproducibility/digest contracts.
def test_digest_uses_path_null_then_raw_file_digest_bytes() -> None:
    digest, files = schedule_interval.calculate_benchmark_input_digest(MANIFEST_DATA)
    aggregate = hashlib.sha256()
    for item in files:
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(item["sha256"]))
    assert digest == aggregate.hexdigest()


def test_digest_rejects_an_unknown_algorithm() -> None:
    bad = {**MANIFEST_DATA, "benchmark_input_digest_algorithm": "sha256-text-v0"}
    with pytest.raises(schedule_interval.ScheduleIntervalValidationError, match="Unsupported"):
        schedule_interval.calculate_benchmark_input_digest(bad)


def test_digest_rejects_unsorted_paths() -> None:
    bad = {
        **MANIFEST_DATA,
        "benchmark_input_files": list(reversed(MANIFEST_DATA["benchmark_input_files"])),
    }
    with pytest.raises(
        schedule_interval.ScheduleIntervalValidationError, match="unique and sorted"
    ):
        schedule_interval.calculate_benchmark_input_digest(bad)


def test_captured_stage_a_output_is_byte_reproducible() -> None:
    first = generator.canonical_fixture_bytes(generator.CAPTURED_ZDUMP_2026C)
    second = generator.canonical_fixture_bytes(generator.CAPTURED_ZDUMP_2026C)
    assert first == second


# Two CLI/offline contracts.
def test_generator_capture_cli_writes_the_canonical_fixture(tmp_path: Path) -> None:
    output = tmp_path / "captured-fixture.json"
    assert generator.main(["--captured-reference", "--output", str(output)]) == 0
    assert output.read_bytes() == FIXTURE.read_bytes()


def test_benchmark_cli_runs_without_network_requirement(tmp_path: Path) -> None:
    output = tmp_path / "cli.json"
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONTZPATH": ""}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.schedule_interval",
            "--manifest",
            MANIFEST_PATH,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (
        json.loads(output.read_text(encoding="utf-8"))["environment"]["network_required"] is False
    )


# Three CI/artifact contracts.
def test_ci_runs_the_schedule_interval_benchmark() -> None:
    assert "Run schedule-interval validation benchmark" in WORKFLOW.read_text(encoding="utf-8")


def test_ci_uploads_the_schedule_interval_validation_artifact() -> None:
    assert "schedule-interval-validation-record" in WORKFLOW.read_text(encoding="utf-8")


def test_ci_supplies_canonical_timezone_and_git_provenance_environment() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'PYTHONTZPATH: ""' in workflow
    assert "ASTROSCOPE_IMPLEMENTATION_COMMIT" in workflow
    assert "ASTROSCOPE_CHECKOUT_COMMIT" in workflow
