"""Independent algebraic limits, coupled solver faults and qualification guards."""

import ast
import copy
import json
import socket
import subprocess
import sys
from decimal import Context, localcontext
from decimal import Decimal as D
from fractions import Fraction as F

import numpy as np
import pytest

from validation import coupled_clock as cc


@pytest.fixture
def inputs():
    return cc.load_inputs()


def archived_candidates(inputs):
    with localcontext(Context(prec=90)):
        return {
            r["id"]: dict(
                site=str(
                    D(r["surrogate_clock_seconds"]) + D(r["candidate_minus_surrogate_seconds"])
                )
            )
            for r in inputs[3]["cases"]
        }


def audit(inputs, mapper=cc.local_mapping):
    return cc.evaluate_inputs(*inputs, archived_candidates(inputs), mapper=mapper)


def simple_state():
    return dict(
        earth_velocity_m_s=["1", "2", "0"],
        position_tt_m=["2", "3", "4"],
        bodies=[
            dict(
                id=i,
                gm_km3_s2="1e-9",
                displacement_tdb_m=["100", "0", "0"],
                barycentric_velocity_m_s=["3", "5", "0"],
            )
            for i in cc.BODY_IDS
        ],
    )


def test_point_mass_coefficients_and_total_not_partial_derivative():
    coeff = cc.coefficients(simple_state())
    fb = cc.FB
    assert coeff["potential"] == 0.1
    np.testing.assert_allclose(coeff["acceleration"], [0.001 * fb, 0, 0], rtol=1e-15, atol=0)
    np.testing.assert_allclose(coeff["vector_potential"], [0.3, 0.5, 0], rtol=1e-15, atol=0)
    np.testing.assert_allclose(
        coeff["gradient_vector_potential"],
        [[0.003 * fb, 0, 0], [0.005 * fb, 0, 0], [0, 0, 0]],
        rtol=1e-15,
        atol=0,
    )
    assert coeff["potential_total_derivative"] == pytest.approx(-0.002 * fb, rel=1e-15)
    assert coeff["potential_total_derivative"] != pytest.approx(-0.003 * fb, rel=1e-6)
    np.testing.assert_allclose(
        coeff["jerk"], np.array([-0.00004, 0.00003, 0]) * fb**2, rtol=1e-15, atol=0
    )
    np.testing.assert_allclose(coeff["B_vector"], [-1.6, -3.6, 0], rtol=1e-15, atol=0)
    np.testing.assert_allclose(
        coeff["B_matrix"],
        np.array([[0.004, 0, 0], [0.008, -0.001, 0], [0, 0, -0.001]]) * fb,
        rtol=1e-15,
        atol=0,
    )


@pytest.mark.parametrize("term", ["leading", "linear_c4", "quadratic_c4", "cubic_c4"])
def test_each_time_term_matches_exact_rational_sign_and_scale(term):
    r, v = np.array([2.0, 3.0, 4.0]), np.array([5.0, -7.0, 11.0])
    coeff = dict(
        B_vector=np.array([13.0, 17.0, -19.0]),
        B_matrix=np.array([[2.0, 3.0, 0.0], [-5.0, 7.0, 0.0], [0.0, 0.0, 11.0]]),
        jerk=np.array([23.0, -29.0, 31.0]),
    )
    c, fg = F(299792458), 1 - F("6.969290134e-10")
    # Contractions computed as integer arithmetic, independently of array products.
    expected = dict(
        leading=fg * 33 / c**2,
        linear_c4=-fg * 1 / c**4,
        quadratic_c4=-fg * 235 / c**4,
        cubic_c4=fg * 29 * 83 / (10 * c**4),
    )
    actual = cc.time_terms(r, v, coeff)[term]
    assert actual == pytest.approx(float(expected[term]), rel=1e-15, abs=0)


def test_zero_station_has_exactly_zero_local_clock():
    state = simple_state()
    state["position_tt_m"] = ["0"] * 3
    result = cc.local_mapping(state)
    assert result["site_shift_seconds"] == 0
    assert all(t == 0 for t in result["terms_seconds"].values())
    assert np.array_equal(result["displacement_tdb_m"], np.zeros(3))


def test_spatial_closed_form_linear_root_and_free_motion_time_term():
    v, x = np.array([10000.0, 20000.0, -30000.0]), np.array([1e6, -2e6, 3e6])
    coeff = dict(
        acceleration=np.zeros(3),
        potential=0.0,
        B_vector=-(v @ v) * v / 2,
        B_matrix=np.zeros((3, 3)),
        jerk=np.zeros(3),
    )
    exact = x - v * (v @ x) / (2 * cc.C**2 + v @ v)
    r, _ = cc.spatial_inverse(x * cc.FG, v, coeff)
    np.testing.assert_allclose(r, exact, rtol=0, atol=1e-9)
    terms = cc.time_terms(r, v, coeff)
    assert terms["linear_c4"] == pytest.approx(
        cc.FG * (v @ v) * (v @ r) / (2 * cc.C**4), rel=1e-15, abs=0
    )


