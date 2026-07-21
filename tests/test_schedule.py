"""Tests for night timelines and observation schedules."""

from datetime import date, time

import pytest
from astropy.utils import iers

from astroscope.schedule import (
    ScheduleChartLabels,
    TimelinePoint,
    calculate_observation_schedule,
    create_local_time_grid,
    create_schedule_figure,
)

iers.conf.auto_download = False


def test_time_grid_crosses_midnight() -> None:
    grid = create_local_time_grid(
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(0, 0),
        timezone_name="Asia/Tokyo",
        interval_minutes=60,
    )

    assert len(grid) == 5
    assert grid[0].date() == date(2024, 1, 1)
    assert grid[-1].date() == date(2024, 1, 2)
    assert grid[-1].time().hour == 0


def test_time_grid_includes_exact_end_time() -> None:
    grid = create_local_time_grid(
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(23, 30),
        timezone_name="Asia/Tokyo",
        interval_minutes=60,
    )

    assert grid[-1].time().hour == 23
    assert grid[-1].time().minute == 30


def test_equal_start_and_end_raise_error() -> None:
    with pytest.raises(ValueError):
        create_local_time_grid(
            local_date=date(2024, 1, 1),
            start_time=time(20, 0),
            end_time=time(20, 0),
            timezone_name="Asia/Tokyo",
            interval_minutes=60,
        )


def test_catalog_schedule_has_timeline_points() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(0, 0),
        interval_minutes=120,
        minimum_altitude_degrees=0.0,
        minimum_moon_separation_degrees=0.0,
        minimum_score=0.0,
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    assert result.sample_count == 3
    assert result.evaluated_target_count == 5
    assert len(result.timeline_points) == 15
    assert result.schedule_blocks


def test_schedule_blocks_do_not_overlap() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(2, 0),
        interval_minutes=120,
        minimum_altitude_degrees=0.0,
        minimum_moon_separation_degrees=0.0,
        minimum_score=0.0,
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    for first, second in zip(
        result.schedule_blocks,
        result.schedule_blocks[1:],
        strict=False,
    ):
        assert first.end_local <= second.start_local

    assert all(block.duration_minutes > 0.0 for block in result.schedule_blocks)


def test_empty_categories_return_empty_schedule() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(22, 0),
        interval_minutes=60,
        include_catalog_targets=False,
        include_solar_system_targets=False,
    )

    assert result.timeline_points == ()
    assert result.schedule_blocks == ()
    assert result.evaluated_target_count == 0


def test_schedule_figure_contains_target_trace() -> None:
    points = (
        TimelinePoint(
            object_key="sirius",
            category="catalog",
            local_datetime_iso=("2024-01-01T20:00+09:00"),
            utc_datetime_iso=("2024-01-01T11:00:00+00:00"),
            altitude_degrees=30.0,
            azimuth_degrees=150.0,
            moon_separation_degrees=70.0,
            total_score=65.0,
            rating="very_good",
            status="observable",
            recommended=True,
            sun_altitude_degrees=-20.0,
        ),
        TimelinePoint(
            object_key="sirius",
            category="catalog",
            local_datetime_iso=("2024-01-01T21:00+09:00"),
            utc_datetime_iso=("2024-01-01T12:00:00+00:00"),
            altitude_degrees=40.0,
            azimuth_degrees=170.0,
            moon_separation_degrees=72.0,
            total_score=75.0,
            rating="very_good",
            status="observable",
            recommended=True,
            sun_altitude_degrees=-25.0,
        ),
    )

    labels = ScheduleChartLabels(
        title="Timeline",
        time_axis="Time",
        score_axis="Score",
        altitude="Altitude",
        moon_separation="Moon separation",
        rating="Rating",
        recommended="Recommended",
        yes="Yes",
        no="No",
    )

    figure = create_schedule_figure(
        points=points,
        display_names={"sirius": "Sirius"},
        rating_names={"very_good": "Very good"},
        labels=labels,
    )

    assert len(figure.data) == 1
    assert figure.data[0].name == "Sirius"
    assert list(figure.data[0].y) == [65.0, 75.0]
    assert list(figure.layout.yaxis.range) == [0, 100]
