"""Normalization identities, corruption sensitivity and false-qualification guards."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal as D
from decimal import localcontext
from fractions import Fraction

import pytest

from validation import time_normalization as tn


@pytest.fixture
def inputs():
    return copy.deepcopy(tn.load_inputs())


def test_complete_offline_evidence(inputs):
    result = tn.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert len(result["controls"]) == 9
    assert len(result["cases"]) == 14
    assert result["fault_rejections"] == dict(omitted_tdb0=9, reversed_lb_sign=8, days_as_seconds=8)
    assert result["evidence"]["claims_reviewed"] == 8
    assert result["evidence"]["applicable_physical_bounds"] == 0
    assert result["combined_counts"] == tn.COUNTS
    assert result["unresolved_components"] == tn.COMPONENTS
    assert all(result[k] is None for k in tn.BOUND_KEYS)
    assert result["full_reference_status"] == "unqualified"
    assert not result["observing_eligible"]


def test_epoch_is_not_synchronized_with_tdb():
    with localcontext() as ctx:
        ctx.prec = 70
        offsets = tn.affine_offsets(D(0))
        assert offsets["tdb_minus_tcb_seconds"] == D("-0.0000655")
        assert offsets["tt_minus_tcg_seconds"] == 0
        assert offsets["tcg_minus_tt_seconds"] == 0
        # Inverse at numerical TDB=T0 is a different event from TCB=T0.
        inverse = Fraction("0.0000655") / (1 - Fraction("1.550519768e-8"))
        assert abs(Fraction(offsets["tcb_minus_tdb_seconds"]) - inverse) < Fraction("1e-70")


@pytest.mark.parametrize("x", [D("-3155760000"), D("-1"), D(0), D("1"), D("31557600000")])
def test_affine_inverse_at_same_event(x):
    with localcontext() as ctx:
        ctx.prec = 70
        forward = tn.affine_offsets(x)
        b = x + forward["tdb_minus_tcb_seconds"]
        a = x + forward["tt_minus_tcg_seconds"]
        assert abs(b + tn.affine_offsets(b)["tcb_minus_tdb_seconds"] - x) < D("1e-55")
        assert abs(a + tn.affine_offsets(a)["tcg_minus_tt_seconds"] - x) < D("1e-55")


def test_exact_rate_over_julian_year():
    with localcontext() as ctx:
        ctx.prec = 70
        zero, year = tn.affine_offsets(D(0)), tn.affine_offsets(D(31557600))
        assert (
            year["tdb_minus_tcb_seconds"] - zero["tdb_minus_tcb_seconds"]
            == -D("1.550519768e-8") * 31557600
        )
        assert year["tt_minus_tcg_seconds"] == -D("6.969290134e-10") * 31557600


@pytest.mark.parametrize("shift", [D("-1000"), D("-0.5"), D(0), D("0.5"), D(1000)])
def test_constant_shift_lower_bound_without_fitting(shift):
    residuals = [D("-0.3"), D("0.1"), D("0.4")]
    result = tn.spread(residuals)
    bound = D(result["any_constant_shift_max_residual_lower_bound_seconds"])
    assert bound == D("0.35")
    assert max(abs(r + shift) for r in residuals) >= bound


def test_zero_discrepancy_does_not_supply_physical_uncertainty(inputs):
    for row in inputs[3]["cases"]:
        row["candidate_tdb_minus_tt_seconds"] = row["reference_tdb_minus_tt_seconds"]
    lookup = {
        D(r["tt_seconds_from_j2000"]): D(r["reference_tdb_minus_tt_seconds"])
        for r in inputs[3]["cases"]
    }
    result = tn.evaluate_inputs(*inputs, candidate=lookup.__getitem__)
    assert result["audit_passed"]
    assert D(result["diagnostics"]["all_samples"]["range_seconds"]) == 0
    assert all(result[k] is None for k in tn.BOUND_KEYS)
    assert not result["observing_eligible"]


def test_changed_candidate_fails_replay_but_still_retains_all_rows(inputs):
    result = tn.evaluate_inputs(*inputs, candidate=lambda tt: D(1))
    assert not result["audit_passed"]
    assert len(result["cases"]) == 14
    assert all(not row["numerical_checks_passed"] for row in result["cases"])
    assert not result["observing_eligible"]


@pytest.mark.parametrize("key", tn.BOUND_KEYS)
@pytest.mark.parametrize("record", [0, 2, 3])
def test_reject_unsupported_bounds(inputs, key, record):
    target = inputs[record]["expected_limits"] if record == 0 else inputs[record]
    target[key] = "3e-9"
    with pytest.raises(tn.NormalizationError, match="unsupported_physical_bound"):
        tn.evaluate_inputs(*inputs)


@pytest.mark.parametrize("index", range(8))
def test_no_evidence_class_can_be_promoted_to_bound(inputs, index):
    inputs[2]["claims"][index]["applicable_physical_bound_seconds"] = "1e-12"
    with pytest.raises(tn.NormalizationError, match="unsupported_physical_bound"):
        tn.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("constant", "defining_constants"),
        ("threshold", "frozen_tolerances"),
        ("missing_control", "control_inventory"),
        ("duplicate_case", "sample_identity"),
        ("missing_case", "sample_count"),
        ("changed_delta", "historical_input_changed"),
        ("changed_date", "historical_input_changed"),
        ("false_independence", "reference_scope"),
        ("promote_combined", "prior_combined_gate"),
        ("missing_component", "uncertainty_components"),
        ("missing_claim", "evidence_inventory"),
        ("erase_conflict", "source_discrepancy_erased"),
        ("wrong_kind", "evidence_category"),
        ("no_source", "evidence_provenance"),
    ],
)
def test_corrupted_contracts_fail_closed(inputs, mutation, error):
    policy, fixture, evidence, prior, coupled = inputs
    if mutation == "constant":
        policy["constants"]["LB"] = "1.55e-8"
    elif mutation == "threshold":
        policy["limits"]["erfa_affine_seconds"] = "1"
    elif mutation == "missing_control":
        fixture["controls"].pop()
    elif mutation == "duplicate_case":
        fixture["cases"][1] = copy.deepcopy(fixture["cases"][0])
    elif mutation == "missing_case":
        fixture["cases"].pop()
    elif mutation == "changed_delta":
        fixture["cases"][0]["reused_de440t_delta_seconds"] = "0"
    elif mutation == "changed_date":
        fixture["cases"][0]["tt_seconds_from_j2000"] = "0"
    elif mutation == "false_independence":
        fixture["independent_physical_time_ephemeris"] = True
    elif mutation == "promote_combined":
        coupled["combined_counts"]["executed"] = 288
    elif mutation == "missing_component":
        policy["unresolved_components"].pop()
    elif mutation == "missing_claim":
        evidence["claims"].pop()
    elif mutation == "erase_conflict":
        evidence["claims"][3]["quoted_rate_period"] = "year"
    elif mutation == "wrong_kind":
        evidence["claims"][0]["kind"] = "physical_bound"
    elif mutation == "no_source":
        evidence["claims"][0]["source_url"] = ""
    with pytest.raises(tn.NormalizationError, match=error):
        tn.evaluate_inputs(*inputs)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e9999", "1e13", "x", 1.0])
def test_invalid_numbers_rejected(value):
    with pytest.raises(tn.NormalizationError):
        tn.number(value)


@pytest.mark.parametrize("part", ["control", "historical", "library"])
def test_numerical_faults_fail_without_discarding_results(inputs, part):
    library = tn.erfa_offsets
    if part == "control":
        inputs[1]["controls"][0]["tdb_minus_tcb_seconds"] = "0"
    elif part == "historical":
        inputs[1]["cases"][0]["tcb_minus_tcg_seconds"] = "0"
    else:

        def library(x):
            out = tn.erfa_offsets(x)
            out["checks"]["tdb_minus_tcb_seconds"]["minus_exact_at_actual_input_seconds"] = "1e-8"
            return out

    result = tn.evaluate_inputs(*inputs, affine_library=library)
    assert not result["audit_passed"]
    assert len(result["controls"]) == 9 and len(result["cases"]) == 14
    assert not result["observing_eligible"]


def test_decimal_context_isolation(inputs):
    with localcontext() as ctx:
        ctx.prec = 9
        result = tn.evaluate_inputs(*inputs)
        assert ctx.prec == 9
    assert result == tn.evaluate_inputs(*inputs)


def test_manifest_tampering_rejected(tmp_path, monkeypatch):
    fake = tmp_path / "manifest.json"
    fake.write_text("{}\n")
    monkeypatch.setattr(tn, "MANIFEST", fake)
    with pytest.raises(tn.NormalizationError, match="manifest_checksum"):
        tn.load_inputs()


def test_reference_is_standard_library_only():
    source = tn.ROOT / "validation/reference_generation/time_normalization.py"
    tree = ast.parse(source.read_text())
    imports = [n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    ]
    assert set(imports) <= sys.stdlib_module_names | {"__future__"}


def test_reference_regeneration_byte_identical(tmp_path):
    out = tmp_path / "reference.json"
    # -S excludes site packages, independently enforcing the reference boundary.
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-m",
            "validation.reference_generation.time_normalization",
            "--output",
            str(out),
        ],
        cwd=tn.ROOT,
        check=True,
    )
    assert out.read_bytes() == tn.FIXTURE.read_bytes()


def test_offline_cli_retains_provenance(tmp_path):
    out = tmp_path / "audit.json"
    env = dict(
        os.environ, ASTROSCOPE_IMPLEMENTATION_COMMIT="a" * 40, ASTROSCOPE_CHECKOUT_COMMIT="b" * 40
    )
    subprocess.run(
        [sys.executable, "-m", "validation.time_normalization", "--output", str(out)],
        cwd=tn.ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    result = json.loads(out.read_text())
    assert result["audit_passed"]
    assert result["implementation_commit"] == "a" * 40
    assert result["checkout_commit"] == "b" * 40
    assert result["manifest_sha256"] == tn.EXPECTED_MANIFEST_SHA256
