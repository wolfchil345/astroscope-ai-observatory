"""Weather-aware observing-condition forecasts."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from math import isfinite
from typing import Any, Final, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from astroscope.observer import get_timezone

WeatherRating = Literal[
    "excellent",
    "good",
    "fair",
    "poor",
    "unsuitable",
]

DewRisk = Literal[
    "low",
    "moderate",
    "high",
    "critical",
]

OPEN_METEO_FORECAST_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"

HOURLY_WEATHER_VARIABLES: Final[tuple[str, ...]] = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation_probability",
    "precipitation",
    "cloud_cover",
    "visibility",
    "wind_speed_10m",
    "wind_gusts_10m",
)

DEW_RISK_ORDER: Final[dict[DewRisk, int]] = {
    "low": 0,
    "moderate": 1,
    "high": 2,
    "critical": 3,
}


class WeatherServiceError(RuntimeError):
    """Raised when weather data cannot be retrieved or parsed."""


@dataclass(frozen=True, slots=True)
class WeatherForecastPoint:
    """Observing conditions for one local forecast hour."""

    local_datetime: datetime
    temperature_c: float
    relative_humidity_percent: float
    dew_point_c: float
    dew_point_spread_c: float
    precipitation_probability_percent: float
    precipitation_mm: float
    cloud_cover_percent: float
    visibility_m: float
    wind_speed_kmh: float
    wind_gusts_kmh: float
    observing_score: float
    rating: WeatherRating
    dew_risk: DewRisk


@dataclass(frozen=True, slots=True)
class WeatherForecastResult:
    """Summary and hourly points for one observing window."""

    points: tuple[WeatherForecastPoint, ...]
    best_point: WeatherForecastPoint
    average_score: float
    maximum_cloud_cover_percent: float
    worst_dew_risk: DewRisk
    start_local_iso: str
    end_local_iso: str
    source_name: str


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """Restrict a value to a closed numeric interval."""

    return max(minimum, min(maximum, value))


def validate_percentage(
    value: float,
    label: str,
) -> None:
    """Validate a percentage value."""

    if not isfinite(value) or not 0.0 <= value <= 100.0:
        raise ValueError(f"{label} must be between 0 and 100.")


def classify_dew_risk(
    temperature_c: float,
    dew_point_c: float,
    relative_humidity_percent: float,
) -> DewRisk:
    """Classify condensation risk using dew spread and humidity."""

    validate_percentage(
        relative_humidity_percent,
        "Relative humidity",
    )

    dew_point_spread = temperature_c - dew_point_c

    if dew_point_spread <= 1.0 or relative_humidity_percent >= 95.0:
        return "critical"

    if dew_point_spread <= 2.5 or relative_humidity_percent >= 90.0:
        return "high"

    if dew_point_spread <= 5.0 or relative_humidity_percent >= 80.0:
        return "moderate"

    return "low"


def calculate_weather_score(
    *,
    cloud_cover_percent: float,
    precipitation_probability_percent: float,
    precipitation_mm: float,
    visibility_m: float,
    relative_humidity_percent: float,
    wind_speed_kmh: float,
    wind_gusts_kmh: float,
) -> float:
    """Calculate a transparent zero-to-100 weather score."""

    validate_percentage(
        cloud_cover_percent,
        "Cloud cover",
    )

    validate_percentage(
        precipitation_probability_percent,
        "Precipitation probability",
    )

    validate_percentage(
        relative_humidity_percent,
        "Relative humidity",
    )

    non_negative_values = {
        "Precipitation": precipitation_mm,
        "Visibility": visibility_m,
        "Wind speed": wind_speed_kmh,
        "Wind gusts": wind_gusts_kmh,
    }

    for label, value in non_negative_values.items():
        if not isfinite(value) or value < 0.0:
            raise ValueError(f"{label} must be a non-negative finite number.")

    cloud_score = 40.0 * (1.0 - cloud_cover_percent / 100.0)

    precipitation_score = 25.0 * (1.0 - precipitation_probability_percent / 100.0)

    visibility_score = 15.0 * clamp(
        visibility_m / 20_000.0,
        0.0,
        1.0,
    )

    humidity_score = 10.0 * clamp(
        (95.0 - relative_humidity_percent) / 35.0,
        0.0,
        1.0,
    )

    wind_score = 10.0 * clamp(
        (40.0 - wind_speed_kmh) / 30.0,
        0.0,
        1.0,
    )

    total_score = cloud_score + precipitation_score + visibility_score + humidity_score + wind_score

    if precipitation_mm >= 0.5:
        total_score = min(
            total_score,
            25.0,
        )

    if wind_gusts_kmh >= 60.0:
        total_score = min(
            total_score,
            20.0,
        )

    return round(
        clamp(
            total_score,
            0.0,
            100.0,
        ),
        1,
    )


def classify_weather_rating(
    score: float,
    *,
    precipitation_mm: float,
    wind_gusts_kmh: float,
) -> WeatherRating:
    """Convert a weather score into an observing rating."""

    if not 0.0 <= score <= 100.0:
        raise ValueError("Weather score must be between 0 and 100.")

    if precipitation_mm >= 0.5 or wind_gusts_kmh >= 60.0:
        return "unsuitable"

    if score >= 80.0:
        return "excellent"

    if score >= 65.0:
        return "good"

    if score >= 50.0:
        return "fair"

    if score >= 30.0:
        return "poor"

    return "unsuitable"


def build_weather_forecast_url(
    *,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    start_date: date,
    end_date: date,
) -> str:
    """Build an Open-Meteo hourly forecast URL."""

    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")

    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    if end_date < start_date:
        raise ValueError("Weather end date cannot precede the start date.")

    get_timezone(timezone_name)

    parameters = {
        "latitude": f"{latitude_deg:.6f}",
        "longitude": f"{longitude_deg:.6f}",
        "elevation": f"{elevation_m:.1f}",
        "hourly": ",".join(HOURLY_WEATHER_VARIABLES),
        "timezone": timezone_name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    return f"{OPEN_METEO_FORECAST_URL}?{urlencode(parameters)}"


def load_weather_payload(
    url: str,
    timeout_seconds: float = 10.0,
) -> Mapping[str, Any]:
    """Retrieve one JSON response from the weather service."""

    request = Request(
        url,
        headers={"User-Agent": ("AstroScope-AI-Observatory/1.0")},
    )

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            response_text = response.read().decode("utf-8")

        payload = json.loads(response_text)

    except (
        HTTPError,
        URLError,
        TimeoutError,
    ) as error:
        raise WeatherServiceError("Could not retrieve the weather forecast.") from error

    except json.JSONDecodeError as error:
        raise WeatherServiceError("The weather service returned invalid JSON.") from error

    if not isinstance(payload, Mapping):
        raise WeatherServiceError("The weather service returned an unexpected response.")

    return payload


def require_float(
    value: Any,
    label: str,
) -> float:
    """Convert one required API value into a finite float."""

    try:
        converted_value = float(value)

    except (TypeError, ValueError) as error:
        raise WeatherServiceError(f"Weather field {label!r} is missing or invalid.") from error

    if not isfinite(converted_value):
        raise WeatherServiceError(f"Weather field {label!r} must be finite.")

    return converted_value


def require_series(
    hourly: Mapping[str, Any],
    key: str,
) -> list[Any]:
    """Return one required hourly data series."""

    value = hourly.get(key)

    if not isinstance(value, list):
        raise WeatherServiceError(f"Weather response is missing hourly field {key!r}.")

    return value


def parse_weather_payload(
    payload: Mapping[str, Any],
    timezone_name: str,
) -> tuple[WeatherForecastPoint, ...]:
    """Convert hourly API arrays into forecast points."""

    if payload.get("error"):
        reason = payload.get(
            "reason",
            "Unknown weather-service error",
        )

        raise WeatherServiceError(str(reason))

    hourly = payload.get("hourly")

    if not isinstance(hourly, Mapping):
        raise WeatherServiceError("Weather response does not contain hourly data.")

    timezone_info = get_timezone(timezone_name)

    times = require_series(hourly, "time")

    temperatures = require_series(
        hourly,
        "temperature_2m",
    )

    humidities = require_series(
        hourly,
        "relative_humidity_2m",
    )

    dew_points = require_series(
        hourly,
        "dew_point_2m",
    )

    precipitation_probabilities = require_series(
        hourly,
        "precipitation_probability",
    )

    precipitation_amounts = require_series(
        hourly,
        "precipitation",
    )

    cloud_covers = require_series(
        hourly,
        "cloud_cover",
    )

    visibilities = require_series(
        hourly,
        "visibility",
    )

    wind_speeds = require_series(
        hourly,
        "wind_speed_10m",
    )

    wind_gusts = require_series(
        hourly,
        "wind_gusts_10m",
    )

    points: list[WeatherForecastPoint] = []

    for (
        timestamp,
        temperature,
        humidity,
        dew_point,
        precipitation_probability,
        precipitation,
        cloud_cover,
        visibility,
        wind_speed,
        wind_gust,
    ) in zip(
        times,
        temperatures,
        humidities,
        dew_points,
        precipitation_probabilities,
        precipitation_amounts,
        cloud_covers,
        visibilities,
        wind_speeds,
        wind_gusts,
        strict=True,
    ):
        try:
            local_datetime = datetime.fromisoformat(str(timestamp))

        except ValueError as error:
            raise WeatherServiceError(f"Invalid weather timestamp: {timestamp!r}") from error

        if local_datetime.tzinfo is None:
            local_datetime = local_datetime.replace(tzinfo=timezone_info)
        else:
            local_datetime = local_datetime.astimezone(timezone_info)

        temperature_value = require_float(
            temperature,
            "temperature_2m",
        )

        humidity_value = require_float(
            humidity,
            "relative_humidity_2m",
        )

        dew_point_value = require_float(
            dew_point,
            "dew_point_2m",
        )

        precipitation_probability_value = require_float(
            precipitation_probability,
            "precipitation_probability",
        )

        precipitation_value = require_float(
            precipitation,
            "precipitation",
        )

        cloud_cover_value = require_float(
            cloud_cover,
            "cloud_cover",
        )

        visibility_value = require_float(
            visibility,
            "visibility",
        )

        wind_speed_value = require_float(
            wind_speed,
            "wind_speed_10m",
        )

        wind_gust_value = require_float(
            wind_gust,
            "wind_gusts_10m",
        )

        observing_score = calculate_weather_score(
            cloud_cover_percent=cloud_cover_value,
            precipitation_probability_percent=(precipitation_probability_value),
            precipitation_mm=precipitation_value,
            visibility_m=visibility_value,
            relative_humidity_percent=(humidity_value),
            wind_speed_kmh=wind_speed_value,
            wind_gusts_kmh=wind_gust_value,
        )

        points.append(
            WeatherForecastPoint(
                local_datetime=local_datetime,
                temperature_c=temperature_value,
                relative_humidity_percent=(humidity_value),
                dew_point_c=dew_point_value,
                dew_point_spread_c=round(
                    temperature_value - dew_point_value,
                    1,
                ),
                precipitation_probability_percent=(precipitation_probability_value),
                precipitation_mm=(precipitation_value),
                cloud_cover_percent=(cloud_cover_value),
                visibility_m=visibility_value,
                wind_speed_kmh=wind_speed_value,
                wind_gusts_kmh=wind_gust_value,
                observing_score=observing_score,
                rating=classify_weather_rating(
                    observing_score,
                    precipitation_mm=(precipitation_value),
                    wind_gusts_kmh=(wind_gust_value),
                ),
                dew_risk=classify_dew_risk(
                    temperature_c=temperature_value,
                    dew_point_c=dew_point_value,
                    relative_humidity_percent=(humidity_value),
                ),
            )
        )

    if not points:
        raise WeatherServiceError("The weather service returned no hourly forecast points.")

    return tuple(points)


def fetch_observing_weather(
    *,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    start_time: time,
    end_time: time,
    timeout_seconds: float = 10.0,
) -> WeatherForecastResult:
    """Fetch and summarize one observing-weather window."""

    if start_time == end_time:
        raise ValueError("Weather start and end times must be different.")

    timezone_info = get_timezone(timezone_name)

    end_date = local_date if end_time > start_time else local_date + timedelta(days=1)

    start_local = datetime.combine(
        local_date,
        start_time.replace(tzinfo=None),
        tzinfo=timezone_info,
    )

    end_local = datetime.combine(
        end_date,
        end_time.replace(tzinfo=None),
        tzinfo=timezone_info,
    )

    request_url = build_weather_forecast_url(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
        timezone_name=timezone_name,
        start_date=local_date,
        end_date=end_date,
    )

    payload = load_weather_payload(
        request_url,
        timeout_seconds=timeout_seconds,
    )

    all_points = parse_weather_payload(
        payload,
        timezone_name,
    )

    matching_points = tuple(
        point for point in all_points if (start_local <= point.local_datetime <= end_local)
    )

    if not matching_points:
        raise WeatherServiceError("No hourly weather points matched the observing window.")

    best_point = max(
        matching_points,
        key=lambda point: (
            point.observing_score,
            -point.cloud_cover_percent,
        ),
    )

    average_score = round(
        sum(point.observing_score for point in matching_points) / len(matching_points),
        1,
    )

    maximum_cloud_cover = max(point.cloud_cover_percent for point in matching_points)

    worst_dew_risk = max(
        (point.dew_risk for point in matching_points),
        key=DEW_RISK_ORDER.__getitem__,
    )

    return WeatherForecastResult(
        points=matching_points,
        best_point=best_point,
        average_score=average_score,
        maximum_cloud_cover_percent=(maximum_cloud_cover),
        worst_dew_risk=worst_dew_risk,
        start_local_iso=start_local.isoformat(timespec="minutes"),
        end_local_iso=end_local.isoformat(timespec="minutes"),
        source_name="Open-Meteo Best Match",
    )
