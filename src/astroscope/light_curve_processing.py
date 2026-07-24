"""Preprocessing utilities for astronomical light curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import median

import numpy as np

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


@dataclass(frozen=True, slots=True)
class PolynomialTrendModel:
    """Polynomial trend fitted to a light curve."""

    degree: int
    reference_time: float
    coefficients: tuple[float, ...]
    weighted: bool

    def __post_init__(self) -> None:
        if self.degree < 1:
            raise LightCurveProcessingError("Trend-model degree must be at least one.")

        if len(self.coefficients) != self.degree + 1:
            raise LightCurveProcessingError(
                "Polynomial coefficient count does not match its degree."
            )

        if not isfinite(self.reference_time):
            raise LightCurveProcessingError("Trend-model reference time must be finite.")

        if any(not isfinite(coefficient) for coefficient in self.coefficients):
            raise LightCurveProcessingError("Trend-model coefficients must be finite.")

    def evaluate(
        self,
        time: float,
    ) -> float:
        """Evaluate the fitted trend at one observation time."""

        if not isfinite(time):
            raise LightCurveProcessingError("Trend evaluation time must be finite.")

        centered_time = time - self.reference_time

        return float(
            np.polyval(
                np.asarray(
                    self.coefficients,
                    dtype=float,
                ),
                centered_time,
            )
        )


@dataclass(frozen=True, slots=True)
class LightCurveDetrendingResult:
    """Detrended light curve, report, and fitted trend model."""

    light_curve: LightCurve
    report: LightCurveProcessingReport
    model: PolynomialTrendModel
    trend_values: tuple[float, ...]


def _validate_polynomial_degree(
    degree: int,
    observation_count: int,
) -> None:
    """Validate a requested detrending degree."""

    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 1 or degree > 5:
        raise LightCurveProcessingError("Polynomial degree must be an integer from 1 to 5.")

    if observation_count <= degree:
        raise LightCurveProcessingError(
            "Polynomial degree must be smaller than the observation count."
        )


def _fit_polynomial_trend(
    light_curve: LightCurve,
    *,
    degree: int,
) -> tuple[PolynomialTrendModel, np.ndarray]:
    """Fit a numerically centered polynomial trend."""

    _validate_polynomial_degree(
        degree,
        light_curve.observation_count,
    )

    times = np.asarray(
        [point.time for point in light_curve.points],
        dtype=float,
    )
    values = np.asarray(
        [point.value for point in light_curve.points],
        dtype=float,
    )

    reference_time = float(np.median(times))
    centered_times = times - reference_time

    weights: np.ndarray | None = None
    weighted = False

    if light_curve.has_uncertainties:
        uncertainties = np.asarray(
            [
                float(point.uncertainty)
                for point in light_curve.points
                if point.uncertainty is not None
            ],
            dtype=float,
        )

        weights = 1.0 / uncertainties
        weighted = True

    try:
        coefficient_array = np.polyfit(
            centered_times,
            values,
            degree,
            w=weights,
        )
    except (
        TypeError,
        ValueError,
        np.linalg.LinAlgError,
    ) as error:
        raise LightCurveProcessingError("Polynomial trend fitting failed.") from error

    trend_values = np.polyval(
        coefficient_array,
        centered_times,
    )

    if not np.all(np.isfinite(trend_values)):
        raise LightCurveProcessingError("Polynomial trend contains non-finite values.")

    model = PolynomialTrendModel(
        degree=degree,
        reference_time=reference_time,
        coefficients=tuple(float(coefficient) for coefficient in coefficient_array),
        weighted=weighted,
    )

    return model, trend_values


def detrend_light_curve(
    light_curve: LightCurve,
    *,
    degree: int = 1,
) -> LightCurveDetrendingResult:
    """Remove a fitted linear or polynomial trend from a light curve."""

    model, trend_array = _fit_polynomial_trend(
        light_curve,
        degree=degree,
    )

    values = np.asarray(
        [point.value for point in light_curve.points],
        dtype=float,
    )

    baseline = float(np.median(values))

    if light_curve.metadata.photometry_kind == "flux":
        if baseline == 0.0:
            raise LightCurveProcessingError("Flux cannot be detrended when its median is zero.")

        trend_scale = max(
            1.0,
            float(np.max(np.abs(trend_array))),
        )
        near_zero_limit = np.finfo(float).eps * trend_scale * 10.0

        if np.any(np.abs(trend_array) <= near_zero_limit):
            raise LightCurveProcessingError("Flux trend is zero or too close to zero.")

        correction_factors = baseline / trend_array
        processed_values = values * correction_factors
    else:
        correction_factors = np.ones_like(
            trend_array,
        )
        processed_values = values - trend_array + baseline

    points = tuple(
        LightCurvePoint(
            time=point.time,
            value=float(processed_value),
            uncertainty=(
                point.uncertainty * abs(float(correction_factor))
                if point.uncertainty is not None
                else None
            ),
        )
        for point, processed_value, correction_factor in zip(
            light_curve.points,
            processed_values,
            correction_factors,
            strict=True,
        )
    )

    processed = LightCurve(
        metadata=light_curve.metadata,
        points=points,
    )

    residuals = values - trend_array
    residual_rms = sqrt(
        float(
            np.mean(
                residuals**2,
            )
        )
    )

    operation = "linear_detrending" if degree == 1 else f"polynomial_detrending_degree_{degree}"

    return LightCurveDetrendingResult(
        light_curve=processed,
        report=LightCurveProcessingReport(
            operation=operation,
            input_count=light_curve.observation_count,
            output_count=processed.observation_count,
            removed_count=0,
            center=baseline,
            scale=residual_rms,
        ),
        model=model,
        trend_values=tuple(float(value) for value in trend_array),
    )
