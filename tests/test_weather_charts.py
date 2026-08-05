"""Tests for observing-weather visualizations."""

from dataclasses import replace
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from astroscope.weather import WeatherForecastPoint
from astroscope.weather_charts import (
    WeatherChartLabels,
    create_weather_conditions_figure,
    create_weather_score_figure,
)


def create_test_point(
    hour: int,
    score: float,
    cloud_cover: float,
    precipitation_probability: float,
    precipitation_mm: float,
) -> WeatherForecastPoint:
    """Create one deterministic forecast point."""

    local_datetime = datetime(
        2024,
        1,
        1,
        hour,
        0,
        tzinfo=ZoneInfo("Asia/Tokyo"),
    )

    return WeatherForecastPoint(
        local_datetime=local_datetime,
        temperature_c=8.0,
        relative_humidity_percent=70.0,
        dew_point_c=3.0,
        dew_point_spread_c=5.0,
        precipitation_probability_percent=(precipitation_probability),
        precipitation_mm=precipitation_mm,
        cloud_cover_percent=cloud_cover,
        visibility_m=20_000.0,
        wind_speed_kmh=8.0,
        wind_gusts_kmh=15.0,
        observing_score=score,
        rating="good",
        dew_risk="moderate",
        utc_datetime=local_datetime.astimezone(UTC),
    )


def create_labels() -> WeatherChartLabels:
    """Create English chart labels for testing."""

    return WeatherChartLabels(
        score_title="Observing score",
        conditions_title="Weather conditions",
        time_axis="Time",
        score_axis="Score",
        cloud_cover="Cloud cover",
        precipitation_probability=("Precipitation probability"),
        precipitation_amount="Precipitation",
        humidity="Humidity",
        wind_speed="Wind speed",
        rating="Rating",
        dew_risk="Dew risk",
    )


def test_weather_score_chart_sorts_points() -> None:
    points = (
        replace(
            create_test_point(
                hour=22,
                score=60.0,
                cloud_cover=40.0,
                precipitation_probability=20.0,
                precipitation_mm=0.0,
            ),
            utc_datetime=datetime(2024, 1, 1, 11, tzinfo=UTC),
        ),
        replace(
            create_test_point(
                hour=20,
                score=85.0,
                cloud_cover=10.0,
                precipitation_probability=0.0,
                precipitation_mm=0.0,
            ),
            utc_datetime=datetime(2024, 1, 1, 12, tzinfo=UTC),
        ),
    )

    figure = create_weather_score_figure(
        points=points,
        labels=create_labels(),
        rating_names={"good": "Good"},
        dew_risk_names={"moderate": "Moderate"},
    )

    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [60.0, 85.0]

    plotted_hours = [value.hour for value in figure.data[0].x]

    assert plotted_hours == [22, 20]
    assert list(figure.layout.yaxis.range) == [0, 100]


def test_weather_conditions_chart_has_three_traces() -> None:
    points = (
        create_test_point(
            hour=20,
            score=85.0,
            cloud_cover=10.0,
            precipitation_probability=5.0,
            precipitation_mm=0.0,
        ),
        create_test_point(
            hour=21,
            score=50.0,
            cloud_cover=60.0,
            precipitation_probability=70.0,
            precipitation_mm=1.5,
        ),
    )

    figure = create_weather_conditions_figure(
        points=points,
        labels=create_labels(),
    )

    assert len(figure.data) == 3

    trace_names = {trace.name for trace in figure.data}

    assert trace_names == {
        "Cloud cover",
        "Precipitation probability",
        "Precipitation",
    }

    assert list(figure.data[0].y) == [10.0, 60.0]
    assert list(figure.data[1].y) == [5.0, 70.0]
    assert list(figure.data[2].y) == [0.0, 1.5]


def test_weather_charts_use_short_margin_keys() -> None:
    figure = create_weather_score_figure(
        points=(),
        labels=create_labels(),
        rating_names={},
        dew_risk_names={},
    )

    assert figure.layout.margin.l == 40
    assert figure.layout.margin.r == 40
    assert figure.layout.margin.t == 70
    assert figure.layout.margin.b == 40
