"""Independent exact cases and fail-closed evidence classification for Mission 39."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from validation import arrival_budget as b


def complete_terms():
    return [
        dict(
            id=name,
            kind="conditional_absolute_bound",
            value_seconds="0",
            evidence="synthetic exact bound for arithmetic tests only",
            domain="toy",
        )
        for name in b.REQUIRED
    ]


def test_exact_light_speed_unit_case():
    assert b.vector_bound("299792458") == 1
    assert b.vector_bound("0") == 0
    assert b.vector_bound("10") == Fraction(5, 149896229)


@pytest.mark.parametrize("angle,expected", [("0", "0"), ("0.25", "0.25"), ("2", "2"), ("9", "2")])
def test_direction_chord_enclosure(angle, expected):
    assert b.direction_bound("299792458", angle) == Fraction(expected)


def test_finite_distance_against_exact_pythagorean_geometry():
    # d=4, perpendicular r=3: exact sqrt(4²+3²)-4 = 1 length unit.
    actual = Fraction(1, 299792458)
    bound = b.finite_distance_bound("3", "4")
    assert bound == Fraction(9, 599584916)
    assert actual <= bound
    assert b.finite_distance_bound("0", "4") == 0


@pytest.mark.parametrize("distance", ["0", "2", "3"])
def test_distance_guard(distance):
    with pytest.raises(b.BudgetError, match="distance_must_exceed_radius"):
        b.finite_distance_bound("3", distance)


def test_einstein_amplitude_units():
    assert b.einstein_amplitude_bound("299792458", "299792458") == 1
    assert b.einstein_amplitude_bound("0", "31000") == 0


def test_inverse_affine_model_independent_expected_error():
    # Intended F(t)=t/2. Candidate Fhat(t)=F(t)-1/8; solve Fhat(t)=3/8.
    # Nominal source B=0; residual=3/8, forward error=1/8, root=0, estimate=1.
    assert b.inverse_bound(Fraction(1, 8), "0.375", "0.5", "0") == 1
    assert b.inverse_bound(Fraction(1, 8), "0.375", "0.5", "0.25") == Fraction(5, 4)


@pytest.mark.parametrize("forward,slope", [(None, "1"), (Fraction(0), None), (None, None)])
def test_unknown_inverse_bound_remains_unknown(forward, slope):
    assert b.inverse_bound(forward, "0", slope, "0") is None


@pytest.mark.parametrize("slope", ["0", "-1"])
def test_invalid_inverse_slope(slope):
    with pytest.raises(b.BudgetError):
        b.inverse_bound(Fraction(0), "0", slope, "0")


@pytest.mark.parametrize(
    "value", [True, 0.0, None, "NaN", "Infinity", "1/2", "1e9999", "9" * 81, "-0.1"]
)
def test_bad_numeric_inputs(value):
    with pytest.raises(b.BudgetError):
        b.vector_bound(value)


def test_decimal_context_cannot_change_exact_bounds():
    with localcontext() as ctx:
        ctx.prec = 3
        assert b.vector_bound("10") == Fraction(5, 149896229)
        assert b.inverse_bound(Fraction(1, 8), "0.375", "0.5", "0") == 1


@pytest.mark.parametrize(
    "value", [Fraction(0), Fraction(1, 3), Fraction(1, 10**15), Fraction(10**20, 3), Fraction(1, 8)]
)
def test_serialized_bound_is_outward_rounded(value):
    record = b.encoded_bound(value)
    assert Fraction(int(record["numerator"]), int(record["denominator"])) == value
    upper = Fraction(record["seconds_upper_12dp"])
    assert value <= upper < value + Fraction(1, 10**12)


def test_absolute_budget_uses_sum_not_rss():
    terms = complete_terms()
    terms[0]["value_seconds"], terms[1]["value_seconds"] = "3", "4"
    result = b.assess_forward_ledger(terms, "toy")
    assert result["forward_total"]["seconds_upper_12dp"] == "7.000000000000"
    assert result["status"] == "complete_conditional_only"
    assert result["observing_eligible"] is False


def test_missing_term_is_not_zero():
    terms = complete_terms()
    terms[0].update(kind="unknown", value_seconds=None, reason="no certified bound")
    result = b.assess_forward_ledger(terms, "toy")
    assert result["forward_total"] is None
    assert result["unknown_terms"] == [b.REQUIRED[0]]
    assert b.assess_forward_ledger(complete_terms(), "toy")["forward_total"] is not None


@pytest.mark.parametrize(
    "kind",
    [
        "sampled_discrepancy",
        "standard_uncertainty",
        "library_inclusion_audit",
        "known",
        "not_applicable",
    ],
)
def test_wrong_evidence_class_rejected(kind):
    terms = complete_terms()
    terms[0]["kind"] = kind
    with pytest.raises(b.BudgetError, match="not_an_absolute_bound"):
        b.assess_forward_ledger(terms, "toy")


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "extra", "domain", "evidence", "unknown_zero"]
)
def test_malformed_ledger_rejected(fault):
    terms = complete_terms()
    if fault == "missing":
        terms.pop()
    elif fault == "duplicate":
        terms[-1] = copy.deepcopy(terms[0])
    elif fault == "extra":
        terms.append(dict(terms[0], id="unplanned"))
    elif fault == "domain":
        terms[0]["domain"] = "other"
    elif fault == "evidence":
        terms[0]["evidence"] = ""
    else:
        terms[0].update(kind="unknown", value_seconds="0", reason="missing")
    with pytest.raises(b.BudgetError):
        b.assess_forward_ledger(terms, "toy")


@pytest.mark.parametrize(
    "lo,hi,a,z,closure,expected",
    [
        ("0", "0", "0", "0", "closed", "inside"),
        ("0", "0", "0", "0", "half_open", "outside"),
        ("0", "1", "0", "1", "closed", "inside"),
        ("0", "1", "0", "1", "half_open", "boundary_indeterminate"),
        ("1", "1", "0", "1", "half_open", "outside"),
        ("0", "0", "0", "1", "half_open", "inside"),
        ("-1", "0", "0", "1", "closed", "boundary_indeterminate"),
        ("-1", "0", "0", "1", "half_open", "boundary_indeterminate"),
        ("2", "3", "0", "1", "closed", "outside"),
        ("-2", "-1", "0", "1", "half_open", "outside"),
        ("0.25", "0.5", "0", "1", "half_open", "inside"),
        ("0.9", "1.1", "0", "1", "closed", "boundary_indeterminate"),
        ("1.000000000000000000001", "1.000000000000000000001", "0", "1", "closed", "outside"),
    ],
)
def test_exact_interval_contract(lo, hi, a, z, closure, expected):
    assert b.interval_membership(lo, hi, a, z, closure) == expected


@pytest.mark.parametrize(
    "args",
    [("1", "0", "0", "1", "closed"), ("0", "1", "1", "0", "closed"), ("0", "1", "0", "1", "open")],
)
def test_invalid_interval_contract(args):
    with pytest.raises(b.BudgetError):
        b.interval_membership(*args)


def test_actual_budget_audit_stays_unqualified():
    record = b.evaluate()
    assert record["passed"]
    assert record["physical_arrival_bound"] is None
    assert record["observing_eligible"] is False
    assert len(record["ledger_assessment"]["unknown_terms"]) == 9
    assert record["prospective_contract_scenario_count"] == 20
    assert record["prospective_contract_execution"] == "not_executed_in_production"
    assert len(record["conditional_examples"]) == 6


def test_contract_sections_and_traceability():
    _, _, contract = b.load_inputs()
    assert len({s["name"] for s in contract["required_sections"]}) == 12
    ids = {s["id"] for s in contract["scenarios"]}
    assert all(set(refs) <= ids for refs in contract["mission36_traceability"].values())
    assert contract["production_implementation"] == "not_started"


@pytest.mark.parametrize("path", [b.MANIFEST, b.POLICY, b.LEDGER, b.CONTRACT])
def test_tampered_inputs_reject(monkeypatch, path):
    original = b.sha
    monkeypatch.setattr(b, "sha", lambda p: "corrupt" if p == path else original(p))
    with pytest.raises(b.BudgetError, match="checksum"):
        b.load_inputs()


def test_audit_requires_no_astronomy_or_network():
    script = """
