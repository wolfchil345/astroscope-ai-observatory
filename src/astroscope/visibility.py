"""Horizontal-coordinate and visibility calculations."""

from dataclasses import dataclass
from datetime import date, time
from math import isfinite
from typing import Final, Literal

import astropy.units as u
from astropy.coordinates import AltAz
from astropy.time import Time

from astroscope.coordinates import create_icrs_coordinate
from astroscope.observer import (
    create_earth_location,
    local_datetime_to_utc,
)

VisibilityStatus = Literal[
    "observable",
    "low_altitude",
    "below_horizon",
]

CARDINAL_DIRECTIONS: Final[tuple[str, ...]] = (
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
)

AIRMASS_MINIMUM_ALTITUDE_DEGREES: Final[float] = 5.0


@dataclass(frozen=True, slots=True)
class HorizontalCoordinateResult:
    """Calculated position of a celestial object in the local sky."""

    altitude_degrees: float
    azimuth_degrees: float
    zenith_distance_degrees: float
    cardinal_direction: str
    airmass: float | None
    is_above_horizon: bool
    is_above_minimum_altitude: bool
    status: VisibilityStatus
    utc_datetime_iso: str


def validate_minimum_altitude(
    minimum_altitude_degrees: float,
) -> None:
    """Validate an observing-altitude threshold."""

    if not 0.0 <= minimum_altitude_degrees <= 90.0:
        raise ValueError("Minimum altitude must be between 0 and 90 degrees.")


def azimuth_to_cardinal(azimuth_degrees: float) -> str:
    """Convert an azimuth angle into an eight-point direction."""

    if not isfinite(azimuth_degrees):
        raise ValueError("Azimuth must be a finite number.")

    wrapped_azimuth = azimuth_degrees % 360.0

    direction_index = int((wrapped_azimuth + 22.5) // 45.0) % len(CARDINAL_DIRECTIONS)

    return CARDINAL_DIRECTIONS[direction_index]


def classify_visibility(
    altitude_degrees: float,
    minimum_altitude_degrees: float,
) -> VisibilityStatus:
    """Classify a target according to altitude and user threshold."""

    if not -90.0 <= altitude_degrees <= 90.0:
        raise ValueError("Altitude must be between -90 and 90 degrees.")

    validate_minimum_altitude(minimum_altitude_degrees)

    if altitude_degrees <= 0.0:
        return "below_horizon"

    if altitude_degrees < minimum_altitude_degrees:
        return "low_altitude"

    return "observable"


def calculate_horizontal_coordinates(
    right_ascension: str,
    declination: str,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    minimum_altitude_degrees: float = 20.0,
) -> HorizontalCoordinateResult:
    """Transform an ICRS position into local AltAz coordinates."""

    validate_minimum_altitude(minimum_altitude_degrees)

    target = create_icrs_coordinate(
        right_ascension=right_ascension,
        declination=declination,
    )

    location = create_earth_location(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
    )

    utc_datetime = local_datetime_to_utc(
        local_date=local_date,
        local_time=local_time,
        timezone_name=timezone_name,
    )

    observation_time = Time(
        utc_datetime,
        scale="utc",
    )

    horizontal_frame = AltAz(
        obstime=observation_time,
        location=location,
        pressure=0.0 * u.hPa,
    )

    horizontal_coordinate = target.transform_to(horizontal_frame)

    altitude_degrees = float(horizontal_coordinate.alt.to_value(u.deg))

    azimuth_degrees = float(horizontal_coordinate.az.to_value(u.deg)) % 360.0

    zenith_distance_degrees = 90.0 - altitude_degrees

    status = classify_visibility(
        altitude_degrees=altitude_degrees,
        minimum_altitude_degrees=minimum_altitude_degrees,
    )

    raw_airmass = float(horizontal_coordinate.secz.value)

    if (
        altitude_degrees >= AIRMASS_MINIMUM_ALTITUDE_DEGREES
        and raw_airmass > 0.0
        and isfinite(raw_airmass)
    ):
        airmass: float | None = raw_airmass
    else:
        airmass = None

    return HorizontalCoordinateResult(
        altitude_degrees=altitude_degrees,
        azimuth_degrees=azimuth_degrees,
        zenith_distance_degrees=zenith_distance_degrees,
        cardinal_direction=azimuth_to_cardinal(azimuth_degrees),
        airmass=airmass,
        is_above_horizon=altitude_degrees > 0.0,
        is_above_minimum_altitude=(altitude_degrees >= minimum_altitude_degrees),
        status=status,
        utc_datetime_iso=utc_datetime.isoformat(timespec="seconds"),
    )
