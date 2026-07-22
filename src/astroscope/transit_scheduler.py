"""Pure calculations for predicting exoplanet transit events."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

HOURS_PER_DAY: Final[float] = 24.0
_TRANSIT_NUMBER_EPSILON: Final[float] = 1e-12


class TransitSchedulerError(ValueError):
    """Raised when transit scheduling inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TransitEphemeris:
    """Orbital timing information required to predict transits.

    Attributes:
        planet_name:
            Display name of the planet.
        orbital_period_days:
            Time between consecutive transits in days.
        reference_mid_transit_jd:
            Julian date of the reference mid-transit.
        transit_duration_hours:
            Total first-to-fourth-contact duration in hours.
        period_uncertainty_days:
            Optional one-sigma uncertainty of the orbital period.
        reference_epoch_uncertainty_days:
            Optional one-sigma uncertainty of the reference transit epoch.
    """

    planet_name: str
    orbital_period_days: float
    reference_mid_transit_jd: float
    transit_duration_hours: float
    period_uncertainty_days: float | None = None
    reference_epoch_uncertainty_days: float | None = None

    def __post_init__(self) -> None:
        """Validate the ephemeris."""

        if not self.planet_name.strip():
            raise TransitSchedulerError("Planet name must not be empty.")

        _require_positive_finite(
            self.orbital_period_days,
            "Orbital period",
        )
        _require_finite(
            self.reference_mid_transit_jd,
            "Reference mid-transit Julian date",
        )
        _require_positive_finite(
            self.transit_duration_hours,
            "Transit duration",
        )
        _require_optional_non_negative_finite(
            self.period_uncertainty_days,
            "Orbital-period uncertainty",
        )
        _require_optional_non_negative_finite(
            self.reference_epoch_uncertainty_days,
            "Reference-epoch uncertainty",
        )


@dataclass(frozen=True, slots=True)
class TransitEvent:
    """One predicted exoplanet transit."""

    planet_name: str
    transit_number: int
    mid_transit_jd: float
    ingress_jd: float
    egress_jd: float
    observation_start_jd: float
    observation_end_jd: float
    timing_uncertainty_days: float

    @property
    def timing_uncertainty_hours(self) -> float:
        """Return the one-sigma timing uncertainty in hours."""

        return self.timing_uncertainty_days * HOURS_PER_DAY

    @property
    def observation_window_hours(self) -> float:
        """Return the complete requested observing-window duration."""

        return (self.observation_end_jd - self.observation_start_jd) * HOURS_PER_DAY


def _require_finite(
    value: float,
    label: str,
) -> None:
    """Require one finite numerical value."""

    if not math.isfinite(value):
        raise TransitSchedulerError(f"{label} must be finite.")


def _require_positive_finite(
    value: float,
    label: str,
) -> None:
    """Require one finite value greater than zero."""

    _require_finite(value, label)

    if value <= 0.0:
        raise TransitSchedulerError(f"{label} must be greater than zero.")


def _require_non_negative_finite(
    value: float,
    label: str,
) -> None:
    """Require one finite value greater than or equal to zero."""

    _require_finite(value, label)

    if value < 0.0:
        raise TransitSchedulerError(f"{label} must not be negative.")


def _require_optional_non_negative_finite(
    value: float | None,
    label: str,
) -> None:
    """Validate an optional non-negative uncertainty."""

    if value is None:
        return

    _require_non_negative_finite(
        value,
        label,
    )


def calculate_transit_number_on_or_after(
    ephemeris: TransitEphemeris,
    target_jd: float,
) -> int:
    """Return the first transit number whose midpoint is on or after a date."""

    _require_finite(
        target_jd,
        "Target Julian date",
    )

    raw_number = (target_jd - ephemeris.reference_mid_transit_jd) / ephemeris.orbital_period_days

    return math.ceil(raw_number - _TRANSIT_NUMBER_EPSILON)


def calculate_transit_number_on_or_before(
    ephemeris: TransitEphemeris,
    target_jd: float,
) -> int:
    """Return the final transit number whose midpoint is on or before a date."""

    _require_finite(
        target_jd,
        "Target Julian date",
    )

    raw_number = (target_jd - ephemeris.reference_mid_transit_jd) / ephemeris.orbital_period_days

    return math.floor(raw_number + _TRANSIT_NUMBER_EPSILON)


