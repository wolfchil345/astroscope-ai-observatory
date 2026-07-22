"""Tests for transit-scheduler dashboard helper functions."""

from datetime import UTC, date, datetime

import pytest

from astroscope.transit_ranking import (
    RankedTransit,
    TransitObservationCandidate,
    score_transit_candidate,
)
from astroscope.transit_schedule import (
    TransitScheduleRequest,
    TransitScheduleResult,
)
from astroscope.transit_schedule_dashboard import (
    TransitDashboardTargetInput,
    build_schedule_request,
    build_schedule_target,
    ranked_schedule_rows,
    utc_datetime_to_julian_date,
)
from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import (
    ObserverSite,
    TransitVisibilitySample,
    TransitVisibilitySummary,
)


def make_ranked_transit() -> RankedTransit:
    """Create one deterministic ranked event."""

    event = TransitEvent(
        planet_name="Dashboard b",
        transit_number=4,
        mid_transit_jd=2_460_000.20,
        ingress_jd=2_460_000.15,
        egress_jd=2_460_000.25,
        observation_start_jd=2_460_000.10,
        observation_end_jd=2_460_000.30,
        timing_uncertainty_days=0.002,
    )

    sample = TransitVisibilitySample(
        julian_date=event.mid_transit_jd,
        target_altitude_degrees=65.0,
        target_azimuth_degrees=180.0,
        airmass=1.1,
        sun_altitude_degrees=-25.0,
        moon_altitude_degrees=15.0,
        moon_separation_degrees=110.0,
        moon_illumination_fraction=0.3,
        target_above_minimum_altitude=True,
        is_astronomical_dark=True,
    )

    visibility = TransitVisibilitySummary(
        planet_name="Dashboard b",
        target_name="Dashboard Star",
        site_name="Osaka",
        samples=(sample,),
        midpoint_sample=sample,
        minimum_target_altitude_degrees=65.0,
        maximum_target_altitude_degrees=65.0,
        maximum_airmass=1.1,
        minimum_moon_separation_degrees=110.0,
        altitude_sample_fraction=1.0,
        dark_sample_fraction=1.0,
        observable_sample_fraction=1.0,
        full_observation_window_visible=True,
    )

    candidate = TransitObservationCandidate(
        event=event,
        visibility=visibility,
        transit_depth_ppm=2_500.0,
        host_magnitude=9.5,
    )

    return RankedTransit(
        rank=1,
        candidate=candidate,
        score=score_transit_candidate(candidate),
    )


def test_utc_datetime_to_julian_date_known_epoch() -> None:
    value = datetime(
        2000,
        1,
        1,
        12,
        0,
        tzinfo=UTC,
    )

    result = utc_datetime_to_julian_date(value)

    assert result == pytest.approx(2_451_545.0)


def test_utc_datetime_to_julian_date_rejects_naive_value() -> None:
    with pytest.raises(
        ValueError,
        match="timezone",
    ):
        utc_datetime_to_julian_date(
            datetime(
                2026,
                1,
                1,
                0,
                0,
            )
        )


def test_build_schedule_request_covers_complete_dates() -> None:
    request = build_schedule_request(
        date(2026, 1, 1),
        date(2026, 1, 2),
        baseline_before_hours=1.0,
        baseline_after_hours=2.0,
        uncertainty_sigma_multiplier=2.0,
        visibility_sample_count=31,
        minimum_altitude_degrees=25.0,
        darkness_sun_altitude_degrees=-12.0,
    )

    assert isinstance(
        request,
        TransitScheduleRequest,
    )
    assert request.end_jd - request.start_jd == pytest.approx(
        2.0,
        abs=1e-8,
    )
    assert request.baseline_after_hours == 2.0
    assert request.visibility_sample_count == 31
    assert request.minimum_altitude_degrees == 25.0
    assert request.darkness_sun_altitude_degrees == -12.0


def test_build_schedule_request_rejects_reversed_dates() -> None:
    with pytest.raises(
        ValueError,
        match="End date",
    ):
        build_schedule_request(
            date(2026, 1, 2),
            date(2026, 1, 1),
            baseline_before_hours=1.0,
            baseline_after_hours=1.0,
            uncertainty_sigma_multiplier=1.0,
            visibility_sample_count=25,
            minimum_altitude_degrees=20.0,
            darkness_sun_altitude_degrees=-18.0,
        )


def test_build_schedule_target_maps_all_fields() -> None:
    target = build_schedule_target(
        TransitDashboardTargetInput(
            planet_name="Test b",
            host_star_name="Test Star",
            right_ascension_degrees=120.0,
            declination_degrees=30.0,
            orbital_period_days=4.5,
            reference_mid_transit_jd=2_460_000.25,
            transit_duration_hours=2.5,
            period_uncertainty_days=0.0001,
            reference_epoch_uncertainty_days=0.001,
            transit_depth_ppm=1_500.0,
            host_magnitude=10.5,
        )
    )

    assert target.ephemeris.planet_name == "Test b"
    assert target.ephemeris.orbital_period_days == pytest.approx(4.5)
    assert target.target.name == "Test Star"
    assert target.target.right_ascension_degrees == pytest.approx(120.0)
    assert target.transit_depth_ppm == 1_500.0
    assert target.host_magnitude == 10.5


def test_ranked_schedule_rows_contains_display_values() -> None:
    ranked = make_ranked_transit()

    result = TransitScheduleResult(
        site=ObserverSite(
            name="Osaka",
            latitude_degrees=34.6937,
            longitude_degrees=135.5023,
            elevation_meters=15.0,
        ),
        request=TransitScheduleRequest(
            start_jd=2_460_000.0,
            end_jd=2_460_001.0,
        ),
        target_count=1,
        predicted_event_count=1,
        ranked_transits=(ranked,),
        targets_without_events=(),
    )

    rows = ranked_schedule_rows(result)

    assert len(rows) == 1
    assert rows[0]["Rank"] == 1
    assert rows[0]["Planet"] == "Dashboard b"
    assert rows[0]["Full window visible"] is True
    assert rows[0]["Midpoint altitude (deg)"] == 65.0
    assert rows[0]["Moon separation (deg)"] == 110.0
    assert rows[0]["Timing uncertainty (h)"] == pytest.approx(0.048)
