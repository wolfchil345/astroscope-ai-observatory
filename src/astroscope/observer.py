"""Observer-location and astronomical-time calculations."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time


@dataclass(frozen=True, slots=True)
class ObserverPreset:
    """A predefined observing location."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float
    timezone_name: str


@dataclass(frozen=True, slots=True)
class AstronomicalTimeResult:
    """Calculated astronomical time values."""

    local_datetime_iso: str
    utc_datetime_iso: str
    julian_date: float
    modified_julian_date: float
    local_sidereal_time_hours: float
    local_sidereal_time_hms: str


OBSERVER_PRESETS: Final[dict[str, ObserverPreset]] = {
    "osaka": ObserverPreset(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
    ),
    "bangkok": ObserverPreset(
        latitude_deg=13.7563,
        longitude_deg=100.5018,
        elevation_m=2.0,
        timezone_name="Asia/Bangkok",
    ),
    "seoul": ObserverPreset(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        elevation_m=38.0,
        timezone_name="Asia/Seoul",
    ),
    "greenwich": ObserverPreset(
        latitude_deg=51.4769,
        longitude_deg=0.0005,
        elevation_m=46.0,
        timezone_name="UTC",
    ),
}


def validate_observer_coordinates(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
) -> None:
    """Validate geodetic observer coordinates."""

    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")

    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    if not -500.0 <= elevation_m <= 10_000.0:
        raise ValueError("Elevation must be between -500 and 10000 metres.")


def create_earth_location(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
) -> EarthLocation:
    """Create an Astropy EarthLocation from geodetic coordinates."""

    validate_observer_coordinates(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
    )

    return EarthLocation.from_geodetic(
        lon=longitude_deg * u.deg,
        lat=latitude_deg * u.deg,
        height=elevation_m * u.m,
    )


def get_timezone(timezone_name: str) -> ZoneInfo:
    """Return a validated time-zone object."""

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Unknown time zone: {timezone_name}") from error


def local_datetime_to_utc(
    local_date: date,
    local_time: time,
    timezone_name: str,
) -> datetime:
    """Convert a local date and time into UTC."""

    timezone_info = get_timezone(timezone_name)
    naive_time = local_time.replace(tzinfo=None)

    local_datetime = datetime.combine(
        local_date,
        naive_time,
        tzinfo=timezone_info,
    )

    return local_datetime.astimezone(UTC)


def decimal_hours_to_hms(hours: float) -> str:
    """Convert decimal hours into HH:MM:SS format."""

    wrapped_hours = hours % 24.0
    total_seconds = int(round(wrapped_hours * 3600.0)) % 86_400

    hour_value, remaining_seconds = divmod(total_seconds, 3600)
    minute_value, second_value = divmod(remaining_seconds, 60)

    return f"{hour_value:02d}:{minute_value:02d}:{second_value:02d}"


def calculate_astronomical_time(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
) -> AstronomicalTimeResult:
    """Calculate UTC, Julian dates, and local sidereal time."""

    location = create_earth_location(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
    )

    timezone_info = get_timezone(timezone_name)

    utc_datetime = local_datetime_to_utc(
        local_date=local_date,
        local_time=local_time,
        timezone_name=timezone_name,
    )

    local_datetime = utc_datetime.astimezone(timezone_info)

    astronomical_time = Time(
        utc_datetime,
        scale="utc",
        location=location,
    )

    sidereal_time = astronomical_time.sidereal_time("apparent")
    sidereal_hours = float(sidereal_time.hour)

    return AstronomicalTimeResult(
        local_datetime_iso=local_datetime.isoformat(timespec="seconds"),
        utc_datetime_iso=utc_datetime.isoformat(timespec="seconds"),
        julian_date=float(astronomical_time.jd),
        modified_julian_date=float(astronomical_time.mjd),
        local_sidereal_time_hours=sidereal_hours,
        local_sidereal_time_hms=decimal_hours_to_hms(sidereal_hours),
    )
