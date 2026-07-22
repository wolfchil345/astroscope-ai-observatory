"""Field-of-view visualization for telescope simulations."""

from dataclasses import dataclass
from math import isfinite
from typing import Final, Literal

import plotly.graph_objects as go

TargetFit = Literal[
    "comfortable",
    "tight",
    "too_large",
]


@dataclass(frozen=True, slots=True)
class AngularSizeTarget:
    """Approximate apparent angular size of one target."""

    key: str
    major_axis_degrees: float
    minor_axis_degrees: float

    def __post_init__(self) -> None:
        values = {
            "Major angular size": self.major_axis_degrees,
            "Minor angular size": self.minor_axis_degrees,
        }

        for label, value in values.items():
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{label} must be a positive finite number.")


@dataclass(frozen=True, slots=True)
class FieldOfViewLabels:
    """Translated labels used by the visualizer."""

    title: str
    angular_distance: str
    field_of_view: str
    target: str
    target_size: str
    fit: str


ANGULAR_SIZE_PRESETS: Final[dict[str, AngularSizeTarget]] = {
    "moon": AngularSizeTarget(
        key="moon",
        major_axis_degrees=0.50,
        minor_axis_degrees=0.50,
    ),
    "m31": AngularSizeTarget(
        key="m31",
        major_axis_degrees=3.10,
        minor_axis_degrees=1.00,
    ),
    "pleiades": AngularSizeTarget(
        key="pleiades",
        major_axis_degrees=1.80,
        minor_axis_degrees=1.80,
    ),
    "orion_nebula": AngularSizeTarget(
        key="orion_nebula",
        major_axis_degrees=1.10,
        minor_axis_degrees=1.00,
    ),
}


def classify_target_fit(
    true_field_degrees: float,
    target: AngularSizeTarget,
) -> TargetFit:
    """Classify whether a target fits inside the field."""

    if not isfinite(true_field_degrees) or true_field_degrees <= 0.0:
        raise ValueError("True field of view must be a positive finite number.")

    comfortable_limit = true_field_degrees * 0.80

    if (
        target.major_axis_degrees <= comfortable_limit
        and target.minor_axis_degrees <= comfortable_limit
    ):
        return "comfortable"

    if (
        target.major_axis_degrees <= true_field_degrees
        and target.minor_axis_degrees <= true_field_degrees
    ):
        return "tight"

    return "too_large"


def create_field_of_view_figure(
    *,
    true_field_degrees: float,
    target: AngularSizeTarget,
    target_name: str,
    fit_name: str,
    labels: FieldOfViewLabels,
) -> go.Figure:
    """Create a telescope field and target-size diagram."""

    if not isfinite(true_field_degrees) or true_field_degrees <= 0.0:
        raise ValueError("True field of view must be a positive finite number.")

    field_radius = true_field_degrees / 2.0
    target_horizontal_radius = target.major_axis_degrees / 2.0
    target_vertical_radius = target.minor_axis_degrees / 2.0

    plot_extent = max(
        field_radius * 1.20,
        target_horizontal_radius * 1.20,
        target_vertical_radius * 1.20,
        0.10,
    )

    figure = go.Figure()

    figure.add_shape(
        type="circle",
        x0=-field_radius,
        y0=-field_radius,
        x1=field_radius,
        y1=field_radius,
        line={
            "width": 3,
        },
    )

    figure.add_shape(
        type="circle",
        x0=-target_horizontal_radius,
        y0=-target_vertical_radius,
        x1=target_horizontal_radius,
        y1=target_vertical_radius,
        line={
            "width": 3,
            "dash": "dot",
        },
    )

    figure.add_trace(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers",
            marker={
                "size": 8,
                "opacity": 0.0,
            },
            name=target_name,
            customdata=[
                [
                    true_field_degrees,
                    target.major_axis_degrees,
                    target.minor_axis_degrees,
                    fit_name,
                ]
            ],
            hovertemplate=(
                f"<b>{target_name}</b><br>"
                f"{labels.field_of_view}: "
                "%{customdata[0]:.3f}°<br>"
                f"{labels.target_size}: "
                "%{customdata[1]:.3f}° × "
                "%{customdata[2]:.3f}°<br>"
                f"{labels.fit}: "
                "%{customdata[3]}"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    figure.add_annotation(
        x=0.0,
        y=field_radius,
        text=(f"{labels.field_of_view}: {true_field_degrees:.3f}°"),
        showarrow=False,
        yshift=22,
    )

    figure.add_annotation(
        x=0.0,
        y=0.0,
        text=target_name,
        showarrow=False,
    )

    figure.update_layout(
        title=labels.title,
        height=600,
        xaxis={
            "title": labels.angular_distance,
            "range": [-plot_extent, plot_extent],
            "zeroline": True,
        },
        yaxis={
            "title": labels.angular_distance,
            "range": [-plot_extent, plot_extent],
            "scaleanchor": "x",
            "scaleratio": 1,
            "zeroline": True,
        },
        margin={
            "l": 50,
            "r": 50,
            "t": 80,
            "b": 50,
        },
        showlegend=False,
    )

    return figure
