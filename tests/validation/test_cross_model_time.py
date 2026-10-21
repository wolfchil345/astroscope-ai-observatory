"""Cross-model evidence, provenance, convention faults and qualification guards."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal as D
from decimal import localcontext

import pytest

from validation import cross_model_time as cm


@pytest.fixture
def inputs():
    return copy.deepcopy(cm.load_inputs())


def test_complete_offline_cross_model_evidence(inputs):
    result = cm.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert len(result["cases"]) == 14
    assert result["diagnostics"]["historical"]["inpop21a_minus_de440t_seconds"]["count"] == 12
    assert result["cross_model_status"] == "qualified_for_sampled_geocentric_diagnostics_only"
    assert result["evidence"] == dict(claims_reviewed=6, applicable_physical_bounds=0)
    assert result["independence"] == cm.INDEPENDENCE
    assert result["site_clocks_unqualified"] == 48
    assert result["combined_counts"] == cm.COUNTS
    assert result["unresolved_components"] == cm.COMPONENTS
    assert all(result[k] is None for k in cm.BOUND_KEYS)
    assert result["full_reference_status"] == "unqualified"
    assert not result["observing_eligible"]


def test_triangle_sign_and_epoch_without_fitted_correction(inputs):
    result = cm.evaluate_inputs(*inputs)
    with localcontext() as ctx:
        ctx.prec = 70
        for row in result["cases"]:
            assert D(row["inpop21a_minus_de440t_seconds"]) == (
                D(row["inpop21a_tdb_minus_tt_seconds"]) - D(row["de440t_tdb_minus_tt_seconds"])
            )
            assert abs(D(row["triangle_closure_seconds"])) <= D("1e-12")
        origin = result["cases"][-1]
        assert origin["id"] == "iau_epoch_tt"
        assert D(origin["iau_epoch_closure_seconds"]) == (
            D(origin["inpop21a_tdb_minus_tt_seconds"]) + D("0.0000655")
        )


def test_zero_model_difference_is_not_physical_accuracy(inputs):
    for new, old, archived in zip(
        inputs[1]["cases"], inputs[4]["cases"], inputs[5]["cases"], strict=True
    ):
        delta = new["cspice"]["delta_seconds"]
        old["cspice"]["delta_seconds"] = delta
        archived["reference_tdb_minus_tt_seconds"] = delta
        with localcontext() as ctx:
            ctx.prec = 70
            archived["candidate_minus_reference_seconds"] = str(
                D(archived["candidate_tdb_minus_tt_seconds"]) - D(delta)
            )
    result = cm.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert all(D(r["inpop21a_minus_de440t_seconds"]) == 0 for r in result["cases"])
    assert all(result[k] is None for k in cm.BOUND_KEYS)
    assert not result["observing_eligible"]


def test_model_disagreement_is_diagnostic_not_acceptance_threshold(inputs):
    with localcontext() as ctx:
        ctx.prec = 70
        for old, archived in zip(inputs[4]["cases"], inputs[5]["cases"], strict=True):
            delta = D(old["cspice"]["delta_seconds"]) + D("0.1")
            old["cspice"]["delta_seconds"] = str(delta)
            archived["reference_tdb_minus_tt_seconds"] = str(delta)
            archived["candidate_minus_reference_seconds"] = str(
                D(archived["candidate_tdb_minus_tt_seconds"]) - delta
            )
    result = cm.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert all(abs(D(r["inpop21a_minus_de440t_seconds"])) > D("0.09") for r in result["cases"])
    assert not result["observing_eligible"]


def test_failed_candidate_replay_retains_all_diagnostics(inputs):
    result = cm.evaluate_inputs(*inputs, candidate=lambda tt: D(1))
    assert not result["audit_passed"]
    assert result["cross_model_status"] == "numerical_qualification_failed"
    assert len(result["cases"]) == 14
    assert all(not r["numerical_checks_passed"] for r in result["cases"])
    assert not result["observing_eligible"]


@pytest.mark.parametrize("key", cm.BOUND_KEYS)
@pytest.mark.parametrize("index", [0, 2, 5, 6])
def test_unsupported_physical_bounds_rejected(inputs, key, index):
    target = inputs[index]["expected_limits"] if index == 0 else inputs[index]
    target[key] = "1e-9"
    with pytest.raises(cm.TimeEphemerisError, match="unsupported_physical_bound"):
        cm.evaluate_inputs(*inputs)


@pytest.mark.parametrize("index", range(6))
def test_no_evidence_class_can_be_promoted_to_bound(inputs, index):
    inputs[2]["claims"][index]["applicable_physical_bound_seconds"] = "1e-9"
    with pytest.raises(cm.TimeEphemerisError, match="unsupported_physical_bound"):
        cm.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("units", "kernel_convention"),
        ("scale", "kernel_convention"),
        ("sign", "kernel_convention"),
        ("segment", "segment_identity"),
        ("hash", "kernel_identity"),
        ("generator", "fixture_provenance"),
        ("candidate_import", "reference_boundary"),
        ("model", "distinct_models"),
        ("missing", "sample_count"),
        ("duplicate", "sample_context"),
        ("tt", "sample_context"),
        ("trace_sign", "equation_sign"),
        ("argument", "tdb_argument"),
        ("solution", "solution_trace"),
        ("threshold", "frozen_tolerances"),
        ("combined", "prior_combined_gate"),
        ("component", "uncertainty_components"),
        ("independence", "independence_claim"),
        ("claim", "evidence_inventory"),
        ("source", "evidence_provenance"),
        ("category", "evidence_category"),
        ("eligibility", "unsupported_eligibility"),
        ("de_value", "de440t_input_changed"),
    ],
)
def test_corruption_fails_closed(inputs, mutation, error):
    policy, fixture, evidence, _, de_fixture, de_record, normalization = inputs
    row = fixture["cases"][0]
    if mutation == "units":
        fixture["units"] = "days"
    elif mutation == "scale":
        fixture["argument_scale"] = "TT"
    elif mutation == "sign":
        fixture["quantity"] = "TDB_minus_TT"
    elif mutation == "segment":
        fixture["segment"]["target"] = 399
    elif mutation == "hash":
        fixture["kernel_sha256"] = "0" * 64
    elif mutation == "generator":
        fixture["generator_sha256"] = "0" * 64
    elif mutation == "candidate_import":
        fixture["forbidden_imports"] = ["erfa"]
    elif mutation == "model":
        de_fixture["kernel_sha256"] = fixture["kernel_sha256"]
    elif mutation == "missing":
        fixture["cases"].pop()
    elif mutation == "duplicate":
        fixture["cases"][1] = copy.deepcopy(row)
    elif mutation == "tt":
        row["tt_seconds_from_j2000"] = "0"
    elif mutation == "trace_sign":
        row["cspice"]["trace"][0]["tt_minus_tdb_seconds"] = "0"
    elif mutation == "argument":
        row["cspice"]["trace"][0]["argument_et_seconds"] = "0"
    elif mutation == "solution":
        row["cspice"]["delta_seconds"] = "0"
    elif mutation == "threshold":
        policy["limits"]["epoch_closure_seconds"] = "1"
    elif mutation == "combined":
        normalization["combined_counts"]["executed"] = 288
    elif mutation == "component":
        policy["unresolved_components"].pop()
    elif mutation == "independence":
        evidence["independence"]["statistically_independent_errors_established"] = True
    elif mutation == "claim":
        evidence["claims"].pop()
    elif mutation == "source":
        evidence["claims"][0]["source_url"] = ""
    elif mutation == "category":
        evidence["claims"][0]["kind"] = "physical_bound"
    elif mutation == "eligibility":
        normalization["observing_eligible"] = True
    elif mutation == "de_value":
        de_record["cases"][0]["reference_tdb_minus_tt_seconds"] = "0"
    with pytest.raises(cm.TimeEphemerisError, match=error):
        cm.evaluate_inputs(*inputs)


def test_decimal_context_isolation(inputs):
    with localcontext() as ctx:
        ctx.prec = 9
        result = cm.evaluate_inputs(*inputs)
        assert ctx.prec == 9
    assert result == cm.evaluate_inputs(*inputs)


def test_manifest_tampering_rejected(tmp_path, monkeypatch):
    fake = tmp_path / "manifest.json"
    fake.write_text("{}\n")
    monkeypatch.setattr(cm, "MANIFEST", fake)
    with pytest.raises(cm.TimeEphemerisError, match="manifest_checksum"):
        cm.load_inputs()


def test_generator_isolation_and_reference_lock():
    source = (cm.ROOT / "validation/reference_generation/cross_model_time.py").read_text()
    tree = ast.parse(source)
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append((node.module or "").split(".")[0])
    assert not set(modules) & {"astropy", "erfa", "pint", "skyfield", "astroscope", "validation"}
    assert "socket" in modules
    assert "spiceypy" in modules and "jplephem" in modules
    with pytest.raises(RuntimeError, match="offline"):
        cm.deny_network()


def test_cli_clean_provenance_fields(tmp_path):
    output = tmp_path / "audit.json"
    env = dict(
        os.environ, ASTROSCOPE_IMPLEMENTATION_COMMIT="a" * 40, ASTROSCOPE_CHECKOUT_COMMIT="b" * 40
    )
    run = subprocess.run(
        [sys.executable, "-m", "validation.cross_model_time", "--output", str(output)],
        cwd=cm.ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    result = json.loads(output.read_text())
    assert result["implementation_commit"] == "a" * 40
    assert result["checkout_commit"] == "b" * 40
    assert isinstance(result["working_tree_dirty"], bool)
    assert result["audit_passed"]
    assert not result["observing_eligible"]
