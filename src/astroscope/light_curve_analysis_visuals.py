"""Scientific Plotly visualizations for light-curve analysis results."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

import plotly.graph_objects as go

from astroscope.light_curve_phase import (
    PhaseBinningResult,
    PhaseFoldResult,
)
from astroscope.light_curve_transit_diagnostics import (
    TransitCandidateDiagnostics,
)
from astroscope.light_curve_transit_search import (
    BoxLeastSquaresSearchResult,
)
from astroscope.light_curve_visuals import LightCurveVisualError


class PeriodogramPointLike(Protocol):
    """Structural type for one periodogram sample."""

    period: float
    power: float


class RankedPeriodCandidateLike(Protocol):
    """Structural type for one ranked period candidate."""

    rank: int
    period: float
    power: float


class PeriodogramResultLike(Protocol):
    """Structural type shared by supported periodogram results."""

    samples: tuple[PeriodogramPointLike, ...]
    candidates: tuple[RankedPeriodCandidateLike, ...]


@dataclass(frozen=True, slots=True)
class LightCurveAnalysisVisualLabels:
    """Translatable labels for scientific analysis figures."""

    period_axis: str = "Period"
    power_axis: str = "Power"
    phase_axis: str = "Phase"
    phase_time_axis: str = "Time from transit midpoint"
    flux_axis: str = "Flux"
    magnitude_axis: str = "Magnitude"
    residual_axis: str = "Residual"
    rank_label: str = "Rank"
    lomb_scargle_series: str = "Lomb-Scargle power"
    period_candidates: str = "Period candidates"
    folded_series: str = "Folded observations"
    binned_series: str = "Phase bins"
    bls_series: str = "BLS power"
    transit_candidates: str = "Transit candidates"
    observed_series: str = "Observed"
    model_series: str = "Box transit model"
    residual_series: str = "Residual"


def _resolve_labels(
    labels: LightCurveAnalysisVisualLabels | None,
) -> LightCurveAnalysisVisualLabels:
    """Return explicit labels or the default English labels."""

    if labels is None:
        return LightCurveAnalysisVisualLabels()

    if not isinstance(
        labels,
        LightCurveAnalysisVisualLabels,
    ):
        raise LightCurveVisualError(
            "Analysis labels must be a LightCurveAnalysisVisualLabels instance."
        )

    return labels


def _validate_finite_values(
    values: Iterable[float],
    *,
    name: str,
    positive: bool = False,
) -> tuple[float, ...]:
    """Convert and validate one numeric plotting series."""

    converted = tuple(float(value) for value in values)

    if not converted:
        raise LightCurveVisualError(f"{name} must contain at least one value.")

    if any(not isfinite(value) for value in converted):
        raise LightCurveVisualError(f"{name} contains non-finite values.")

    if positive and any(value <= 0.0 for value in converted):
        raise LightCurveVisualError(f"{name} must contain values greater than zero.")

    return converted


def _error_bar_settings(
    uncertainties: Iterable[float | None],
) -> dict[str, object] | None:
    """Create Plotly error-bar settings when all errors exist."""

    raw_values = tuple(uncertainties)

    if not raw_values or any(value is None for value in raw_values):
        return None

    values = _validate_finite_values(
        (float(value) for value in raw_values if value is not None),
        name="Uncertainties",
        positive=True,
    )

    return {
        "type": "data",
        "array": values,
        "visible": True,
    }


def _value_axis_title(
    photometry_kind: str,
    labels: LightCurveAnalysisVisualLabels,
) -> str:
    """Return the vertical-axis title for one photometry kind."""

    if photometry_kind == "flux":
        return labels.flux_axis

    if photometry_kind == "magnitude":
        return labels.magnitude_axis

    raise LightCurveVisualError(f"Unsupported photometry kind: {photometry_kind!r}.")


def _configure_figure(
    figure: go.Figure,
    *,
    title: str,
    x_axis_title: str,
    y_axis_title: str,
    show_legend: bool,
    reverse_y_axis: bool = False,
) -> go.Figure:
    """Apply common scientific-figure layout settings."""

    figure.update_layout(
        title=title,
        template="plotly_white",
        hovermode="closest",
        showlegend=show_legend,
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
    )

    if reverse_y_axis:
        figure.update_yaxes(autorange="reversed")

    return figure


def _build_periodogram_figure(
    result: PeriodogramResultLike,
    *,
    title: str,
    series_name: str,
    candidate_name: str,
    labels: LightCurveAnalysisVisualLabels,
) -> go.Figure:
    """Build a periodogram with highlighted ranked candidates."""

    sorted_samples = tuple(
        sorted(
            result.samples,
            key=lambda sample: sample.period,
        )
    )

    periods = _validate_finite_values(
        (sample.period for sample in sorted_samples),
        name="Periodogram periods",
        positive=True,
    )
    powers = _validate_finite_values(
        (sample.power for sample in sorted_samples),
        name="Periodogram powers",
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=periods,
            y=powers,
            mode="lines",
            name=series_name,
            hovertemplate=(
                f"{labels.period_axis}: %{{x:.6g}}<br>"
                f"{labels.power_axis}: %{{y:.6g}}"
                "<extra>%{fullData.name}</extra>"
            ),
        )
    )

    candidates = tuple(result.candidates)

    if candidates:
        candidate_periods = _validate_finite_values(
            (candidate.period for candidate in candidates),
            name="Candidate periods",
            positive=True,
        )
        candidate_powers = _validate_finite_values(
            (candidate.power for candidate in candidates),
            name="Candidate powers",
        )

        figure.add_trace(
            go.Scatter(
                x=candidate_periods,
                y=candidate_powers,
                mode="markers",
                name=candidate_name,
                customdata=tuple(candidate.rank for candidate in candidates),
                marker={
                    "size": 10,
                    "symbol": "diamond",
                },
                hovertemplate=(
                    f"{labels.rank_label}: %{{customdata}}<br>"
                    f"{labels.period_axis}: %{{x:.6g}}<br>"
                    f"{labels.power_axis}: %{{y:.6g}}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )

    return _configure_figure(
        figure,
        title=title,
        x_axis_title=labels.period_axis,
        y_axis_title=labels.power_axis,
        show_legend=True,
    )


def build_lomb_scargle_periodogram_figure(
    result: PeriodogramResultLike,
    *,
    title: str = "Lomb-Scargle periodogram",
    labels: LightCurveAnalysisVisualLabels | None = None,
) -> go.Figure:
    """Plot Lomb-Scargle power and ranked period candidates."""

    resolved_labels = _resolve_labels(labels)

    return _build_periodogram_figure(
        result,
        title=title,
        series_name=resolved_labels.lomb_scargle_series,
        candidate_name=resolved_labels.period_candidates,
        labels=resolved_labels,
    )


def build_phase_folded_figure(
    phase_fold: PhaseFoldResult,
    *,
    phase_binning: PhaseBinningResult | None = None,
    title: str = "Phase-folded light curve",
    labels: LightCurveAnalysisVisualLabels | None = None,
) -> go.Figure:
    """Plot folded observations and optional phase bins."""

    resolved_labels = _resolve_labels(labels)

    if phase_binning is not None and phase_binning.phase_fold != phase_fold:
        raise LightCurveVisualError("Phase bins must belong to the supplied phase fold.")

    phases = _validate_finite_values(
        (point.phase for point in phase_fold.points),
        name="Folded phases",
    )
    values = _validate_finite_values(
        (point.value for point in phase_fold.points),
        name="Folded measurements",
    )

    observation_arguments: dict[str, object] = {
        "x": phases,
        "y": values,
        "mode": "markers",
        "name": resolved_labels.folded_series,
        "hovertemplate": (
            f"{resolved_labels.phase_axis}: %{{x:.6g}}<br>"
            "Measurement: %{y:.6g}"
            "<extra>%{fullData.name}</extra>"
        ),
    }

    observation_errors = _error_bar_settings(point.uncertainty for point in phase_fold.points)

    if observation_errors is not None:
        observation_arguments["error_y"] = observation_errors

    figure = go.Figure()

    figure.add_trace(go.Scatter(**observation_arguments))

    if phase_binning is not None:
        bin_phases = _validate_finite_values(
            (phase_bin.phase_center for phase_bin in phase_binning.bins),
            name="Phase-bin centers",
        )
        bin_values = _validate_finite_values(
            (phase_bin.value for phase_bin in phase_binning.bins),
            name="Phase-bin measurements",
        )

        bin_arguments: dict[str, object] = {
            "x": bin_phases,
            "y": bin_values,
            "mode": "lines+markers",
            "name": resolved_labels.binned_series,
            "marker": {
                "size": 9,
                "symbol": "diamond",
            },
            "hovertemplate": (
                f"{resolved_labels.phase_axis}: %{{x:.6g}}<br>"
                "Binned measurement: %{y:.6g}"
                "<extra>%{fullData.name}</extra>"
            ),
        }

        bin_errors = _error_bar_settings(phase_bin.uncertainty for phase_bin in phase_binning.bins)

        if bin_errors is not None:
            bin_arguments["error_y"] = bin_errors

        figure.add_trace(go.Scatter(**bin_arguments))

    photometry_kind = phase_fold.light_curve.metadata.photometry_kind

    return _configure_figure(
        figure,
        title=title,
        x_axis_title=resolved_labels.phase_axis,
        y_axis_title=_value_axis_title(
            photometry_kind,
            resolved_labels,
        ),
        show_legend=phase_binning is not None,
        reverse_y_axis=(photometry_kind == "magnitude"),
    )


def build_bls_periodogram_figure(
    result: BoxLeastSquaresSearchResult,
    *,
    title: str = "Box Least Squares periodogram",
    labels: LightCurveAnalysisVisualLabels | None = None,
) -> go.Figure:
    """Plot BLS power and ranked transit candidates."""

    resolved_labels = _resolve_labels(labels)

    return _build_periodogram_figure(
        result,
        title=title,
        series_name=resolved_labels.bls_series,
        candidate_name=resolved_labels.transit_candidates,
        labels=resolved_labels,
    )


def _sorted_diagnostic_points(
    diagnostics: TransitCandidateDiagnostics,
):
    """Return diagnostic points sorted around transit midpoint."""

    if not diagnostics.points:
        raise LightCurveVisualError("Transit diagnostics contain no points.")

    return tuple(
        sorted(
            diagnostics.points,
            key=lambda point: (
                point.phase_time,
                point.time,
            ),
        )
    )


def build_transit_model_figure(
    diagnostics: TransitCandidateDiagnostics,
    *,
    title: str | None = None,
    labels: LightCurveAnalysisVisualLabels | None = None,
) -> go.Figure:
    """Plot observed flux against the fitted box-transit model."""

    resolved_labels = _resolve_labels(labels)
    points = _sorted_diagnostic_points(diagnostics)

    phase_times = _validate_finite_values(
        (point.phase_time for point in points),
        name="Transit phase times",
    )
    observed_fluxes = _validate_finite_values(
        (point.observed_flux for point in points),
        name="Observed transit fluxes",
    )
    model_fluxes = _validate_finite_values(
        (point.model_flux for point in points),
        name="Model transit fluxes",
    )

    observation_arguments: dict[str, object] = {
        "x": phase_times,
        "y": observed_fluxes,
        "mode": "markers",
        "name": resolved_labels.observed_series,
        "hovertemplate": (
            f"{resolved_labels.phase_time_axis}: %{{x:.6g}}<br>"
            f"{resolved_labels.flux_axis}: %{{y:.6g}}"
            "<extra>%{fullData.name}</extra>"
        ),
    }

    observation_errors = _error_bar_settings(point.uncertainty for point in points)

    if observation_errors is not None:
        observation_arguments["error_y"] = observation_errors

    figure = go.Figure()

    figure.add_trace(go.Scatter(**observation_arguments))

    figure.add_trace(
        go.Scatter(
            x=phase_times,
            y=model_fluxes,
            mode="lines",
            line_shape="hv",
            name=resolved_labels.model_series,
            hovertemplate=(
                f"{resolved_labels.phase_time_axis}: "
                "%{x:.6g}<br>"
                f"{resolved_labels.flux_axis}: %{{y:.6g}}"
                "<extra>%{fullData.name}</extra>"
            ),
        )
    )

    resolved_title = (
        title if title is not None else (f"Transit model: P = {diagnostics.candidate.period:.6g}")
    )

    return _configure_figure(
        figure,
        title=resolved_title,
        x_axis_title=resolved_labels.phase_time_axis,
        y_axis_title=resolved_labels.flux_axis,
        show_legend=True,
    )


def build_transit_residual_figure(
    diagnostics: TransitCandidateDiagnostics,
    *,
    title: str = "Transit-model residuals",
    labels: LightCurveAnalysisVisualLabels | None = None,
) -> go.Figure:
    """Plot observed-minus-model residuals around transit."""

    resolved_labels = _resolve_labels(labels)
    points = _sorted_diagnostic_points(diagnostics)

    phase_times = _validate_finite_values(
        (point.phase_time for point in points),
        name="Residual phase times",
    )
    residuals = _validate_finite_values(
        (point.residual for point in points),
        name="Transit residuals",
    )

    residual_arguments: dict[str, object] = {
        "x": phase_times,
        "y": residuals,
        "mode": "markers",
        "name": resolved_labels.residual_series,
        "hovertemplate": (
            f"{resolved_labels.phase_time_axis}: %{{x:.6g}}<br>"
            f"{resolved_labels.residual_axis}: %{{y:.6g}}"
            "<extra>%{fullData.name}</extra>"
        ),
    }

    residual_errors = _error_bar_settings(point.uncertainty for point in points)

    if residual_errors is not None:
        residual_arguments["error_y"] = residual_errors

    figure = go.Figure()

    figure.add_trace(go.Scatter(**residual_arguments))

    figure.add_shape(
        type="line",
        x0=0.0,
        x1=1.0,
        xref="paper",
        y0=0.0,
        y1=0.0,
        yref="y",
        line={
            "dash": "dash",
        },
    )

    return _configure_figure(
        figure,
        title=title,
        x_axis_title=resolved_labels.phase_time_axis,
        y_axis_title=resolved_labels.residual_axis,
        show_legend=False,
    )
