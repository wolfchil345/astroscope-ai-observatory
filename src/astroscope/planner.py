"""Transparent observation-planning and target-ranking engine."""

from dataclasses import dataclass
from datetime import date, time
from math import isfinite, radians, sin
from typing import Final, Literal

import astropy.units as u
from astropy.coordinates import AltAz, SkyCoord, get_body, solar_system_ephemeris
from astropy.time import Time

from astroscope.coordinates import CELESTIAL_PRESETS
from astroscope.observer import (
    create_earth_location,
    local_datetime_to_utc,
)
from astroscope.solar_system import (
    SOLAR_SYSTEM_BODIES,
    calculate_solar_system_body,
)
from astroscope.visibility import (
    VisibilityStatus,
    calculate_horizontal_coordinates,
)

PlannerCategory = Literal["catalog", "solar_system"]

PlannerRating = Literal[
    "excellent",
    "very_good",
    "good",
    "fair",
    "poor",
]

ALTITUDE_MAX_SCORE: Final[float] = 45.0
AIRMASS_MAX_SCORE: Final[float] = 20.0
MOON_SEPARATION_MAX_SCORE: Final[float] = 20.0
DARKNESS_MAX_SCORE: Final[float] = 15.0

MAXIMUM_TOTAL_SCORE: Final[float] = (
    ALTITUDE_MAX_SCORE + AIRMASS_MAX_SCORE + MOON_SEPARATION_MAX_SCORE + DARKNESS_MAX_SCORE
)

PLANNER_SOLAR_SYSTEM_BODIES: Final[tuple[str, ...]] = tuple(
    body for body in SOLAR_SYSTEM_BODIES if body != "sun"
)


@dataclass(frozen=True, slots=True)
class ObservationPlanEntry:
    """One ranked astronomical observation target."""

    object_key: str
    category: PlannerCategory
    altitude_degrees: float
    azimuth_degrees: float
    cardinal_direction: str
    airmass: float | None
    moon_separation_degrees: float
    status: VisibilityStatus
    altitude_score: float
    airmass_score: float
    moon_separation_score: float
    darkness_score: float
    total_score: float
    rating: PlannerRating
    recommended: bool


@dataclass(frozen=True, slots=True)
class ObservationPlanResult:
    """Complete target-ranking result for one observation time."""

    entries: tuple[ObservationPlanEntry, ...]
    sun_altitude_degrees: float
    recommended_count: int
    total_target_count: int
    utc_datetime_iso: str


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Restrict a numeric value to a closed interval."""

    return max(minimum, min(maximum, value))


def calculate_altitude_score(
    altitude_degrees: float,
) -> float:
    """Score target altitude from zero to 45 points."""

    if not -90.0 <= altitude_degrees <= 90.0:
        raise ValueError("Altitude must be between -90 and 90 degrees.")

    if altitude_degrees <= 0.0:
        return 0.0

    altitude_fraction = clamp(
        altitude_degrees / 75.0,
        0.0,
        1.0,
    )

    return ALTITUDE_MAX_SCORE * altitude_fraction


def calculate_airmass_score(
    airmass: float | None,
) -> float:
    """Score airmass from zero to 20 points."""

    if airmass is None:
        return 0.0

    if not isfinite(airmass) or airmass <= 0.0:
        raise ValueError("Airmass must be a positive finite number.")

    airmass_fraction = clamp(
        (3.0 - airmass) / 2.0,
        0.0,
        1.0,
    )

    return AIRMASS_MAX_SCORE * airmass_fraction


def calculate_moon_separation_score(
    separation_degrees: float,
    minimum_separation_degrees: float,
    *,
    target_is_moon: bool = False,
) -> float:
    """Score angular separation from the Moon."""

    if not 0.0 <= separation_degrees <= 180.0:
        raise ValueError("Moon separation must be between 0 and 180 degrees.")

    if not 0.0 <= minimum_separation_degrees <= 180.0:
        raise ValueError("Minimum Moon separation must be between 0 and 180 degrees.")

    if target_is_moon:
        return MOON_SEPARATION_MAX_SCORE

    if separation_degrees < minimum_separation_degrees:
        return 0.0

    ideal_separation = 90.0 if minimum_separation_degrees < 90.0 else 180.0

    if ideal_separation == minimum_separation_degrees:
        return MOON_SEPARATION_MAX_SCORE

    separation_fraction = clamp(
        (separation_degrees - minimum_separation_degrees)
        / (ideal_separation - minimum_separation_degrees),
        0.0,
        1.0,
    )

    return MOON_SEPARATION_MAX_SCORE * separation_fraction


def calculate_darkness_score(
    sun_altitude_degrees: float,
) -> float:
    """Score darkness using the Sun's altitude."""

    if not -90.0 <= sun_altitude_degrees <= 90.0:
        raise ValueError("Sun altitude must be between -90 and 90 degrees.")

    if sun_altitude_degrees >= 0.0:
        return 0.0

    if sun_altitude_degrees <= -18.0:
        return DARKNESS_MAX_SCORE

    darkness_fraction = -sun_altitude_degrees / 18.0

    return DARKNESS_MAX_SCORE * darkness_fraction


