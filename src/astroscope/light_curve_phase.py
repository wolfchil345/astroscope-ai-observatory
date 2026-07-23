"""Phase folding and phase binning for astronomical light curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite, sqrt
from numbers import Real
from statistics import fmean, stdev
from typing import Final

from astroscope.light_curve import LightCurve, LightCurveError

_MINIMUM_BIN_COUNT: Final[int] = 2
_MAXIMUM_BIN_COUNT: Final[int] = 500


class LightCurvePhaseError(LightCurveError):
    """Raised when light-curve phase analysis cannot be completed."""


@dataclass(frozen=True, slots=True)
class PhaseFoldedPoint:
    """One observation mapped onto a periodic phase cycle."""

    time: float
    phase: float
    cycle: int
    value: float
    uncertainty: float | None


@dataclass(frozen=True, slots=True)
class PhaseFoldResult:
    """A light curve folded onto one periodic cycle."""

    light_curve: LightCurve
    period: float
    epoch: float
    points: tuple[PhaseFoldedPoint, ...]

    @property
    def observation_count(self) -> int:
        """Return the number of folded observations."""

        return len(self.points)


@dataclass(frozen=True, slots=True)
class PhaseBin:
    """Summary of observations inside one phase interval."""

    index: int
    phase_start: float
    phase_end: float
    phase_center: float
    observation_count: int
    value: float
    uncertainty: float | None


@dataclass(frozen=True, slots=True)
class PhaseBinningResult:
    """Binned representation of a phase-folded light curve."""

    phase_fold: PhaseFoldResult
    bin_count: int
    minimum_points: int
    weighted: bool
    bins: tuple[PhaseBin, ...]

    @property
    def populated_bin_count(self) -> int:
        """Return the number of bins containing enough observations."""

        return len(self.bins)


def _finite_number(
    value: object,
    *,
    name: str,
) -> float:
    """Convert one finite real number to float."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise LightCurvePhaseError(f"{name} must be a finite real number.")

    converted = float(value)

    if not isfinite(converted):
        raise LightCurvePhaseError(f"{name} must be a finite real number.")

    return converted


def fold_light_curve(
    light_curve: LightCurve,
    *,
    period: float,
    epoch: float | None = None,
) -> PhaseFoldResult:
    """Fold observations onto phases in the interval from zero to one."""

    resolved_period = _finite_number(
        period,
        name="Period",
    )

    if resolved_period <= 0.0:
        raise LightCurvePhaseError("Period must be greater than zero.")

    if epoch is None:
        resolved_epoch = light_curve.points[0].time
    else:
        resolved_epoch = _finite_number(
            epoch,
            name="Epoch",
        )

    folded_points: list[PhaseFoldedPoint] = []

    for point in light_curve.points:
        relative_cycle = (point.time - resolved_epoch) / resolved_period

        cycle = floor(relative_cycle)
        phase = relative_cycle - cycle

        if phase >= 1.0:
            phase = 0.0
            cycle += 1

        folded_points.append(
            PhaseFoldedPoint(
                time=point.time,
                phase=float(phase),
                cycle=cycle,
                value=point.value,
                uncertainty=point.uncertainty,
            )
        )

    folded_points.sort(
        key=lambda point: (
            point.phase,
            point.time,
        )
    )

    return PhaseFoldResult(
        light_curve=light_curve,
        period=resolved_period,
        epoch=resolved_epoch,
        points=tuple(folded_points),
    )


def _validate_binning_settings(
    phase_fold: PhaseFoldResult,
    *,
    bin_count: int,
    minimum_points: int,
) -> None:
    """Validate phase-binning controls."""

    if (
        isinstance(bin_count, bool)
        or not isinstance(bin_count, int)
        or not _MINIMUM_BIN_COUNT <= bin_count <= _MAXIMUM_BIN_COUNT
    ):
        raise LightCurvePhaseError("Bin count must be an integer from 2 to 500.")

    if (
        isinstance(minimum_points, bool)
        or not isinstance(minimum_points, int)
        or minimum_points < 1
    ):
        raise LightCurvePhaseError("Minimum points must be a positive integer.")

    if minimum_points > phase_fold.observation_count:
        raise LightCurvePhaseError("Minimum points cannot exceed the observation count.")


def _unweighted_uncertainty(
    points: tuple[PhaseFoldedPoint, ...],
) -> float | None:
    """Estimate uncertainty for one unweighted phase bin."""

    if len(points) > 1:
        values = [point.value for point in points]

        return float(stdev(values) / sqrt(len(values)))

    return points[0].uncertainty


def bin_phase_fold(
    phase_fold: PhaseFoldResult,
    *,
    bin_count: int = 20,
    minimum_points: int = 1,
    use_uncertainties: bool = True,
) -> PhaseBinningResult:
    """Combine nearby phase-folded observations into equal-width bins."""

    _validate_binning_settings(
        phase_fold,
        bin_count=bin_count,
        minimum_points=minimum_points,
    )

    grouped_points: list[list[PhaseFoldedPoint]] = [[] for _ in range(bin_count)]

    for point in phase_fold.points:
        index = min(
            int(point.phase * bin_count),
            bin_count - 1,
        )
        grouped_points[index].append(point)

    weighted = use_uncertainties and all(
        point.uncertainty is not None for point in phase_fold.points
    )

    bins: list[PhaseBin] = []

    for index, raw_points in enumerate(grouped_points):
        if len(raw_points) < minimum_points:
            continue

        points = tuple(raw_points)

        if weighted:
            weights = tuple(
                1.0 / float(point.uncertainty) ** 2
                for point in points
                if point.uncertainty is not None
            )
            total_weight = sum(weights)

            value = (
                sum(
                    weight * point.value
                    for weight, point in zip(
                        weights,
                        points,
                        strict=True,
                    )
                )
                / total_weight
            )

            uncertainty: float | None = sqrt(1.0 / total_weight)
        else:
            value = fmean(point.value for point in points)
            uncertainty = _unweighted_uncertainty(points)

        phase_start = index / bin_count
        phase_end = (index + 1) / bin_count

        bins.append(
            PhaseBin(
                index=index,
                phase_start=phase_start,
                phase_end=phase_end,
                phase_center=(phase_start + phase_end) / 2.0,
                observation_count=len(points),
                value=float(value),
                uncertainty=uncertainty,
            )
        )

    if not bins:
        raise LightCurvePhaseError("No phase bins contain the required number of observations.")

    return PhaseBinningResult(
        phase_fold=phase_fold,
        bin_count=bin_count,
        minimum_points=minimum_points,
        weighted=weighted,
        bins=tuple(bins),
    )
