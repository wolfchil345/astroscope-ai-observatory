"""Transparent scoring and ranking for exoplanet transit observations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import TransitVisibilitySummary


class TransitRankingError(ValueError):
    """Raised when transit-ranking inputs are invalid."""


@dataclass(frozen=True, slots=True)
class RankingWeights:
    """Relative importance of each observation-quality component."""

    observable_fraction: float = 0.30
    midpoint_altitude: float = 0.15
    darkness_fraction: float = 0.15
    moon_separation: float = 0.10
    transit_depth: float = 0.10
    timing_confidence: float = 0.10
    host_brightness: float = 0.05
    full_window_visibility: float = 0.05

    def __post_init__(self) -> None:
        """Validate all ranking weights."""

        for label, value in self.as_items():
            _require_non_negative_finite(
                value,
                f"{label} weight",
            )

        if self.total <= 0.0:
            raise TransitRankingError("At least one ranking weight must be greater than zero.")

    @property
    def total(self) -> float:
        """Return the sum of all component weights."""

        return sum(value for _, value in self.as_items())

    def as_items(self) -> tuple[tuple[str, float], ...]:
        """Return component labels and weights."""

        return (
            (
                "Observable fraction",
                self.observable_fraction,
            ),
            (
                "Midpoint altitude",
                self.midpoint_altitude,
            ),
            (
                "Darkness fraction",
                self.darkness_fraction,
            ),
            (
                "Moon separation",
                self.moon_separation,
            ),
            (
                "Transit depth",
                self.transit_depth,
            ),
            (
                "Timing confidence",
                self.timing_confidence,
            ),
            (
                "Host brightness",
                self.host_brightness,
            ),
            (
                "Full-window visibility",
                self.full_window_visibility,
            ),
        )


@dataclass(frozen=True, slots=True)
class TransitObservationCandidate:
    """Transit event and observing information used for ranking."""

    event: TransitEvent
    visibility: TransitVisibilitySummary
    transit_depth_ppm: float | None = None
    host_magnitude: float | None = None

    def __post_init__(self) -> None:
        """Validate candidate consistency and optional metadata."""

        if self.event.planet_name != self.visibility.planet_name:
            raise TransitRankingError("Event and visibility planet names must match.")

        _require_unit_interval(
            self.visibility.observable_sample_fraction,
            "Observable sample fraction",
        )
        _require_unit_interval(
            self.visibility.dark_sample_fraction,
            "Dark sample fraction",
        )
        _require_unit_interval(
            self.visibility.altitude_sample_fraction,
            "Altitude sample fraction",
        )

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
class TransitScoreBreakdown:
    """Normalized component scores and total priority score."""

    observable_fraction_score: float
    midpoint_altitude_score: float
    darkness_fraction_score: float
    moon_separation_score: float
    transit_depth_score: float
    timing_confidence_score: float
    host_brightness_score: float
    full_window_visibility_score: float
    total_score: float
    missing_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankedTransit:
    """One transit candidate with rank and score information."""

    rank: int
    candidate: TransitObservationCandidate
    score: TransitScoreBreakdown


def _require_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite numerical value."""

    if not math.isfinite(value):
        raise TransitRankingError(f"{label} must be finite.")


