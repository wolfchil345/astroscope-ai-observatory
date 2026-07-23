"""Box Least Squares transit searches for astronomical light curves."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Final, Literal

import numpy as np
from astropy.timeseries import BoxLeastSquares

from astroscope.light_curve import LightCurve, LightCurveError

TransitSearchObjective = Literal["likelihood", "snr"]

_MINIMUM_OBSERVATION_COUNT: Final[int] = 20
_MAXIMUM_OVERSAMPLE: Final[int] = 100
_MAXIMUM_CANDIDATE_COUNT: Final[int] = 20


class LightCurveTransitSearchError(LightCurveError):
    """Raised when a transit search cannot be completed."""


@dataclass(frozen=True, slots=True)
class TransitPeriodogramPoint:
    """One sample from a Box Least Squares periodogram."""

    period: float
    power: float
    duration: float
    transit_time: float
    depth: float
    depth_error: float
    depth_snr: float


@dataclass(frozen=True, slots=True)
class TransitSearchCandidate:
    """One ranked box-shaped transit candidate."""

    rank: int
    period: float
    power: float
    duration: float
    transit_time: float
    depth: float
    depth_error: float
    depth_snr: float


@dataclass(frozen=True, slots=True)
class BoxLeastSquaresSearchResult:
    """Complete result of a Box Least Squares transit search."""

    minimum_period: float
    maximum_period: float
    durations: tuple[float, ...]
    objective: TransitSearchObjective
    observation_baseline: float
    weighted: bool
    samples: tuple[TransitPeriodogramPoint, ...]
    candidates: tuple[TransitSearchCandidate, ...]

    @property
    def best_candidate(self) -> TransitSearchCandidate:
        """Return the highest-power transit candidate."""

        if not self.candidates:
            raise LightCurveTransitSearchError("The transit search contains no candidates.")

        return self.candidates[0]


def _finite_float(
    value: object,
    *,
    name: str,
) -> float:
    """Convert a finite real value to float."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise LightCurveTransitSearchError(f"{name} must be a finite real number.")

    converted = float(value)

    if not isfinite(converted):
        raise LightCurveTransitSearchError(f"{name} must be a finite real number.")

    return converted


def _normalize_durations(
    durations: Iterable[float],
) -> tuple[float, ...]:
    """Validate and normalize candidate transit durations."""

    try:
        raw_durations = tuple(durations)
    except TypeError as error:
        raise LightCurveTransitSearchError(
            "Transit durations must be an iterable of finite numbers."
        ) from error

    if not raw_durations:
        raise LightCurveTransitSearchError("At least one transit duration is required.")

    normalized: list[float] = []

    for duration in raw_durations:
        converted = _finite_float(
            duration,
            name="Transit duration",
        )

        if converted <= 0.0:
            raise LightCurveTransitSearchError("Transit durations must be greater than zero.")

        normalized.append(converted)

    return tuple(sorted(set(normalized)))


def _validate_search_settings(
    *,
    light_curve: LightCurve,
    minimum_period: float,
    maximum_period: float,
    durations: tuple[float, ...],
    objective: str,
    oversample: int,
    frequency_factor: float,
    candidate_count: int,
) -> None:
    """Validate Box Least Squares search settings."""

    if light_curve.metadata.photometry_kind != "flux":
        raise LightCurveTransitSearchError(
            "Box Least Squares transit search requires flux measurements."
        )

    if light_curve.observation_count < _MINIMUM_OBSERVATION_COUNT:
        raise LightCurveTransitSearchError("Transit search requires at least twenty observations.")

    if minimum_period <= 0.0:
        raise LightCurveTransitSearchError("Minimum period must be greater than zero.")

    if maximum_period <= minimum_period:
        raise LightCurveTransitSearchError(
            "Maximum period must be greater than the minimum period."
        )

    if any(duration >= minimum_period for duration in durations):
        raise LightCurveTransitSearchError(
            "Every transit duration must be shorter than the minimum period."
        )

    if objective not in {"likelihood", "snr"}:
        raise LightCurveTransitSearchError("Objective must be either 'likelihood' or 'snr'.")

    if (
        isinstance(oversample, bool)
        or not isinstance(oversample, int)
        or not 1 <= oversample <= _MAXIMUM_OVERSAMPLE
    ):
        raise LightCurveTransitSearchError("Oversample must be an integer from 1 to 100.")

    if frequency_factor <= 0.0:
        raise LightCurveTransitSearchError("Frequency factor must be greater than zero.")

    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or not 1 <= candidate_count <= _MAXIMUM_CANDIDATE_COUNT
    ):
        raise LightCurveTransitSearchError("Candidate count must be an integer from 1 to 20.")

    if light_curve.duration <= 0.0:
        raise LightCurveTransitSearchError("Observation baseline must be greater than zero.")


