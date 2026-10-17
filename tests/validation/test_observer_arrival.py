"""Independent fixture, failure, offline and precision gates for Mission 38."""

from __future__ import annotations

import copy
import socket
from decimal import Decimal, localcontext

import astropy.units as u
import erfa
import numpy as np
import pytest
from astropy.time import Time, TimeDelta
from astropy.utils import iers

from validation import observer_arrival_model as model
from validation.observer_arrival import evaluate


@pytest.fixture(scope="module")
def inputs():
    return model.load_inputs()


@pytest.fixture
def case(inputs):
    return copy.deepcopy(inputs[1]["cases"][0])


@pytest.fixture
def converter():
    with model.frozen_converter() as value:
        yield value


def test_independent_reference_benchmark():
    result = evaluate()
    assert result["passed"], result["maxima_seconds"]
    assert result["counts"] == dict(
        geometric=288, leap=5, geometric_passed=288, leap_passed=5, excluded=0
    )
    assert result["observing_eligible"] is False
    assert all(v > 0 for v in result["correction_sign_counts"].values())
    for mutation in result["mutation_checks"].values():
        assert mutation["tested_count"] == 288
        assert mutation["detected_count"] > 0


def test_cartesian_coverage_and_contact_probes(inputs):
    policy, fixture = inputs
    expected = {
        (d, s["name"], t["ra_deg"], t["dec_deg"], role)
        for d in policy["dates"]
        for s in policy["sites"]
        for t in policy["targets"]
        for role in policy["roles"]
    }
    observed = {
        (r["utc"][:10], r["site"]["name"], r["target"]["ra_deg"], r["target"]["dec_deg"], r["role"])
        for r in fixture["cases"]
    }
    assert observed == expected
    assert len(observed) == len(fixture["cases"]) == 288
    assert fixture["reference"]["packages"]["skyfield"] == "1.55"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"scale": "utc"}, "unsupported_coordinate"),
        ({"scale": "unknown"}, "unsupported_coordinate"),
        ({"reference_position": "heliocentric"}, "unsupported_coordinate"),
        ({"reference_position": "observer"}, "unsupported_coordinate"),
        ({"model_id": "full_relativistic_bjd"}, "unsupported_correction_model"),
        ({"input_state": "resolved_observer"}, "already_resolved_or_unknown_state"),
        ({"input_state": "unknown"}, "already_resolved_or_unknown_state"),
    ],
)
def test_coordinate_contract(converter, case, kwargs, code):
    with pytest.raises(model.ArrivalError, match=code):
        converter.inverse(case["geometric_tdb_jd"], case["site"], case["target"], **kwargs)


@pytest.mark.parametrize(
    "which,key,value,code",
    [
        ("site", "datum", None, "unsupported_frame"),
        ("site", "latitude_deg", 91, "invalid_context_number"),
        ("site", "longitude_deg", -181, "invalid_context_number"),
        ("site", "elevation_m", float("nan"), "invalid_context_number"),
        ("site", "elevation_m", True, "invalid_context_number"),
        ("site", "latitude_deg", None, "invalid_context_number"),
        ("target", "frame", "FK5", "unsupported_frame"),
        ("target", "ra_deg", float("inf"), "invalid_context_number"),
        ("target", "dec_deg", -91, "invalid_context_number"),
        ("target", "ra_deg", "0", "invalid_context_number"),
        ("target", "coordinate_epoch", None, "unsupported_motion"),
        ("target", "motion_assumption", None, "unsupported_motion"),
        ("target", "motion_assumption", "proper_motion", "unsupported_motion"),
    ],
)
def test_incomplete_or_unsupported_context(converter, case, which, key, value, code):
    case[which][key] = value
    with pytest.raises(model.ArrivalError, match=code):
        converter.inverse(case["geometric_tdb_jd"], case["site"], case["target"])


@pytest.mark.parametrize(
    "value", [None, 2460389.0, True, "NaN", "Infinity", "bad", "1e100", "2399999", "9" * 101]
)
def test_invalid_jd(converter, case, value):
    with pytest.raises(model.ArrivalError):
        converter.inverse(value, case["site"], case["target"])