def calculate_mid_transit_jd(
    ephemeris: TransitEphemeris,
    transit_number: int,
) -> float:
    """Calculate the midpoint Julian date for one transit number."""

    if isinstance(transit_number, bool) or not isinstance(
        transit_number,
        int,
    ):
        raise TransitSchedulerError("Transit number must be an integer.")

    return ephemeris.reference_mid_transit_jd + transit_number * ephemeris.orbital_period_days


def calculate_timing_uncertainty_days(
    ephemeris: TransitEphemeris,
    transit_number: int,
) -> float:
    """Propagate epoch and orbital-period uncertainty.

    The one-sigma uncertainty is estimated as:

        sigma_T(n) = sqrt(sigma_epoch^2 + (n * sigma_period)^2)
    """

    if isinstance(transit_number, bool) or not isinstance(
        transit_number,
        int,
    ):
        raise TransitSchedulerError("Transit number must be an integer.")

    epoch_uncertainty = ephemeris.reference_epoch_uncertainty_days or 0.0
    period_uncertainty = ephemeris.period_uncertainty_days or 0.0

    return math.hypot(
        epoch_uncertainty,
        transit_number * period_uncertainty,
    )


def build_transit_event(
    ephemeris: TransitEphemeris,
    transit_number: int,
    *,
    baseline_before_hours: float = 1.0,
    baseline_after_hours: float = 1.0,
    uncertainty_sigma_multiplier: float = 1.0,
) -> TransitEvent:
    """Build one complete transit and observing window."""

    _require_non_negative_finite(
        baseline_before_hours,
        "Pre-transit baseline",
    )
    _require_non_negative_finite(
        baseline_after_hours,
        "Post-transit baseline",
    )
    _require_non_negative_finite(
        uncertainty_sigma_multiplier,
        "Uncertainty multiplier",
    )

    mid_transit_jd = calculate_mid_transit_jd(
        ephemeris,
        transit_number,
    )

    half_duration_days = ephemeris.transit_duration_hours / HOURS_PER_DAY / 2.0

    timing_uncertainty_days = calculate_timing_uncertainty_days(
        ephemeris,
        transit_number,
    )

    uncertainty_margin_days = timing_uncertainty_days * uncertainty_sigma_multiplier

    ingress_jd = mid_transit_jd - half_duration_days
    egress_jd = mid_transit_jd + half_duration_days

    observation_start_jd = (
        ingress_jd - baseline_before_hours / HOURS_PER_DAY - uncertainty_margin_days
    )

    observation_end_jd = egress_jd + baseline_after_hours / HOURS_PER_DAY + uncertainty_margin_days

    return TransitEvent(
        planet_name=ephemeris.planet_name,
        transit_number=transit_number,
        mid_transit_jd=mid_transit_jd,
        ingress_jd=ingress_jd,
        egress_jd=egress_jd,
        observation_start_jd=observation_start_jd,
        observation_end_jd=observation_end_jd,
        timing_uncertainty_days=timing_uncertainty_days,
    )


def predict_transits(
    ephemeris: TransitEphemeris,
    start_jd: float,
    end_jd: float,
    *,
    baseline_before_hours: float = 1.0,
    baseline_after_hours: float = 1.0,
    uncertainty_sigma_multiplier: float = 1.0,
    maximum_events: int = 10_000,
) -> tuple[TransitEvent, ...]:
    """Predict transits whose midpoints fall inside an inclusive date range."""

    _require_finite(
        start_jd,
        "Start Julian date",
    )
    _require_finite(
        end_jd,
        "End Julian date",
    )

    if end_jd < start_jd:
        raise TransitSchedulerError("End Julian date must not be earlier than start Julian date.")

    if isinstance(maximum_events, bool) or not isinstance(
        maximum_events,
        int,
    ):
        raise TransitSchedulerError("Maximum events must be an integer.")

    if maximum_events <= 0:
        raise TransitSchedulerError("Maximum events must be greater than zero.")

    first_number = calculate_transit_number_on_or_after(
        ephemeris,
        start_jd,
    )
    final_number = calculate_transit_number_on_or_before(
        ephemeris,
        end_jd,
    )

    if final_number < first_number:
        return ()

    event_count = final_number - first_number + 1

    if event_count > maximum_events:
        raise TransitSchedulerError(
            "Requested date range contains "
            f"{event_count} transits, exceeding the "
            f"limit of {maximum_events}."
        )

    return tuple(
        build_transit_event(
            ephemeris,
            transit_number,
            baseline_before_hours=(baseline_before_hours),
            baseline_after_hours=(baseline_after_hours),
            uncertainty_sigma_multiplier=(uncertainty_sigma_multiplier),
        )
        for transit_number in range(
            first_number,
            final_number + 1,
        )
    )
