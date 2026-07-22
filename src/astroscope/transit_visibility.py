"""Observer geometry and visibility analysis for exoplanet transits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from astropy import units as u
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    SkyCoord,
    get_body,
)
from astropy.time import Time

from astroscope.transit_scheduler import TransitEvent

ASTRONOMICAL_TWILIGHT_DEGREES: Final[float] = -18.0
DEFAULT_MINIMUM_ALTITUDE_DEGREES: Final[float] = 20.0
MAXIMUM_VISIBILITY_SAMPLES: Final[int] = 10_001


class TransitVisibilityError(ValueError):
    """Raised when observer-visibility inputs are invalid."""


@dataclass(frozen=True, slots=True)
class ObserverSite:
    """Geographic location of an observer."""

    name: str
    latitude_degrees: float
    longitude_degrees: float
    elevation_meters: float = 0.0

    def __post_init__(self) -> None:
        """Validate the observing site."""

        if not self.name.strip():
            raise TransitVisibilityError("Observer-site name must not be empty.")

        _require_bounded_finite(
            self.latitude_degrees,
            "Latitude",
            minimum=-90.0,
            maximum=90.0,
        )
        _require_bounded_finite(
            self.longitude_degrees,
            "Longitude",
            minimum=-180.0,
            maximum=180.0,
        )
        _require_finite(
            self.elevation_meters,
            "Elevation",
        )

    def earth_location(self) -> EarthLocation:
        """Return this site as an Astropy EarthLocation."""

        return EarthLocation.from_geodetic(
            lon=self.longitude_degrees * u.deg,
            lat=self.latitude_degrees * u.deg,
            height=self.elevation_meters * u.m,
        )


@dataclass(frozen=True, slots=True)
class TransitTarget:
    """Equatorial coordinates of a transit host star."""

    name: str
    right_ascension_degrees: float
    declination_degrees: float

    def __post_init__(self) -> None:
        """Validate the target coordinates."""

        if not self.name.strip():
            raise TransitVisibilityError("Transit-target name must not be empty.")

        _require_finite(
            self.right_ascension_degrees,
            "Right ascension",
        )

        if not 0.0 <= self.right_ascension_degrees < 360.0:
            raise TransitVisibilityError(
                "Right ascension must be at least 0 and less than 360 degrees."
            )

        _require_bounded_finite(
            self.declination_degrees,
            "Declination",
            minimum=-90.0,
            maximum=90.0,
        )

    def sky_coordinate(self) -> SkyCoord:
        """Return the target as an ICRS SkyCoord."""

        return SkyCoord(
            ra=self.right_ascension_degrees * u.deg,
            dec=self.declination_degrees * u.deg,
            frame="icrs",
        )


@dataclass(frozen=True, slots=True)
class TransitVisibilitySample:
    """Visibility conditions at one instant."""

    julian_date: float
    target_altitude_degrees: float
    target_azimuth_degrees: float
    airmass: float | None
    sun_altitude_degrees: float
    moon_altitude_degrees: float
    moon_separation_degrees: float
    moon_illumination_fraction: float
    target_above_minimum_altitude: bool
    is_astronomical_dark: bool

    @property
    def is_observable(self) -> bool:
        """Return whether altitude and darkness conditions both pass."""

        return self.target_above_minimum_altitude and self.is_astronomical_dark


@dataclass(frozen=True, slots=True)
class TransitVisibilitySummary:
    """Visibility summary across an observing window."""

    planet_name: str
    target_name: str
    site_name: str
    samples: tuple[TransitVisibilitySample, ...]
    midpoint_sample: TransitVisibilitySample
    minimum_target_altitude_degrees: float
    maximum_target_altitude_degrees: float
    maximum_airmass: float | None
    minimum_moon_separation_degrees: float
    altitude_sample_fraction: float
    dark_sample_fraction: float
    observable_sample_fraction: float
    full_observation_window_visible: bool


def _require_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite numerical value."""

    if not math.isfinite(value):
        raise TransitVisibilityError(f"{label} must be finite.")


