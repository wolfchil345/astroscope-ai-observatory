"""Plotly presentation for observation-schedule results."""

from collections.abc import Mapping
from dataclasses import dataclass

import plotly.graph_objects as go

from astroscope.schedule import TimelinePoint


@dataclass(frozen=True, slots=True)
class ScheduleChartLabels:
    """Translated labels for the score timeline."""

    title: str
    time_axis: str
    score_axis: str
    altitude: str
    moon_separation: str
    rating: str
    recommended: str
    yes: str
    no: str


def create_schedule_figure(
    points: tuple[TimelinePoint, ...],
    display_names: Mapping[str, str],
    rating_names: Mapping[str, str],
    labels: ScheduleChartLabels,
) -> go.Figure:
    """Create an interactive score timeline."""

    figure = go.Figure()

    object_keys = sorted(
        {point.object_key for point in points},
        key=lambda key: display_names.get(key, key),
    )

    for object_key in object_keys:
        object_points = sorted(
            (point for point in points if point.object_key == object_key),
            key=lambda point: point.utc_datetime_iso,
        )

        figure.add_trace(
            go.Scatter(
                x=[point.local_datetime_iso for point in object_points],
                y=[point.total_score for point in object_points],
                mode="lines+markers",
                name=display_names.get(
                    object_key,
                    object_key,
                ),
                customdata=[
                    [
                        point.altitude_degrees,
                        point.moon_separation_degrees,
                        rating_names.get(
                            point.rating,
                            point.rating,
                        ),
                        (labels.yes if point.recommended else labels.no),
                    ]
                    for point in object_points
                ],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{x}<br>"
                    f"{labels.score_axis}: "
                    "%{y:.1f}<br>"
                    f"{labels.altitude}: "
                    "%{customdata[0]:.2f}°<br>"
                    f"{labels.moon_separation}: "
                    "%{customdata[1]:.2f}°<br>"
                    f"{labels.rating}: "
                    "%{customdata[2]}<br>"
                    f"{labels.recommended}: "
                    "%{customdata[3]}"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        title=labels.title,
        height=620,
        hovermode="x unified",
        xaxis={
            "title": labels.time_axis,
            "type": "date",
        },
        yaxis={
            "title": labels.score_axis,
            "range": [0, 100],
        },
        margin={
            "l": 40,
            "r": 40,
            "t": 70,
            "b": 40,
        },
    )

    return figure
