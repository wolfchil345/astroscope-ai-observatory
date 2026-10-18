"""Mission 43: numerical evidence must not promote incomplete physical bounds."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal, localcontext

import pytest

from validation import site_clock as sc


@pytest.fixture
def inputs():
    data = copy.deepcopy(sc.load_inputs())
    candidates = {
        r["id"]: {"site": r["astropy_site_seconds"], "geocentre": r["astropy_geocentric_seconds"]}
        for r in data[4]["cases"]
    }
    return [*data, candidates]


def test_complete_evidence_remains_unqualified(inputs):
    result = sc.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert len(result["cases"]) == 48
    assert result["geocentric_control_count"] == 12
    assert result["geocentric_controls_passed"]
    assert result["formal_eop_record_count"] == 8
    assert result["site_reference_status"] == "unqualified"
    assert result["physical_site_clock_bound_seconds"] is None
    assert result["physical_arrival_bound_seconds"] is None
    assert not result["observing_eligible"]
    assert all(not r["observing_eligible"] for r in result["cases"])
    assert result["missing_bound_components"] == list(sc.BUDGET_IDS)
    assert result["combined_counts"] == {
        "candidates": 288,
        "executed": 0,
        "blocked": 288,
        "solar_eligible": 240,
        "solar_excluded": 48,
    }
    with localcontext() as ctx:
        ctx.prec = 70
        for row in result["cases"]:
            assert Decimal(row["candidate_minus_surrogate_seconds"]) == (
                Decimal(row["geocentric_model_difference_seconds"])
                + Decimal(row["site_increment_difference_seconds"])
            )


@pytest.mark.parametrize("difference", ["0", "1"])
def test_candidate_model_difference_never_establishes_accuracy(inputs, difference):
    # Alter candidate and its archival regression baseline together: this isolates
    # the physical qualification gate, not the separate live-regression check.
    references = {r["id"]: r for r in inputs[1]["cases"]}
    for old in inputs[4]["cases"]:
        value = str(
            Decimal(references[old["id"]]["solution"]["delta_seconds"]) + Decimal(difference)
        )
        old["astropy_site_seconds"] = inputs[-1][old["id"]]["site"] = value
    result = sc.evaluate_inputs(*inputs)
    assert result["audit_passed"]
    assert all(
        Decimal(r["candidate_minus_surrogate_seconds"]) == Decimal(difference)
        for r in result["cases"]
    )
    assert result["physical_site_clock_bound_seconds"] is None
    assert not result["observing_eligible"]


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("model_id", "exact-site-clock", "model_identity"),
        ("units", {"position": "km", "velocity": "km/s", "clock": "s"}, "frame_or_units"),
        ("position_frame", "BCRS", "frame_or_units"),
        ("forbidden_imports", ["erfa"], "reference_boundary"),
        ("approximate_skyfield_clock", "enabled", "reference_boundary"),
        ("kernel_sha256", "0" * 64, "reference_provenance"),
        ("packages", {}, "reference_provenance"),
        ("eop_formal_errors_are_hard_bounds", True, "eop_claim"),
        ("observed_dx_dy_applied", True, "eop_claim"),
        ("physical_site_clock_bound_seconds", "0", "unsupported_qualification"),
        ("observing_eligible", True, "unsupported_qualification"),
        ("eop_source_sha256", "0" * 64, "eop_provenance"),
    ],
)
def test_reference_claim_mutations(inputs, key, value, error):
    inputs[1][key] = value
    with pytest.raises(sc.SiteClockError, match=error):
        sc.evaluate_inputs(*inputs)


@pytest.mark.parametrize("component", range(6))
@pytest.mark.parametrize("bound", ["0", "1e-9"])
def test_unknown_component_cannot_be_replaced_by_numeric_bound(inputs, component, bound):
    inputs[0]["physical_budget_components"][component]["hard_bound_seconds"] = bound
    with pytest.raises(sc.SiteClockError, match="unevidenced_bound"):
        sc.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing_site", "site_inventory"),
        ("duplicate_site", "site_inventory"),
        ("missing_control", "control_inventory"),
        ("wrong_site", "site_context"),
        ("wrong_geo", "geo_mapping"),
        ("wrong_tt", "tt_context"),
        ("missing_eop", "eop_inventory"),
        ("eop_mean", "eop_mean_changed"),
        ("negative_sigma", "negative_formal_error"),
        ("missing_sigma", "formal_error_inventory"),
        ("empty_trace", "trace_count"),
        ("convergence", "false_convergence"),
        ("solution", "solution_trace"),
        ("variant", "variant_inventory"),
        ("tolerance", "frozen_threshold"),
        ("iterations", "frozen_iterations"),
        ("gate", "gate_changed"),
        ("prior", "combined_gate"),
        ("nonzero_control", "nonzero_geocentre_site_term"),
    ],
)
def test_structural_faults_fail_closed(inputs, mutation, error):
    policy, fixture = inputs[:2]
    row = fixture["cases"][0]
    eop = fixture["eop_records"][0]
    if mutation == "missing_site":
        fixture["cases"].pop()
    elif mutation == "duplicate_site":
        fixture["cases"][1] = copy.deepcopy(row)
    elif mutation == "missing_control":
        fixture["geocentric_controls"].pop()
    elif mutation == "wrong_site":
        row["site"]["longitude_deg"] = 0
    elif mutation == "wrong_geo":
        row["geocentric_id"] = "wrong"
    elif mutation == "wrong_tt":
        row["tt_seconds_from_j2000"] = "0"
    elif mutation == "missing_eop":
        fixture["eop_records"].pop()
    elif mutation == "eop_mean":
        eop["xp_arcsec"] = "0"
    elif mutation == "negative_sigma":
        eop["formal_errors"]["xp_arcsec"] = "-1"
    elif mutation == "missing_sigma":
        eop["formal_errors"].pop("dx_arcsec")
    elif mutation == "empty_trace":
        row["solution"]["trace"] = []
    elif mutation == "convergence":
        row["solution"]["converged"] = False
    elif mutation == "solution":
        row["solution"]["delta_seconds"] = "0"
    elif mutation == "variant":
        row["variants"].pop("utc_as_ut1")
    elif mutation == "tolerance":
        policy["design"]["solver_residual_seconds"] = "1e-3"
    elif mutation == "iterations":
        policy["design"]["solver_max_iterations"] = 9
    elif mutation == "gate":
        policy["gate"]["observing_eligible"] = True
    elif mutation == "prior":
        inputs[5]["combined_counts"]["executed"] = 288
    elif mutation == "nonzero_control":
        fixture["geocentric_controls"][0]["solution"]["trace"][0]["site_term_seconds"] = "1e-9"
    with pytest.raises(sc.SiteClockError, match=error):
        sc.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("delta_seconds", "1", "trace_continuity"),
        ("tt_minus_tdb_seconds", "1", "mapping_sign_or_algebra"),
        ("site_term_seconds", "0", "mapping_sign_or_algebra"),
        ("next_delta_seconds", "0", "mapping_update"),
        ("et_seconds", "0", "tdb_argument"),
    ],
)
def test_trace_faults(inputs, key, value, error):
    inputs[1]["cases"][0]["solution"]["trace"][0][key] = value
    with pytest.raises(sc.SiteClockError, match=error):
        sc.evaluate_inputs(*inputs)


@pytest.mark.parametrize("factor", ["0", "-1", "2", "0.001"])
def test_omitted_reversed_doubled_or_kilometre_site_vectors_detected_all_48(inputs, factor):
    for row in inputs[1]["cases"]:
        row["site_position_gcrs_m"] = [
            str(Decimal(x) * Decimal(factor)) for x in row["site_position_gcrs_m"]
        ]
    result = sc.evaluate_inputs(*inputs)
    assert not result["audit_passed"]
    assert sum(not r["numerical_checks_passed"] for r in result["cases"]) == 48


@pytest.mark.parametrize("fault", ["velocity_reader", "candidate", "variant"])
def test_numerical_failure_is_retained(inputs, fault):
    row = inputs[1]["cases"][0]
    if fault == "velocity_reader":
        row["jplephem_velocity_m_s"][0] = "0"
    elif fault == "candidate":
        inputs[-1][row["id"]]["site"] = "0"
    else:
        row["variants"]["utc_as_ut1"]["site_term_seconds"] = "0"
    result = sc.evaluate_inputs(*inputs)
    assert not result["audit_passed"]
    assert sum(not r["numerical_checks_passed"] for r in result["cases"]) == 1
    assert len(result["cases"]) == 48


@pytest.mark.parametrize("value", ["nan", "Infinity", "-Infinity", "1e999", "", 1.0, True])
def test_invalid_numbers(value):
    with pytest.raises(sc.SiteClockError, match="finite_decimal_string_required"):
        sc.number(value)


def test_conditional_inequality_is_tight_for_collinear_perturbations(inputs):
    example = inputs[0]["conditional_sensitivity_example"]
    result = sc.conditional_sensitivity(example)
    with localcontext() as ctx:
        ctx.prec = 70
        v, r, dr, dv = [Decimal(example[k]) for k in ("V_m_s", "R_m", "delta_r_m", "delta_v_m_s")]
        exact = ((v + dv) * (r + dr) - v * r) / Decimal(299792458) ** 2
        assert Decimal(result["vector_perturbation_envelope_seconds"]) == exact
    assert result["physical_total_bound_seconds"] is None
    assert not result["observing_eligible"]


@pytest.mark.parametrize("key", ["V_m_s", "R_m", "delta_r_m", "delta_v_m_s", "U_m2_s2"])
def test_negative_conditional_inputs_rejected(inputs, key):
    example = inputs[0]["conditional_sensitivity_example"]
    example[key] = "-1"
    with pytest.raises(sc.SiteClockError, match="negative_bound_input"):
        sc.conditional_sensitivity(example)


def test_zero_hypothetical_errors_do_not_establish_zero_physical_error(inputs):
    for key in ("delta_r_m", "delta_v_m_s", "U_m2_s2", "V_m_s"):
        inputs[0]["conditional_sensitivity_example"][key] = "0"
    result = sc.evaluate_inputs(*inputs)
    assert Decimal(result["conditional_sensitivity"]["vector_perturbation_envelope_seconds"]) == 0
    assert result["physical_site_clock_bound_seconds"] is None
    assert not result["observing_eligible"]


def test_decimal_context_isolation(inputs):
    expected = sc.evaluate_inputs(*inputs)
    with localcontext() as ctx:
        ctx.prec = 6
        assert sc.evaluate_inputs(*inputs) == expected


def test_argument_quantization_not_confused_with_clock_correction_precision(inputs):
    result = sc.evaluate_inputs(*inputs)
    assert max(
        Decimal(r["max_et_argument_quantization_seconds"]) for r in result["cases"]
    ) > Decimal("1e-9")
    assert result["physical_site_clock_bound_seconds"] is None


def test_nonconvergence_is_retained_not_relabeled():
    # Algebraically valid alternating fixed-point trace that fails its stopping
    # criterion. Synthetic, not an extra physical benchmark case.
    trace = []
    for index in range(8):
        delta, d = (0, -1) if index % 2 == 0 else (1, 0)
        trace.append(
            dict(
                delta_seconds=str(delta),
                tt_minus_tdb_seconds=str(d),
                site_term_seconds="0",
                residual_seconds=str(delta + d),
                next_delta_seconds=str(-d),
                et_seconds=str(delta),
            )
        )
    solution = dict(trace=trace, converged=False, delta_seconds="0")
    assert not sc.validate_solution(solution, Decimal(0))
    solution["converged"] = True
    with pytest.raises(sc.SiteClockError, match="false_convergence"):
        sc.validate_solution(solution, Decimal(0))


def test_integrity_and_independent_generator_boundary():
    policy, fixture, *_ = sc.load_inputs()
    path = sc.ROOT / "validation/reference_generation/site_clock.py"
    assert fixture["policy_sha256"] == sc.sha(sc.POLICY)
    assert fixture["generator_sha256"] == sc.sha(path)
    assert fixture["packages"] == policy["reference_packages"]
    tree = ast.parse(path.read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    assert not imports & {"astropy", "erfa", "astroscope", "pint", "validation"}
    assert {"skyfield", "spiceypy", "jplephem"} <= imports
    assert 'patch.object(timelib, "tdb_minus_tt", deny)' in path.read_text()


def test_manifest_tampering(monkeypatch, tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"files": {}}')
    monkeypatch.setattr(sc, "MANIFEST", path)
    with pytest.raises(sc.SiteClockError, match="manifest_checksum"):
        sc.load_inputs()


def test_cli_live_candidate_and_provenance(tmp_path):
    output = tmp_path / "result.json"
    subprocess.run(
        [sys.executable, "-m", "validation.site_clock", "--output", str(output)],
        cwd=sc.ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ASTROSCOPE_IMPLEMENTATION_COMMIT": "head-marker",
            "ASTROSCOPE_CHECKOUT_COMMIT": "checkout-marker",
        },
    )
    result = json.loads(output.read_text())
    assert result["audit_passed"]
    assert result["implementation_commit"] == "head-marker"
    assert result["checkout_commit"] == "checkout-marker"
    assert isinstance(result["working_tree_dirty"], bool)
    assert not result["observing_eligible"]


def test_network_blocked():
    with pytest.raises(RuntimeError, match="offline"):
        sc.deny_network()