def _require_bounded_finite(
    value: float,
    label: str,
    *,
    minimum: float,
    maximum: float,
) -> None:
    """Require a finite number inside an inclusive interval."""

    _require_finite(value, label)

    if not minimum <= value <= maximum:
        raise TransitVisibilityError(f"{label} must be between {minimum} and {maximum}.")


def _validate_visibility_limits(
    minimum_altitude_degrees: float,
    darkness_sun_altitude_degrees: float,
) -> None:
    """Validate altitude and darkness thresholds."""

    _require_bounded_finite(
        minimum_altitude_degrees,
        "Minimum target altitude",
        minimum=-90.0,
        maximum=90.0,
    )
    _require_bounded_finite(
        darkness_sun_altitude_degrees,
        "Darkness Sun altitude",
        minimum=-90.0,
        maximum=90.0,
    )


def calculate_airmass_from_altitude_degrees(
    altitude_degrees: float,
) -> float | None:
    """Estimate geometric airmass using the secant approximation.

    Values at or below the geometric horizon return None.
    """

    _require_bounded_finite(
        altitude_degrees,
        "Altitude",
        minimum=-90.0,
        maximum=90.0,
    )

    if altitude_degrees <= 0.0:
        return None

    return 1.0 / math.sin(math.radians(altitude_degrees))


def calculate_moon_illumination_fraction(
    elongation_degrees: float,
) -> float:
    """Estimate illuminated lunar fraction from Sun-Moon elongation."""

    _require_bounded_finite(
        elongation_degrees,
        "Sun-Moon elongation",
        minimum=0.0,
        maximum=180.0,
    )

    elongation_radians = math.radians(elongation_degrees)

    return (1.0 - math.cos(elongation_radians)) / 2.0


def sample_transit_visibility(
    site: ObserverSite,
    target: TransitTarget,
    julian_date: float,
    *,
    minimum_altitude_degrees: float = (DEFAULT_MINIMUM_ALTITUDE_DEGREES),
    darkness_sun_altitude_degrees: float = (ASTRONOMICAL_TWILIGHT_DEGREES),
) -> TransitVisibilitySample:
    """Calculate observing conditions at one Julian date."""

    _require_finite(
        julian_date,
        "Julian date",
    )
    _validate_visibility_limits(
        minimum_altitude_degrees,
        darkness_sun_altitude_degrees,
    )

    location = site.earth_location()
    observation_time = Time(
        julian_date,
        format="jd",
        scale="utc",
    )

    horizontal_frame = AltAz(
        obstime=observation_time,
        location=location,
        pressure=0.0 * u.hPa,
    )

    target_coordinate = target.sky_coordinate()
    target_horizontal = target_coordinate.transform_to(horizontal_frame)

    sun_coordinate = get_body(
        "sun",
        observation_time,
        location=location,
    )
    moon_coordinate = get_body(
        "moon",
        observation_time,
        location=location,
    )

    sun_horizontal = sun_coordinate.transform_to(horizontal_frame)
    moon_horizontal = moon_coordinate.transform_to(horizontal_frame)

    target_in_moon_frame = target_coordinate.transform_to(moon_coordinate.frame)

    target_altitude_degrees = float(target_horizontal.alt.deg)
    target_azimuth_degrees = float(target_horizontal.az.deg)
    sun_altitude_degrees = float(sun_horizontal.alt.deg)
    moon_altitude_degrees = float(moon_horizontal.alt.deg)

    moon_separation_degrees = float(target_in_moon_frame.separation(moon_coordinate).deg)

    sun_moon_elongation_degrees = float(sun_coordinate.separation(moon_coordinate).deg)

    moon_illumination_fraction = calculate_moon_illumination_fraction(sun_moon_elongation_degrees)

    return TransitVisibilitySample(
        julian_date=julian_date,
        target_altitude_degrees=(target_altitude_degrees),
        target_azimuth_degrees=(target_azimuth_degrees),
        airmass=(calculate_airmass_from_altitude_degrees(target_altitude_degrees)),
        sun_altitude_degrees=sun_altitude_degrees,
        moon_altitude_degrees=moon_altitude_degrees,
        moon_separation_degrees=(moon_separation_degrees),
        moon_illumination_fraction=(moon_illumination_fraction),
        target_above_minimum_altitude=(target_altitude_degrees >= minimum_altitude_degrees),
        is_astronomical_dark=(sun_altitude_degrees <= darkness_sun_altitude_degrees),
    )


