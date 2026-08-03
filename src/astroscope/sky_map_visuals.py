"""Plotly presentation for interactive local sky-map results."""

from collections.abc import Mapping
from dataclasses import dataclass

import plotly.graph_objects as go

from astroscope.sky_map import SkyMapPoint, SkyObjectCategory


@dataclass(frozen=True, slots=True)
class SkyMapLabels:
    """Translated labels used by the interactive sky map."""

    title: str
    catalog_trace: str
    solar_system_trace: str
    altitude: str
    azimuth: str
    direction: str
    status: str
    zenith: str
    horizon: str


def create_sky_map_figure(
    points: tuple[SkyMapPoint, ...],
    display_names: Mapping[str, str],
    direction_names: Mapping[str, str],
    status_names: Mapping[str, str],
    labels: SkyMapLabels,
) -> go.Figure:
    """Create an interactive Plotly polar sky map."""

    figure = go.Figure()

    visible_points = tuple(point for point in points if point.is_above_horizon)

    category_settings: tuple[
        tuple[SkyObjectCategory, str, int],
        ...,
    ] = (
        (
            "catalog",
            labels.catalog_trace,
            12,
        ),
        (
            "solar_system",
            labels.solar_system_trace,
            15,
        ),
    )

    for category, trace_name, marker_size in category_settings:
        category_points = tuple(point for point in visible_points if point.category == category)

        if not category_points:
            continue

        custom_data = [
            [
                point.altitude_degrees,
                point.azimuth_degrees,
                direction_names.get(
                    point.cardinal_direction,
                    point.cardinal_direction,
                ),
                status_names.get(
                    point.status,
                    point.status,
                ),
            ]
            for point in category_points
        ]

        figure.add_trace(
            go.Scatterpolar(
                r=[point.radial_distance_degrees for point in category_points],
                theta=[point.azimuth_degrees for point in category_points],
                mode="markers+text",
                text=[
                    display_names.get(
                        point.object_key,
                        point.object_key,
                    )
                    for point in category_points
                ],
                textposition="top center",
                customdata=custom_data,
                marker={
                    "size": marker_size,
                },
                name=trace_name,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{labels.altitude}: "
                    "%{customdata[0]:.2f}°<br>"
                    f"{labels.azimuth}: "
                    "%{customdata[1]:.2f}°<br>"
                    f"{labels.direction}: "
                    "%{customdata[2]}<br>"
                    f"{labels.status}: "
                    "%{customdata[3]}"
                    "<extra></extra>"
                ),
            )
        )

    direction_order = (
        "north",
        "northeast",
        "east",
        "southeast",
        "south",
        "southwest",
        "west",
        "northwest",
    )

    figure.update_layout(
        title=labels.title,
        height=720,
        showlegend=True,
        margin={
            "l": 40,
            "r": 40,
            "t": 80,
            "b": 40,
        },
        polar={
            "radialaxis": {
                "range": [0, 90],
                "tickmode": "array",
                "tickvals": [0, 30, 60, 90],
                "ticktext": [
                    labels.zenith,
                    "60°",
                    "30°",
                    labels.horizon,
                ],
            },
            "angularaxis": {
                "rotation": 90,
                "direction": "clockwise",
                "tickmode": "array",
                "tickvals": [
                    0,
                    45,
                    90,
                    135,
                    180,
                    225,
                    270,
                    315,
                ],
                "ticktext": [
                    direction_names.get(
                        direction,
                        direction,
                    )
                    for direction in direction_order
                ],
            },
        },
    )

    return figure
