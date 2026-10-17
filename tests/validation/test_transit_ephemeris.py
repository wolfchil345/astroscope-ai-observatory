"""Independent evidence, failure sensitivity and offline contract for Mission 35."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from dataclasses import fields, replace
from pathlib import Path

import pytest

from astroscope import transit_scheduler as production
from validation import transit_ephemeris as benchmark

MANIFEST, POLICY, FIXTURE = benchmark.load_inputs()
EPHEMERIDES = {e["id"]: e for e in FIXTURE["ephemerides"]}


@pytest.mark.parametrize("case", FIXTURE["events"], ids=lambda c: c["id"])
def test_event_against_frozen_decimal_reference(case):
    assert (
        benchmark.check_event(case, EPHEMERIDES[case["ephemeris_id"]], POLICY)["status"] == "passed"
    )


@pytest.mark.parametrize("case", FIXTURE["ranges"], ids=lambda c: c["id"])
def test_range_against_frozen_enumeration(case):
    result = benchmark.check_range(case, EPHEMERIDES[case["ephemeris_id"]])
    assert result["status"] == ("passed" if case["eligible"] else "boundary_indeterminate")


@pytest.mark.parametrize("case", benchmark.rejection_cases(), ids=lambda c: c["id"])
def test_rejection_contract(case):
    assert benchmark.check_rejection(case, EPHEMERIDES["dyadic"])["status"] == "expected_rejection"


def test_manifest_and_coverage():
    assert MANIFEST["counts"] == {
        "events": 189,
        "ranges": 189,
        "ephemerides": 9,
        "covariance_diagnostics": 20,
    }
    assert {c["cycle"] for c in FIXTURE["events"]} == {-10000, -100, -1, 0, 1, 100, 10000}
    assert sum(c["eligible"] for c in FIXTURE["ranges"]) == 165
    assert {e["uncertainty_status"] for e in FIXTURE["ephemerides"]} == {
        "unknown_component",
        "supplied",
        "explicit_zero",
    }
    assert any(not c["expected_cycles"] and c["eligible"] for c in FIXTURE["ranges"])


@pytest.mark.parametrize("relative", [benchmark.MANIFEST, *MANIFEST["files"]])
def test_corrupt_evidence_is_rejected(tmp_path, relative):
    for name in [benchmark.MANIFEST, *MANIFEST["files"]]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(benchmark.ROOT / name, destination)
    path = tmp_path / relative
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum mismatch"):
        benchmark.load_inputs(tmp_path)


@pytest.mark.parametrize(
    "field",
    [
        "mid_transit_jd",
        "ingress_jd",
        "egress_jd",
        "observation_start_jd",
        "observation_end_jd",
        "timing_uncertainty_days",
    ],
)
@pytest.mark.parametrize("bad_value", ["offset", "nan"])
def test_wrong_or_nonfinite_numerical_output_fails(monkeypatch, field, bad_value):
    original = production.build_transit_event

    def altered(*args, **kwargs):
        result = original(*args, **kwargs)
        value = getattr(result, field) + 1 / 86400 if bad_value == "offset" else float("nan")
        return replace(result, **{field: value})

    monkeypatch.setattr(production, "build_transit_event", altered)
    assert (
        benchmark.check_event(FIXTURE["events"][0], EPHEMERIDES["dyadic"], POLICY)["status"]
        == "failed"
    )


@pytest.mark.parametrize("eligible", [True, False])
@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_missing_extra_duplicate_events_fail(monkeypatch, eligible, mutation):
    case = next(
        c
        for c in FIXTURE["ranges"]
        if c["eligible"] == eligible and c["id"].endswith("inclusive_three")
    )
    original = production.predict_transits

    def altered(*args, **kwargs):
        result = original(*args, **kwargs)
        if mutation == "missing":
            return ()
        if mutation == "duplicate":
            return result + result
        extra = production.build_transit_event(args[0], 5000)
        return (*result, extra)

    monkeypatch.setattr(production, "predict_transits", altered)
    assert benchmark.check_range(case, EPHEMERIDES[case["ephemeris_id"]])["status"] == "failed"


@pytest.mark.parametrize(
    "method",
    [
        "calculate_transit_number_on_or_after",
        "calculate_transit_number_on_or_before",
    ],
)
def test_gross_boundary_index_error_fails(monkeypatch, method):
    case = next(c for c in FIXTURE["ranges"] if not c["eligible"])
    monkeypatch.setattr(production, method, lambda *args: 12345)
    assert benchmark.check_range(case, EPHEMERIDES[case["ephemeris_id"]])["status"] == "failed"


def test_stage_a_import_boundary_and_reproducibility(tmp_path):
    generator = benchmark.ROOT / "validation/reference_generation/transit_ephemeris.py"
    tree = ast.parse(generator.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module.split(".")[0])
    assert set(imports) <= sys.stdlib_module_names | {"__future__"}
    run = subprocess.run(
        [sys.executable, "-I", str(generator), "--output-root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    for name in [benchmark.FIXTURE, benchmark.MANIFEST]:
        assert (tmp_path / name).read_bytes() == (benchmark.ROOT / name).read_bytes()


def test_runner_never_imports_reference_generator():
    tree = ast.parse(Path(benchmark.__file__).read_text(encoding="utf-8"))
    assert "reference_generation" not in {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert "validation.reference_generation.transit_ephemeris" not in sys.modules


def test_full_cli_without_network_or_reference_engines(tmp_path):
    # sitecustomize is loaded before production/validation imports in the fresh child.
    (tmp_path / "sitecustomize.py").write_text("""
