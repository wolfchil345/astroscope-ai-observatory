"""Tests for weather-aware observing conditions."""

from datetime import date, time
from urllib.parse import parse_qs, urlparse

import pytest

import astroscope.weather as weather_module
from astroscope.weather import (
    WeatherServiceError,
    build_weather_forecast_url,
    calculate_weather_score,
    classify_dew_risk,
    classify_weather_rating,
    fetch_observing_weather,
    parse_weather_payload,
)


def sample_weather_payload() -> dict[str, object]:
    """Create deterministic hourly weather data."""

    return {
        "latitude": 34.69,
        "longitude": 135.50,
        "timezone": "Asia/Tokyo",
        "hourly": {
            "time": [
                "2024-01-01T20:00",
                "2024-01-01T21:00",
                "2024-01-02T00:00",
                "2024-01-02T04:00",
            ],
            "temperature_2m": [
                10.0,
                9.0,
                7.0,
                5.0,
            ],
            "relative_humidity_2m": [
                60.0,
                65.0,
                82.0,
                96.0,
            ],
            "dew_point_2m": [
                2.0,
                3.0,
                4.0,
                4.5,
            ],
            "precipitation_probability": [
                0.0,
                5.0,
                20.0,
                90.0,
            ],
            "precipitation": [
                0.0,
                0.0,
                0.0,
                1.0,
            ],
            "cloud_cover": [
                5.0,
                15.0,
                50.0,
                100.0,
            ],
            "visibility": [
                24_000.0,
                20_000.0,
                12_000.0,
                500.0,
            ],
            "wind_speed_10m": [
                5.0,
                8.0,
                15.0,
                35.0,
            ],
            "wind_gusts_10m": [
                10.0,
                15.0,
                25.0,
                70.0,
            ],
        },
    }


def test_clear_weather_scores_higher_than_stormy_weather() -> None:
    clear_score = calculate_weather_score(
        cloud_cover_percent=5.0,
        precipitation_probability_percent=0.0,
        precipitation_mm=0.0,
        visibility_m=25_000.0,
        relative_humidity_percent=55.0,
        wind_speed_kmh=5.0,
        wind_gusts_kmh=10.0,
    )

    stormy_score = calculate_weather_score(
        cloud_cover_percent=100.0,
        precipitation_probability_percent=95.0,
        precipitation_mm=3.0,
        visibility_m=500.0,
        relative_humidity_percent=98.0,
        wind_speed_kmh=45.0,
        wind_gusts_kmh=70.0,
    )

    assert clear_score > stormy_score
    assert clear_score >= 80.0
    assert stormy_score <= 20.0


@pytest.mark.parametrize(
    (
        "temperature",
        "dew_point",
        "humidity",
        "expected",
    ),
    [
        (10.0, 2.0, 50.0, "low"),
        (10.0, 6.0, 82.0, "moderate"),
        (10.0, 8.0, 91.0, "high"),
        (10.0, 9.5, 96.0, "critical"),
    ],
)
def test_dew_risk_classification(
    temperature: float,
    dew_point: float,
    humidity: float,
    expected: str,
) -> None:
    result = classify_dew_risk(
        temperature_c=temperature,
        dew_point_c=dew_point,
        relative_humidity_percent=humidity,
    )

    assert result == expected


@pytest.mark.parametrize(
    (
        "score",
        "precipitation",
        "gusts",
        "expected",
    ),
    [
        (90.0, 0.0, 10.0, "excellent"),
        (70.0, 0.0, 10.0, "good"),
        (55.0, 0.0, 10.0, "fair"),
        (35.0, 0.0, 10.0, "poor"),
        (20.0, 0.0, 10.0, "unsuitable"),
        (80.0, 1.0, 10.0, "unsuitable"),
        (80.0, 0.0, 70.0, "unsuitable"),
    ],
)
def test_weather_rating(
    score: float,
    precipitation: float,
    gusts: float,
    expected: str,
) -> None:
    result = classify_weather_rating(
        score,
        precipitation_mm=precipitation,
        wind_gusts_kmh=gusts,
    )

    assert result == expected


def test_weather_url_contains_required_parameters() -> None:
    url = build_weather_forecast_url(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
    )

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    assert parsed_url.path == "/v1/forecast"
    assert query["timezone"] == ["Asia/Tokyo"]
    assert query["start_date"] == ["2024-01-01"]
    assert query["end_date"] == ["2024-01-02"]

    hourly_variables = query["hourly"][0]

    assert "cloud_cover" in hourly_variables
    assert "visibility" in hourly_variables
    assert "dew_point_2m" in hourly_variables


def test_weather_payload_is_parsed() -> None:
    points = parse_weather_payload(
        sample_weather_payload(),
        timezone_name="Asia/Tokyo",
    )

    assert len(points) == 4

    first_point = points[0]
    final_point = points[-1]

    assert first_point.local_datetime.hour == 20
    assert first_point.observing_score > (final_point.observing_score)
    assert first_point.dew_risk == "low"
    assert final_point.dew_risk == "critical"
    assert final_point.rating == "unsuitable"


def test_api_error_payload_raises_error() -> None:
    with pytest.raises(
        WeatherServiceError,
        match="Forecast date is out of range",
    ):
        parse_weather_payload(
            {
                "error": True,
                "reason": ("Forecast date is out of range"),
            },
            timezone_name="Asia/Tokyo",
        )


def test_cross_midnight_weather_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        weather_module,
        "load_weather_payload",
        lambda url, timeout_seconds=10.0: sample_weather_payload(),
    )

    result = fetch_observing_weather(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(4, 0),
    )

    assert len(result.points) == 4
    assert result.points[0].local_datetime.date() == (date(2024, 1, 1))
    assert result.points[-1].local_datetime.date() == (date(2024, 1, 2))

    assert result.best_point.local_datetime.hour == 20
    assert result.worst_dew_risk == "critical"
    assert result.maximum_cloud_cover_percent == 100.0
    assert 0.0 <= result.average_score <= 100.0


def test_equal_start_and_end_time_raise_error() -> None:
    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        fetch_observing_weather(
            latitude_deg=34.6937,
            longitude_deg=135.5023,
            elevation_m=15.0,
            timezone_name="Asia/Tokyo",
            local_date=date(2024, 1, 1),
            start_time=time(20, 0),
            end_time=time(20, 0),
        )