@pytest.mark.parametrize("value", ["2451545.0", "2460310.5", "2460676.5"])
def test_outside_historical_domain(converter, case, value):
    with pytest.raises(model.ArrivalError, match="outside_frozen_domain"):
        converter.inverse(value, case["site"], case["target"])
    with pytest.raises(model.ArrivalError, match="outside_frozen_domain"):
        converter.observer_utc(value)


def test_forward_requires_explicit_tai(converter, case):
    with pytest.raises(model.ArrivalError, match="observer_tai_required"):
        converter.forward(Time("2024-03-20", scale="utc"), case["site"], case["target"])


def test_solver_nonconvergence(converter, case, monkeypatch):
    calls = []

    def alternating(*args):
        calls.append(1)
        return TimeDelta((-1) ** len(calls), format="sec", scale="tdb")

    monkeypatch.setattr(converter, "_correction", alternating)
    with pytest.raises(model.ArrivalError, match="solver_nonconvergence"):
        converter.inverse(case["geometric_tdb_jd"], case["site"], case["target"])
    assert len(calls) == 8


def test_nonfinite_solver_rejected(converter, case, monkeypatch):
    monkeypatch.setattr(
        converter, "_correction", lambda *args: TimeDelta(float("nan"), format="sec", scale="tdb")
    )
    with pytest.raises(model.ArrivalError, match="nonfinite_solver_residual"):
        converter.inverse(case["geometric_tdb_jd"], case["site"], case["target"])


def test_sub_single_float_jd_precision_survives(converter, case):
    with localcontext() as ctx:
        ctx.prec = 80
        first = Decimal("2460389.5")  # Exact binary midpoint; both inputs round to it.
        second = first + Decimal("1e-10")
        assert float(first) == float(second)
        a = converter.inverse(str(first), case["site"], case["target"])
        b = converter.inverse(str(second), case["site"], case["target"])
    assert float((b.tai - a.tai).to_value(u.s)) == pytest.approx(8.64e-6, abs=1e-7)
    assert not a.observing_eligible and not b.observing_eligible


@pytest.mark.parametrize("index", [1, 2, 3])
def test_leap_datetime_rejects(converter, inputs, index):
    row = inputs[1]["leap_cases"][index]
    assert converter.observer_utc(row["observer_tai_jd"]).isot == row["utc"]
    with pytest.raises(model.ArrivalError, match="unrepresentable_utc_datetime"):
        converter.datetime_export(row["observer_tai_jd"])


def test_elapsed_si_margin_through_leap(converter, inputs):
    rows = inputs[1]["leap_cases"]
    a = model.time_from_jd(rows[0]["observer_tai_jd"], "tai")
    b = model.time_from_jd(rows[-1]["observer_tai_jd"], "tai")
    assert (b - a).to_value(u.s) == pytest.approx(2, abs=1e-8)
    assert (a + TimeDelta(1, format="sec")).utc.isot.startswith("2016-12-31T23:59:60")
    assert (
        converter.datetime_export(rows[-1]["observer_tai_jd"]).isoformat() == "2017-01-01T00:00:00"
    )


def test_frozen_context_restores_tables_and_blocks_network():
    # Initialize lazy table loading before snapshotting external state.
    _ = Time("2024-01-01", scale="tai").utc
    previous_leaps = erfa.leap_seconds.get().copy()
    previous_download = iers.conf.auto_download
    previous_table = iers.earth_orientation_table.get()
    with pytest.raises(RuntimeError, match="deliberate failure"):
        with model.frozen_converter() as converter:
            with pytest.raises(RuntimeError, match="offline"):
                socket.create_connection(("example.invalid", 80))
            assert iers.conf.auto_download is False
            raise RuntimeError("deliberate failure")
    assert np.array_equal(erfa.leap_seconds.get(), previous_leaps)
    assert iers.conf.auto_download == previous_download
    assert iers.earth_orientation_table.get() is previous_table
    with pytest.raises(model.ArrivalError, match="research_context_closed"):
        converter.observer_utc("2460389.5")


@pytest.mark.parametrize(
    "path", [model.MANIFEST, model.POLICY, model.EOP, model.LEAPS, model.FIXTURE]
)
def test_input_integrity_rejects_tampering(monkeypatch, path):
    original = model.sha
    monkeypatch.setattr(model, "sha", lambda p: "corrupt" if p == path else original(p))
    with pytest.raises(model.ArrivalError, match="checksum"):
        model.load_inputs()