def test_full_local_mapping_is_rotation_covariant():
    state = simple_state()
    rotation = np.array([[0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]])
    other = copy.deepcopy(state)

    def rotate(values):
        return [str(x) for x in rotation @ np.array(values, dtype=float)]

    for k in ("earth_velocity_m_s", "position_tt_m"):
        other[k] = rotate(other[k])
    for b in other["bodies"]:
        for k in ("displacement_tdb_m", "barycentric_velocity_m_s"):
            b[k] = rotate(b[k])
    a, b = cc.local_mapping(state), cc.local_mapping(other)
    np.testing.assert_allclose(
        b["displacement_tdb_m"], rotation @ a["displacement_tdb_m"], rtol=1e-15, atol=0
    )
    for k in a["terms_seconds"]:
        assert a["terms_seconds"][k] == pytest.approx(b["terms_seconds"][k], rel=1e-14, abs=0)


@pytest.mark.parametrize("d0,slope,shift", [(0.001, 1e-5, 2e-6), (-0.001, -1e-5, -2e-6), (0, 0, 0)])
def test_solver_against_analytic_affine_clock(d0, slope, shift):
    def reader(key):
        return dict(et_seconds=key, clock_tt_minus_tdb_seconds=str(d0 + slope * float(key)))

    result = cc.solve("0", reader, lambda state: dict(site_shift_seconds=shift))
    assert result["converged"]
    assert float(result["delta_seconds"]) == pytest.approx((shift - d0) / (1 + slope), abs=2e-18)


def test_solver_keeps_nonconvergence():
    def reader(key):
        return dict(et_seconds=key, clock_tt_minus_tdb_seconds=str(0.001 + float(key)))

    result = cc.solve("0", reader, lambda state: dict(site_shift_seconds=0))
    assert not result["converged"] and len(result["trace"]) == 8


@pytest.mark.parametrize("failure", ["wrong_epoch", "nonfinite", "out_of_range", "missing"])
def test_solver_refuses_bad_oracle(failure):
    def reader(key):
        if failure == "missing":
            return cc.frozen_reader([dict(et_seconds="0")])(key)
        return dict(
            et_seconds="0" if failure == "wrong_epoch" else key,
            clock_tt_minus_tdb_seconds="nan"
            if failure == "nonfinite"
            else ("1" if failure == "out_of_range" else "0"),
        )

    with pytest.raises(cc.CoupledClockError):
        cc.solve("10", reader, lambda state: dict(site_shift_seconds=0))


def test_complete_offline_case_inventory_and_closed_physical_gate(inputs):
    result = audit(inputs)
    assert result["audit_passed"]
    assert len(result["cases"]) == 48 and len(result["geocentric_controls"]) == 12
    assert result["physical_site_clock_bound_seconds"] is None
    assert result["physical_arrival_bound_seconds"] is None
    assert result["continuous_clock_root_bound_seconds"] is None
    assert result["combined_counts"]["executed"] == 0
    assert result["combined_counts"]["blocked"] == 288
    assert result["unresolved_components"] == cc.BUDGET


@pytest.mark.parametrize(
    "fault", ["no_c4", "reverse_c4", "no_fg", "double_geocentric", "legacy_vector"]
)
def test_faulty_mappings_are_rejected_without_discarding_rows(inputs, fault):
    def mapper(state):
        result = cc.local_mapping(state)
        terms = result["terms_seconds"]
        if fault == "no_c4":
            result["site_shift_seconds"] = terms["leading"]
        elif fault == "reverse_c4":
            result["site_shift_seconds"] = 2 * terms["leading"] - result["site_shift_seconds"]
        elif fault == "no_fg":
            result["site_shift_seconds"] /= cc.FG
        elif fault == "double_geocentric":
            result["site_shift_seconds"] -= float(state["clock_tt_minus_tdb_seconds"])
        else:
            result["site_shift_seconds"] = (
                cc.vector(state["earth_velocity_m_s"]) @ cc.vector(state["position_tt_m"])
            ) / cc.C**2
        return result

    result = audit(inputs, mapper)
    assert not result["audit_passed"]
    assert len(result["cases"]) == 48
    assert all(not r["numerical_checks_passed"] for r in result["cases"])
    assert result["observing_eligible"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "id",
        "duplicate",
        "site",
        "tt",
        "body",
        "gm",
        "epoch",
        "delta",
        "quantization",
        "convergence",
        "sum",
        "unused_state",
        "control",
        "frame",
        "approximate",
        "bound",
        "gate",
        "tolerance",
        "constants",
        "source",
        "imports",
        "packages",
        "kernel",
    ],
)
def test_contract_and_trace_corruption_fails(inputs, fault):
    p, f = inputs[:2]
    row, state = f["cases"][0], f["cases"][0]["states"][0]
    if fault == "id":
        row["id"] = "invented"
    elif fault == "duplicate":
        f["cases"][1] = copy.deepcopy(row)
    elif fault == "site":
        row["site"]["latitude_deg"] = 0
    elif fault == "tt":
        row["tt_seconds_from_j2000"] = "0"
    elif fault == "body":
        state["bodies"][0]["id"] = 399
    elif fault == "gm":
        state["bodies"][0]["gm_km3_s2"] = "1"
    elif fault == "epoch":
        state["et_seconds"] = "0"
    elif fault == "delta":
        row["solution"]["trace"][0]["delta_seconds"] = "1e-6"
    elif fault == "quantization":
        row["solution"]["trace"][0]["argument_error_seconds"] = "0.1"
    elif fault == "convergence":
        row["solution"]["converged"] = False
    elif fault == "sum":
        state["reference"]["terms_seconds"]["leading"] = "0"
    elif fault == "unused_state":
        extra = copy.deepcopy(state)
        extra["et_seconds"] = "0"
        row["states"].append(extra)
    elif fault == "control":
        f["geocentric_controls"].pop()
    elif fault == "frame":
        f["frame"] = "unscaled"
    elif fault == "approximate":
        f["approximate_skyfield_clock"] = "enabled"
    elif fault == "bound":
        f["physical_site_clock_bound_seconds"] = "2e-13"
    elif fault == "gate":
        p["gate"]["observing_eligible"] = True
    elif fault == "tolerance":
        p["design"]["candidate_reference_seconds"] = "1e-6"
    elif fault == "constants":
        p["constants"]["L_G"] = "0"
    elif fault == "source":
        p["sources"][0]["physical_bound_seconds"] = "2e-13"
    elif fault == "imports":
        f["forbidden_imports"] = ["erfa"]
    elif fault == "packages":
        f["packages"]["numpy"] = "0"
    else:
        f["kernel_sha256"] = "0" * 64
    with pytest.raises(cc.CoupledClockError):
        audit(inputs)


