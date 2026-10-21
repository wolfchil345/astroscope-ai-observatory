"""Sensitivity signs, correlation, missing evidence and offline reproducibility."""

from __future__ import annotations

import ast
import copy
import json
import socket
import subprocess
import sys
from decimal import Decimal as D
from decimal import localcontext

import numpy as np
import pytest

from validation import clock_sensitivity as cs


@pytest.fixture
def inputs():
    return copy.deepcopy(cs.load_inputs())


def test_complete_supplied_input_audit_preserves_unknown_physics(inputs):
    result = cs.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert result["counts"] == dict(
        states=12,
        partials=516,
        partial_implementation_checks=1032,
        mappings=28,
        synthetic_controls=9,
        known_covariances=7,
        unknown_covariances=2,
    )
    assert result["combined_counts"] == cs.COUNTS
    assert result["site_clocks_unqualified"] == 48
    assert result["unresolved_components"] == cs.COMPONENTS
    assert all(result[k] is None for k in cs.BOUND_KEYS)
    assert result["full_reference_status"] == "unqualified"
    assert not result["observing_eligible"]
    assert not result["physical_covariance_propagated"]
    assert not result["physical_linearization_domain_established"]
    assert result["evidence_availability"] == cs.AVAILABILITY


def test_correlations_change_variance_and_never_replace_missing_cross_terms(inputs):
    rows = {r["id"]: r for r in cs.evaluate_inputs(*inputs)["controls"]}
    expected = dict(
        independent="13",
        positive_correlation="19",
        negative_correlation="7",
        perfect_cancellation="0",
        constant_rate_two_intervals="100",
        anchor_rate_correlation="9",
        zero_variance="0",
    )
    for key, variance in expected.items():
        assert rows[key]["linearized_variance_seconds_squared"] == variance
    # The same uncertain rate persists across two intervals: (2+3)^2 * 4,
    # not (2^2+3^2)*4. A covariance cancellation does not cancel a separate box bound.
    assert rows["perfect_cancellation"]["linearized_box_bound_seconds"] == "4"
    assert rows["unknown_cross_covariance"]["linearized_variance_seconds_squared"] is None
    assert rows["unknown_cross_covariance"]["linearized_box_bound_seconds"] == "5"
    assert rows["unknown_covariance"]["linearized_box_bound_seconds"] is None


def test_gm_units_and_outer_planet_metres_are_accepted(inputs):
    state = inputs[3]["geocentric_controls"][0]["states"][-1]
    vector = cs.state_vector(state)
    assert vector.shape == (43,)
    assert vector[6] == float(D(state["bodies"][0]["gm_km3_s2"]) * 10**9)
    assert max(abs(vector[3:].reshape(10, 4)[:, :3].ravel())) > 1e12


def test_analytic_signs_scale_and_absolute_position_chain_rule():
    vector = np.zeros(43)
    vector[:3] = [10, -20, 30]
    for i in range(10):
        vector[3 + 4 * i : 7 + 4 * i] = [1e11 * (i + 1), -2e11, 3e11, 1e19]
    _, gradient, numerical = cs.rate_gradients(vector)
    assert (gradient[:3] * vector[:3] < 0).all()
    body_gradient = gradient[3:].reshape(10, 4)
    assert (body_gradient[:, 3] < 0).all()
    assert (body_gradient[:, :3] * vector[3:].reshape(10, 4)[:, :3] > 0).all()
    np.testing.assert_allclose(gradient, numerical, rtol=5e-13, atol=1e-45)
    # Perturb Earth x with body positions held fixed: every displacement x decreases.
    trial = vector.astype(complex)
    trial[3::4] -= 1j
    assert cs.scalar_rate(trial).imag == pytest.approx(-sum(body_gradient[:, 0]), rel=5e-13)
    scaled = vector.copy()
    scaled[3::4] *= 2
    scaled[4::4] *= 2
    scaled[5::4] *= 2
    _, scaled_gradient, _ = cs.rate_gradients(scaled)
    np.testing.assert_allclose(
        scaled_gradient[3:].reshape(10, 4)[:, :3], body_gradient[:, :3] / 4, rtol=5e-13, atol=1e-45
    )


