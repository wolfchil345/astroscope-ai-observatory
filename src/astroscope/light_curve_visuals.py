"""Plotly visualizations for astronomical light curves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import plotly.graph_objects as go

from astroscope.light_curve import LightCurve, LightCurveError


class LightCurveVisualError(LightCurveError):
    """Raised when a light-curve visualization cannot be created."""


@dataclass(frozen=True, slots=True)
class LightCurveVisualLabels:
    """Translatable labels used by light-curve figures."""

    time_axis: str = "Time"
    flux_axis: str = "Flux"
    magnitude_axis: str = "Magnitude"
    raw_series: str = "Raw"
    processed_series: str = "Processed"


_DEFAULT_LABELS: Final[LightCurveVisualLabels] = LightCurveVisualLabels()


def _resolve_labels(
    labels: LightCurveVisualLabels | None,
) -> LightCurveVisualLabels:
    """Return explicit labels or the default English labels."""

    if labels is None:
        return _DEFAULT_LABELS

    if not isinstance(labels, LightCurveVisualLabels):
        raise LightCurveVisualError("Labels must be a LightCurveVisualLabels instance.")

    return labels


def _validate_connect_points(
    connect_points: bool,
) -> None:
    """Validate the line-connection setting."""

    if not isinstance(connect_points, bool):
        raise LightCurveVisualError("Connect points must be a boolean value.")


def _value_axis_title(
    light_curve: LightCurve,
    labels: LightCurveVisualLabels,
) -> str:
    """Return the appropriate vertical-axis title."""

    photometry_kind = light_curve.metadata.photometry_kind

    if photometry_kind == "flux":
        return labels.flux_axis

    if photometry_kind == "magnitude":
        return labels.magnitude_axis

    raise LightCurveVisualError(f"Unsupported photometry kind: {photometry_kind!r}.")


def _uncertainty_values(
    light_curve: LightCurve,
) -> tuple[float, ...] | None:
    """Return uncertainty values when the curve contains them."""

    if not light_curve.has_uncertainties:
        return None

    raw_uncertainties = tuple(point.uncertainty for point in light_curve.points)

    if any(uncertainty is None for uncertainty in raw_uncertainties):
        raise LightCurveVisualError("Light-curve uncertainties are incomplete.")

    return tuple(float(uncertainty) for uncertainty in raw_uncertainties if uncertainty is not None)


def _build_trace(
    light_curve: LightCurve,
    *,
    name: str,
    connect_points: bool,
    labels: LightCurveVisualLabels,
) -> go.Scatter:
    """Create one Plotly trace from a light curve."""

    value_axis = _value_axis_title(
        light_curve,
        labels,
    )

    trace_arguments: dict[str, object] = {
        "x": tuple(point.time for point in light_curve.points),
        "y": tuple(point.value for point in light_curve.points),
        "mode": ("lines+markers" if connect_points else "markers"),
        "name": name,
        "hovertemplate": (
            f"{labels.time_axis}: %{{x:.6g}}<br>"
            f"{value_axis}: %{{y:.6g}}"
            "<extra>%{fullData.name}</extra>"
        ),
    }

    uncertainties = _uncertainty_values(light_curve)

    if uncertainties is not None:
        trace_arguments["error_y"] = {
            "type": "data",
            "array": uncertainties,
            "visible": True,
        }

    return go.Scatter(**trace_arguments)


def _configure_figure(
    figure: go.Figure,
    *,
    light_curve: LightCurve,
    title: str,
    labels: LightCurveVisualLabels,
    show_legend: bool,
) -> go.Figure:
    """Apply shared light-curve layout settings."""

    figure.update_layout(
        title=title,
        template="plotly_white",
        hovermode="closest",
        showlegend=show_legend,
        xaxis_title=labels.time_axis,
        yaxis_title=_value_axis_title(
            light_curve,
            labels,
        ),
    )

    if light_curve.metadata.photometry_kind == "magnitude":
        figure.update_yaxes(autorange="reversed")

    return figure


def build_light_curve_figure(
    light_curve: LightCurve,
    *,
    title: str | None = None,
    series_name: str | None = None,
    connect_points: bool = False,
    labels: LightCurveVisualLabels | None = None,
) -> go.Figure:
    """Build a Plotly figure for one astronomical light curve."""

    _validate_connect_points(connect_points)

    resolved_labels = _resolve_labels(labels)
    resolved_title = (
        title if title is not None else (f"{light_curve.metadata.object_name} light curve")
    )
    resolved_series_name = (
        series_name if series_name is not None else light_curve.metadata.object_name
    )

    figure = go.Figure()

    figure.add_trace(
        _build_trace(
            light_curve,
            name=resolved_series_name,
            connect_points=connect_points,
            labels=resolved_labels,
        )
    )

    return _configure_figure(
        figure,
        light_curve=light_curve,
        title=resolved_title,
        labels=resolved_labels,
        show_legend=False,
    )


def build_light_curve_comparison_figure(
    raw_light_curve: LightCurve,
    processed_light_curve: LightCurve,
    *,
    title: str | None = None,
    raw_name: str | None = None,
    processed_name: str | None = None,
    connect_points: bool = False,
    labels: LightCurveVisualLabels | None = None,
) -> go.Figure:
    """Compare raw and processed versions of one light curve."""

    _validate_connect_points(connect_points)

    raw_kind = raw_light_curve.metadata.photometry_kind
    processed_kind = processed_light_curve.metadata.photometry_kind

    if raw_kind != processed_kind:
        raise LightCurveVisualError("Compared light curves must use the same photometry kind.")

    resolved_labels = _resolve_labels(labels)
    resolved_title = (
        title
        if title is not None
        else (f"{raw_light_curve.metadata.object_name} light-curve comparison")
    )

    figure = go.Figure()

    figure.add_trace(
        _build_trace(
            raw_light_curve,
            name=(raw_name if raw_name is not None else resolved_labels.raw_series),
            connect_points=connect_points,
            labels=resolved_labels,
        )
    )

    figure.add_trace(
        _build_trace(
            processed_light_curve,
            name=(
                processed_name if processed_name is not None else resolved_labels.processed_series
            ),
            connect_points=connect_points,
            labels=resolved_labels,
        )
    )

    return _configure_figure(
        figure,
        light_curve=raw_light_curve,
        title=resolved_title,
        labels=resolved_labels,
        show_legend=True,
    )