def _result_array(
    values: object,
    *,
    name: str,
) -> np.ndarray:
    """Convert and validate one BLS result array."""

    array = np.asarray(
        values,
        dtype=float,
    ).reshape(-1)

    if array.size == 0:
        raise LightCurveTransitSearchError(f"Transit-search {name} array is empty.")

    if not np.all(np.isfinite(array)):
        raise LightCurveTransitSearchError(
            f"Transit-search {name} array contains non-finite values."
        )

    return array


def _validate_result_shapes(
    arrays: tuple[np.ndarray, ...],
) -> None:
    """Require all BLS result arrays to have identical shapes."""

    expected_shape = arrays[0].shape

    if any(array.shape != expected_shape for array in arrays[1:]):
        raise LightCurveTransitSearchError("Transit-search result arrays have inconsistent shapes.")


def _local_maximum_indices(
    powers: np.ndarray,
) -> tuple[int, ...]:
    """Return indices of local periodogram maxima."""

    if powers.size == 1:
        return (0,)

    maxima = np.zeros(
        powers.size,
        dtype=bool,
    )

    maxima[0] = powers[0] >= powers[1]
    maxima[-1] = powers[-1] >= powers[-2]

    if powers.size > 2:
        maxima[1:-1] = (powers[1:-1] >= powers[:-2]) & (powers[1:-1] >= powers[2:])

    indices = np.flatnonzero(maxima)

    if indices.size == 0:
        return (int(np.argmax(powers)),)

    return tuple(int(index) for index in indices)


def _select_candidate_indices(
    *,
    periods: np.ndarray,
    powers: np.ndarray,
    observation_baseline: float,
    candidate_count: int,
) -> tuple[int, ...]:
    """Select strong separated local periodogram maxima."""

    local_indices = _local_maximum_indices(powers)

    ranked_indices = sorted(
        local_indices,
        key=lambda index: float(powers[index]),
        reverse=True,
    )

    selected: list[int] = []
    minimum_frequency_separation = 0.5 / observation_baseline

    for index in ranked_indices:
        frequency = 1.0 / float(periods[index])

        separated = all(
            abs(frequency - 1.0 / float(periods[selected_index])) >= minimum_frequency_separation
            for selected_index in selected
        )

        if not separated:
            continue

        selected.append(index)

        if len(selected) == candidate_count:
            break

    if not selected:
        selected.append(int(np.argmax(powers)))

    return tuple(selected)


