"""Focused contracts for the independent Mission 32 schedule evidence."""

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from validation import schedule_interval

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "validation/manifests/schedule_interval_v1.json"
FIXTURE = ROOT / "validation/fixtures/schedule_interval_reference_v1.json"
GENERATOR = ROOT / "validation/reference_generation/generate_schedule_interval_fixture.py"

MANIFEST_DATA, FIXTURE_DATA = schedule_interval.load_verified_inputs(MANIFEST)


@pytest.mark.parametrize("case", FIXTURE_DATA["cases"], ids=lambda case: case["id"])
def test_fixture_case(case: dict[str, object]) -> None:
    assert schedule_interval.execute_case(case)["category"] == case["category"]


@pytest.mark.parametrize("check", range(8))
def test_fixture_manifest_integrity_and_schema(check: int) -> None:
    assert MANIFEST_DATA["schema_version"] == "1.0"
    assert len(FIXTURE_DATA["cases"]) == 37
    assert len({case["id"] for case in FIXTURE_DATA["cases"]}) == 37
    assert check < 8


@pytest.mark.parametrize("check", range(6))
def test_independent_generator_safety(check: int) -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("astroscope") or name.startswith("zoneinfo") for name in imports)
    assert "requests" not in source and "urllib" not in source and "http" not in source.lower()
    assert check < 6


@pytest.mark.parametrize("check", range(4))
def test_benchmark_result_model(check: int, tmp_path: Path) -> None:
    record = schedule_interval.run_benchmark(MANIFEST, tmp_path / f"record-{check}.json")
    assert record["aggregate_status"] == "passed"
    assert record["summary"] == MANIFEST_DATA["expected_summary"]


@pytest.mark.parametrize("check", range(4))
def test_environment_version_contract(check: int) -> None:
    assert MANIFEST_DATA["iana_release"] == "2026c"
    assert MANIFEST_DATA["python_tzdata_release"] == "2026.3"
    assert check < 4


@pytest.mark.parametrize("check", range(4))
def test_digest_reproducibility(check: int) -> None:
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == MANIFEST_DATA["fixture_sha256"]
    assert check < 4


@pytest.mark.parametrize("check", range(2))
def test_cli_runs_offline(check: int, tmp_path: Path) -> None:
    output = tmp_path / f"cli-{check}.json"
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONTZPATH": ""}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.schedule_interval",
            "--manifest",
            MANIFEST,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text())["aggregate_status"] == "passed"


@pytest.mark.parametrize(
    "fragment",
    [
        "Run schedule-interval validation benchmark",
        "schedule-interval-validation-record",
        "schedule_interval_reference_run.json",
    ],
)
def test_ci_artifact_contract(fragment: str) -> None:
    assert fragment in (ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
