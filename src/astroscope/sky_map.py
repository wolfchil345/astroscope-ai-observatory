"""Interactive local sky-map calculations and Plotly rendering."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time
from typing import Literal

import plotly.graph_objects as go

from astroscope.coordinates import CELESTIAL_PRESETS
from astroscope.solar_system import (
    SOLAR_SYSTEM_BODIES,
    calculate_solar_system_body,
)
from astroscope.visibility import (
    VisibilityStatus,
    calculate_horizontal_coordinates,
)

SkyObjectCategory = Literal["catalog", "solar_system"]


@dataclass(frozen=True, slots=True)
class SkyMapPoint:
    """One celestial object plotted in the observer's local sky."""

    object_key: str
    category: SkyObjectCategory
    altitude_degrees: float
    azimuth_degrees: float
    radial_distance_degrees: float
    cardinal_direction: str
    status: VisibilityStatus
    is_above_horizon: bool


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


def altitude_to_radial_distance(
    altitude_degrees: float,
) -> float:
    """Convert altitude into distance from the chart centre."""

    if not -90.0 <= altitude_degrees <= 90.0:
        raise ValueError("Altitude must be between -90 and 90 degrees.")

    return 90.0 - altitude_degrees


def calculate_sky_map_points(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    minimum_altitude_degrees: float = 20.0,
    include_catalog_objects: bool = True,
    include_solar_system_objects: bool = True,
) -> tuple[SkyMapPoint, ...]:
    """Calculate local sky positions for all selected object groups."""

    points: list[SkyMapPoint] = []

    if include_catalog_objects:
        for object_key, preset in CELESTIAL_PRESETS.items():
            result = calculate_horizontal_coordinates(
                right_ascension=preset.right_ascension,
                declination=preset.declination,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            points.append(
                SkyMapPoint(
                    object_key=object_key,
                    category="catalog",
                    altitude_degrees=result.altitude_degrees,
                    azimuth_degrees=result.azimuth_degrees,
                    radial_distance_degrees=(altitude_to_radial_distance(result.altitude_degrees)),
                    cardinal_direction=(result.cardinal_direction),
                    status=result.status,
                    is_above_horizon=(result.is_above_horizon),
                )
            )

    if include_solar_system_objects:
        for body_key in SOLAR_SYSTEM_BODIES:
            result = calculate_solar_system_body(
                body=body_key,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            points.append(
                SkyMapPoint(
                    object_key=body_key,
                    category="solar_system",
                    altitude_degrees=result.altitude_degrees,
                    azimuth_degrees=result.azimuth_degrees,
                    radial_distance_degrees=(altitude_to_radial_distance(result.altitude_degrees)),
                    cardinal_direction=(result.cardinal_direction),
                    status=result.status,
                    is_above_horizon=(result.is_above_horizon),
                )
            )

    return tuple(points)


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