def _validate_transit_event(
    event: TransitEvent,
) -> None:
    """Validate the event timing used by the visibility engine."""

    timing_values = (
        ("Ingress Julian date", event.ingress_jd),
        ("Mid-transit Julian date", event.mid_transit_jd),
        ("Egress Julian date", event.egress_jd),
        (
            "Observation-start Julian date",
            event.observation_start_jd,
        ),
        (
            "Observation-end Julian date",
            event.observation_end_jd,
        ),
    )

    for label, value in timing_values:
        _require_finite(value, label)

    if not (
        event.observation_start_jd
        <= event.ingress_jd
        <= event.mid_transit_jd
        <= event.egress_jd
        <= event.observation_end_jd
    ):
        raise TransitVisibilityError("Transit-event times must be in chronological order.")


def analyze_transit_visibility(
    event: TransitEvent,
    site: ObserverSite,
    target: TransitTarget,
    *,
    sample_count: int = 25,
    minimum_altitude_degrees: float = (DEFAULT_MINIMUM_ALTITUDE_DEGREES),
    darkness_sun_altitude_degrees: float = (ASTRONOMICAL_TWILIGHT_DEGREES),
) -> TransitVisibilitySummary:
    """Analyze visibility across a complete observing window."""

    _validate_transit_event(event)
    _validate_visibility_limits(
        minimum_altitude_degrees,
        darkness_sun_altitude_degrees,
    )

    if isinstance(sample_count, bool) or not isinstance(
        sample_count,
        int,
    ):
        raise TransitVisibilityError("Sample count must be an integer.")

    if sample_count < 3:
        raise TransitVisibilityError("Sample count must be at least 3.")

    if sample_count > MAXIMUM_VISIBILITY_SAMPLES:
        raise TransitVisibilityError(
            f"Sample count exceeds the visibility limit of {MAXIMUM_VISIBILITY_SAMPLES}."
        )

    sample_julian_dates = np.linspace(
        event.observation_start_jd,
        event.observation_end_jd,
        sample_count,
        dtype=float,
    )

    samples = tuple(
        sample_transit_visibility(
            site,
            target,
            float(julian_date),
            minimum_altitude_degrees=(minimum_altitude_degrees),
            darkness_sun_altitude_degrees=(darkness_sun_altitude_degrees),
        )
        for julian_date in sample_julian_dates
    )

    midpoint_sample = min(
        samples,
        key=lambda sample: abs(sample.julian_date - event.mid_transit_jd),
    )

    target_altitudes = tuple(sample.target_altitude_degrees for sample in samples)

    available_airmasses = tuple(sample.airmass for sample in samples if sample.airmass is not None)

    sample_total = len(samples)

    altitude_sample_fraction = (
        sum(sample.target_above_minimum_altitude for sample in samples) / sample_total
    )

    dark_sample_fraction = sum(sample.is_astronomical_dark for sample in samples) / sample_total

    observable_sample_fraction = sum(sample.is_observable for sample in samples) / sample_total

    return TransitVisibilitySummary(
        planet_name=event.planet_name,
        target_name=target.name,
        site_name=site.name,
        samples=samples,
        midpoint_sample=midpoint_sample,
        minimum_target_altitude_degrees=min(target_altitudes),
        maximum_target_altitude_degrees=max(target_altitudes),
        maximum_airmass=(max(available_airmasses) if available_airmasses else None),
        minimum_moon_separation_degrees=min(sample.moon_separation_degrees for sample in samples),
        altitude_sample_fraction=(altitude_sample_fraction),
        dark_sample_fraction=dark_sample_fraction,
        observable_sample_fraction=(observable_sample_fraction),
        full_observation_window_visible=all(sample.is_observable for sample in samples),
    )
