"""Provenance mismatch, correlated basis transformations and fail-closed evidence."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from decimal import Decimal as D

import pytest

from validation import ephemeris_covariance as ec


@pytest.fixture
def inputs():
    return copy.deepcopy(ec.load_inputs())


def test_complete_audit_preserves_physical_unknowns(inputs):
    result = ec.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert result["counts"] == dict(
        reviewed_sources=9,
        target_products=2,
        qualified_physical_products=0,
        missing_target_requirements=18,
        synthetic_controls=4,
    )
    assert result["combined_counts"] == ec.COUNTS
    assert result["site_clocks_unqualified"] == 48
    assert result["unresolved_components"] == ec.COMPONENTS
    assert all(result[k] is None for k in ec.BOUND_KEYS)
    assert result["full_reference_status"] == "unqualified"
    assert not result["physical_covariance_acquired"]
    assert not result["physical_covariance_propagated"]
    assert not result["physical_linearization_domain_established"]
    assert not result["observing_eligible"]
    assert all(t["missing_requirements"] == ec.REQUIREMENTS for t in result["targets"])
    assert [D(c["variance"]) for c in result["controls"]] == [52, 52, 52, 0]


def test_transformation_retains_off_diagonals_and_consider_parameters(inputs):
    p = inputs[0]
    result = ec.evaluate_inputs(*inputs)["controls"][2]
    # Original mu-x correlation -2 becomes -2 * 1e9 * 1e3, never zero.
    assert D(result["covariance"][0][1]) == D("-2e12")
    assert list(map(D, result["jacobian"])) == [D("-1e-9"), D("0.001"), D("0.002")]
    receipt = ec.synthetic_receipt(p["synthetic_context"], p["controls"][0])
    receipt["jacobian"][2] = "0"  # dropping the consider parameter changes the answer
    assert ec.validate_receipt(receipt, p["synthetic_context"]) == 44


@pytest.mark.parametrize("key", sorted(ec.CONTEXT_KEYS))
@pytest.mark.parametrize("side", ["covariance_context", "response_context"])
def test_each_context_dimension_must_match(inputs, key, side):
    p = inputs[0]
    receipt = ec.synthetic_receipt(p["synthetic_context"], p["controls"][0])
    receipt[side][key] = None
    with pytest.raises(ec.TimeEphemerisError, match="context_mismatch"):
        ec.validate_receipt(receipt, p["synthetic_context"])


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("physical", "physical_receipt"),
        ("sqrt", "representation"),
        ("missing_context", "context_schema"),
        ("duplicate", "parameter_identity"),
        ("fixed", "parameter_role"),
        ("units", "parameter_units"),
        ("interval", "invalid_validity"),
        ("epoch", "invalid_validity"),
        ("instantaneous", "response_or_anchor"),
        ("unknown_anchor", "response_or_anchor"),
        ("missing_covariance", "complete_covariance"),
        ("missing_cross", "complete_covariance"),
        ("asymmetric", "asymmetric"),
        ("indefinite", "not_psd"),
        ("ragged", "shape"),
        ("nonfinite", "finite_decimal"),
        ("bool", "finite_decimal"),
        ("short_jacobian", "response_shape"),
    ],
)
def test_invalid_receipts_rejected_even_if_declared_context_agrees(inputs, fault, reason):
    p = inputs[0]
    context = p["synthetic_context"]
    if fault == "duplicate":
        context["parameters"][1]["id"] = "x"
    elif fault == "fixed":
        context["parameters"][0]["role"] = "fixed"
    elif fault == "units":
        context["parameters"][0]["unit"] = "au"
    elif fault == "interval":
        context["validity_jd"].reverse()
    elif fault == "epoch":
        context["reference_epoch_jd"] = "1"
    elif fault == "instantaneous":
        context["response_kind"] = "instantaneous_rate_partials"
    elif fault == "unknown_anchor":
        context["anchor_kind"] = "uncertain_without_cross_covariance"
    receipt = ec.synthetic_receipt(context, p["controls"][0])
    if fault == "physical":
        receipt["synthetic"] = False
    elif fault == "sqrt":
        receipt["representation"] = "square_root"
    elif fault == "missing_context":
        receipt["response_context"].pop("solution_id")
    elif fault == "missing_covariance":
        receipt["covariance"] = None
    elif fault == "missing_cross":
        receipt["covariance"][0][1] = receipt["covariance"][1][0] = None
    elif fault == "asymmetric":
        receipt["covariance"][0][1] = "0"
    elif fault == "indefinite":
        receipt["covariance"][0][1] = receipt["covariance"][1][0] = "100"
    elif fault == "ragged":
        receipt["covariance"][0].pop()
    elif fault == "nonfinite":
        receipt["covariance"][0][0] = "NaN"
    elif fault == "bool":
        receipt["jacobian"][0] = True
    elif fault == "short_jacobian":
        receipt["jacobian"].pop()
    with pytest.raises(ec.TimeEphemerisError, match=reason):
        ec.validate_receipt(receipt, context)


@pytest.mark.parametrize(
    "order,scales",
    [
        ([0, 0, 2], ["1"] * 3),
        ([0, 1, True], ["1"] * 3),
        ([0, 1, 2], ["0", "1", "1"]),
        ([0, 1, 2], ["1", "-1", "1"]),
        ([0, 1, 2], ["NaN", "1", "1"]),
        ([0, 1, 2], ["1"]),
    ],
)
def test_invalid_basis_map_rejected(inputs, order, scales):
    p = inputs[0]
    with pytest.raises(ec.TimeEphemerisError):
        ec.transform(
            ec.synthetic_receipt(p["synthetic_context"], p["controls"][0]),
            p["synthetic_context"],
            order,
            scales,
        )


@pytest.mark.parametrize("index", [0, 2, 3])
@pytest.mark.parametrize("key", [*ec.BOUND_KEYS, "observing_eligible"])
def test_no_physical_promotion(inputs, index, key):
    inputs[index][key] = True if key == "observing_eligible" else "1e-9"
    with pytest.raises(ec.TimeEphemerisError, match="unsupported"):
        ec.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "target",
        "requirement",
        "kernel",
        "receipt",
        "reference",
        "control",
        "physical",
        "prior",
    ],
)
def test_evidence_and_inventory_cannot_be_silently_qualified(inputs, fault):
    p, f, e, prior = inputs
    if fault == "source":
        e["sources"].pop()
    elif fault == "target":
        e["targets"].pop()
    elif fault == "requirement":
        p["requirements"].pop()
    elif fault == "kernel":
        p["targets"][0]["kernel_sha256"] = e["targets"][0]["kernel_sha256"] = "0" * 64
    elif fault == "receipt":
        p["targets"][0]["requirements"]["full_correlations"] = "claimed"
        e["targets"][0]["requirements"]["full_correlations"] = "claimed"
    elif fault == "reference":
        f["independent_physical_reference"] = True
    elif fault == "control":
        f["controls"].pop()
    elif fault == "physical":
        e["physical_covariance_acquired"] = True
    elif fault == "prior":
        prior["full_reference_status"] = "qualified"
    with pytest.raises(ec.TimeEphemerisError):
        ec.evaluate_inputs(p, f, e, prior)


def test_wrong_reference_value_fails_numerical_acceptance(inputs):
    inputs[1]["controls"][0]["covariance"][0][1] = "0"
    result = ec.evaluate_inputs(*inputs)
    assert result["audit_passed"] is False
    assert result["controls"][0]["passed"] is False


def test_generator_is_isolated_and_byte_reproducible(tmp_path):
    output = tmp_path / "reference.json"
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-m",
            "validation.reference_generation.ephemeris_covariance",
            "--output",
            str(output),
        ],
        cwd=ec.ROOT,
        check=True,
        timeout=30,
    )
    assert output.read_bytes() == ec.FIXTURE.read_bytes()
    source = ec.ROOT / "validation/reference_generation/ephemeris_covariance.py"
    tree = ast.parse(source.read_text())
    modules = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    modules |= {
        a.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for a in node.names
    }
    assert modules <= sys.stdlib_module_names | {"__future__"}
    assert "validation" not in modules


def test_manifest_integrity_detects_missing_input(monkeypatch):
    original = ec.sha
    monkeypatch.setattr(ec, "sha", lambda p: "wrong" if p == ec.EVIDENCE else original(p))
    with pytest.raises(ec.TimeEphemerisError, match="input_checksum"):
        ec.load_inputs()


def test_audit_denies_network(monkeypatch):
    import socket

    def attempted_fetch():
        socket.create_connection(("example.com", 443))

    monkeypatch.setattr(ec, "load_inputs", attempted_fetch)
    with pytest.raises(RuntimeError, match="offline"):
        ec.evaluate()


def test_canonical_record_matches_current_science():
    path = ec.ROOT / "validation/results/ephemeris_covariance_reference_run.json"
    assert path.exists(), "Canonical record must be retained"
    expected = json.loads(path.read_text())
    assert expected["working_tree_dirty"] is False
    runtime = {"python_version", "implementation_commit", "checkout_commit", "working_tree_dirty"}
    assert {k: v for k, v in expected.items() if k not in runtime} == {
        k: v for k, v in ec.evaluate().items() if k not in runtime
    }
