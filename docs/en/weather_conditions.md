🌐 Language: [English](../en/weather_conditions.md) | [日本語](../ja/weather_conditions.md) | [한국어](../ko/weather_conditions.md) | [ไทย](../th/weather_conditions.md)

# Weather-Aware Observing Conditions

This module retrieves an hourly weather forecast and evaluates whether conditions are suitable for astronomical observation.

## Forecast variables

- Temperature
- Relative humidity
- Dew point
- Precipitation probability
- Precipitation amount
- Cloud cover
- Visibility
- Wind speed
- Wind gusts

## Weather score

The transparent score contains:

- Cloud cover: 40 points
- Precipitation probability: 25 points
- Visibility: 15 points
- Humidity: 10 points
- Wind speed: 10 points

Rain and dangerous wind gusts limit the maximum score.

## Dew risk

Dew risk is estimated from relative humidity and the difference between temperature and dew point.

- Low
- Moderate
- High
- Critical

## Forecast limitation

This feature uses near-term forecast-model output. It is not a guarantee of actual sky conditions and does not directly measure astronomical seeing or transparency.

## Data attribution

Weather data are provided by Open-Meteo under CC BY 4.0. AstroScope transforms the source data by calculating observing scores, ratings, and dew-risk categories.

## Implemented files

- `src/astroscope/weather.py`
- `src/astroscope/weather_charts.py`
- `src/astroscope/weather_messages.py`
- `tests/test_weather.py`
- `tests/test_weather_charts.py`