import importlib.abc,socket,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'astropy','erfa','numpy','skyfield','astroscope'}:
   raise RuntimeError('forbidden astronomy import')
sys.meta_path.insert(0,Block())
def deny(*a,**k): raise RuntimeError('network disabled')
socket.create_connection=deny
socket.socket.connect=deny
from validation.arrival_budget import evaluate
r=evaluate()
assert r['passed'] and r['physical_arrival_bound'] is None
print('offline conditional audit passed')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=b.ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert "offline conditional audit passed" in result.stdout


def test_site_aware_clock_inclusion_dispatch(monkeypatch):
    import erfa
    from astropy.coordinates import EarthLocation
    from astropy.time import Time
    from astropy.utils import iers

    calls = []

    def capture(jd1, jd2, ut, lon, u, v):
        calls.append((float(lon), float(u), float(v)))
        return 0.0

    monkeypatch.setattr(erfa, "dtdb", capture)
    with iers.conf.set_temp("auto_download", False):
        _ = Time("2024-03-20", scale="tt").delta_tdb_tt
        _ = Time(
            "2024-03-20", scale="tt", location=EarthLocation.from_geodetic(139.6503, 35.6762, 40)
        ).delta_tdb_tt
    assert calls[0] == (0, 0, 0)
    assert all(x != 0 for x in calls[1])
    # Dispatch evidence only: patched return values never become an accuracy oracle.


def test_example_decimal_rounding_conforms_to_policy():
    for example in b.evaluate()["conditional_examples"]:
        bound = example["conditional_bound"]
        exact = Fraction(int(bound["numerator"]), int(bound["denominator"]))
        assert Fraction(Decimal(bound["seconds_upper_12dp"])) >= exact
    json.dumps(b.evaluate(), allow_nan=False)
