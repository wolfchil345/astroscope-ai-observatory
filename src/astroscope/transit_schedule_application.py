"""UI-independent request construction for transit schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from astropy.time import Time

from astroscope.transit_schedule import (
    TransitScheduleRequest,
    TransitScheduleTarget,
)
from astroscope.transit_scheduler import TransitEphemeris
from astroscope.transit_visibility import TransitTarget


@dataclass(frozen=True, slots=True)
class TransitDashboardTargetInput:
    """User-entered ephemeris and host-star information."""

    planet_name: str
    host_star_name: str
    right_ascension_degrees: float
    declination_degrees: float
    orbital_period_days: float
    reference_mid_transit_jd: float
    transit_duration_hours: float
    period_uncertainty_days: float
    reference_epoch_uncertainty_days: float
    transit_depth_ppm: float | None
    host_magnitude: float | None


def utc_datetime_to_julian_date(
    value: datetime,
) -> float:
    """Convert a timezone-aware datetime to a UTC Julian date."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must include timezone information.")

    utc_value = value.astimezone(UTC)

    return float(
        Time(
            utc_value,
            scale="utc",
        ).jd
    )


def build_schedule_request(
    start_date: date,
    end_date: date,
    *,
    baseline_before_hours: float,
    baseline_after_hours: float,
    uncertainty_sigma_multiplier: float,
    visibility_sample_count: int,
    minimum_altitude_degrees: float,
    darkness_sun_altitude_degrees: float,
) -> TransitScheduleRequest:
    """Build a complete UTC schedule request from calendar dates."""

    if end_date < start_date:
        raise ValueError("End date must not be earlier than start date.")

    start_datetime = datetime.combine(
        start_date,
        time.min,
        tzinfo=UTC,
    )
    end_datetime = datetime.combine(
        end_date,
        time.max,
        tzinfo=UTC,
    )

    return TransitScheduleRequest(
        start_jd=utc_datetime_to_julian_date(start_datetime),
        end_jd=utc_datetime_to_julian_date(end_datetime),
        baseline_before_hours=baseline_before_hours,
        baseline_after_hours=baseline_after_hours,
        uncertainty_sigma_multiplier=(uncertainty_sigma_multiplier),
        visibility_sample_count=visibility_sample_count,
        minimum_altitude_degrees=(minimum_altitude_degrees),
        darkness_sun_altitude_degrees=(darkness_sun_altitude_degrees),
    )


def build_schedule_target(
    target_input: TransitDashboardTargetInput,
) -> TransitScheduleTarget:
    """Convert dashboard target input into schedule-domain objects."""

    ephemeris = TransitEphemeris(
        planet_name=target_input.planet_name,
        orbital_period_days=(target_input.orbital_period_days),
        reference_mid_transit_jd=(target_input.reference_mid_transit_jd),
        transit_duration_hours=(target_input.transit_duration_hours),
        period_uncertainty_days=(target_input.period_uncertainty_days),
        reference_epoch_uncertainty_days=(target_input.reference_epoch_uncertainty_days),
    )

    target = TransitTarget(
        name=target_input.host_star_name,
        right_ascension_degrees=(target_input.right_ascension_degrees),
        declination_degrees=(target_input.declination_degrees),
    )

    return TransitScheduleTarget(
        ephemeris=ephemeris,
        target=target,
        transit_depth_ppm=(target_input.transit_depth_ppm),
        host_magnitude=target_input.host_magnitude,
    )
