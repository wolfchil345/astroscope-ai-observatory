"""Period analysis for astronomical light curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Final

import numpy as np
from astropy.timeseries import LombScargle

from astroscope.light_curve import LightCurve, LightCurveError

_MINIMUM_OBSERVATION_COUNT: Final[int] = 5
_MAXIMUM_CANDIDATE_COUNT: Final[int] = 20
_MAXIMUM_SAMPLES_PER_PEAK: Final[int] = 100


class LightCurvePeriodError(LightCurveError):
    """Raised when light-curve period analysis cannot be completed."""


@dataclass(frozen=True, slots=True)
class PeriodogramPoint:
    """One frequency sample in a Lomb-Scargle periodogram."""

    frequency: float
    period: float
    power: float


@dataclass(frozen=True, slots=True)
class PeriodCandidate:
    """One ranked periodic-signal candidate."""

    rank: int
    frequency: float
    period: float
    power: float
    false_alarm_probability: float | None


@dataclass(frozen=True, slots=True)
class LombScargleResult:
    """Complete Lomb-Scargle period-analysis result."""

    minimum_period: float
    maximum_period: float
    observation_baseline: float
    weighted: bool
    samples: tuple[PeriodogramPoint, ...]
    candidates: tuple[PeriodCandidate, ...]

    @property
    def best_candidate(self) -> PeriodCandidate:
        """Return the highest-power period candidate."""

        if not self.candidates:
            raise LightCurvePeriodError("The period analysis contains no candidates.")

        return self.candidates[0]

    @property
    def best_period(self) -> float:
        """Return the strongest detected period."""

        return self.best_candidate.period

    @property
    def best_frequency(self) -> float:
        """Return the strongest detected frequency."""

        return self.best_candidate.frequency


def _validate_analysis_settings(
    *,
    light_curve: LightCurve,
    minimum_period: float,
    maximum_period: float,
    samples_per_peak: int,
    candidate_count: int,
) -> None:
    """Validate Lomb-Scargle analysis settings."""

    if light_curve.observation_count < _MINIMUM_OBSERVATION_COUNT:
        raise LightCurvePeriodError("Period analysis requires at least five observations.")

    if not isfinite(minimum_period) or minimum_period <= 0.0:
        raise LightCurvePeriodError("Minimum period must be a finite value greater than zero.")

    if not isfinite(maximum_period) or maximum_period <= minimum_period:
        raise LightCurvePeriodError(
            "Maximum period must be finite and greater than the minimum period."
        )

    if (
        isinstance(samples_per_peak, bool)
        or not isinstance(samples_per_peak, int)
        or not 1 <= samples_per_peak <= _MAXIMUM_SAMPLES_PER_PEAK
    ):
        raise LightCurvePeriodError("Samples per peak must be an integer from 1 to 100.")

    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or not 1 <= candidate_count <= _MAXIMUM_CANDIDATE_COUNT
    ):
        raise LightCurvePeriodError("Candidate count must be an integer from 1 to 20.")

    if light_curve.duration <= 0.0:
        raise LightCurvePeriodError("The observation baseline must be greater than zero.")


def _false_alarm_probability(
    *,
    model: LombScargle,
    power: float,
    minimum_frequency: float,
    maximum_frequency: float,
) -> float | None:
    """Calculate a bounded false-alarm probability when possible."""

    try:
        probability = float(
            model.false_alarm_probability(
                power,
                minimum_frequency=minimum_frequency,
                maximum_frequency=maximum_frequency,
            )
        )
    except (FloatingPointError, RuntimeError, ValueError):
        return None

    if not isfinite(probability):
        return None

    return min(1.0, max(0.0, probability))


def _select_candidate_indices(
    *,
    frequencies: np.ndarray,
    powers: np.ndarray,
    observation_baseline: float,
    candidate_count: int,
) -> tuple[int, ...]:
    """Select strong candidates while avoiding adjacent samples."""

    sorted_indices = np.argsort(powers)[::-1]
    selected: list[int] = []

    minimum_separation = 0.5 / observation_baseline

    for raw_index in sorted_indices:
        index = int(raw_index)
        frequency = float(frequencies[index])

        sufficiently_separated = all(
            abs(frequency - float(frequencies[selected_index])) >= minimum_separation
            for selected_index in selected
        )

        if not sufficiently_separated:
            continue

        selected.append(index)

        if len(selected) == candidate_count:
            break

    return tuple(selected)


def analyze_lomb_scargle(
    light_curve: LightCurve,
    *,
    minimum_period: float,
    maximum_period: float,
    samples_per_peak: int = 10,
    candidate_count: int = 5,
) -> LombScargleResult:
    """Calculate a Lomb-Scargle periodogram and ranked candidates."""

    _validate_analysis_settings(
        light_curve=light_curve,
        minimum_period=minimum_period,
        maximum_period=maximum_period,
        samples_per_peak=samples_per_peak,
        candidate_count=candidate_count,
    )

    times = np.asarray(
        [point.time for point in light_curve.points],
        dtype=float,
    )
    values = np.asarray(
        [point.value for point in light_curve.points],
        dtype=float,
    )

    uncertainties: np.ndarray | None = None
    weighted = light_curve.has_uncertainties

    if weighted:
        uncertainties = np.asarray(
            [
                float(point.uncertainty)
                for point in light_curve.points
                if point.uncertainty is not None
            ],
            dtype=float,
        )

    minimum_frequency = 1.0 / maximum_period
    maximum_frequency = 1.0 / minimum_period

    try:
        model = LombScargle(
            times,
            values,
            dy=uncertainties,
            fit_mean=True,
            center_data=True,
        )

        frequencies, powers = model.autopower(
            minimum_frequency=minimum_frequency,
            maximum_frequency=maximum_frequency,
            samples_per_peak=samples_per_peak,
        )
    except (FloatingPointError, TypeError, ValueError) as error:
        raise LightCurvePeriodError("Lomb-Scargle period analysis failed.") from error

    frequencies = np.asarray(frequencies, dtype=float)
    powers = np.asarray(powers, dtype=float)

    if frequencies.size == 0 or powers.size == 0:
        raise LightCurvePeriodError("Lomb-Scargle analysis produced no periodogram samples.")

    if frequencies.shape != powers.shape:
        raise LightCurvePeriodError("Periodogram frequency and power arrays have different shapes.")

    if not np.all(np.isfinite(frequencies)):
        raise LightCurvePeriodError("Periodogram frequencies contain non-finite values.")

    if not np.all(np.isfinite(powers)):
        raise LightCurvePeriodError("Periodogram powers contain non-finite values.")

    periods = 1.0 / frequencies

    samples = tuple(
        PeriodogramPoint(
            frequency=float(frequency),
            period=float(period),
            power=float(power),
        )
        for frequency, period, power in zip(
            frequencies,
            periods,
            powers,
            strict=True,
        )
    )

    candidate_indices = _select_candidate_indices(
        frequencies=frequencies,
        powers=powers,
        observation_baseline=light_curve.duration,
        candidate_count=candidate_count,
    )

    candidates = tuple(
        PeriodCandidate(
            rank=rank,
            frequency=float(frequencies[index]),
            period=float(periods[index]),
            power=float(powers[index]),
            false_alarm_probability=_false_alarm_probability(
                model=model,
                power=float(powers[index]),
                minimum_frequency=minimum_frequency,
                maximum_frequency=maximum_frequency,
            ),
        )
        for rank, index in enumerate(
            candidate_indices,
            start=1,
        )
    )

    if not candidates:
        raise LightCurvePeriodError("Lomb-Scargle analysis produced no period candidates.")

    return LombScargleResult(
        minimum_period=minimum_period,
        maximum_period=maximum_period,
        observation_baseline=light_curve.duration,
        weighted=weighted,
        samples=samples,
        candidates=candidates,
    )
