"""Tests for observer-location and astronomical-time calculations."""

from datetime import UTC, date, datetime, time

import pytest

from astroscope.observer import (
    calculate_astronomical_time,
    create_earth_location,
    decimal_hours_to_hms,
    local_datetime_to_utc,
    validate_observer_coordinates,
)


def test_create_earth_location() -> None:
    location = create_earth_location(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
    )

    longitude, latitude, height = location.to_geodetic()

    assert latitude.deg == pytest.approx(34.6937)
    assert longitude.deg == pytest.approx(135.5023)
    assert height.value == pytest.approx(15.0)


def test_tokyo_local_time_converts_to_utc() -> None:
    result = local_datetime_to_utc(
        local_date=date(2026, 1, 1),
        local_time=time(12, 0),
        timezone_name="Asia/Tokyo",
    )

    assert result == datetime(
        2026,
        1,
        1,
        3,
        0,
        tzinfo=UTC,
    )


def test_bangkok_local_time_converts_to_utc() -> None:
    result = local_datetime_to_utc(
        local_date=date(2026, 1, 1),
        local_time=time(12, 0),
        timezone_name="Asia/Bangkok",
    )

    assert result == datetime(
        2026,
        1,
        1,
        5,
        0,
        tzinfo=UTC,
    )


def test_julian_and_modified_julian_dates_are_consistent() -> None:
    result = calculate_astronomical_time(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
    )

    expected_mjd = result.julian_date - 2_400_000.5

    assert result.modified_julian_date == pytest.approx(expected_mjd)
    assert 0.0 <= result.local_sidereal_time_hours < 24.0
    assert len(result.local_sidereal_time_hms) == 8
    assert result.utc_datetime_iso.endswith("+00:00")


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (0.0, "00:00:00"),
        (1.5, "01:30:00"),
        (23.9997222, "23:59:59"),
        (24.0, "00:00:00"),
        (25.0, "01:00:00"),
    ],
)
def test_decimal_hours_to_hms(hours: float, expected: str) -> None:
    assert decimal_hours_to_hms(hours) == expected


@pytest.mark.parametrize(
    ("latitude", "longitude", "elevation"),
    [
        (91.0, 0.0, 0.0),
        (-91.0, 0.0, 0.0),
        (0.0, 181.0, 0.0),
        (0.0, -181.0, 0.0),
        (0.0, 0.0, 20_000.0),
    ],
)
def test_invalid_observer_coordinates_raise_error(
    latitude: float,
    longitude: float,
    elevation: float,
) -> None:
    with pytest.raises(ValueError):
        validate_observer_coordinates(
            latitude_deg=latitude,
            longitude_deg=longitude,
            elevation_m=elevation,
        )


def test_unknown_timezone_raises_error() -> None:
    with pytest.raises(ValueError, match="Unknown time zone"):
        local_datetime_to_utc(
            local_date=date(2026, 1, 1),
            local_time=time(12, 0),
            timezone_name="Planet/Mars",
        )
