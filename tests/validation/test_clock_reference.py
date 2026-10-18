"""Mission 41 tests distinguish a passing audit from a qualified clock reference."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import subprocess
import sys
from decimal import Decimal, localcontext

import pytest

from validation import clock_reference as cr


@pytest.fixture
def inputs():
    return copy.deepcopy(cr.load_inputs())


def test_complete_negative_qualification_evidence(inputs):
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"] is True
    assert r["clock_qualification_outcome"] == "unsuccessful"
    assert r["full_reference_status"] == "unqualified"
    assert r["qualified_route_count"] == 0
    assert r["physical_clock_bound_seconds"] is None
    assert r["physical_arrival_bound_seconds"] is None
    assert r["observing_eligible"] is False
    assert r["combined_counts"] == dict(
        candidates=288,
        executed=0,
        blocked=288,
        solar_eligible=240,
        solar_excluded=48,
    )
    assert all(not row["qualified"] for row in r["routes"])
    assert r["routes"][0]["independent_of_candidate_clock_backend"] is False
    assert r["routes"][1]["executable"] is False
    assert r["routes"][2]["matches_selected_site_clock_convention"] is False
    assert r["routes"][2]["independent_of_candidate_clock_backend"] is True
    assert r["routes"][3]["independent_of_candidate_clock_backend"] is False
    assert all(not row["reference_uncertainty_established_for_domain"] for row in r["routes"])
    for row in r["combined_cases"]:
        assert row["status"] == "blocked_before_combined_evaluation"
        assert row["reference_coordinate_jd"] is None
        assert row["candidate_coordinate_jd"] is None
        assert row["residual_seconds"] is None
        assert row["observing_eligible"] is False
        assert row["reasons"][0] == "no_qualified_independent_matched_clock_reference"
    assert sum(len(r["reasons"]) == 2 for r in r["combined_cases"]) == 48


def test_zero_residual_does_not_establish_independence(inputs):
    for row in inputs[1]["cases"]:
        for key in cr.COLUMNS:
            row[key] = "0"
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"]
    assert r["qualified_route_count"] == 0
    assert r["combined_counts"]["executed"] == 0
    assert r["physical_clock_bound_seconds"] is None


def test_common_mode_bias_cannot_promote_shared_backend(inputs):
    for row in inputs[1]["cases"]:
        for key in ("astropy_site_seconds", "pint_default_seconds", "erfa_utc_seconds"):
            row[key] = str(Decimal(row[key]) + Decimal("0.0001"))
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"]
    assert not any(row["qualified"] for row in r["routes"])
    assert r["combined_counts"]["blocked"] == 288


@pytest.mark.parametrize("key", ["pint_default_seconds", "erfa_utc_seconds"])
def test_wrapper_fault_is_detected_without_claiming_accuracy(inputs, key):
    for row in inputs[1]["cases"]:
        row[key] = str(Decimal(row[key]) + Decimal("1e-10"))
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"] is False
    assert all(not row["shared_backend_controls_passed"] for row in r["diagnostic_rows"])
    assert r["clock_qualification_outcome"] == "unsuccessful"


def test_geocentric_denominator_is_not_target_or_site_inflated(inputs):
    r = cr.evaluate_inputs(*inputs)
    assert len(r["diagnostic_rows"]) == 48
    assert r["diagnostics"]["skyfield_minus_astropy_geocentre"]["count"] == 12
    assert all(
        v["count"] == 48
        for k, v in r["diagnostics"].items()
        if k != "skyfield_minus_astropy_geocentre"
    )
    assert all(
        v["interpretation"] == "diagnostic_difference_no_accuracy_threshold"
        for k, v in r["diagnostics"].items()
        if k not in ("pint_minus_astropy", "explicit_utc_minus_astropy")
    )


def test_signed_diagnostics_and_decimal_context_isolation(inputs):
    expected = cr.evaluate_inputs(*inputs)
    with localcontext() as ctx:
        ctx.prec = 6
        actual = cr.evaluate_inputs(*inputs)
    assert actual == expected
    s = expected["diagnostics"]["site_minus_geocentre"]
    assert Decimal(s["minimum_seconds"]) < 0 < Decimal(s["maximum_seconds"])
    assert Decimal(s["maximum_absolute_seconds"]) == max(
        abs(Decimal(row["differences_seconds"]["site_minus_geocentre"]))
        for row in expected["diagnostic_rows"]
    )


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("remove_clock", "clock_denominator"),
        ("duplicate_clock", "clock_denominator"),
        ("rename_clock", "clock_inventory"),
        ("site_context", "clock_context"),
        ("utc_context", "clock_context"),
        ("missing_dispatch", "pint_dispatch_count_or_shape"),
        ("wrong_dispatch_date", "pint_dispatch_arguments"),
        ("wrong_dispatch_site", "pint_dispatch_arguments"),
        ("wrong_dispatch_ut", "pint_dispatch_arguments"),
        ("geocentric_site_dependence", "geocentric_site_dependence"),
        ("remove_combined", "combined_inventory"),
        ("duplicate_combined", "combined_inventory"),
        ("target_context", "combined_context"),
        ("hidden_solar_exclusion", "solar_domain_evidence"),
        ("convention", "convention_mismatch"),
        ("tolerance", "frozen_tolerance_changed"),
    ],
)
def test_corrupt_or_relabelled_evidence_rejected(inputs, mutation, error):
    p, f, _, s = inputs
    row = f["cases"][0]
    if mutation == "remove_clock":
        f["cases"].pop()
    elif mutation == "duplicate_clock":
        f["cases"][-1] = copy.deepcopy(row)
    elif mutation == "rename_clock":
        row["id"] = "invented"
    elif mutation == "site_context":
        row["site"]["elevation_m"] = 41
    elif mutation == "utc_context":
        row["utc"] = "2024-03-20T11:00:00"
    elif mutation == "missing_dispatch":
        row["pint_dtdb_calls"] = []
    elif mutation == "wrong_dispatch_date":
        row["pint_dtdb_calls"][0][0] = "2451545"
    elif mutation == "wrong_dispatch_site":
        row["pint_dtdb_calls"][0][4] = "0"
    elif mutation == "wrong_dispatch_ut":
        row["pint_dtdb_calls"][0][2] = "0"
    elif mutation == "geocentric_site_dependence":
        row["astropy_geocentric_seconds"] = "0"
    elif mutation == "remove_combined":
        s["historical"].pop()
    elif mutation == "duplicate_combined":
        s["historical"][-1] = copy.deepcopy(s["historical"][0])
    elif mutation == "target_context":
        s["historical"][0]["target"]["ra_deg"] = 1
    elif mutation == "hidden_solar_exclusion":
        s["historical"][0]["exclusion_reasons"] = []
    elif mutation == "convention":
        s["convention_id"] = "generic_bjd_tdb"
    elif mutation == "tolerance":
        p["diagnostic_design"]["shared_backend_reproduction_tolerance_seconds"] = "1"
    with pytest.raises(cr.ClockReferenceError, match=error):
        cr.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("method", "upstream_identity"),
        ("inheritance", "pint_inheritance_changed"),
        ("skyfield_interface", "skyfield_interface_changed"),
        ("fallback", "ephemeris_outcome_changed"),
        ("fake_success", "ephemeris_outcome_changed"),
        ("fake_bound", "unsupported_evidence_claim"),
        ("fake_eligibility", "unsupported_evidence_claim"),
        ("fake_independence", "unsupported_evidence_claim"),
        ("unknown_route", "route_inventory"),
    ],
)
def test_route_identity_and_negative_outcome_are_not_silently_overridden(inputs, mutation, error):
    p, f, _, _ = inputs
    if mutation == "method":
        f["method_sha256"]["pint_default"] = "0" * 64
    elif mutation == "inheritance":
        f["topo_default_inherited"] = False
    elif mutation == "skyfield_interface":
        f["skyfield_parameters"].append("site")
    elif mutation == "fallback":
        f["ephemeris_probe"]["fallback_used"] = True
    elif mutation == "fake_success":
        f["ephemeris_probe"]["outcome"] = "success"
    elif mutation == "fake_bound":
        f["physical_clock_bound_seconds"] = "0"
    elif mutation == "fake_eligibility":
        f["observing_eligible"] = True
    elif mutation == "fake_independence":
        f["evidence_kind"] = "independent_reference"
    elif mutation == "unknown_route":
        p["routes"].append({"id": "new_package_name"})
    with pytest.raises(cr.ClockReferenceError, match=error):
        cr.evaluate_inputs(*inputs)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e999", "1e11", True, 0.0, "0" * 81])
def test_invalid_numeric_evidence(value, inputs):
    inputs[1]["cases"][0]["astropy_site_seconds"] = value
    with pytest.raises(cr.ClockReferenceError):
        cr.evaluate_inputs(*inputs)


def test_missing_and_corrupt_manifest_rejected(monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(cr, "MANIFEST", missing)
    with pytest.raises(cr.ClockReferenceError, match="input_unavailable"):
        cr.load_inputs()
    missing.write_text("{}")
    with pytest.raises(cr.ClockReferenceError, match="manifest_checksum"):
        cr.load_inputs()


def test_pinned_input_tamper_rejected(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"altered.json": "0" * 64}}))
    (tmp_path / "altered.json").write_text("changed")
    monkeypatch.setattr(cr, "MANIFEST", manifest)
    monkeypatch.setattr(cr, "ROOT", tmp_path)
    monkeypatch.setattr(cr, "EXPECTED_MANIFEST_SHA256", cr.sha(manifest))
    with pytest.raises(cr.ClockReferenceError, match="input_checksum"):
        cr.load_inputs()


def test_live_astropy_reproduces_archived_algorithm_not_independent_accuracy(inputs):
    from astropy.time import Time

    from validation.observer_arrival_model import context_coordinates, frozen_converter

    p, f, historical, _ = inputs
    assert (
        hashlib.sha256(inspect.getsource(Time._get_delta_tdb_tt).encode()).hexdigest()
        == (p["source_method_sha256"]["astropy_clock"])
    )
    target = {
        **historical["targets"][0],
        "frame": "ICRS",
        "coordinate_epoch": "J2000",
        "motion_assumption": "fixed_icrs_direction_at_infinity",
    }
    with frozen_converter():
        for row in f["cases"]:
            loc, _ = context_coordinates(row["site"], target)
            t = Time(row["utc"], scale="utc", location=loc).tt
            actual = Decimal.from_float(float(t.delta_tdb_tt))
            assert abs(actual - Decimal(row["astropy_site_seconds"])) <= Decimal("1e-12")


def test_cli_is_offline_and_astronomy_import_free(tmp_path):
    output = tmp_path / "audit.json"
    code = """
