"""Mission 54: independent windows plus explicit discrete-sampling counterexamples."""

import json
import math
import socket
from dataclasses import replace

import pytest

from astroscope import transit_visibility as tv
from astroscope.transit_scheduler import TransitEvent
from validation.visibility_sampling import (
    ROOT,
    classification_bounds,
    evaluate,
    frozen_environment,
    load_inputs,
)


@pytest.fixture(scope="module")
def inputs():
    return load_inputs()


@pytest.mark.parametrize("index", range(16))
@pytest.mark.parametrize("count", [3, 9, 25])
def test_independent_window(inputs, index, count, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    policy, fixture = inputs
    with frozen_environment():
        result = evaluate(fixture["windows"][index], count, policy)
    assert result["passed"], result
    assert result["continuous_coverage_certified"] is False


@pytest.mark.parametrize("threshold", [0.0, 20.0])
def test_inclusive_altitude_boundary(inputs, threshold):
    # Contract probe: use returned angle as threshold, not an accuracy oracle.
    _, fixture = inputs
    window = fixture["windows"][0]
    site, target = tv.ObserverSite(**window["site"]), tv.TransitTarget(**window["target"])
    jd = window["event"]["mid_transit_jd"]
    with frozen_environment():
        sample = tv.sample_transit_visibility(site, target, jd)
        angle = sample.target_altitude_degrees
        for limit, expected in [
            (angle, True),
            (math.nextafter(angle, math.inf), False),
            (math.nextafter(angle, -math.inf), True),
        ]:
            actual = tv.sample_transit_visibility(site, target, jd, minimum_altitude_degrees=limit)
            assert actual.target_above_minimum_altitude is expected
        # Secant/horizon equality has a distinct <= 0 null policy.
        assert tv.calculate_airmass_from_altitude_degrees(threshold) == (
            None if threshold == 0 else 1 / math.sin(math.radians(threshold))
        )
        sun = sample.sun_altitude_degrees
        for limit, expected in [
            (sun, True),
            (math.nextafter(sun, -math.inf), False),
            (math.nextafter(sun, math.inf), True),
        ]:
            assert (
                tv.sample_transit_visibility(
                    site, target, jd, darkness_sun_altitude_degrees=limit
                ).is_astronomical_dark
                is expected
            )


def test_reference_boundary_uncertainty(inputs):
    policy, _ = inputs
    grid = {"target_altitude_degrees": [19, 20, 21], "sun_altitude_degrees": [-19, -18, -17]}
    bounds = classification_bounds(grid, policy)
    assert bounds == {"altitude": [1 / 3, 2 / 3], "dark": [1 / 3, 2 / 3], "observable": [0, 1 / 3]}


def test_sparse_grid_can_miss_internal_obstruction(inputs, monkeypatch):
    _, fixture = inputs
    w = fixture["windows"][0]
    event = TransitEvent(**w["event"])
    start, end = event.observation_start_jd, event.observation_end_jd

    def controlled(site, target, jd, **kwargs):
        x = (jd - start) / (end - start)
        # An explicitly synthetic interior visibility gap: all 3 coarse nodes miss it.
        visible = not 0.2 < x < 0.3
        return tv.TransitVisibilitySample(
            jd, 40 if visible else 0, 90, 1.5 if visible else None, -30, -10, 60, 0.5, visible, True
        )

    monkeypatch.setattr(tv, "sample_transit_visibility", controlled)
    coarse = tv.analyze_transit_visibility(event, None, None, sample_count=3)
    dense = tv.analyze_transit_visibility(event, None, None, sample_count=9)
    assert coarse.full_observation_window_visible
    assert coarse.observable_sample_fraction == 1
    assert not dense.full_observation_window_visible
    assert dense.observable_sample_fraction == 8 / 9
    assert coarse.midpoint_sample.julian_date != event.mid_transit_jd


def test_zero_duration_and_tie_contract(inputs, monkeypatch):
    _, fixture = inputs
    event = TransitEvent(**fixture["windows"][0]["event"])

    def controlled(site, target, jd, **kwargs):
        return tv.TransitVisibilitySample(jd, -1, 0, None, -30, 0, 50, 0.5, False, True)

    monkeypatch.setattr(tv, "sample_transit_visibility", controlled)
    event = replace(
        event,
        observation_start_jd=100,
        ingress_jd=100.25,
        mid_transit_jd=100.25,
        egress_jd=100.5,
        observation_end_jd=101,
    )
    result = tv.analyze_transit_visibility(event, None, None, sample_count=3)
    assert result.midpoint_sample.julian_date == 100  # first on exact tie
    assert result.maximum_airmass is None
    event = replace(
        event,
        observation_start_jd=100,
        ingress_jd=100,
        mid_transit_jd=100,
        egress_jd=100,
        observation_end_jd=100,
    )
    result = tv.analyze_transit_visibility(event, None, None, sample_count=3)
    assert [s.julian_date for s in result.samples] == [100] * 3
    assert result.observable_sample_fraction == 0


@pytest.mark.parametrize("field", ["ingress_jd", "egress_jd"])
def test_incomplete_input_window_rejected(inputs, field):
    _, fixture = inputs
    event = TransitEvent(**fixture["windows"][0]["event"])
    event = replace(
        event,
        **{
            field: event.observation_start_jd - 1
            if field == "ingress_jd"
            else event.observation_end_jd + 1
        },
    )
    with pytest.raises(tv.TransitVisibilityError, match="chronological"):
        tv.analyze_transit_visibility(event, None, None)


def test_fixture_has_dense_diagnostics_and_no_physical_promotion(inputs):
    policy, fixture = inputs
    assert policy["physical_arrival_qualification_changed"] is False
    assert all(len(w["grids"]["241"]["jd"]) == 241 for w in fixture["windows"])
    manifest = json.loads((ROOT / "validation/manifests/visibility_sampling_v1.json").read_text())
    assert "validation/fixtures/solar_lunar_eop_v1.json" in manifest["files"]