@pytest.mark.parametrize("f", ["0", "0.25", "-0.25", "1e-10", "-1e-10"])
def test_implicit_mapping_gains_satisfy_differentiated_equations(f):
    with localcontext() as ctx:
        ctx.prec = 70
        gains = cs.mapping_gains(f)
        denom = 1 + D(f)
        assert abs(denom * gains["delta_per_clock_perturbation"] + 1) < D("1e-60")
        assert abs(denom * gains["delta_per_tt"] + D(f)) < D("1e-60")
        assert abs(gains["tdb_per_tt"] - (1 + gains["delta_per_tt"])) < D("1e-60")


@pytest.mark.parametrize("f", ["-1", "-0.5", "-2", "NaN"])
def test_bad_mapping_domain_fails_closed(f):
    with pytest.raises(cs.TimeEphemerisError):
        cs.mapping_gains(f)


@pytest.mark.parametrize(
    "cov",
    [
        [["0", "0", "0"], ["0", "4", "2"], ["0", "2", "1"]],
        [["4", "2", "0"], ["2", "1", "0"], ["0", "0", "0"]],
        [["1", "2", "3"], ["2", "4", "6"], ["3", "6", "9"]],
    ],
)
def test_singular_psd_covariance_and_zero_pivots(cov):
    variance, _ = cs.propagate(["1", "1", "1"], cov, None)
    assert variance >= 0


@pytest.mark.parametrize(
    "jac,cov,bounds,reason",
    [
        (["1", "0"], [["1", "2"], ["2", "1"]], None, "covariance_not_psd"),
        (["1", "1"], [["0", "1"], ["1", "1"]], None, "covariance_not_psd"),
        (["1", "1"], [["1", "0"], ["1", "1"]], None, "covariance_asymmetric"),
        (["1", "1"], [["1", None], ["0", "1"]], None, "covariance_asymmetric"),
        (["1", "1"], [["1", "0"], ["0"]], None, "covariance_shape"),
        (["1", "1"], [["1", "0"]], None, "covariance_shape"),
        (["1", "1"], [["-1", None], [None, "1"]], None, "covariance_negative_diagonal"),
        (["1"], [["NaN"]], None, "finite_decimal_string_required"),
        (["1"], [["Infinity"]], None, "finite_decimal_string_required"),
        ([True], [["1"]], None, "finite_decimal_string_required"),
        ([], [], None, "jacobian_shape"),
        (["1"], None, ["-1"], "box_negative"),
        (["1"], None, [], "box_shape"),
        (["1"], None, ["NaN"], "finite_decimal_string_required"),
    ],
)
def test_invalid_uncertainty_inputs_are_rejected(jac, cov, bounds, reason):
    with pytest.raises(cs.TimeEphemerisError, match=reason):
        cs.propagate(jac, cov, bounds)


def test_unit_rescaling_preserves_correlated_output_variance():
    # Change first input from seconds to milliseconds, including the cross entries.
    before = cs.propagate(["1", "2"], [["4", "3"], ["3", "9"]], ["2", "3"])
    after = cs.propagate(["0.001", "2"], [["4000000", "3000"], ["3000", "9"]], ["2000", "3"])
    assert before == after


@pytest.mark.parametrize("index", [0, 2, 6])
@pytest.mark.parametrize("key", [*cs.BOUND_KEYS, "observing_eligible"])
def test_no_bound_or_eligibility_can_be_promoted(inputs, index, key):
    inputs[index][key] = True if key == "observing_eligible" else "1e-9"
    with pytest.raises(cs.TimeEphemerisError, match="unsupported"):
        cs.evaluate_inputs(*inputs)


