"""Tests for transit-scheduler dashboard helper functions."""

import pytest

from astroscope import (
    transit_schedule_application,
    transit_schedule_dashboard,
)
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
    build_dashboard_exports,
    ranked_schedule_rows,
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


def test_dashboard_compatibility_imports_preserve_identity() -> None:
    assert (
        transit_schedule_dashboard.TransitDashboardTargetInput
        is transit_schedule_application.TransitDashboardTargetInput
    )
    assert (
        transit_schedule_dashboard.utc_datetime_to_julian_date
        is transit_schedule_application.utc_datetime_to_julian_date
    )
    assert (
        transit_schedule_dashboard.build_schedule_request
        is transit_schedule_application.build_schedule_request
    )
    assert (
        transit_schedule_dashboard.build_schedule_target
        is transit_schedule_application.build_schedule_target
    )


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


def test_build_dashboard_exports_creates_three_formats() -> None:
    ranked = make_ranked_transit()

    result = TransitScheduleResult(
        site=ObserverSite(
            name="Osaka Rooftop",
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

    exports = build_dashboard_exports(result)

    assert exports.csv_filename.startswith("astroscope-transits-osaka-rooftop-")
    assert exports.csv_filename.endswith(".csv")
    assert exports.json_filename.endswith(".json")
    assert exports.calendar_filename.endswith(".ics")

    assert exports.csv_data.startswith("rank,planet_name")
    assert '"planet_name": "Dashboard b"' in exports.json_data
    assert exports.calendar_data.startswith("BEGIN:VCALENDAR\r\n")
    assert "SUMMARY:Transit: Dashboard b" in exports.calendar_data
