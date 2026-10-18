"""Component oracle, convention mismatch and domain-accounting regressions."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from decimal import ROUND_DOWN, Context, Decimal, localcontext

import pytest

from validation import source_reference as s


def descriptor():
    return dict(
        s.CONVENTION,
        source_id="synthetic case",
        algorithm_version="frozen v1",
        data_identity="pinned model data",
    )


def test_independent_log_two_series_sign_and_constant():
    # ln(2) = 2 atanh(1/3), evaluated independently without Decimal.ln().
    with localcontext(Context(prec=60)):
        x = Decimal(1) / 3
        ln2 = 2 * sum(x ** (2 * k + 1) / (2 * k + 1) for k in range(90))
        expected = 2 * Decimal("132712440018000000000") / Decimal("299792458") ** 3 * ln2
        assert abs(s.solar_correction("1", "-1") - expected) < Decimal("1e-60")
    assert s.solar_correction("1", "0") == 0
    assert s.solar_correction("1", "0.8") < 0


def test_radial_normalization_cannot_be_dropped():
    with localcontext(Context(prec=60)):
        shift1 = s.solar_correction("0.9", "0.6") - s.solar_correction("1", "0.6")
        shift2 = s.solar_correction("0.9", "0")
        assert abs(shift1 - shift2) < Decimal("1e-60")
        assert abs(shift1) > Decimal("0.000001")


def test_monotonic_component_behavior():
    assert s.solar_correction("0.9", "0") < s.solar_correction("1", "0")
    assert s.solar_correction("1", "0") < s.solar_correction("1.1", "0")
    assert s.solar_correction("1", "-0.8") > s.solar_correction("1", "0.8")


def test_decimal_context_does_not_change_result():
    expected = s.solar_correction("0.9", "0.6")
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_DOWN
        assert s.solar_correction("0.9", "0.6") == expected


@pytest.mark.parametrize("radius,mu", [("0.9", "-1"), ("1.1", "0.8"), ("1", "0.8")])
def test_component_closed_boundaries(radius, mu):
    assert s.domain_reasons(radius, mu) == []
    assert s.solar_correction(radius, mu).is_finite()


@pytest.mark.parametrize(
    "radius,mu",
    [
        ("0.899999999999999999999", "0"),
        ("1.100000000000000000001", "0"),
        ("1", "0.800000000000000000001"),
        ("1", "-1.000000000000000000001"),
        ("0", "0"),
        ("1", "1"),
        ("-1", "0"),
    ],
)
def test_domain_rejects_without_epsilon_or_clamping(radius, mu):
    with pytest.raises(s.ReferenceError, match="outside_component_domain"):
        s.solar_correction(radius, mu)


@pytest.mark.parametrize("value", [None, True, 1.0, "NaN", "Infinity", "1/2", "1e999", "9" * 81])
def test_nonfinite_or_ambiguous_numeric_input(value):
    with pytest.raises(s.ReferenceError):
        s.solar_correction(value, "0")


def test_explicit_metadata_never_authenticates_source_or_grants_eligibility():
    result = s.source_compatibility(descriptor())
    assert result["status"] == "compatible_declarations_for_study_only"
    assert result["evidence_authenticated"] is False
    assert result["observing_eligible"] is False


@pytest.mark.parametrize("field", list(s.CONVENTION))
def test_convention_mismatch_rejects(field):
    value = descriptor()
    value[field] = "different or unknown"
    with pytest.raises(s.ReferenceError, match="incompatible_"):
        s.source_compatibility(value)


@pytest.mark.parametrize("value", ["BJD_TDB", {"scale": "tdb"}, {}, None])
def test_generic_label_or_missing_inventory_rejects(value):
    with pytest.raises(s.ReferenceError, match="explicit_source_descriptor_required"):
        s.source_compatibility(value)


@pytest.mark.parametrize("field", sorted(s.PROVENANCE))
def test_source_provenance_is_required(field):
    value = descriptor()
    value[field] = " "
    with pytest.raises(s.ReferenceError, match="source_provenance_required"):
        s.source_compatibility(value)


def test_extra_correction_cannot_hide_in_descriptor():
    value = dict(descriptor(), additional_einstein=True)
    with pytest.raises(s.ReferenceError, match="explicit_source_descriptor_required"):
        s.source_compatibility(value)


@pytest.mark.parametrize(
    "path",
    [
        s.MANIFEST,
        s.POLICY,
        s.FIXTURE,
        s.ROOT / "docs/research/evidence/pint_reference_input_audit_v1.json",
        s.ROOT / "validation/reference_generation/source_reference.py",
    ],
)
def test_manifest_and_input_corruption_reject(monkeypatch, path):
    original = s.sha
    monkeypatch.setattr(s, "sha", lambda p: "corrupt" if p == path else original(p))
    with pytest.raises(s.ReferenceError, match="checksum"):
        s.load_inputs()


def test_missing_input_rejects(monkeypatch):
    def missing(_):
        raise FileNotFoundError("missing input")

    monkeypatch.setattr(s, "sha", missing)
    with pytest.raises(s.ReferenceError, match="input_unavailable"):
        s.load_inputs()


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "context",
        "hidden_exclusion",
        "excluded_value",
        "scalar",
        "direction",
        "vector_shape",
    ],
)
def test_census_accounting_and_input_integrity(monkeypatch, fault):
    policy, fixture = s.load_inputs()
    fixture = copy.deepcopy(fixture)
    rows = fixture["historical"]
    included = next(r for r in rows if not r["exclusion_reasons"])
    excluded = next(r for r in rows if r["exclusion_reasons"])
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif fault == "context":
        rows[0]["utc"] = "2025-01-01T00:00:00+00:00"
    elif fault == "hidden_exclusion":
        included.update(status="excluded", exclusion_reasons=["manual"])
    elif fault == "excluded_value":
        excluded["pint_propagation_delay_seconds"] = "0"
    elif fault == "scalar":
        included["radius_au"] = "1.1"
    elif fault == "direction":
        included["direction_icrs"] = ["1", "1", "1"]
    else:
        included["observer_to_sun_au"] = ["1"]
    monkeypatch.setattr(s, "load_inputs", lambda: (policy, fixture))
    with pytest.raises(s.ReferenceError):
        s.evaluate()


def test_reference_error_fails_numeric_qualification(monkeypatch):
    policy, fixture = s.load_inputs()
    fixture = copy.deepcopy(fixture)
    fixture["synthetic"][0]["pint_propagation_delay_seconds"] = "0.1"
    monkeypatch.setattr(s, "load_inputs", lambda: (policy, fixture))
    result = s.evaluate()
    assert result["passed"] is False
    assert result["reference_qualification"] == "failed_component_comparison"
    assert result["observing_eligible"] is False


def test_frozen_census_and_reference_scope():
    result = s.evaluate()
    assert result["passed"]
    assert result["summaries"]["synthetic"]["compared"] == 45
    assert result["summaries"]["historical"]["compared"] == 240
    assert result["summaries"]["historical"]["excluded"] == 48
    assert len(result["rows"]) == 333
    assert result["physical_arrival_bound_seconds"] is None
    assert result["physical_reference_bound_seconds"] is None
    assert result["full_reference_status"] == "unqualified"
    assert result["full_pint_timing_pipeline_executed"] is False
    assert result["observing_eligible"] is False
    for mutation in result["mutations"].values():
        assert mutation["detected"] + mutation["undetected"] == mutation["denominator"] == 285
        assert mutation["detected"] > 0


def test_audit_is_independent_of_astronomy_imports_and_network():
    script = """
import importlib.abc,socket,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'astropy','erfa','numpy','skyfield','pint','astroscope'}:
   raise RuntimeError('forbidden import')
sys.meta_path.insert(0,Block())
def deny(*a,**k): raise RuntimeError('network disabled')
socket.create_connection=deny
socket.socket.connect=deny
socket.socket.connect_ex=deny
from validation.source_reference import evaluate
assert evaluate()['passed']
"""
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_cli_retains_explicit_scope_and_provenance(tmp_path):
    path = tmp_path / "result.json"
    completed = subprocess.run(
        [sys.executable, "-m", "validation.source_reference", "--output", str(path)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(path.read_text())
    assert result["passed"] and result["physical_reference_bound_seconds"] is None
    assert len(result["implementation_commit"]) == 40
    assert result["manifest_sha256"] == s.EXPECTED_MANIFEST_SHA256
