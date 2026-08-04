"""Tests for smart observation planning and ranking."""

from datetime import date, time

import pytest
from astropy.utils import iers

from astroscope.planner import (
    MAXIMUM_TOTAL_SCORE,
    PLANNER_SOLAR_SYSTEM_BODIES,
    calculate_airmass_score,
    calculate_altitude_score,
    calculate_darkness_score,
    calculate_moon_separation_score,
    calculate_observation_plan,
    classify_planner_rating,
)

iers.conf.auto_download = False


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (-20.0, 0.0),
        (0.0, 0.0),
        (75.0, 45.0),
        (90.0, 45.0),
    ],
)
def test_altitude_score(
    altitude: float,
    expected: float,
) -> None:
    assert calculate_altitude_score(altitude) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("airmass", "expected"),
    [
        (None, 0.0),
        (1.0, 20.0),
        (2.0, 10.0),
        (3.0, 0.0),
        (4.0, 0.0),
    ],
)
def test_airmass_score(
    airmass: float | None,
    expected: float,
) -> None:
    assert calculate_airmass_score(airmass) == pytest.approx(expected)


def test_moon_separation_score() -> None:
    assert calculate_moon_separation_score(
        separation_degrees=30.0,
        minimum_separation_degrees=30.0,
    ) == pytest.approx(0.0)

    assert calculate_moon_separation_score(
        separation_degrees=90.0,
        minimum_separation_degrees=30.0,
    ) == pytest.approx(20.0)


def test_moon_target_receives_full_separation_score() -> None:
    assert calculate_moon_separation_score(
        separation_degrees=0.0,
        minimum_separation_degrees=30.0,
        target_is_moon=True,
    ) == pytest.approx(20.0)


@pytest.mark.parametrize(
    ("sun_altitude", "expected"),
    [
        (10.0, 0.0),
        (0.0, 0.0),
        (-9.0, 7.5),
        (-18.0, 15.0),
        (-30.0, 15.0),
    ],
)
def test_darkness_score(
    sun_altitude: float,
    expected: float,
) -> None:
    assert calculate_darkness_score(sun_altitude) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (90.0, "excellent"),
        (70.0, "very_good"),
        (55.0, "good"),
        (40.0, "fair"),
        (20.0, "poor"),
    ],
)
def test_planner_rating(
    score: float,
    expected: str,
) -> None:
    assert classify_planner_rating(score) == expected


def test_catalog_plan_contains_five_targets() -> None:
    result = calculate_observation_plan(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    assert result.total_target_count == 5
    assert len(result.entries) == 5
    assert all(entry.category == "catalog" for entry in result.entries)


def test_solar_system_plan_excludes_sun() -> None:
    result = calculate_observation_plan(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_targets=False,
        include_solar_system_targets=True,
    )

    object_keys = {entry.object_key for entry in result.entries}

    assert result.total_target_count == len(PLANNER_SOLAR_SYSTEM_BODIES)

    assert "sun" not in object_keys
    assert "moon" in object_keys


def test_plan_is_sorted_by_score() -> None:
    result = calculate_observation_plan(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 7, 1),
        local_time=time(21, 0),
    )

    scores = [entry.total_score for entry in result.entries]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_all_scores_have_valid_ranges() -> None:
    result = calculate_observation_plan(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 7, 1),
        local_time=time(21, 0),
    )

    for entry in result.entries:
        assert 0.0 <= entry.total_score <= (MAXIMUM_TOTAL_SCORE)

        assert 0.0 <= (entry.moon_separation_degrees) <= 180.0


def test_empty_category_selection_returns_empty_plan() -> None:
    result = calculate_observation_plan(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_targets=False,
        include_solar_system_targets=False,
    )

    assert result.entries == ()
    assert result.total_target_count == 0
    assert result.recommended_count == 0


def test_invalid_minimum_score_raises_error() -> None:
    with pytest.raises(ValueError):
        calculate_observation_plan(
            latitude_deg=34.6937,
            longitude_deg=135.5023,
            elevation_m=15.0,
            timezone_name="Asia/Tokyo",
            local_date=date(2024, 1, 1),
            local_time=time(21, 0),
            minimum_score=101.0,
        )


@pytest.mark.parametrize(
    ("fold", "expected_utc"),
    [
        (0, "2026-11-01T05:00:00+00:00"),
        (1, "2026-11-01T06:00:00+00:00"),
    ],
)
def test_planner_preserves_new_york_repeated_hour_fold(
    fold: int,
    expected_utc: str,
) -> None:
    result = calculate_observation_plan(
        latitude_deg=40.7128,
        longitude_deg=-74.0060,
        elevation_m=10.0,
        timezone_name="America/New_York",
        local_date=date(2026, 11, 1),
        local_time=time(1, 0, fold=fold),
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    assert result.utc_datetime_iso == expected_utc
