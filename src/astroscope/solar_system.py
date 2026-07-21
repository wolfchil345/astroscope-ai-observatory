"""Solar System ephemeris and local-sky calculations."""

from dataclasses import dataclass
from datetime import date, time
from math import cos, radians
from typing import Final

import astropy.units as u
from astropy.coordinates import (
    AltAz,
    get_body,
    solar_system_ephemeris,
)
from astropy.time import Time

from astroscope.observer import (
    create_earth_location,
    local_datetime_to_utc,
)
from astroscope.visibility import (
    VisibilityStatus,
    azimuth_to_cardinal,
    classify_visibility,
    validate_minimum_altitude,
)

SOLAR_SYSTEM_BODIES: Final[tuple[str, ...]] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
)


@dataclass(frozen=True, slots=True)
class SolarSystemResult:
    """Calculated apparent position of a Solar System body."""

    body_key: str
    right_ascension_hms: str
    declination_dms: str
    right_ascension_degrees: float
    declination_degrees: float
    distance_au: float
    distance_km: float
    altitude_degrees: float
    azimuth_degrees: float
    cardinal_direction: str
    is_above_horizon: bool
    status: VisibilityStatus
    solar_elongation_degrees: float
    moon_separation_degrees: float
    moon_illumination_fraction: float
    utc_datetime_iso: str
    ephemeris_name: str


def validate_body_name(body: str) -> str:
    """Validate and normalize a Solar System body name."""

    normalized_body = body.strip().lower()

    if normalized_body not in SOLAR_SYSTEM_BODIES:
        supported = ", ".join(SOLAR_SYSTEM_BODIES)

        raise ValueError(f"Unsupported Solar System body: {body}. Supported bodies: {supported}.")

    return normalized_body


def calculate_moon_illumination(
    sun_moon_separation_degrees: float,
) -> float:
    """Estimate the illuminated fraction of the Moon.

    This approximation uses the apparent angular separation
    between the Sun and Moon as observed from Earth.
    """

    if not 0.0 <= sun_moon_separation_degrees <= 180.0:
        raise ValueError("Sun-Moon separation must be between 0 and 180 degrees.")

    illumination = (1.0 - cos(radians(sun_moon_separation_degrees))) / 2.0

    return min(1.0, max(0.0, illumination))


def calculate_solar_system_body(
    body: str,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    minimum_altitude_degrees: float = 20.0,
) -> SolarSystemResult:
    """Calculate a Solar System body's apparent local position."""

    body_key = validate_body_name(body)
    validate_minimum_altitude(minimum_altitude_degrees)

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
        location=location,
    )

    with solar_system_ephemeris.set("builtin"):
        body_position = get_body(
            body_key,
            observation_time,
            location=location,
        )

        sun_position = get_body(
            "sun",
            observation_time,
            location=location,
        )

        moon_position = get_body(
            "moon",
            observation_time,
            location=location,
        )

    horizontal_frame = AltAz(
        obstime=observation_time,
        location=location,
        pressure=0.0 * u.hPa,
    )

    horizontal_position = body_position.transform_to(horizontal_frame)

    altitude_degrees = float(horizontal_position.alt.to_value(u.deg))

    azimuth_degrees = float(horizontal_position.az.to_value(u.deg)) % 360.0

    solar_elongation_degrees = float(body_position.separation(sun_position).to_value(u.deg))

    moon_separation_degrees = float(body_position.separation(moon_position).to_value(u.deg))

    sun_moon_separation_degrees = float(sun_position.separation(moon_position).to_value(u.deg))

    moon_illumination_fraction = calculate_moon_illumination(sun_moon_separation_degrees)

    status = classify_visibility(
        altitude_degrees=altitude_degrees,
        minimum_altitude_degrees=minimum_altitude_degrees,
    )

    return SolarSystemResult(
        body_key=body_key,
        right_ascension_hms=body_position.ra.to_string(
            unit=u.hourangle,
            sep=":",
            precision=3,
            pad=True,
        ),
        declination_dms=body_position.dec.to_string(
            unit=u.deg,
            sep=":",
            precision=2,
            alwayssign=True,
            pad=True,
        ),
        right_ascension_degrees=float(body_position.ra.to_value(u.deg)),
        declination_degrees=float(body_position.dec.to_value(u.deg)),
        distance_au=float(body_position.distance.to_value(u.au)),
        distance_km=float(body_position.distance.to_value(u.km)),
        altitude_degrees=altitude_degrees,
        azimuth_degrees=azimuth_degrees,
        cardinal_direction=azimuth_to_cardinal(azimuth_degrees),
        is_above_horizon=altitude_degrees > 0.0,
        status=status,
        solar_elongation_degrees=solar_elongation_degrees,
        moon_separation_degrees=moon_separation_degrees,
        moon_illumination_fraction=moon_illumination_fraction,
        utc_datetime_iso=utc_datetime.isoformat(timespec="seconds"),
        ephemeris_name="builtin",
    )
