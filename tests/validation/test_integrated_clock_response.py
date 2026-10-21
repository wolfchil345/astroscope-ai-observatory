"""Integrated transport, anchor correlations, implicit mapping and offline evidence."""

from __future__ import annotations

import ast
import copy
import json
import socket
import subprocess
import sys
from decimal import Context, localcontext
from decimal import Decimal as D

import pytest

from validation import integrated_clock_response as ic


@pytest.fixture
def inputs():
    return copy.deepcopy(ic.load_inputs())


@pytest.fixture(scope="module")
def audited():
    return ic.evaluate()


def test_full_audit_and_physical_unknowns(audited):
    assert audited["audit_passed"]
    assert audited["counts"] == dict(
        synthetic_cases=8,
        integration_grids=32,
        augmented_values_per_case=18,
        endpoint_parameter_partials=120,
        implicit_parameter_partials=40,
        covariance_mode_pairs=24,
        known_variance_values=32,
        unknown_variance_values=16,
    )
    assert audited["combined_counts"] == ic.COUNTS
    assert audited["unresolved_components"] == ic.COMPONENTS
    assert audited["inherited_unestablished_receipt_requirements"] == 18
    assert audited["site_clocks_unqualified"] == 48
    assert audited["full_reference_status"] == "unqualified"
    assert not audited["observing_eligible"]
    assert not audited["physical_covariance_acquired"]
    assert not audited["physical_covariance_propagated"]
    assert not audited["physical_linearization_domain_established"]
    assert all(audited[k] is None for k in ic.BOUND_KEYS)
    for case in audited["cases"]:
        assert case["passed"] and case["refinement_passed"]
        assert abs(D(case["implicit"]["equation_residual_seconds"])) <= D("1e-35")
        for result in case["covariances"]:
            if result["mode"] == "unknown_cross":
                assert result["clock_variance"] is result["implicit_variance"] is None
            else:
                assert D(result["clock_variance"]) >= 0 and D(result["implicit_variance"]) >= 0


@pytest.mark.parametrize("index", [1, 5])
@pytest.mark.parametrize("parameter", range(5))
def test_implicit_response_matches_fixed_tt_perturbations(inputs, index, parameter):
    p, f, _, _ = inputs
    case = p["cases"][index]
    tt = f["cases"][index]["tt_seconds"]
    h = D("1e-6")
    plus, minus = copy.deepcopy(case), copy.deepcopy(case)
    plus["parameters"][parameter] = str(D(case["parameters"][parameter]) + h)
    minus["parameters"][parameter] = str(D(case["parameters"][parameter]) - h)
    with localcontext(Context(prec=60)):
        fd = (ic.solve(plus, tt)["b"] - ic.solve(minus, tt)["b"]) / (2 * h)
        response = ic.solve(case, tt)["jacobian"][parameter]
        assert abs(fd - response) <= D("1e-8")


@pytest.mark.parametrize("index", [1, 5])
def test_segment_chaining_requires_carried_sensitivities(inputs, index):
    case = inputs[0]["cases"][index]
    with localcontext(Context(prec=60)):
        p = ic.validate_case(case)
        half = D(case["span_seconds"]) / 2
        middle = ic.advance(ic.initial(p), half, 64, p, case["family"])
        joined = ic.advance(middle, half, 64, p, case["family"])
        direct = ic.integrate(case, 2 * half, 128)
        assert all(abs(a - b) < D("1e-50") for a, b in zip(joined, direct, strict=True))
        reset = ic.initial([middle[0], middle[1], p[2], p[3], middle[2]])
        lost = ic.advance(reset, half, 64, p, case["family"])
        assert abs(lost[15] - direct[15]) > D("1e-8")