import sys, socket, runpy
class DenyAstronomy:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'astropy','erfa','numpy','pint','skyfield','astroscope'}:
            raise AssertionError('astronomy import: '+fullname)
sys.meta_path.insert(0,DenyAstronomy())
def deny(*a,**k): raise AssertionError('network')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
sys.argv=['clock_reference','--output',sys.argv[1]]
runpy.run_module('validation.clock_reference',run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(output)],
        cwd=cr.ROOT,
        env={**os.environ, "ASTROSCOPE_IMPLEMENTATION_COMMIT": "test-head"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    r = json.loads(output.read_text())
    assert r["implementation_commit"] == "test-head"
    assert isinstance(r["working_tree_dirty"], bool)
    assert r["fixture_sha256"] == cr.sha(cr.FIXTURE)
    assert r["audit_passed"] is True
    assert r["clock_qualification_outcome"] == "unsuccessful"
    assert r["combined_counts"]["executed"] == 0


@pytest.mark.parametrize("bias,passes", [("1e-12", True), ("1.0001e-12", False)])
def test_frozen_shared_backend_threshold_boundary(inputs, bias, passes):
    for row in inputs[1]["cases"]:
        row["pint_default_seconds"] = str(Decimal(row["pint_default_seconds"]) + Decimal(bias))
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"] is passes
    assert r["qualified_route_count"] == 0


def test_large_mismatched_diagnostic_is_never_an_accuracy_pass(inputs):
    for row in inputs[1]["cases"]:
        row["skyfield_geocentric_seconds"] = "0.009"
    r = cr.evaluate_inputs(*inputs)
    assert r["audit_passed"] is True
    assert r["diagnostics"]["skyfield_minus_astropy_geocentre"]["interpretation"] == (
        "diagnostic_difference_no_accuracy_threshold"
    )
    assert r["clock_qualification_outcome"] == "unsuccessful"
    assert r["physical_clock_bound_seconds"] is None