def search_box_least_squares(
    light_curve: LightCurve,
    *,
    minimum_period: float,
    maximum_period: float,
    durations: Iterable[float],
    objective: TransitSearchObjective = "snr",
    oversample: int = 10,
    frequency_factor: float = 1.0,
    candidate_count: int = 5,
) -> BoxLeastSquaresSearchResult:
    """Search a flux light curve for periodic box-shaped transit signals."""

    resolved_minimum_period = _finite_float(
        minimum_period,
        name="Minimum period",
    )
    resolved_maximum_period = _finite_float(
        maximum_period,
        name="Maximum period",
    )
    resolved_frequency_factor = _finite_float(
        frequency_factor,
        name="Frequency factor",
    )
    resolved_durations = _normalize_durations(durations)

    _validate_search_settings(
        light_curve=light_curve,
        minimum_period=resolved_minimum_period,
        maximum_period=resolved_maximum_period,
        durations=resolved_durations,
        objective=objective,
        oversample=oversample,
        frequency_factor=resolved_frequency_factor,
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

    try:
        model = BoxLeastSquares(
            times,
            values,
            dy=uncertainties,
        )

        raw_result = model.autopower(
            np.asarray(
                resolved_durations,
                dtype=float,
            ),
            objective=objective,
            method="fast",
            oversample=oversample,
            minimum_period=resolved_minimum_period,
            maximum_period=resolved_maximum_period,
            frequency_factor=resolved_frequency_factor,
        )
    except (
        FloatingPointError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        raise LightCurveTransitSearchError("Box Least Squares transit search failed.") from error

    periods = _result_array(
        raw_result.period,
        name="period",
    )
    powers = _result_array(
        raw_result.power,
        name="power",
    )
    result_durations = _result_array(
        raw_result.duration,
        name="duration",
    )
    transit_times = _result_array(
        raw_result.transit_time,
        name="transit-time",
    )
    depths = _result_array(
        raw_result.depth,
        name="depth",
    )
    depth_errors = _result_array(
        raw_result.depth_err,
        name="depth-error",
    )
    depth_snrs = _result_array(
        raw_result.depth_snr,
        name="depth-SNR",
    )

    result_arrays = (
        periods,
        powers,
        result_durations,
        transit_times,
        depths,
        depth_errors,
        depth_snrs,
    )

    _validate_result_shapes(result_arrays)

    period_tolerance = (
        np.finfo(float).eps
        * max(
            1.0,
            abs(resolved_minimum_period),
            abs(resolved_maximum_period),
        )
        * 16.0
    )

    period_mask = (periods >= resolved_minimum_period - period_tolerance) & (
        periods <= resolved_maximum_period + period_tolerance
    )

    if not np.any(period_mask):
        raise LightCurveTransitSearchError(
            "No transit-search samples remain inside the requested period range."
        )

    (
        periods,
        powers,
        result_durations,
        transit_times,
        depths,
        depth_errors,
        depth_snrs,
    ) = tuple(array[period_mask] for array in result_arrays)

    filtered_arrays = (
        periods,
        powers,
        result_durations,
        transit_times,
        depths,
        depth_errors,
        depth_snrs,
    )

    _validate_result_shapes(filtered_arrays)

    samples = tuple(
        TransitPeriodogramPoint(
            period=float(period),
            power=float(power),
            duration=float(duration),
            transit_time=float(transit_time),
            depth=float(depth),
            depth_error=float(depth_error),
            depth_snr=float(depth_snr),
        )
        for (
            period,
            power,
            duration,
            transit_time,
            depth,
            depth_error,
            depth_snr,
        ) in zip(
            periods,
            powers,
            result_durations,
            transit_times,
            depths,
            depth_errors,
            depth_snrs,
            strict=True,
        )
    )

    candidate_indices = _select_candidate_indices(
        periods=periods,
        powers=powers,
        observation_baseline=light_curve.duration,
        candidate_count=candidate_count,
    )

    candidates = tuple(
        TransitSearchCandidate(
            rank=rank,
            period=float(periods[index]),
            power=float(powers[index]),
            duration=float(result_durations[index]),
            transit_time=float(transit_times[index]),
            depth=float(depths[index]),
            depth_error=float(depth_errors[index]),
            depth_snr=float(depth_snrs[index]),
        )
        for rank, index in enumerate(
            candidate_indices,
            start=1,
        )
    )

    return BoxLeastSquaresSearchResult(
        minimum_period=resolved_minimum_period,
        maximum_period=resolved_maximum_period,
        durations=resolved_durations,
        objective=objective,
        observation_baseline=light_curve.duration,
        weighted=weighted,
        samples=samples,
        candidates=candidates,
    )
