"""Tests for horizontal coordinates and visibility."""

from datetime import date, time

import pytest
from astropy.utils import iers

from astroscope.visibility import (
    azimuth_to_cardinal,
    calculate_horizontal_coordinates,
    classify_visibility,
    validate_minimum_altitude,
)

iers.conf.auto_download = False


@pytest.mark.parametrize(
    ("azimuth", "expected"),
    [
        (0.0, "north"),
        (44.9, "northeast"),
        (90.0, "east"),
        (135.0, "southeast"),
        (180.0, "south"),
        (225.0, "southwest"),
        (270.0, "west"),
        (315.0, "northwest"),
        (359.9, "north"),
        (360.0, "north"),
    ],
)
def test_azimuth_to_cardinal(
    azimuth: float,
    expected: str,
) -> None:
    assert azimuth_to_cardinal(azimuth) == expected


@pytest.mark.parametrize(
    ("altitude", "minimum", "expected"),
    [
        (45.0, 20.0, "observable"),
        (10.0, 20.0, "low_altitude"),
        (0.0, 20.0, "below_horizon"),
        (-30.0, 20.0, "below_horizon"),
    ],
)
def test_classify_visibility(
    altitude: float,
    minimum: float,
    expected: str,
) -> None:
    assert (
        classify_visibility(
            altitude_degrees=altitude,
            minimum_altitude_degrees=minimum,
        )
        == expected
    )


@pytest.mark.parametrize(
    "minimum_altitude",
    [-1.0, 91.0],
)
def test_invalid_minimum_altitude_raises_error(
    minimum_altitude: float,
) -> None:
    with pytest.raises(ValueError):
        validate_minimum_altitude(minimum_altitude)


def test_polaris_is_above_horizon_from_osaka() -> None:
    result = calculate_horizontal_coordinates(
        right_ascension="02h31m49.09456s",
        declination="+89d15m50.7923s",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        minimum_altitude_degrees=20.0,
    )

    assert result.is_above_horizon
    assert result.is_above_minimum_altitude
    assert result.status == "observable"
    assert 25.0 < result.altitude_degrees < 45.0
    assert result.cardinal_direction == "north"
    assert result.airmass is not None


def test_far_southern_target_is_below_osaka_horizon() -> None:
    result = calculate_horizontal_coordinates(
        right_ascension="00h00m00s",
        declination="-80d00m00s",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        minimum_altitude_degrees=20.0,
    )

    assert not result.is_above_horizon
    assert not result.is_above_minimum_altitude
    assert result.status == "below_horizon"
    assert result.altitude_degrees < 0.0
    assert result.airmass is None


def test_horizontal_coordinate_ranges() -> None:
    result = calculate_horizontal_coordinates(
        right_ascension="18h36m56.33635s",
        declination="+38d47m01.2802s",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 7, 1),
        local_time=time(21, 0),
    )

    assert -90.0 <= result.altitude_degrees <= 90.0
    assert 0.0 <= result.azimuth_degrees < 360.0

    assert result.zenith_distance_degrees == pytest.approx(90.0 - result.altitude_degrees)

    assert result.utc_datetime_iso.endswith("+00:00")


def test_non_finite_azimuth_raises_error() -> None:
    with pytest.raises(ValueError):
        azimuth_to_cardinal(float("nan"))
