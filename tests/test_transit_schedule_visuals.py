"""Tests for transit-schedule Plotly visualizations."""

from datetime import UTC

import plotly.graph_objects as go
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
from astroscope.transit_schedule_visuals import (
    TransitScheduleVisualError,
    create_schedule_timeline_figure,
    create_transit_altitude_figure,
    create_transit_score_figure,
    julian_date_to_utc_datetime,
)
from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import (
    ObserverSite,
    TransitVisibilitySample,
    TransitVisibilitySummary,
)


def make_ranked_transit() -> RankedTransit:
    """Create one deterministic ranked transit."""

    event = TransitEvent(
        planet_name="Example b",
        transit_number=3,
        mid_transit_jd=2_460_000.20,
        ingress_jd=2_460_000.15,
        egress_jd=2_460_000.25,
        observation_start_jd=2_460_000.10,
        observation_end_jd=2_460_000.30,
        timing_uncertainty_days=0.001,
    )

    samples = tuple(
        TransitVisibilitySample(
            julian_date=julian_date,
            target_altitude_degrees=altitude,
            target_azimuth_degrees=180.0,
            airmass=1.2,
            sun_altitude_degrees=sun_altitude,
            moon_altitude_degrees=moon_altitude,
            moon_separation_degrees=100.0,
            moon_illumination_fraction=0.4,
            target_above_minimum_altitude=True,
            is_astronomical_dark=True,
        )
        for (
            julian_date,
            altitude,
            sun_altitude,
            moon_altitude,
        ) in (
            (
                2_460_000.10,
                40.0,
                -25.0,
                15.0,
            ),
            (
                2_460_000.20,
                60.0,
                -30.0,
                20.0,
            ),
            (
                2_460_000.30,
                45.0,
                -24.0,
                25.0,
            ),
        )
    )

    visibility = TransitVisibilitySummary(
        planet_name="Example b",
        target_name="Example Star",
        site_name="Test Observatory",
        samples=samples,
        midpoint_sample=samples[1],
        minimum_target_altitude_degrees=40.0,
        maximum_target_altitude_degrees=60.0,
        maximum_airmass=1.6,
        minimum_moon_separation_degrees=100.0,
        altitude_sample_fraction=1.0,
        dark_sample_fraction=1.0,
        observable_sample_fraction=1.0,
        full_observation_window_visible=True,
    )

    candidate = TransitObservationCandidate(
        event=event,
        visibility=visibility,
        transit_depth_ppm=2_000.0,
        host_magnitude=10.0,
    )

    score = score_transit_candidate(candidate)

    return RankedTransit(
        rank=1,
        candidate=candidate,
        score=score,
    )


def make_schedule_result(
    ranked_transits: tuple[RankedTransit, ...],
) -> TransitScheduleResult:
    """Create one deterministic schedule result."""

    return TransitScheduleResult(
        site=ObserverSite(
            name="Test Observatory",
            latitude_degrees=35.0,
            longitude_degrees=135.0,
            elevation_meters=100.0,
        ),
        request=TransitScheduleRequest(
            start_jd=2_460_000.0,
            end_jd=2_460_001.0,
        ),
        target_count=1,
        predicted_event_count=len(ranked_transits),
        ranked_transits=ranked_transits,
        targets_without_events=(),
    )


def test_julian_date_conversion_returns_utc_datetime() -> None:
    result = julian_date_to_utc_datetime(2_451_545.0)

    assert result.tzinfo == UTC
    assert result.year == 2000
    assert result.month == 1
    assert result.day == 1


@pytest.mark.parametrize(
    "invalid_julian_date",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_julian_date_conversion_rejects_invalid_value(
    invalid_julian_date: float,
) -> None:
    with pytest.raises(TransitScheduleVisualError):
        julian_date_to_utc_datetime(invalid_julian_date)


def test_timeline_contains_two_traces_per_event() -> None:
    result = make_schedule_result((make_ranked_transit(),))

    figure = create_schedule_timeline_figure(result)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 2
    assert figure.data[0].name == "Observation window"
    assert figure.data[1].name == "Transit"


def test_empty_timeline_contains_annotation() -> None:
    figure = create_schedule_timeline_figure(make_schedule_result(()))

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 0
    assert len(figure.layout.annotations) == 1


def test_altitude_figure_contains_three_curves() -> None:
    figure = create_transit_altitude_figure(make_ranked_transit())

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 3
    assert [trace.name for trace in figure.data] == [
        "Target altitude",
        "Sun altitude",
        "Moon altitude",
    ]


def test_score_figure_contains_component_bar_chart() -> None:
    figure = create_transit_score_figure(make_ranked_transit())

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 8
    assert all(0.0 <= value <= 100.0 for value in figure.data[0].x)
