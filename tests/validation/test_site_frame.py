"""Independent identities, inverse certificates, and false-bound regressions."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from decimal import localcontext
from fractions import Fraction as F

import numpy as np
import pytest

from validation import site_frame as sf


@pytest.fixture
def inputs():
    return copy.deepcopy(sf.load_inputs())


def test_complete_component_result_preserves_physical_gate(inputs):
    r = sf.evaluate_inputs(*inputs)
    assert r["audit_passed"]
    assert r["reference_case_count"] == len(r["cases"]) == 48
    assert r["zero_control_count"] == 12
    assert r["combined_counts"] == inputs[3]["combined_counts"]
    assert r["combined_counts"]["blocked"] == 288
    assert not r["full_clock_recomputed"]
    assert r["physical_spatial_bound_m"] is None
    assert r["physical_site_clock_bound_seconds"] is None
    assert r["physical_arrival_bound_seconds"] is None
    assert not r["observing_eligible"]
    assert all(
        x["physical_spatial_bound_m"] is None and not x["observing_eligible"] for x in r["cases"]
    )


@pytest.mark.parametrize(
    "w,v",
    [
        (F(0), [F(0)] * 3),
        (F(10**9), [F(0)] * 3),
        (F(0), [F(30000), F(10000), F(-9000)]),
        (F(10**9), [F(30000), F(10000), F(-9000)]),
    ],
)
def test_linear_limit_against_independent_closed_form(w, v):
    # Sherman-Morrison inverse of A I + v v^T/(2c²), not a replay of iteration.
    x = [F(6000000), F(-2000000), F(1000000)]
    a = [F(0)] * 3
    alpha = 1 + w / sf.C**2
    root = [
        xi / alpha
        - vi * sf.dot(v, x) / (2 * sf.C**2 * alpha * (alpha + sf.dot(v, v) / (2 * sf.C**2)))
        for xi, vi in zip(x, v, strict=True)
    ]
    assert sf.certificate(x, v, w, a, root)["exact_bound"] == 0
    z = [root[0] + F("1e-8"), root[1] - F("2e-8"), root[2]]
    certified = sf.certificate(x, v, w, a, z)
    assert sf.l1(sf.difference(z, root)) <= certified["exact_bound"]
    assert F(certified["upper_bound_m"]) >= certified["exact_bound"]


def test_nonlinear_known_root_and_certificate():
    # Construct X from a known root, then perturb the trial point.
    root = [F(6000000), F(-2000000), F(1000000)]
    v, w, a = [F(30000), F(-7000), F(4000)], F(10**9), [F(".006"), F("-.002"), F(".001")]
    x = [ri + ci for ri, ci in zip(root, sf.correction(root, v, w, a), strict=True)]
    z = [root[0] + F(".00001"), *root[1:]]
    cert = sf.certificate(x, v, w, a, z)
    assert cert["root_unique_in_ball"]
    assert sf.l1(sf.difference(z, root)) <= cert["exact_bound"]
    assert cert["bound_scope"] == "declared_polynomial_supplied_inputs_only"
    _, numerical = sf.candidate_inverse(
        [sf.display(sf.FG * t) for t in x],
        [sf.display(t) for t in v],
        sf.display(w),
        [sf.display(t / sf.FB) for t in a],
    )
    assert sf.l1(sf.difference(sf.float_vector(numerical), [sf.FB * t for t in root])) < F("2e-8")


@pytest.mark.parametrize("value", [F(0), F(1, 3), F(1, 10**40), F(1234567, 10**40)])
def test_certificate_display_rounds_outward_exactly(value):
    displayed = F(sf.upward(value))
    assert value <= displayed < value + F("1e-36")


def test_spatial_correction_rotation_covariance():
    def rotate(x):
        return [-x[1], x[0], x[2]]

    r, v, a = [F(6e6), F(2e6), F(-1e6)], [F(20000), F(9000), F(-3000)], [F(".006"), F(".002"), F(0)]
    w = F(10**9)
    assert sf.correction(rotate(r), rotate(v), w, rotate(a)) == rotate(sf.correction(r, v, w, a))


def test_velocity_perpendicular_limit_and_scale_only():
    first, final = sf.candidate_inverse(["0", "6000000", "0"], ["30000", "0", "0"], "0", ["0"] * 3)
    expected = float(sf.FB / sf.FG * 6000000)
    assert first[0] == final[0] == first[2] == final[2] == 0
    assert abs(first[1] - expected) < 2e-9
    assert np.array_equal(first, final)


@pytest.mark.parametrize(
    "kind",
    ["omit_pn", "omit_tdb_scaling", "omit_tt_unscaling", "reverse_pn_sign", "omit_acceleration"],
)
def test_frozen_faults_detected_in_all_48_cases(inputs, kind):
    def broken(p, v, w, a):
        if kind == "omit_acceleration":
            return sf.candidate_inverse(p, v, w, ["0"] * 3)
        if kind == "omit_pn":
            out = np.array(p, dtype=float) * float(sf.FB / sf.FG)
            return out, out
        if kind == "omit_tdb_scaling":
            return tuple(x / float(sf.FB) for x in sf.candidate_inverse(p, v, w, a))
        if kind == "omit_tt_unscaling":
            return sf.candidate_inverse([str(float(t) * float(sf.FG)) for t in p], v, w, a)
        nominal = np.array(p, dtype=float) * float(sf.FB / sf.FG)
        return tuple(2 * nominal - x for x in sf.candidate_inverse(p, v, w, a))

    r = sf.evaluate_inputs(*inputs, candidate=broken)
    assert not r["audit_passed"]
    assert sum(not x["numerical_checks_passed"] for x in r["cases"]) == 48
    assert r["physical_spatial_bound_m"] is None


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("model_id", "exact-relativistic-model", "model_identity"),
        ("forbidden_imports", ["erfa"], "reference_boundary"),
        ("packages", {}, "reference_boundary"),
        ("kernel_sha256", "0" * 64, "source_provenance"),
        ("gm_source_sha256", "0" * 64, "source_provenance"),
        ("source_position_assumption", "surveyed ITRF", "station_scale_assumption"),
        ("coefficient_model", "complete gravity", "gravity_claim"),
        ("physical_spatial_bound_m", "0", "false_qualification"),
        ("observing_eligible", True, "false_qualification"),
    ],
)
def test_unsupported_reference_claims_rejected(inputs, key, value, error):
    inputs[1][key] = value
    with pytest.raises(sf.SiteFrameError, match=error):
        sf.evaluate_inputs(*inputs)


@pytest.mark.parametrize("source", range(6))
@pytest.mark.parametrize("value", ["0", "2e-13"])
def test_published_statement_cannot_promote_to_physical_total(inputs, source, value):
    inputs[0]["sources"][source]["numeric_physical_bound_seconds"] = value
    with pytest.raises(sf.SiteFrameError, match="unsupported_bound_transfer"):
        sf.evaluate_inputs(*inputs)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing", "site_inventory"),
        ("duplicate", "site_inventory"),
        ("position", "frozen_event_context"),
        ("epoch", "frozen_event_context"),
        ("velocity", "frozen_event_context"),
        ("site", "frozen_event_context"),
        ("earth", "body_inventory"),
        ("emb", "body_inventory"),
        ("duplicate_body", "body_inventory"),
        ("missing_control", "control_inventory"),
        ("trace_length", "reference_trace_count"),
        ("inverse_sign", "reference_trace_update"),
        ("output_scale", "output_scale"),
        ("tolerance", "frozen_design"),
        ("scale", "scale_constants"),
        ("gate", "gate_changed"),
        ("prior", "combined_gate"),
        ("evidence", "evidence_inventory"),
    ],
)
def test_context_and_protocol_faults(inputs, mutation, error):
    p, f = inputs[:2]
    row = f["cases"][0]
    if mutation == "missing":
        f["cases"].pop()
    elif mutation == "duplicate":
        f["cases"][1] = copy.deepcopy(row)
    elif mutation == "position":
        row["position_tt_m"][0] = "0"
    elif mutation == "epoch":
        row["et_seconds"] = "0"
    elif mutation == "velocity":
        row["velocity_m_s"][0] = "0"
    elif mutation == "site":
        row["site"]["datum"] = "GRS80"
    elif mutation == "earth":
        row["bodies"][0]["id"] = 399
    elif mutation == "emb":
        row["bodies"][0]["id"] = 3
    elif mutation == "duplicate_body":
        row["bodies"][1] = copy.deepcopy(row["bodies"][0])
    elif mutation == "missing_control":
        f["zero_controls"].pop()
    elif mutation == "trace_length":
        row["reference"]["tcb_trace_m"].pop()
    elif mutation == "inverse_sign":
        row["reference"]["tcb_trace_m"][0][0] = "0"
    elif mutation == "output_scale":
        row["reference"]["tdb_inverse_m"][0] = "0"
    elif mutation == "tolerance":
        p["design"]["candidate_reference_l1_m"] = "1"
    elif mutation == "scale":
        p["constants"]["L_B"] = "0"
    elif mutation == "gate":
        p["gate"]["physical_spatial_bound_m"] = "1e-9"
    elif mutation == "prior":
        inputs[3]["combined_counts"]["executed"] = 288
    elif mutation == "evidence":
        p["sources"].pop()
    with pytest.raises(sf.SiteFrameError, match=error):
        sf.evaluate_inputs(*inputs)


@pytest.mark.parametrize("value", ["nan", "Infinity", "-Infinity", "1e999", "", 1.0, True])
def test_nonfinite_or_nonstrings_rejected(value):
    with pytest.raises(sf.SiteFrameError, match="finite_decimal_string_required"):
        sf.rat(value)


@pytest.mark.parametrize(
    "fault,error",
    [
        ("v", "coefficient_domain"),
        ("a", "coefficient_domain"),
        ("w", "coefficient_domain"),
        ("x", "ball_not_invariant"),
        ("z", "point_outside_ball"),
    ],
)
def test_certificate_domain_is_enforced(fault, error):
    x, v, a, z, w = [F(1)] * 3, [F(1)] * 3, [F(0)] * 3, [F(1)] * 3, F(1)
    if fault == "v":
        v[0] = F(70001)
    elif fault == "a":
        a[0] = F(".031")
    elif fault == "w":
        w = F(-1)
    elif fault == "x":
        x[0] = sf.RADIUS
    else:
        z[0] = sf.RADIUS
    with pytest.raises(sf.SiteFrameError, match=error):
        sf.certificate(x, v, w, a, z)


def test_gravity_replay_known_one_body():
    w, a = sf.replay_gravity([dict(gm_km3_s2="1", displacement_tdb_m=["1000", "0", "0"])])
    assert w == 1000000 and a == [1000, 0, 0]


def test_coefficient_reader_mismatch_retained_as_failure(inputs):
    inputs[1]["cases"][0]["fresh_earth_velocity_m_s"][0] = "0"
    result = sf.evaluate_inputs(*inputs)
    assert not result["audit_passed"]
    assert sum(not r["numerical_checks_passed"] for r in result["cases"]) == 1


def test_candidate_nan_rejected(inputs):
    with pytest.raises(sf.SiteFrameError, match="candidate_nonfinite"):
        sf.evaluate_inputs(*inputs, candidate=lambda *a: ([float("nan")] * 3, [0.0] * 3))


def test_decimal_context_isolation(inputs):
    expected = sf.evaluate_inputs(*inputs)
    with localcontext() as context:
        context.prec = 6
        assert sf.evaluate_inputs(*inputs) == expected


def test_manifest_and_reference_boundary(monkeypatch, tmp_path):
    policy, fixture, *_ = sf.load_inputs()
    source = sf.ROOT / "validation/reference_generation/site_frame.py"
    assert fixture["policy_sha256"] == sf.sha(sf.POLICY)
    assert fixture["generator_sha256"] == sf.sha(source)
    assert fixture["packages"] == policy["reference_packages"]
    imports = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    assert not imports & {"astropy", "erfa", "astroscope", "validation", "skyfield", "pint"}
    assert {"fractions", "spiceypy"} <= imports
    fake = tmp_path / "manifest.json"
    fake.write_text('{"files": {}}')
    monkeypatch.setattr(sf, "MANIFEST", fake)
    with pytest.raises(sf.SiteFrameError, match="manifest_checksum"):
        sf.load_inputs()


def test_live_cli_provenance_and_network(tmp_path):
    path = tmp_path / "audit.json"
    subprocess.run(
        [sys.executable, "-m", "validation.site_frame", "--output", str(path)],
        cwd=sf.ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ASTROSCOPE_IMPLEMENTATION_COMMIT": "head-marker",
            "ASTROSCOPE_CHECKOUT_COMMIT": "checkout-marker",
        },
    )
    r = json.loads(path.read_text())
    assert r["audit_passed"] and not r["observing_eligible"]
    assert r["implementation_commit"] == "head-marker"
    assert r["checkout_commit"] == "checkout-marker"
    with pytest.raises(RuntimeError, match="offline"):
        sf.deny_network()
