"""Generate ranked exoplanet transit observing schedules."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from astroscope.transit_ranking import (
    DEFAULT_RANKING_WEIGHTS,
    RankedTransit,
    RankingWeights,
    TransitObservationCandidate,
    rank_transit_candidates,
)
from astroscope.transit_scheduler import (
    TransitEphemeris,
    predict_transits,
)
from astroscope.transit_visibility import (
    ASTRONOMICAL_TWILIGHT_DEGREES,
    DEFAULT_MINIMUM_ALTITUDE_DEGREES,
    MAXIMUM_VISIBILITY_SAMPLES,
    ObserverSite,
    TransitTarget,
    analyze_transit_visibility,
)

DEFAULT_MAXIMUM_EVENTS_PER_TARGET: Final[int] = 1_000
DEFAULT_MAXIMUM_TOTAL_EVENTS: Final[int] = 5_000


class TransitScheduleError(ValueError):
    """Raised when transit-schedule inputs are invalid."""


@dataclass(frozen=True, slots=True)
class TransitScheduleTarget:
    """One planet, host-star position, and optional ranking metadata."""

    ephemeris: TransitEphemeris
    target: TransitTarget
    transit_depth_ppm: float | None = None
    host_magnitude: float | None = None

    def __post_init__(self) -> None:
        """Validate optional target metadata."""

        if self.transit_depth_ppm is not None:
            _require_non_negative_finite(
                self.transit_depth_ppm,
                "Transit depth",
            )

        if self.host_magnitude is not None:
            _require_finite(
                self.host_magnitude,
                "Host magnitude",
            )


@dataclass(frozen=True, slots=True)
class TransitScheduleRequest:
    """Time range and visibility settings for schedule generation."""

    start_jd: float
    end_jd: float
    baseline_before_hours: float = 1.0
    baseline_after_hours: float = 1.0
    uncertainty_sigma_multiplier: float = 1.0
    visibility_sample_count: int = 25
    minimum_altitude_degrees: float = DEFAULT_MINIMUM_ALTITUDE_DEGREES
    darkness_sun_altitude_degrees: float = ASTRONOMICAL_TWILIGHT_DEGREES
    maximum_events_per_target: int = DEFAULT_MAXIMUM_EVENTS_PER_TARGET
    maximum_total_events: int = DEFAULT_MAXIMUM_TOTAL_EVENTS

    def __post_init__(self) -> None:
        """Validate schedule-generation settings."""

        _require_finite(
            self.start_jd,
            "Start Julian date",
        )
        _require_finite(
            self.end_jd,
            "End Julian date",
        )

        if self.end_jd < self.start_jd:
            raise TransitScheduleError(
                "End Julian date must not be earlier than start Julian date."
            )

        _require_non_negative_finite(
            self.baseline_before_hours,
            "Pre-transit baseline",
        )
        _require_non_negative_finite(
            self.baseline_after_hours,
            "Post-transit baseline",
        )
        _require_non_negative_finite(
            self.uncertainty_sigma_multiplier,
            "Uncertainty multiplier",
        )

        _require_bounded_finite(
            self.minimum_altitude_degrees,
            "Minimum target altitude",
            minimum=-90.0,
            maximum=90.0,
        )
        _require_bounded_finite(
            self.darkness_sun_altitude_degrees,
            "Darkness Sun altitude",
            minimum=-90.0,
            maximum=90.0,
        )

        _require_integer_in_range(
            self.visibility_sample_count,
            "Visibility sample count",
            minimum=3,
            maximum=MAXIMUM_VISIBILITY_SAMPLES,
        )
        _require_positive_integer(
            self.maximum_events_per_target,
            "Maximum events per target",
        )
        _require_positive_integer(
            self.maximum_total_events,
            "Maximum total events",
        )


@dataclass(frozen=True, slots=True)
class TransitScheduleResult:
    """Complete ranked observing schedule."""

    site: ObserverSite
    request: TransitScheduleRequest
    target_count: int
    predicted_event_count: int
    ranked_transits: tuple[RankedTransit, ...]
    targets_without_events: tuple[str, ...]

    @property
    def best_transit(self) -> RankedTransit | None:
        """Return the highest-ranked transit, when one exists."""

        if not self.ranked_transits:
            return None

        return self.ranked_transits[0]

    @property
    def fully_visible_count(self) -> int:
        """Return the number of fully visible observing windows."""

        return sum(
            ranked.candidate.visibility.full_observation_window_visible
            for ranked in self.ranked_transits
        )

    @property
    def observable_transit_count(self) -> int:
        """Return the number of events with some observable samples."""

        return sum(
            ranked.candidate.visibility.observable_sample_fraction > 0.0
            for ranked in self.ranked_transits
        )


def _require_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite number."""

    if not math.isfinite(value):
        raise TransitScheduleError(f"{label} must be finite.")


