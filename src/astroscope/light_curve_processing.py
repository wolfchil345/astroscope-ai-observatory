"""Preprocessing utilities for astronomical light curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median

from astroscope.light_curve import (
    LightCurve,
    LightCurveError,
    LightCurvePoint,
)

_MAD_TO_STANDARD_DEVIATION = 1.4826


class LightCurveProcessingError(LightCurveError):
    """Raised when light-curve preprocessing cannot be completed."""


@dataclass(frozen=True, slots=True)
class LightCurveProcessingReport:
    """Summary of one light-curve preprocessing operation."""

    operation: str
    input_count: int
    output_count: int
    removed_count: int
    center: float
    scale: float | None = None


@dataclass(frozen=True, slots=True)
class LightCurveProcessingResult:
    """Processed light curve and its operation report."""

    light_curve: LightCurve
    report: LightCurveProcessingReport


def _replace_values(
    *,
    light_curve: LightCurve,
    values: tuple[float, ...],
    uncertainty_scale: float = 1.0,
) -> LightCurve:
    """Create a new light curve while: tuple[float, ...],
        uncertainty_scale: float = 1.0,
    ) -> Light preserving times and metadata."""

    if len(values) != light_curve.observation_count:
        raise LightCurveProcessingError("Processed values must match the observation count.")

    points = tuple(
        LightCurvePoint(
            time=point.time,
            value=value,
            uncertainty=(
                point.uncertainty * uncertainty_scale if point.uncertainty is not None else None
            ),
        )
        for point, value in zip(
            light_curve.points,
            values,
            strict=True,
        )
    )

    return LightCurve(
        metadata=light_curve.metadata,
        points=points,
    )


def normalize_light_curve(
    light_curve: LightCurve,
) -> LightCurveProcessingResult:
    """Normalize flux or center magnitude measurements around their median."""

    values = tuple(point.value for point in light_curve.points)
    center = float(median(values))

    if not isfinite(center):
        raise LightCurveProcessingError("The light-curve median must be finite.")

    if light_curve.metadata.photometry_kind == "flux":
        if center == 0.0:
            raise LightCurveProcessingError("Flux cannot be normalized when its median is zero.")

        normalized_values = tuple(value / center for value in values)
        uncertainty_scale = 1.0 / abs(center)
        operation = "median_flux_normalization"
    else:
        normalized_values = tuple(value - center for value in values)
        uncertainty_scale = 1.0
        operation = "median_magnitude_centering"

    processed = _replace_values(
        light_curve=light_curve,
        values=normalized_values,
        uncertainty_scale=uncertainty_scale,
    )

    return LightCurveProcessingResult(
        light_curve=processed,
        report=LightCurveProcessingReport(
            operation=operation,
            input_count=light_curve.observation_count,
            output_count=processed.observation_count,
            removed_count=0,
            center=center,
        ),
    )


def sigma_clip_light_curve(
    light_curve: LightCurve,
    *,
    sigma: float = 5.0,
) -> LightCurveProcessingResult:
    """Remove robust statistical outliers using median absolute deviation."""

    if not isfinite(sigma) or sigma <= 0.0:
        raise LightCurveProcessingError("Sigma threshold must be a finite value greater than zero.")

    values = tuple(point.value for point in light_curve.points)
    center = float(median(values))

    absolute_deviations = tuple(abs(value - center) for value in values)
    median_absolute_deviation = float(median(absolute_deviations))
    robust_scale = _MAD_TO_STANDARD_DEVIATION * median_absolute_deviation

    if robust_scale == 0.0:
        return LightCurveProcessingResult(
            light_curve=light_curve,
            report=LightCurveProcessingReport(
                operation="robust_sigma_clipping",
                input_count=light_curve.observation_count,
                output_count=light_curve.observation_count,
                removed_count=0,
                center=center,
                scale=0.0,
            ),
        )

    limit = sigma * robust_scale

    retained_points = tuple(
        point for point in light_curve.points if abs(point.value - center) <= limit
    )

    if len(retained_points) < 3:
        raise LightCurveProcessingError("Sigma clipping would leave fewer than three observations.")

    processed = LightCurve(
        metadata=light_curve.metadata,
        points=retained_points,
    )

    return LightCurveProcessingResult(
        light_curve=processed,
        report=LightCurveProcessingReport(
            operation="robust_sigma_clipping",
            input_count=light_curve.observation_count,
            output_count=processed.observation_count,
            removed_count=(light_curve.observation_count - processed.observation_count),
            center=center,
            scale=robust_scale,
        ),
    )