@pytest.mark.parametrize("kind", ["state", "body", "partial", "mapping", "control"])
def test_missing_inventory_cannot_silently_reduce_checks(inputs, kind):
    if kind == "state":
        inputs[3]["geocentric_controls"].pop()
    elif kind == "body":
        inputs[3]["geocentric_controls"][0]["states"][-1]["bodies"].pop()
    elif kind == "partial":
        inputs[1]["rates"][0]["partials"].pop()
    elif kind == "mapping":
        inputs[1]["mappings"].pop()
    else:
        inputs[1]["controls"].pop()
    with pytest.raises(cs.TimeEphemerisError, match="inventory"):
        cs.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "fault",
    ["argument", "duplicate_state", "tolerance", "evidence", "prior_gate", "physical_reference"],
)
def test_provenance_and_evidence_faults(inputs, fault):
    if fault == "argument":
        inputs[1]["rates"][0]["et_seconds"] = "0"
    elif fault == "duplicate_state":
        case = inputs[3]["geocentric_controls"][0]
        case["states"].append(copy.deepcopy(case["states"][-1]))
    elif fault == "tolerance":
        inputs[0]["limits"]["partial_relative"] = "1"
    elif fault == "evidence":
        inputs[2]["inputs"][2]["status"] = "archived"
    elif fault == "prior_gate":
        inputs[6]["combined_counts"]["executed"] = 288
    else:
        inputs[1]["independent_physical_reference"] = True
    with pytest.raises(cs.TimeEphemerisError):
        cs.evaluate_inputs(*inputs)


@pytest.mark.parametrize("fault", ["sign", "gm_units", "complex", "rate"])
def test_failed_numerics_retain_diagnostics_and_block_qualification(inputs, fault):
    def bad(vector):
        rate, analytic, complex_step = cs.rate_gradients(vector)
        if fault == "sign":
            analytic[3] *= -1
        elif fault == "gm_units":
            analytic[6] *= 1e9
        elif fault == "complex":
            complex_step[:] = 0
        else:
            rate += 1e-10
        return rate, analytic, complex_step

    result = cs.evaluate_inputs(*inputs, candidate=bad)
    assert not result["audit_passed"]
    assert len(result["rates"]) == 12
    assert all(not row["passed"] for row in result["rates"])
    assert not result["observing_eligible"]


def test_corrupted_fixture_hash_fails_before_evaluation(monkeypatch):
    real = cs.sha
    monkeypatch.setattr(cs, "sha", lambda path: "bad" if path == cs.FIXTURE else real(path))
    with pytest.raises(cs.TimeEphemerisError, match="input_checksum"):
        cs.load_inputs()


def test_candidate_network_is_disabled_inside_evaluation(monkeypatch):
    def probe(*args):
        socket.create_connection(("example.invalid", 443))

    monkeypatch.setattr(cs, "evaluate_inputs", probe)
    with pytest.raises(RuntimeError, match="offline"):
        cs.evaluate()


def test_reference_has_only_stdlib_imports_and_regenerates_identically(tmp_path):
    source = cs.ROOT / "validation/reference_generation/clock_sensitivity.py"
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module.split(".")[0]]
        else:
            continue
        assert set(modules) <= sys.stdlib_module_names | {"__future__"}
    output = tmp_path / "reference.json"
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-m",
            "validation.reference_generation.clock_sensitivity",
            "--output",
            str(output),
        ],
        cwd=cs.ROOT,
        check=True,
    )
    assert output.read_bytes() == cs.FIXTURE.read_bytes()


def test_canonical_scientific_record_replays():
    path = cs.ROOT / "validation/results/clock_sensitivity_reference_run.json"
    canonical = json.loads(path.read_text())
    current = cs.evaluate()
    runtime = {
        "python_version",
        "candidate_packages",
        "implementation_commit",
        "checkout_commit",
        "working_tree_dirty",
    }
    assert {k: v for k, v in canonical.items() if k not in runtime} == {
        k: v for k, v in current.items() if k not in runtime
    }
    assert canonical["working_tree_dirty"] is False