def _require_non_negative_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite number greater than or equal to zero."""

    _require_finite(value, label)

    if value < 0.0:
        raise TransitScheduleError(f"{label} must not be negative.")


def _require_bounded_finite(
    value: float,
    label: str,
    *,
    minimum: float,
    maximum: float,
) -> None:
    """Require a finite value inside an inclusive interval."""

    _require_finite(value, label)

    if not minimum <= value <= maximum:
        raise TransitScheduleError(f"{label} must be between {minimum} and {maximum}.")


def _require_positive_integer(
    value: int,
    label: str,
) -> None:
    """Require an integer greater than zero."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TransitScheduleError(f"{label} must be an integer.")

    if value <= 0:
        raise TransitScheduleError(f"{label} must be greater than zero.")


def _require_integer_in_range(
    value: int,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> None:
    """Require an integer inside an inclusive interval."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TransitScheduleError(f"{label} must be an integer.")

    if not minimum <= value <= maximum:
        raise TransitScheduleError(f"{label} must be between {minimum} and {maximum}.")


def _validate_unique_planets(
    targets: tuple[TransitScheduleTarget, ...],
) -> None:
    """Reject duplicate planet entries."""

    seen_planets: set[str] = set()

    for schedule_target in targets:
        normalized_name = schedule_target.ephemeris.planet_name.strip().casefold()

        if normalized_name in seen_planets:
            raise TransitScheduleError(
                "Schedule targets must not contain duplicate planet names: "
                f"{schedule_target.ephemeris.planet_name}."
            )

        seen_planets.add(normalized_name)


def generate_transit_schedule(
    targets: tuple[TransitScheduleTarget, ...],
    site: ObserverSite,
    request: TransitScheduleRequest,
    *,
    weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> TransitScheduleResult:
    """Predict, analyze, score, and rank transit events."""

    _validate_unique_planets(targets)

    candidates: list[TransitObservationCandidate] = []
    targets_without_events: list[str] = []
    predicted_event_count = 0

    for schedule_target in targets:
        events = predict_transits(
            schedule_target.ephemeris,
            request.start_jd,
            request.end_jd,
            baseline_before_hours=request.baseline_before_hours,
            baseline_after_hours=request.baseline_after_hours,
            uncertainty_sigma_multiplier=(request.uncertainty_sigma_multiplier),
            maximum_events=request.maximum_events_per_target,
        )

        if not events:
            targets_without_events.append(schedule_target.ephemeris.planet_name)
            continue

        predicted_event_count += len(events)

        if predicted_event_count > request.maximum_total_events:
            raise TransitScheduleError(
                "Predicted event count exceeds the schedule limit of "
                f"{request.maximum_total_events}."
            )

        for event in events:
            visibility = analyze_transit_visibility(
                event,
                site,
                schedule_target.target,
                sample_count=request.visibility_sample_count,
                minimum_altitude_degrees=(request.minimum_altitude_degrees),
                darkness_sun_altitude_degrees=(request.darkness_sun_altitude_degrees),
            )

            candidates.append(
                TransitObservationCandidate(
                    event=event,
                    visibility=visibility,
                    transit_depth_ppm=(schedule_target.transit_depth_ppm),
                    host_magnitude=(schedule_target.host_magnitude),
                )
            )

    ranked_transits = rank_transit_candidates(
        tuple(candidates),
        weights=weights,
    )

    return TransitScheduleResult(
        site=site,
        request=request,
        target_count=len(targets),
        predicted_event_count=predicted_event_count,
        ranked_transits=ranked_transits,
        targets_without_events=tuple(targets_without_events),
    )