@pytest.mark.parametrize("value", ["nan", "inf", "-Infinity", "1e999999", "", 1.0, True, "1e25"])
def test_unbounded_or_nonfinite_inputs_rejected(value):
    with pytest.raises(cc.CoupledClockError):
        cc.number(value)


def test_small_coefficient_cancellation_regression(inputs):
    for row in inputs[1]["cases"]:
        if row["id"] not in {"2024-09-22_tokyo_12", "2024-09-22_paranal_12"}:
            continue
        for state in row["states"]:
            value = cc.coefficients(state)["B_matrix"][1, 2]
            expected = D(state["reference"]["coefficients"]["B_matrix"][1][2])
            assert abs(D.from_float(float(value)) - expected) <= abs(expected) * D("5e-14")
    failure = json.loads(
        (cc.ROOT / "validation/results/coupled_clock_development_failure.json").read_text()
    )
    assert not failure["audit_passed"]
    assert sum(not r["numerical_checks_passed"] for r in failure["cases"]) == 2


def test_insufficient_guard_precision_rejected(monkeypatch):
    class Info:
        nmant = 52

    monkeypatch.setattr(cc.np, "finfo", lambda dtype: Info())
    with pytest.raises(cc.CoupledClockError, match="extended_precision_unavailable"):
        cc.coefficients(simple_state())


def test_reader_disagreement_retained_as_failed_evidence(inputs):
    inputs[1]["cases"][0]["states"][0]["reader_check"]["clock_seconds"] = "0"
    result = audit(inputs)
    assert not result["audit_passed"]
    assert sum(not r["numerical_checks_passed"] for r in result["cases"]) == 1


def test_decimal_context_does_not_change_audit(inputs):
    expected = audit(inputs)
    with localcontext() as context:
        context.prec = 6
        assert audit(inputs) == expected


def test_manifest_and_reference_independence(inputs, monkeypatch, tmp_path):
    source = cc.ROOT / "validation/reference_generation/coupled_clock.py"
    assert inputs[1]["generator_sha256"] == cc.sha(source)
    assert inputs[1]["policy_sha256"] == cc.sha(cc.POLICY)
    imports = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    assert not imports & {"astropy", "erfa", "astroscope", "validation", "pint"}
    assert {"decimal", "spiceypy", "jplephem", "skyfield"} <= imports
    invalid = tmp_path / "manifest.json"
    invalid.write_text("{}")
    monkeypatch.setattr(cc, "MANIFEST", invalid)
    with pytest.raises(cc.CoupledClockError, match="manifest_checksum"):
        cc.load_inputs()


def test_live_offline_audit_and_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(socket.socket, "connect", cc.deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", cc.deny_network)
    monkeypatch.setattr(socket, "create_connection", cc.deny_network)
    assert cc.evaluate()["audit_passed"]
    output = tmp_path / "record.json"
    subprocess.run(
        [sys.executable, "-m", "validation.coupled_clock", "--output", str(output)],
        cwd=cc.ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    record = json.loads(output.read_text())
    assert record["audit_passed"] and record["observing_eligible"] is False
    assert len(record["implementation_commit"]) == 40