def _require_non_negative_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite value greater than or equal to zero."""

    _require_finite(value, label)

    if value < 0.0:
        raise TransitRankingError(f"{label} must not be negative.")


def _require_unit_interval(
    value: float,
    label: str,
) -> None:
    """Require a value between zero and one."""

    _require_finite(value, label)

    if not 0.0 <= value <= 1.0:
        raise TransitRankingError(f"{label} must be between 0 and 1.")


def _clamp_unit(value: float) -> float:
    """Clamp one value to the inclusive range from zero to one."""

    return max(
        0.0,
        min(1.0, value),
    )


def score_midpoint_altitude(
    altitude_degrees: float,
) -> float:
    """Score target altitude from zero at the horizon to one at zenith."""

    _require_finite(
        altitude_degrees,
        "Midpoint altitude",
    )

    return _clamp_unit(altitude_degrees / 90.0)


def score_moon_separation(
    separation_degrees: float,
) -> float:
    """Score Moon separation, reaching full credit at 90 degrees."""

    _require_finite(
        separation_degrees,
        "Moon separation",
    )

    if not 0.0 <= separation_degrees <= 180.0:
        raise TransitRankingError("Moon separation must be between 0 and 180 degrees.")

    return _clamp_unit(separation_degrees / 90.0)


def score_transit_depth(
    transit_depth_ppm: float,
) -> float:
    """Score transit depth logarithmically.

    A depth of 10,000 ppm or greater receives full credit.
    """

    _require_non_negative_finite(
        transit_depth_ppm,
        "Transit depth",
    )

    reference_depth_ppm = 10_000.0

    return _clamp_unit(math.log10(1.0 + transit_depth_ppm) / math.log10(1.0 + reference_depth_ppm))


def score_timing_confidence(
    timing_uncertainty_hours: float,
) -> float:
    """Score ephemeris confidence using exponential decay.

    A two-hour uncertainty produces a score of approximately 0.368.
    """

    _require_non_negative_finite(
        timing_uncertainty_hours,
        "Timing uncertainty",
    )

    uncertainty_scale_hours = 2.0

    return math.exp(-timing_uncertainty_hours / uncertainty_scale_hours)


def score_host_brightness(
    host_magnitude: float,
) -> float:
    """Score apparent host-star magnitude.

    Magnitude 5 or brighter receives full credit.
    Magnitude 16 or fainter receives zero credit.
    """

    _require_finite(
        host_magnitude,
        "Host magnitude",
    )

    brightest_reference = 5.0
    faintest_reference = 16.0

    return _clamp_unit(
        (faintest_reference - host_magnitude) / (faintest_reference - brightest_reference)
    )


DEFAULT_RANKING_WEIGHTS: Final[RankingWeights] = RankingWeights()


def score_transit_candidate(
    candidate: TransitObservationCandidate,
    *,
    weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> TransitScoreBreakdown:
    """Calculate the complete priority score for one transit."""

    missing_fields: list[str] = []

    observable_fraction_score = candidate.visibility.observable_sample_fraction

    midpoint_altitude_score = score_midpoint_altitude(
        candidate.visibility.midpoint_sample.target_altitude_degrees
    )

    darkness_fraction_score = candidate.visibility.dark_sample_fraction

    moon_separation_score = score_moon_separation(
        candidate.visibility.minimum_moon_separation_degrees
    )

    if candidate.transit_depth_ppm is None:
        transit_depth_score = 0.5
        missing_fields.append("transit_depth_ppm")
    else:
        transit_depth_score = score_transit_depth(candidate.transit_depth_ppm)

    timing_confidence_score = score_timing_confidence(candidate.event.timing_uncertainty_hours)

    if candidate.host_magnitude is None:
        host_brightness_score = 0.5
        missing_fields.append("host_magnitude")
    else:
        host_brightness_score = score_host_brightness(candidate.host_magnitude)

    full_window_visibility_score = float(candidate.visibility.full_observation_window_visible)

    weighted_sum = (
        observable_fraction_score * weights.observable_fraction
        + midpoint_altitude_score * weights.midpoint_altitude
        + darkness_fraction_score * weights.darkness_fraction
        + moon_separation_score * weights.moon_separation
        + transit_depth_score * weights.transit_depth
        + timing_confidence_score * weights.timing_confidence
        + host_brightness_score * weights.host_brightness
        + full_window_visibility_score * weights.full_window_visibility
    )

    total_score = weighted_sum / weights.total * 100.0

    return TransitScoreBreakdown(
        observable_fraction_score=(observable_fraction_score),
        midpoint_altitude_score=(midpoint_altitude_score),
        darkness_fraction_score=(darkness_fraction_score),
        moon_separation_score=(moon_separation_score),
        transit_depth_score=(transit_depth_score),
        timing_confidence_score=(timing_confidence_score),
        host_brightness_score=(host_brightness_score),
        full_window_visibility_score=(full_window_visibility_score),
        total_score=total_score,
        missing_fields=tuple(missing_fields),
    )


def rank_transit_candidates(
    candidates: tuple[TransitObservationCandidate, ...],
    *,
    weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> tuple[RankedTransit, ...]:
    """Rank transit candidates from highest to lowest priority."""

    scored_candidates = tuple(
        (
            candidate,
            score_transit_candidate(
                candidate,
                weights=weights,
            ),
        )
        for candidate in candidates
    )

    ordered_candidates = sorted(
        scored_candidates,
        key=lambda item: (
            -item[1].total_score,
            -float(item[0].visibility.full_observation_window_visible),
            -item[0].visibility.observable_sample_fraction,
            -item[0].visibility.midpoint_sample.target_altitude_degrees,
            item[0].event.planet_name.casefold(),
            item[0].event.transit_number,
        ),
    )

    return tuple(
        RankedTransit(
            rank=rank,
            candidate=candidate,
            score=score,
        )
        for rank, (
            candidate,
            score,
        ) in enumerate(
            ordered_candidates,
            start=1,
        )
    )