def calculate_approximate_airmass(
    altitude_degrees: float,
) -> float | None:
    """Estimate simple geometric airmass from altitude."""

    if altitude_degrees < 5.0:
        return None

    altitude_sine = sin(radians(altitude_degrees))

    if altitude_sine <= 0.0:
        return None

    airmass = 1.0 / altitude_sine

    if not isfinite(airmass):
        return None

    return airmass


def classify_planner_rating(
    total_score: float,
) -> PlannerRating:
    """Convert a numeric score into a quality rating."""

    if not 0.0 <= total_score <= MAXIMUM_TOTAL_SCORE:
        raise ValueError("Planner score must be between 0 and 100.")

    if total_score >= 80.0:
        return "excellent"

    if total_score >= 65.0:
        return "very_good"

    if total_score >= 50.0:
        return "good"

    if total_score >= 35.0:
        return "fair"

    return "poor"


def create_plan_entry(
    *,
    object_key: str,
    category: PlannerCategory,
    altitude_degrees: float,
    azimuth_degrees: float,
    cardinal_direction: str,
    airmass: float | None,
    moon_separation_degrees: float,
    sun_altitude_degrees: float,
    status: VisibilityStatus,
    minimum_altitude_degrees: float,
    minimum_moon_separation_degrees: float,
    minimum_score: float,
) -> ObservationPlanEntry:
    """Calculate score components for one target."""

    target_is_moon = object_key == "moon"

    altitude_score = calculate_altitude_score(altitude_degrees)

    airmass_score = calculate_airmass_score(airmass)

    moon_separation_score = calculate_moon_separation_score(
        separation_degrees=moon_separation_degrees,
        minimum_separation_degrees=(minimum_moon_separation_degrees),
        target_is_moon=target_is_moon,
    )

    darkness_score = calculate_darkness_score(sun_altitude_degrees)

    total_score = round(
        altitude_score + airmass_score + moon_separation_score + darkness_score,
        1,
    )

    moon_condition_passes = (
        target_is_moon or moon_separation_degrees >= minimum_moon_separation_degrees
    )

    recommended = (
        altitude_degrees >= minimum_altitude_degrees
        and status == "observable"
        and moon_condition_passes
        and total_score >= minimum_score
    )

    return ObservationPlanEntry(
        object_key=object_key,
        category=category,
        altitude_degrees=altitude_degrees,
        azimuth_degrees=azimuth_degrees,
        cardinal_direction=cardinal_direction,
        airmass=airmass,
        moon_separation_degrees=(moon_separation_degrees),
        status=status,
        altitude_score=round(altitude_score, 1),
        airmass_score=round(airmass_score, 1),
        moon_separation_score=round(
            moon_separation_score,
            1,
        ),
        darkness_score=round(darkness_score, 1),
        total_score=total_score,
        rating=classify_planner_rating(total_score),
        recommended=recommended,
    )