@pytest.mark.parametrize("fault", ["acceleration", "clock_transport", "clock_direct", "anchor"])
def test_reference_detects_missing_terms(inputs, monkeypatch, fault):
    case = inputs[0]["cases"][5]
    original = ic.rhs
    if fault == "anchor":
        old = ic.initial

        def broken_initial(p):
            result = old(p)
            result[17] = D(0)
            return result

        monkeypatch.setattr(ic, "initial", broken_initial)
    else:

        def broken_rhs(y, p, family):
            result = original(y, p, family)
            if fault == "acceleration":
                result[10] -= 1
            elif fault == "clock_direct":
                result[16] -= 1
            else:
                for i in range(5):
                    result[13 + i] = D(int(i == 3))
            return result

        monkeypatch.setattr(ic, "rhs", broken_rhs)
    y = ic.integrate(case, case["span_seconds"])
    ref = list(map(D, inputs[1]["cases"][5]["augmented_state"]))
    assert any(abs(a - b) > D("1e-8") for a, b in zip(y[13:], ref[13:], strict=True))


def test_anchor_correlations_are_not_dropped(inputs, audited):
    p = inputs[0]
    c = audited["cases"][3]
    g = list(map(D, c["augmented_state"][13:18]))
    diagonal = copy.deepcopy(p["synthetic_covariance"])
    for i in range(5):
        for j in range(5):
            if i != j:
                diagonal[i][j] = "0"
    assert abs(ic.variance(g, diagonal) - D(c["covariances"][0]["clock_variance"])) > D("1e-10")
    zero = audited["cases"][0]["covariances"]
    assert D(zero[0]["clock_variance"]) == D("0.000026")
    assert D(zero[1]["clock_variance"]) == 0
    assert zero[2]["clock_variance"] is None


@pytest.mark.parametrize("index", [0, 4])
def test_exact_zero_serialization_regression(inputs, index):
    case = inputs[0]["cases"][index]
    y = ic.integrate(case, D("0E-322"))
    assert y == ic.initial(ic.validate_case(case))
    assert ic.variance([D("0E-322")] * 4 + [D(1)], inputs[0]["synthetic_covariance"]) == D(
        "0.000026"
    )
    ref = inputs[1]["cases"][index]["augmented_state"]
    assert all(v == "0" for v in ref if D(v) == 0)


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("physical", "physical_model"),
        ("family", "unknown_dynamics"),
        ("missing", "case_schema"),
        ("shape", "parameter_shape"),
        ("nan", "finite_decimal"),
        ("bool", "finite_decimal"),
        ("huge", "parameter_domain"),
        ("span", "span_domain"),
        ("anchor", "anchor_domain"),
    ],
)
def test_invalid_case_rejected(inputs, fault, reason):
    case = inputs[0]["cases"][1]
    if fault == "physical":
        case["synthetic"] = False
    elif fault == "family":
        case["family"] = "DE440"
    elif fault == "missing":
        case.pop("synthetic")
    elif fault == "shape":
        case["parameters"].pop()
    elif fault == "nan":
        case["parameters"][0] = "NaN"
    elif fault == "bool":
        case["parameters"][0] = True
    elif fault == "huge":
        case["parameters"][0] = "11"
    elif fault == "span":
        case["span_seconds"] = "5"
    elif fault == "anchor":
        case["anchor_b_seconds"] = "1001"
    with pytest.raises(ic.TimeEphemerisError, match=reason):
        ic.integrate(case, "1")


@pytest.mark.parametrize("steps", [0, -1, 17, True, 128.0])
def test_invalid_grid_rejected(inputs, steps):
    with pytest.raises(ic.TimeEphemerisError, match="step_inventory"):
        ic.integrate(inputs[0]["cases"][1], "1", steps)


@pytest.mark.parametrize("span", ["NaN", "Infinity", "5", True, 0.0])
def test_invalid_span_rejected(inputs, span):
    with pytest.raises(ic.TimeEphemerisError):
        ic.integrate(inputs[0]["cases"][1], span)


def test_implicit_denominator_and_convergence_fail_closed(inputs):
    case = inputs[0]["cases"][1]
    bad = copy.deepcopy(case)
    bad["parameters"] = ["0", "0", "0", "-1", "0"]
    with pytest.raises(ic.TimeEphemerisError, match="implicit_denominator"):
        ic.solve(bad, "1")
    with pytest.raises(ic.TimeEphemerisError, match="implicit_no_convergence"):
        ic.solve(case, inputs[1]["cases"][1]["tt_seconds"], max_iterations=1)
    with pytest.raises(ic.TimeEphemerisError, match="span_domain"):
        ic.solve(case, "100")


