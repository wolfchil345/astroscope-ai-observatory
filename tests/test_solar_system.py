"""Tests for Solar System ephemeris calculations."""

from datetime import date, time

import pytest
from astropy.utils import iers

from astroscope.solar_system import (
    SOLAR_SYSTEM_BODIES,
    calculate_moon_illumination,
    calculate_solar_system_body,
    validate_body_name,
)

iers.conf.auto_download = False


@pytest.mark.parametrize(
    "body",
    SOLAR_SYSTEM_BODIES,
)
def test_supported_body_names_are_valid(body: str) -> None:
    assert validate_body_name(body) == body


def test_body_name_is_normalized() -> None:
    assert validate_body_name("  Jupiter  ") == "jupiter"


def test_invalid_body_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported Solar System body",
    ):
        validate_body_name("vulcan")


@pytest.mark.parametrize(
    ("separation", "expected"),
    [
        (0.0, 0.0),
        (90.0, 0.5),
        (180.0, 1.0),
    ],
)
def test_moon_illumination_reference_values(
    separation: float,
    expected: float,
) -> None:
    result = calculate_moon_illumination(separation)

    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "separation",
    [-1.0, 181.0],
)
def test_invalid_moon_separation_raises_error(
    separation: float,
) -> None:
    with pytest.raises(ValueError):
        calculate_moon_illumination(separation)


def test_jupiter_result_has_valid_ranges() -> None:
    result = calculate_solar_system_body(
        body="jupiter",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        minimum_altitude_degrees=20.0,
    )

    assert result.body_key == "jupiter"
    assert 0.0 <= result.right_ascension_degrees < 360.0
    assert -90.0 <= result.declination_degrees <= 90.0
    assert -90.0 <= result.altitude_degrees <= 90.0
    assert 0.0 <= result.azimuth_degrees < 360.0
    assert result.distance_au > 0.0
    assert result.distance_km > 0.0
    assert 0.0 <= result.solar_elongation_degrees <= 180.0
    assert 0.0 <= result.moon_separation_degrees <= 180.0
    assert 0.0 <= result.moon_illumination_fraction <= 1.0
    assert result.ephemeris_name == "builtin"
    assert result.utc_datetime_iso.endswith("+00:00")


def test_sun_has_zero_solar_separation() -> None:
    result = calculate_solar_system_body(
        body="sun",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 6, 1),
        local_time=time(12, 0),
    )

    assert result.solar_elongation_degrees == pytest.approx(
        0.0,
        abs=1e-8,
    )


def test_moon_has_zero_moon_separation() -> None:
    result = calculate_solar_system_body(
        body="moon",
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 6, 1),
        local_time=time(21, 0),
    )

    assert result.moon_separation_degrees == pytest.approx(
        0.0,
        abs=1e-8,
    )


def test_formatted_coordinates_exist() -> None:
    result = calculate_solar_system_body(
        body="venus",
        latitude_deg=13.7563,
        longitude_deg=100.5018,
        elevation_m=2.0,
        timezone_name="Asia/Bangkok",
        local_date=date(2024, 3, 1),
        local_time=time(18, 0),
    )

    assert result.right_ascension_hms.count(":") == 2
    assert result.declination_dms.count(":") == 2