def calculate_observation_plan(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    minimum_altitude_degrees: float = 20.0,
    minimum_moon_separation_degrees: float = 30.0,
    minimum_score: float = 40.0,
    include_catalog_targets: bool = True,
    include_solar_system_targets: bool = True,
) -> ObservationPlanResult:
    """Rank catalogue and Solar System targets."""

    if not 0.0 <= minimum_score <= 100.0:
        raise ValueError("Minimum score must be between 0 and 100.")

    if not 0.0 <= minimum_moon_separation_degrees <= 180.0:
        raise ValueError("Minimum Moon separation must be between 0 and 180 degrees.")

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

    horizontal_frame = AltAz(
        obstime=observation_time,
        location=location,
        pressure=0.0 * u.hPa,
    )

    with solar_system_ephemeris.set("builtin"):
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

    sun_horizontal = sun_position.transform_to(horizontal_frame)

    moon_horizontal = moon_position.transform_to(horizontal_frame)

    sun_altitude_degrees = float(sun_horizontal.alt.to_value(u.deg))

    entries: list[ObservationPlanEntry] = []

    if include_catalog_targets:
        for object_key, preset in CELESTIAL_PRESETS.items():
            horizontal_result = calculate_horizontal_coordinates(
                right_ascension=(preset.right_ascension),
                declination=preset.declination,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            target_horizontal = SkyCoord(
                az=(horizontal_result.azimuth_degrees * u.deg),
                alt=(horizontal_result.altitude_degrees * u.deg),
                frame=horizontal_frame,
            )

            moon_separation_degrees = float(
                target_horizontal.separation(moon_horizontal).to_value(u.deg)
            )

            entries.append(
                create_plan_entry(
                    object_key=object_key,
                    category="catalog",
                    altitude_degrees=(horizontal_result.altitude_degrees),
                    azimuth_degrees=(horizontal_result.azimuth_degrees),
                    cardinal_direction=(horizontal_result.cardinal_direction),
                    airmass=horizontal_result.airmass,
                    moon_separation_degrees=(moon_separation_degrees),
                    sun_altitude_degrees=(sun_altitude_degrees),
                    status=horizontal_result.status,
                    minimum_altitude_degrees=(minimum_altitude_degrees),
                    minimum_moon_separation_degrees=(minimum_moon_separation_degrees),
                    minimum_score=minimum_score,
                )
            )

    if include_solar_system_targets:
        for body_key in PLANNER_SOLAR_SYSTEM_BODIES:
            solar_result = calculate_solar_system_body(
                body=body_key,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            entries.append(
                create_plan_entry(
                    object_key=body_key,
                    category="solar_system",
                    altitude_degrees=(solar_result.altitude_degrees),
                    azimuth_degrees=(solar_result.azimuth_degrees),
                    cardinal_direction=(solar_result.cardinal_direction),
                    airmass=calculate_approximate_airmass(solar_result.altitude_degrees),
                    moon_separation_degrees=(solar_result.moon_separation_degrees),
                    sun_altitude_degrees=(sun_altitude_degrees),
                    status=solar_result.status,
                    minimum_altitude_degrees=(minimum_altitude_degrees),
                    minimum_moon_separation_degrees=(minimum_moon_separation_degrees),
                    minimum_score=minimum_score,
                )
            )

    ranked_entries = tuple(
        sorted(
            entries,
            key=lambda entry: (
                entry.total_score,
                entry.altitude_degrees,
            ),
            reverse=True,
        )
    )

    recommended_count = sum(entry.recommended for entry in ranked_entries)

    return ObservationPlanResult(
        entries=ranked_entries,
        sun_altitude_degrees=(sun_altitude_degrees),
        recommended_count=recommended_count,
        total_target_count=len(ranked_entries),
        utc_datetime_iso=utc_datetime.isoformat(timespec="seconds"),
    )
