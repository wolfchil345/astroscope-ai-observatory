"""Scientific accuracy, failure sensitivity, reproducibility and offline provenance."""

from __future__ import annotations

import ast
import json
import math
import os
import socket
import subprocess
import sys
from dataclasses import replace

import pytest
from astropy.utils import iers

from validation import celestial_coordinates as benchmark

MANIFEST, FIXTURE = benchmark.load_inputs()
CASES = FIXTURE["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_fixed_scientific_reference(case):
    with benchmark.fixed_earth_orientation():
        result = benchmark.evaluate_case(case, MANIFEST)
    assert result["status"] == "passed", result


@pytest.mark.parametrize("case", FIXTURE["invalid_inputs"], ids=lambda c: c["id"])
def test_invalid_input_contract(case):
    result = benchmark.evaluate_invalid(case, CASES[0])
    assert result["status"] == "passed", result


def test_fixture_coverage():
    assert len(CASES) == 768
    assert len({c["site"] for c in CASES}) == 8
    assert len({c["utc"] for c in CASES}) == 16
    assert len([c for c in CASES if c["category"].startswith("boundary")]) == 88
    assert len([c for c in CASES if c["category"] == "near_culmination"]) == 96
    assert len([c for c in CASES if c["category"] == "utc_date_boundary"]) == 8
    assert any(c["expected"]["altitude_deg"] < 0 for c in CASES)
    assert any(c["expected"]["altitude_deg"] > 89 for c in CASES)
    assert any(c["expected"]["azimuth_deg"] < 1 for c in CASES)
    assert any(c["expected"]["azimuth_deg"] > 359 for c in CASES)
    assert {c["site"] for c in CASES if c["latitude_deg"] > 70} == {"arctic"}
    assert {c["site"] for c in CASES if c["latitude_deg"] < -70} == {"antarctic"}


def test_reference_generator_independence_and_integrity():
    path = benchmark.ROOT / "validation/reference_generation/celestial_coordinates.py"
    imports = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(n.startswith(("astropy", "astroscope", "erfa")) for n in imports)
    assert benchmark.sha(path) == FIXTURE["reference"]["generator_sha256"]
    assert FIXTURE["reference"]["versions"]["skyfield"] == "1.55"
    assert len(FIXTURE["reference"]["kernel_sha256"]) == 64
    assert FIXTURE["reference"]["eop_sha256"] == benchmark.sha(benchmark.EOP)
    assert benchmark.sha(benchmark.MANIFEST) == benchmark.EXPECTED_MANIFEST_SHA256


def test_offline_record_and_settings_restoration(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Benchmark attempted network access")

    previous_table = iers.earth_orientation_table.get()
    previous_download = iers.conf.auto_download
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    output = tmp_path / "run.json"
    result = benchmark.run_benchmark(output)
    assert result["aggregate_status"] == "passed"
    assert result["failed_cases"] == result["failed_input_contracts"] == 0
    assert json.loads(output.read_text()) == result
    assert iers.earth_orientation_table.get() is previous_table
    assert iers.conf.auto_download == previous_download
    assert all(len(h) == 64 for h in result["input_sha256"].values())
    assert result["summary"]["azimuth_arcsec"]["count"] == 756
    assert result["summary"]["direction_arcsec"]["count"] == 768
    assert result["classification_summary"]["horizon_boundary_indeterminate"] == 5
    for summary in result["summary"].values():
        assert summary["inside_tolerance_percent"] == 100
        assert summary["median"] <= summary["maximum"]
        assert summary["rms"] + 1e-15 >= summary["mean"]
        assert summary["worst_case"]["id"] in {c["id"] for c in CASES}


def test_settings_restore_on_exception():
    previous_table = iers.earth_orientation_table.get()
    with pytest.raises(RuntimeError), benchmark.fixed_earth_orientation():
        raise RuntimeError("test failure")
    assert iers.earth_orientation_table.get() is previous_table


@pytest.mark.parametrize("kind", ["manifest", "fixture"])
def test_tampered_inputs_rejected(kind, tmp_path, monkeypatch):
    manifest = json.loads(benchmark.MANIFEST.read_text())
    manifest["files"]["validation/fixtures/celestial_coordinates_v1.json"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(benchmark, "MANIFEST", path)
    if kind == "fixture":
        monkeypatch.setattr(benchmark, "EXPECTED_MANIFEST_SHA256", benchmark.sha(path))
    with pytest.raises(ValueError, match="checksum"):
        benchmark.load_inputs()


@pytest.mark.parametrize(
    "field,offset,metric",
    [
        ("altitude_degrees", 3 / 3600, "altitude_arcsec"),
        ("azimuth_degrees", 11 / 3600, "azimuth_arcsec"),
        ("altitude_degrees", float("nan"), "altitude_arcsec"),
        ("azimuth_degrees", float("inf"), "azimuth_arcsec"),
    ],
)
def test_coordinate_tolerance_regressions(field, offset, metric, monkeypatch):
    original = benchmark.calculate_horizontal_coordinates

    def wrong(**kwargs):
        result = original(**kwargs)
        return replace(result, **{field: getattr(result, field) + offset})

    monkeypatch.setattr(benchmark, "calculate_horizontal_coordinates", wrong)
    with benchmark.fixed_earth_orientation():
        result = benchmark.evaluate_case(CASES[0], MANIFEST)
    assert result["status"] == "failed"
    assert metric in result["failures"]


@pytest.mark.parametrize("defect", ["horizon", "airmass", "utc", "sidereal"])
def test_noncoordinate_defects_fail(defect, monkeypatch):
    case = next(c for c in CASES if 30 < c["expected"]["altitude_deg"] < 70)
    original = benchmark.calculate_horizontal_coordinates
    original_time = benchmark.calculate_astronomical_time

    def wrong(**kwargs):
        result = original(**kwargs)
        if defect == "horizon":
            return replace(result, is_above_horizon=not result.is_above_horizon)
        if defect == "airmass":
            return replace(result, airmass=result.airmass * 1.01)
        return replace(result, utc_datetime_iso="2020-01-01T00:00:00+00:00")

    def wrong_time(**kwargs):
        result = original_time(**kwargs)
        return replace(result, local_sidereal_time_hours=result.local_sidereal_time_hours + 0.1)

    if defect == "sidereal":
        monkeypatch.setattr(benchmark, "calculate_astronomical_time", wrong_time)
    else:
        monkeypatch.setattr(benchmark, "calculate_horizontal_coordinates", wrong)
    with benchmark.fixed_earth_orientation():
        result = benchmark.evaluate_case(case, MANIFEST)
    assert result["status"] == "failed", result


@pytest.mark.parametrize("altitude", [-0.1, 0.0, 0.1, 4.9, 5.1, 19.9, 20.1, 89.5])
def test_boundary_cases_are_explicit(altitude):
    case = next(c for c in CASES if c["category"] == f"boundary_{altitude}")
    with benchmark.fixed_earth_orientation():
        result = benchmark.evaluate_case(case, MANIFEST)
    assert result["status"] == "passed"
    if altitude == 0:
        assert result["horizon_comparison"].startswith("boundary_indeterminate")
    else:
        assert result["actual"]["above_horizon"] == (altitude > 0)
    if altitude < 5:
        assert result["actual"]["airmass"] is None
    elif altitude < 20:
        assert result["airmass_regime"] == "low_altitude_model_only"
    else:
        assert result["airmass_regime"] == "plane_parallel_approximation"
    assert ("azimuth_arcsec" in result["excluded_metrics"]) == (altitude > 89)


def test_circular_metrics_and_zenith():
    assert benchmark.circular_error(359.99, 0.01, 360) == pytest.approx(0.02)
    assert benchmark.circular_error(23.99, 0.01, 24) == pytest.approx(0.02)
    assert benchmark.direction_error(90, 0, 90, 180) < 1e-9
    assert math.isnan(benchmark.direction_error(math.nan, 0, 0, 0))


def test_statistics_include_failures_and_worst_case():
    rows = [
        {"id": str(i), "scenario": {"site": "test"}, "errors": {"a": v}, "excluded_metrics": {}}
        for i, v in enumerate([0.0, 1.0, 2.0, 3.0])
    ]
    s = benchmark.summarize(rows, {"a": 2})["a"]
    assert s["mean"] == s["median"] == 1.5
    assert s["rms"] == pytest.approx(math.sqrt(3.5))
    assert s["inside_tolerance"] == 3
    assert s["inside_tolerance_percent"] == 75
    assert s["worst_case"]["id"] == "3"
    rows[0]["errors"]["a"] = math.nan
    s = benchmark.summarize(rows, {"a": 2})["a"]
    assert s["nonfinite_count"] == 1
    assert s["mean"] is None  # Nonfinite failures cannot disappear from averages.
    assert s["inside_tolerance_percent"] == 50


def test_cli_runs_without_network_or_reference_engine(tmp_path):
    guard = tmp_path / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import socket, sys\n"
        "def deny(*a, **k): raise RuntimeError('network is disabled')\n"
        "socket.socket.connect = deny\nsocket.create_connection = deny\n"
        "sys.modules['skyfield'] = None\n"
    )
    output = tmp_path / "offline.json"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(guard), str(benchmark.ROOT / "src"), str(benchmark.ROOT)]
        ),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "validation.celestial_coordinates", "--output", str(output)],
        cwd=benchmark.ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text())["aggregate_status"] == "passed"


def test_cli_failure_record(tmp_path, monkeypatch):
    case = CASES[0]
    monkeypatch.setattr(
        benchmark,
        "load_inputs",
        lambda: (MANIFEST, {**FIXTURE, "cases": [case], "invalid_inputs": []}),
    )
    original = benchmark.calculate_horizontal_coordinates

    def wrong(**kwargs):
        return replace(original(**kwargs), altitude_degrees=math.nan)

    monkeypatch.setattr(benchmark, "calculate_horizontal_coordinates", wrong)
    output = tmp_path / "failed.json"
    monkeypatch.setattr(sys, "argv", ["benchmark", "--output", str(output)])
    assert benchmark.main() == 1
    record = json.loads(output.read_text())
    assert record["failed_cases"] == 1
    assert record["results"][0]["actual"]["altitude_deg"] is None
    assert record["summary"]["altitude_arcsec"]["nonfinite_count"] == 1
