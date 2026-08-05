"""Interactive charts for observing-weather forecasts."""

from dataclasses import dataclass
from datetime import UTC

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from astroscope.weather import WeatherForecastPoint


@dataclass(frozen=True, slots=True)
class WeatherChartLabels:
    """Translated labels used by weather charts."""

    score_title: str
    conditions_title: str
    time_axis: str
    score_axis: str
    cloud_cover: str
    precipitation_probability: str
    precipitation_amount: str
    humidity: str
    wind_speed: str
    rating: str
    dew_risk: str


def create_weather_score_figure(
    points: tuple[WeatherForecastPoint, ...],
    labels: WeatherChartLabels,
    rating_names: dict[str, str],
    dew_risk_names: dict[str, str],
) -> go.Figure:
    """Create an interactive observing-score timeline."""

    ordered_points = tuple(
        sorted(
            points,
            key=lambda point: (
                point.utc_datetime
                if point.utc_datetime is not None
                else point.local_datetime.astimezone(UTC)
            ),
        )
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=[point.local_datetime for point in ordered_points],
            y=[point.observing_score for point in ordered_points],
            mode="lines+markers",
            name=labels.score_axis,
            customdata=[
                [
                    point.cloud_cover_percent,
                    point.relative_humidity_percent,
                    point.wind_speed_kmh,
                    rating_names.get(
                        point.rating,
                        point.rating,
                    ),
                    dew_risk_names.get(
                        point.dew_risk,
                        point.dew_risk,
                    ),
                ]
                for point in ordered_points
            ],
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"{labels.score_axis}: "
                "%{y:.1f}<br>"
                f"{labels.cloud_cover}: "
                "%{customdata[0]:.1f}%<br>"
                f"{labels.humidity}: "
                "%{customdata[1]:.1f}%<br>"
                f"{labels.wind_speed}: "
                "%{customdata[2]:.1f} km/h<br>"
                f"{labels.rating}: "
                "%{customdata[3]}<br>"
                f"{labels.dew_risk}: "
                "%{customdata[4]}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title=labels.score_title,
        height=500,
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


def create_weather_conditions_figure(
    points: tuple[WeatherForecastPoint, ...],
    labels: WeatherChartLabels,
) -> go.Figure:
    """Create cloud and precipitation forecast charts."""

    ordered_points = tuple(
        sorted(
            points,
            key=lambda point: (
                point.utc_datetime
                if point.utc_datetime is not None
                else point.local_datetime.astimezone(UTC)
            ),
        )
    )

    figure = make_subplots(
        specs=[
            [
                {
                    "secondary_y": True,
                }
            ]
        ]
    )

    figure.add_trace(
        go.Scatter(
            x=[point.local_datetime for point in ordered_points],
            y=[point.cloud_cover_percent for point in ordered_points],
            mode="lines+markers",
            name=labels.cloud_cover,
            hovertemplate=(f"<b>%{{x}}</b><br>{labels.cloud_cover}: %{{y:.1f}}%<extra></extra>"),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Scatter(
            x=[point.local_datetime for point in ordered_points],
            y=[point.precipitation_probability_percent for point in ordered_points],
            mode="lines+markers",
            name=labels.precipitation_probability,
            hovertemplate=(
                f"<b>%{{x}}</b><br>{labels.precipitation_probability}: %{{y:.1f}}%<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Bar(
            x=[point.local_datetime for point in ordered_points],
            y=[point.precipitation_mm for point in ordered_points],
            name=labels.precipitation_amount,
            opacity=0.45,
            hovertemplate=(
                f"<b>%{{x}}</b><br>{labels.precipitation_amount}: %{{y:.2f}} mm<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    figure.update_xaxes(
        title_text=labels.time_axis,
    )

    figure.update_yaxes(
        title_text="%",
        range=[0, 100],
        secondary_y=False,
    )

    figure.update_yaxes(
        title_text="mm",
        rangemode="tozero",
        secondary_y=True,
    )

    figure.update_layout(
        title=labels.conditions_title,
        height=520,
        hovermode="x unified",
        barmode="overlay",
        margin={
            "l": 40,
            "r": 40,
            "t": 70,
            "b": 40,
        },
    )

    return figure
