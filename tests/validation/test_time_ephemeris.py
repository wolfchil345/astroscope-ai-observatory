"""Mission 42 rejects false clock qualification and corrupted mapping evidence."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal, localcontext

import pytest

from validation import time_ephemeris as te


@pytest.fixture
def inputs():
    return copy.deepcopy(te.load_inputs())


def test_complete_integrated_model_evidence(inputs):
    result = te.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert len(result["cases"]) == 14
    assert result["diagnostics"]["historical_candidate_minus_reference"]["count"] == 12
    assert result["diagnostics"]["epoch_probe_candidate_minus_reference"]["count"] == 2
    assert result["diagnostics"]["reader_offset_difference"]["count"] == 14
    assert result["full_reference_status"] == "unqualified"
    assert result["physical_geocentric_clock_bound_seconds"] is None
    assert result["physical_site_clock_bound_seconds"] is None
    assert result["physical_arrival_bound_seconds"] is None
    assert not result["observing_eligible"]
    assert len(result["site_mapping_cases"]) == 48
    assert all(not r["observing_eligible"] for r in result["site_mapping_cases"])
    assert result["combined_counts"] == inputs[-1]["combined_counts"]
    assert result["combined_counts"]["executed"] == 0
    assert result["combined_counts"]["blocked"] == 288
    assert result["same_kernel_reader_check"]


def test_zero_candidate_residual_does_not_qualify_accuracy(inputs):
    by_tt = {
        Decimal(r["tt_seconds_from_j2000"]): Decimal(r["cspice"]["delta_seconds"])
        for r in inputs[1]["cases"]
    }
    result = te.evaluate_inputs(*inputs, candidate=by_tt.__getitem__)
    assert result["audit_passed"]
    assert all(Decimal(r["candidate_minus_reference_seconds"]) == 0 for r in result["cases"])
    assert result["full_reference_status"] == "unqualified"
    assert not result["observing_eligible"]


def test_large_candidate_difference_is_diagnostic_not_tuned_acceptance(inputs):
    result = te.evaluate_inputs(*inputs, candidate=lambda tt: Decimal("1"))
    assert result["audit_passed"]
    assert Decimal(
        result["diagnostics"]["historical_candidate_minus_reference"]["maximum_absolute_seconds"]
    ) > Decimal("0.9")
    assert result["physical_site_clock_bound_seconds"] is None
    assert result["combined_counts"]["executed"] == 0


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("quantity", "TDB_minus_TT", "kernel_convention"),
        ("units", "days", "kernel_convention"),
        ("argument_scale", "TT", "kernel_convention"),
        ("origin", "site", "kernel_convention"),
        ("kernel_sha256", "0" * 64, "kernel_identity"),
        ("kernel_size_bytes", 1, "kernel_identity"),
        ("forbidden_imports", ["erfa"], "independence_boundary"),
        ("same_kernel_for_both_readers", False, "independence_boundary"),
        ("physical_geocentric_clock_bound_seconds", "1e-9", "unsupported_reference_claim"),
        ("observing_eligible", True, "unsupported_reference_claim"),
        ("model_id", "site-clock", "reference_model"),
    ],
)
def test_reject_mislabeled_reference(inputs, key, value, error):
    inputs[1][key] = value
    with pytest.raises(te.TimeEphemerisError, match=error):
        te.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("delta_seconds", "0.001", "trace_continuity"),
        ("tt_minus_tdb_seconds", "1", "equation_sign"),
        ("next_delta_seconds", "0", "solver_update"),
        ("argument_et_seconds", "764200869.184", "tdb_argument"),
        ("argument_quantization_seconds", "0", "argument_quantization"),
        ("equation_residual_seconds", "0", "equation_sign"),
    ],
)
def test_detect_trace_faults(inputs, key, value, error):
    inputs[1]["cases"][0]["cspice"]["trace"][0][key] = value
    with pytest.raises(te.TimeEphemerisError, match=error):
        te.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing", "sample_count"),
        ("duplicate", "sample_context"),
        ("wrong_tt", "sample_context"),
        ("wrong_method", "solver_method"),
        ("wrong_convergence", "convergence_claim"),
        ("wrong_solution", "solution_trace"),
        ("collapsed_jd", "tdb_argument"),
        ("empty_trace", "trace_length"),
        ("bad_historical_tt", "historical_tt_input"),
        ("geocentre_site_dependence", "historical_geocentre_inventory"),
        ("loosen_tolerance", "frozen_tolerance"),
        ("promote_prior", "prior_combined_gate"),
    ],
)
def test_mutations_fail_closed(inputs, mutation, error):
    row = inputs[1]["cases"][0]
    if mutation == "missing":
        inputs[1]["cases"].pop()
    elif mutation == "duplicate":
        inputs[1]["cases"][1] = copy.deepcopy(row)
    elif mutation == "wrong_tt":
        row["tt_seconds_from_j2000"] = "0"
    elif mutation == "wrong_method":
        row["cspice"]["method"] = "newton"
    elif mutation == "wrong_convergence":
        row["cspice"]["converged"] = False
    elif mutation == "wrong_solution":
        row["cspice"]["delta_seconds"] = "0"
    elif mutation == "collapsed_jd":
        row["jplephem"]["trace"][0]["argument_jd_parts"] = ["2460390", "0"]
    elif mutation == "empty_trace":
        row["cspice"]["trace"] = []
    elif mutation == "bad_historical_tt":
        inputs[3]["cases"][0]["tt_jd_parts"][1] = "0"
    elif mutation == "geocentre_site_dependence":
        inputs[3]["cases"][0]["astropy_geocentric_seconds"] = "0"
    elif mutation == "loosen_tolerance":
        inputs[0]["reader_contract"]["offset_agreement_seconds"] = "1e-3"
    elif mutation == "promote_prior":
        inputs[-1]["combined_counts"]["executed"] = 288
    with pytest.raises(te.TimeEphemerisError, match=error):
        te.evaluate_inputs(*inputs)


@pytest.mark.parametrize("value", ["nan", "Infinity", "-Infinity", "", "1e999", 1.0, True])
def test_finite_decimal_strings_required(value):
    with pytest.raises(te.TimeEphemerisError, match="finite_decimal_string_required"):
        te.number(value)


def test_decimal_context_isolation_and_signed_results(inputs):
    expected = te.evaluate_inputs(*inputs)
    with localcontext() as ctx:
        ctx.prec = 6
        actual = te.evaluate_inputs(*inputs)
    assert actual == expected
    values = [Decimal(r["candidate_minus_reference_seconds"]) for r in actual["cases"][:12]]
    assert Decimal(
        actual["diagnostics"]["historical_candidate_minus_reference"]["maximum_absolute_seconds"]
    ) == max(map(abs, values))


def test_candidate_nonfinite_is_rejected(inputs):
    with pytest.raises(te.TimeEphemerisError, match="candidate_nonfinite"):
        te.evaluate_inputs(*inputs, candidate=lambda tt: Decimal("NaN"))


def test_true_frozen_inputs_and_import_boundary():
    policy, fixture, *_ = te.load_inputs()
    source = te.ROOT / "validation/reference_generation/time_ephemeris.py"
    assert fixture["policy_sha256"] == te.sha(te.POLICY)
    assert fixture["generator_sha256"] == te.sha(source)
    assert fixture["packages"] == policy["reference_packages"]
    tree = ast.parse(source.read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    assert not imports & {"astropy", "erfa", "pint", "skyfield", "astroscope", "validation"}
    assert {"spiceypy", "jplephem"} <= imports


def test_manifest_tampering_is_rejected(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"files": {}}')
    monkeypatch.setattr(te, "MANIFEST", manifest)
    with pytest.raises(te.TimeEphemerisError, match="manifest_checksum"):
        te.load_inputs()


def test_clock_argument_quantization_is_not_hidden(inputs):
    result = te.evaluate_inputs(*inputs)
    maximum = max(
        Decimal(r["max_argument_quantization_seconds"]["cspice"]) for r in result["cases"]
    )
    assert maximum > Decimal("1e-9")
    assert all(
        Decimal(r["max_argument_quantization_seconds"]["jplephem"]) < Decimal("1e-9")
        for r in result["cases"]
    )


def test_cli_offline_provenance(tmp_path):
    output = tmp_path / "result.json"
    env = {
        **os.environ,
        "ASTROSCOPE_IMPLEMENTATION_COMMIT": "head-marker",
        "ASTROSCOPE_CHECKOUT_COMMIT": "checkout-marker",
    }
    subprocess.run(
        [sys.executable, "-m", "validation.time_ephemeris", "--output", str(output)],
        cwd=te.ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(output.read_text())
    assert result["audit_passed"]
    assert result["implementation_commit"] == "head-marker"
    assert result["checkout_commit"] == "checkout-marker"
    assert not result["observing_eligible"]
    assert isinstance(result["working_tree_dirty"], bool)


def test_network_denied():
    with pytest.raises(RuntimeError, match="offline"):
        te.deny_network()