import importlib.abc
import socket
import sys
class BlockReference(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("validation.reference_generation", "skyfield", "astropy")):
            raise AssertionError("Forbidden reference/astronomy import: " + fullname)
sys.meta_path.insert(0, BlockReference())
def blocked(*args, **kwargs):
    raise AssertionError("Network is disabled")
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
""")
    destination = tmp_path / "result.json"
    run = subprocess.run(
        [sys.executable, "-m", "validation.transit_ephemeris", "--output", str(destination)],
        cwd=benchmark.ROOT,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    record = json.loads(destination.read_text(encoding="utf-8"))
    assert record["overall_passed"]
    assert record["counts"] == {
        "passed": 354,
        "boundary_indeterminate": 24,
        "expected_rejection": 49,
    }
    assert record["scientific_status"].startswith("bounded_arithmetic_only")
    assert record["range_topology"]["eligible"] == 165
    assert len(record["environment"]["input_sha256"]) == 5


def test_cli_failure_exit_and_record(monkeypatch, tmp_path):
    monkeypatch.setattr(
        benchmark, "run_benchmark", lambda: {"overall_passed": False, "counts": {"failed": 1}}
    )
    output = tmp_path / "failed.json"
    monkeypatch.setattr(sys, "argv", ["benchmark", "--output", str(output)])
    assert benchmark.main() == 1
    assert json.loads(output.read_text(encoding="utf-8"))["counts"]["failed"] == 1


def test_none_is_not_a_scientific_zero_claim():
    unknown, zero = (benchmark.make_ephemeris(EPHEMERIDES[k]) for k in ["unknown", "explicit_zero"])
    assert production.calculate_timing_uncertainty_days(unknown, 1000) == 0.0
    assert production.calculate_timing_uncertainty_days(zero, 1000) == 0.0
    assert EPHEMERIDES["unknown"]["uncertainty_status"] == "unknown_component"
    assert EPHEMERIDES["explicit_zero"]["uncertainty_status"] == "explicit_zero"


@pytest.mark.parametrize("case", FIXTURE["covariance_diagnostics"])
def test_covariance_model_gap_is_explicit(case):
    assert case["status"] == "unsupported_model_diagnostic"
    value = production.calculate_timing_uncertainty_days(
        benchmark.make_ephemeris(EPHEMERIDES[case["ephemeris_id"]]), case["cycle"]
    )
    assert value == pytest.approx(float(case["independent_sigma_days"]), rel=1e-12, abs=1e-15)
    assert abs(value - float(case["correlated_sigma_days"])) > 1e-8
    assert (float(case["correlated_sigma_days"]) > value) == (
        case["cycle"] * float(case["rho"]) > 0
    )


def test_model_has_no_time_coordinate_or_covariance_contract():
    names = {f.name for f in fields(production.TransitEphemeris)}
    assert not names & {"time_scale", "time_coordinate", "reference_position", "covariance"}
    # This limitation audit must be updated if a later mission introduces these contracts.
    for module in ["transit_visibility", "transit_schedule_exports"]:
        path = benchmark.ROOT / f"src/astroscope/{module}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        times = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Time"
        ]
        assert times
        assert all(
            any(
                k.arg == "scale" and isinstance(k.value, ast.Constant) and k.value.value == "utc"
                for k in node.keywords
            )
            for node in times
        )


def test_literal_published_midpoints_and_capacity_boundary():
    # Independently hand-added historical coefficients, not values generated in this test.
    e = EPHEMERIDES["wasp12_2011_historical"]
    for n, expected in [(-1, "2454507.88539755"), (1, "2454510.06824245")]:
        case = next(
            c for c in FIXTURE["events"] if c["ephemeris_id"] == e["id"] and c["cycle"] == n
        )
        assert case["expected"]["mid_transit_jd"] == expected
    ep = benchmark.make_ephemeris(EPHEMERIDES["dyadic"])
    events = production.predict_transits(ep, 2450000.25, 2450004.25, maximum_events=3)
    assert [e.transit_number for e in events] == [0, 1, 2]


@pytest.mark.parametrize(
    "method",
    [
        production.calculate_transit_number_on_or_after,
        production.calculate_transit_number_on_or_before,
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_selection_target_is_rejected(method, value):
    with pytest.raises(production.TransitSchedulerError):
        method(benchmark.make_ephemeris(EPHEMERIDES["dyadic"]), value)
