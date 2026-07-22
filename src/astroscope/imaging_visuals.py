"""Astrophotography sensor-frame and mosaic visualizations."""

from dataclasses import dataclass
from math import cos, isfinite, radians, sin
from typing import Final

import plotly.graph_objects as go

from astroscope.imaging import (
    ImagingTargetSpec,
    TargetFramingResult,
)


@dataclass(frozen=True, slots=True)
class ImagingFrameLabels:
    """Translated labels for an imaging-frame diagram."""

    title: str
    horizontal_axis: str
    vertical_axis: str
    target: str
    sensor_panel: str
    rotation: str
    mosaic: str


DEFAULT_FIGURE_MARGIN: Final[dict[str, int]] = {
    "l": 50,
    "r": 50,
    "t": 85,
    "b": 50,
}


def _validate_positive_finite(
    value: float,
    label: str,
) -> None:
    """Require a positive finite number."""

    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be a positive finite number.")


def _validate_rotation(
    rotation_degrees: float,
) -> None:
    """Require a finite rotation angle."""

    if not isfinite(rotation_degrees):
        raise ValueError("Sensor rotation must be finite.")


def _rotate_point(
    x_value: float,
    y_value: float,
    angle_radians: float,
) -> tuple[float, float]:
    """Rotate one point around the origin."""

    rotated_x = x_value * cos(angle_radians) - y_value * sin(angle_radians)

    rotated_y = x_value * sin(angle_radians) + y_value * cos(angle_radians)

    return rotated_x, rotated_y


def rectangle_vertices(
    *,
    width_degrees: float,
    height_degrees: float,
    center_x: float = 0.0,
    center_y: float = 0.0,
    rotation_degrees: float = 0.0,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return closed vertices for a rotated rectangle."""

    _validate_positive_finite(
        width_degrees,
        "Rectangle width",
    )

    _validate_positive_finite(
        height_degrees,
        "Rectangle height",
    )

    _validate_rotation(rotation_degrees)

    half_width = width_degrees / 2.0
    half_height = height_degrees / 2.0

    local_vertices = (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
        (-half_width, -half_height),
    )

    angle_radians = radians(rotation_degrees % 180.0)

    x_values: list[float] = []
    y_values: list[float] = []

    for x_value, y_value in local_vertices:
        rotated_x, rotated_y = _rotate_point(
            x_value,
            y_value,
            angle_radians,
        )

        x_values.append(rotated_x + center_x)

        y_values.append(rotated_y + center_y)

    return tuple(x_values), tuple(y_values)


def create_imaging_frame_figure(
    *,
    field_width_degrees: float,
    field_height_degrees: float,
    target: ImagingTargetSpec,
    framing: TargetFramingResult,
    rotation_degrees: float,
    target_name: str,
    labels: ImagingFrameLabels,
) -> go.Figure:
    """Create a rotated sensor-frame and mosaic diagram."""

    _validate_positive_finite(
        field_width_degrees,
        "Field width",
    )

    _validate_positive_finite(
        field_height_degrees,
        "Field height",
    )

    _validate_rotation(rotation_degrees)

    if framing.target != target:
        raise ValueError("Framing result and target must match.")

    target_x, target_y = rectangle_vertices(
        width_degrees=target.width_degrees,
        height_degrees=target.height_degrees,
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=target_x,
            y=target_y,
            mode="lines",
            fill="toself",
            opacity=0.35,
            name=f"{labels.target}: {target_name}",
            hovertemplate=(
                f"<b>{target_name}</b><br>"
                f"{target.width_degrees:.3f}° × "
                f"{target.height_degrees:.3f}°"
                "<extra></extra>"
            ),
        )
    )

    overlap_fraction = framing.overlap_percent / 100.0

    horizontal_step = field_width_degrees * (1.0 - overlap_fraction)

    vertical_step = field_height_degrees * (1.0 - overlap_fraction)

    rotation_radians = radians(rotation_degrees % 180.0)

    plotted_x_values = list(target_x)
    plotted_y_values = list(target_y)

    panel_number = 0

    for row_index in range(framing.panels_vertical):
        unrotated_center_y = ((framing.panels_vertical - 1) / 2.0 - row_index) * vertical_step

        for column_index in range(framing.panels_horizontal):
            panel_number += 1

            unrotated_center_x = (
                column_index - (framing.panels_horizontal - 1) / 2.0
            ) * horizontal_step

            center_x, center_y = _rotate_point(
                unrotated_center_x,
                unrotated_center_y,
                rotation_radians,
            )

            panel_x, panel_y = rectangle_vertices(
                width_degrees=field_width_degrees,
                height_degrees=field_height_degrees,
                center_x=center_x,
                center_y=center_y,
                rotation_degrees=rotation_degrees,
            )

            plotted_x_values.extend(panel_x)
            plotted_y_values.extend(panel_y)

            figure.add_trace(
                go.Scatter(
                    x=panel_x,
                    y=panel_y,
                    mode="lines",
                    fill="toself",
                    opacity=0.18,
                    name=(f"{labels.sensor_panel} {panel_number}"),
                    showlegend=panel_number == 1,
                    hovertemplate=(
                        f"<b>{labels.sensor_panel} "
                        f"{panel_number}</b><br>"
                        f"{field_width_degrees:.3f}° × "
                        f"{field_height_degrees:.3f}°<br>"
                        f"{labels.rotation}: "
                        f"{rotation_degrees:.1f}°"
                        "<extra></extra>"
                    ),
                )
            )

    maximum_extent = max(
        max(abs(value) for value in plotted_x_values),
        max(abs(value) for value in plotted_y_values),
        0.1,
    )

    plot_extent = maximum_extent * 1.20

    figure.add_annotation(
        x=0.0,
        y=plot_extent * 0.94,
        text=(
            f"{labels.mosaic}: "
            f"{framing.panels_horizontal} × "
            f"{framing.panels_vertical} = "
            f"{framing.total_panels}"
        ),
        showarrow=False,
    )

    figure.update_layout(
        title=labels.title,
        height=650,
        xaxis={
            "title": labels.horizontal_axis,
            "range": [
                -plot_extent,
                plot_extent,
            ],
            "zeroline": True,
        },
        yaxis={
            "title": labels.vertical_axis,
            "range": [
                -plot_extent,
                plot_extent,
            ],
            "scaleanchor": "x",
            "scaleratio": 1,
            "zeroline": True,
        },
        margin=DEFAULT_FIGURE_MARGIN,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0.0,
        },
    )

    return figure