@pytest.mark.parametrize("fault", ["ragged", "asymmetric", "indefinite", "nonfinite", "mode"])
def test_covariance_validation_before_anchor_assumption(inputs, fault):
    cov = inputs[0]["synthetic_covariance"]
    mode = "fixed"
    if fault == "ragged":
        cov[0].pop()
    elif fault == "asymmetric":
        cov[0][4] = "0"
    elif fault == "indefinite":
        cov[0][4] = cov[4][0] = "1"
    elif fault == "nonfinite":
        cov[4][4] = "NaN"
    elif fault == "mode":
        mode = "assume_independent"
    with pytest.raises(ic.TimeEphemerisError):
        ic.covariance_mode(cov, mode)


@pytest.mark.parametrize("index", [0, 2, 3])
@pytest.mark.parametrize(
    "key", [*ic.BOUND_KEYS, "observing_eligible", "physical_covariance_propagated"]
)
def test_physical_promotions_rejected(inputs, index, key):
    inputs[index][key] = True if not key.endswith("_seconds") else "1e-9"
    with pytest.raises(ic.TimeEphemerisError, match="unsupported"):
        ic.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "fault", ["policy", "case", "independence", "provenance", "prior", "evidence"]
)
def test_frozen_contract_preserved(inputs, fault):
    p, f, e, prior = inputs
    if fault == "policy":
        p["steps"] = [8, 16, 32, 64]
    elif fault == "case":
        f["cases"].pop()
    elif fault == "independence":
        f["independent_physical_reference"] = True
    elif fault == "provenance":
        f["generator_sha256"] = "0" * 64
    elif fault == "prior":
        prior["inherited_unestablished_receipt_requirements"] = 0
    elif fault == "evidence":
        e["sources"].pop()
    with pytest.raises(ic.TimeEphemerisError):
        ic.evaluate_inputs(p, f, e, prior)


def test_wrong_reference_rejected_numerically(inputs):
    p, f, _, _ = inputs
    f["cases"][1]["augmented_state"][13] = "1"
    result = ic.evaluate_case(p["cases"][1], f["cases"][1], p["synthetic_covariance"])
    assert result["passed"] is False


def test_reference_regenerates_offline_with_standard_library_only(tmp_path):
    out = tmp_path / "reference.json"
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-m",
            "validation.reference_generation.integrated_clock_response",
            "--output",
            str(out),
        ],
        cwd=ic.ROOT,
        check=True,
        timeout=30,
    )
    assert out.read_bytes() == ic.FIXTURE.read_bytes()
    source = ic.ROOT / "validation/reference_generation/integrated_clock_response.py"
    tree = ast.parse(source.read_text())
    modules = {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    modules |= {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert modules <= sys.stdlib_module_names | {"__future__"}
    assert "validation" not in modules


def test_offline_guard(monkeypatch):
    def fetch():
        socket.create_connection(("example.com", 443))

    monkeypatch.setattr(ic, "load_inputs", fetch)
    with pytest.raises(RuntimeError, match="offline"):
        ic.evaluate()


def test_input_integrity(monkeypatch):
    original = ic.sha
    monkeypatch.setattr(ic, "sha", lambda p: "changed" if p == ic.FIXTURE else original(p))
    with pytest.raises(ic.TimeEphemerisError, match="input_checksum"):
        ic.load_inputs()


def test_clean_canonical_matches_current_science(audited):
    path = ic.ROOT / "validation/results/integrated_clock_response_reference_run.json"
    assert path.exists(), "Canonical record must be retained"
    expected = json.loads(path.read_text())
    assert expected["working_tree_dirty"] is False
    runtime = {"python_version", "implementation_commit", "checkout_commit", "working_tree_dirty"}
    assert {k: v for k, v in expected.items() if k not in runtime} == {
        k: v for k, v in audited.items() if k not in runtime
    }


@pytest.mark.parametrize("field", ["b_seconds", "tt_seconds"])
def test_reference_coordinate_metadata_cannot_move_endpoint(inputs, field):
    p, f, _, _ = inputs
    f["cases"][1][field] = "0"
    with pytest.raises(ic.TimeEphemerisError, match="reference_"):
        ic.evaluate_case(p["cases"][1], f["cases"][1], p["synthetic_covariance"])
