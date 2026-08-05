"""Mission 31 characterization for strict weather sample identity and selection."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from urllib.parse import parse_qs, urlparse

import pytest

import astroscope.weather as weather
from astroscope.i18n import translate
from astroscope.weather import (
    WeatherCivilEndpoint,
    WeatherSelectionWindowRequest,
    WeatherServiceError,
    build_weather_forecast_url,
    fetch_observing_weather,
    fetch_observing_weather_strict,
    parse_weather_payload,
    parse_weather_unix_payload,
    resolve_weather_selection_window,
)


def weather_payload(times: list[int]) -> dict[str, object]:
    """Build a minimal corrected GMT Unix provider response."""

    fields = {
        "temperature_2m": 10.0,
        "relative_humidity_2m": 60.0,
        "dew_point_2m": 2.0,
        "precipitation_probability": 0.0,
        "precipitation": 0.0,
        "cloud_cover": 10.0,
        "visibility": 20_000.0,
        "wind_speed_10m": 5.0,
        "wind_gusts_10m": 10.0,
    }
    return {
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "utc_offset_seconds": 0,
        "hourly": {"time": times, **{key: [value] * len(times) for key, value in fields.items()}},
    }


def window(
    timezone_name: str,
    start_date: date,
    start_time: time,
    end_date: date,
    end_time: time,
    start_fold: int | None = None,
    end_fold: int | None = None,
):
    """Resolve one explicit weather selection window."""

    return resolve_weather_selection_window(
        WeatherSelectionWindowRequest(
            timezone_name=timezone_name,
            start=WeatherCivilEndpoint(start_date, start_time, start_fold),
            end=WeatherCivilEndpoint(end_date, end_time, end_fold),
        )
    )


@pytest.mark.parametrize("case", range(10))
def test_provider_url_parser_and_metadata_contract(case: int) -> None:
    """Cover corrected URL, Unix parsing, metadata, and legacy ISO safety."""

    if case in {0, 1, 2, 3}:
        query = parse_qs(
            urlparse(
                build_weather_forecast_url(
                    latitude_deg=35.0,
                    longitude_deg=139.0,
                    elevation_m=10.0,
                    timezone_name="GMT",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 2),
                    timeformat="unixtime",
                )
            ).query
        )
        assertions = (
            query["timezone"] == ["GMT"],
            query["timeformat"] == ["unixtime"],
            query["start_date"] == ["2025-01-01"] and query["end_date"] == ["2025-01-02"],
            query["hourly"][0] == ",".join(weather.HOURLY_WEATHER_VARIABLES),
        )
        assert assertions[case]
    elif case == 4:
        points, _ = parse_weather_unix_payload(
            weather_payload([int(datetime(2025, 1, 1, 15, tzinfo=UTC).timestamp())]),
            "Asia/Tokyo",
        )
        assert points[0].utc_datetime == datetime(2025, 1, 1, 15, tzinfo=UTC)
        assert points[0].local_datetime.isoformat() == "2025-01-02T00:00:00+09:00"
    elif case == 5:
        payload = weather_payload([1_736_937_600])
        payload["timezone"] = "Asia/Tokyo"
        with pytest.raises(WeatherServiceError, match="timezone"):
            parse_weather_unix_payload(payload, "Asia/Tokyo")
    elif case == 6:
        with pytest.raises(WeatherServiceError, match="Invalid Unix"):
            parse_weather_unix_payload(weather_payload(["bad"]), "UTC")
    elif case == 7:
        with pytest.raises(WeatherServiceError, match="strictly increasing"):
            parse_weather_unix_payload(weather_payload([2, 1]), "UTC")
    elif case == 8:
        with pytest.raises(WeatherServiceError, match="strictly increasing"):
            parse_weather_unix_payload(weather_payload([1, 1]), "UTC")
    else:
        legacy = weather_payload([1])
        legacy["timezone"] = "Asia/Tokyo"
        legacy["hourly"]["time"] = ["2025-01-01T20:00"]
        assert parse_weather_payload(legacy, "Asia/Tokyo")[0].utc_datetime is not None


@pytest.mark.parametrize("case", range(12))
def test_strict_weather_selection_window_construction(case: int) -> None:
    """Cover ordinary, precise, ambiguous, gap, and invalid strict endpoints."""

    if case == 0:
        assert (
            window(
                "Asia/Tokyo", date(2025, 1, 1), time(20), date(2025, 1, 1), time(21)
            ).start_utc.hour
            == 11
        )
    elif case == 1:
        assert window(
            "Asia/Tokyo", date(2025, 1, 1), time(20), date(2025, 1, 2), time(4)
        ).end_utc.date() == date(2025, 1, 1)
    elif case == 2:
        assert (
            window(
                "UTC", date(2025, 1, 1), time(1, 2, 3), date(2025, 1, 1), time(1, 2, 4)
            ).start_utc.second
            == 3
        )
    elif case == 3:
        assert (
            window(
                "UTC", date(2025, 1, 1), time(1, 2, 3, 4), date(2025, 1, 1), time(1, 2, 3, 5)
            ).start_utc.microsecond
            == 4
        )
    elif case in {4, 5}:
        result = window(
            "America/New_York",
            date(2025, 11, 2),
            time(1, 30),
            date(2025, 11, 2),
            time(2, 30),
            case - 4,
        )
        assert result.start_utc < result.end_utc
    elif case in {6, 7}:
        result = window(
            "America/New_York",
            date(2025, 11, 2),
            time(0, 30),
            date(2025, 11, 2),
            time(1, 30),
            None,
            case - 6,
        )
        assert result.start_utc < result.end_utc
    elif case == 8:
        with pytest.raises(ValueError, match="Ambiguous"):
            window(
                "America/New_York", date(2025, 11, 2), time(1, 30), date(2025, 11, 2), time(2, 30)
            )
    elif case == 9:
        with pytest.raises(ValueError, match="Nonexistent"):
            window("America/New_York", date(2025, 3, 9), time(2, 30), date(2025, 3, 9), time(4))
    elif case == 10:
        with pytest.raises(ValueError, match="before"):
            window("UTC", date(2025, 1, 1), time(1), date(2025, 1, 1), time(1))
    else:
        with pytest.raises(ValueError, match="before"):
            window("UTC", date(2025, 1, 1), time(2), date(2025, 1, 1), time(1))


@pytest.mark.parametrize("case", range(8))
def test_utc_filtering_uses_closed_physical_envelope(
    monkeypatch: pytest.MonkeyPatch, case: int
) -> None:
    """Closed sample selection is based only on UTC identity."""

    start = datetime(2025, 11, 2, 5, tzinfo=UTC)
    values = [int((start.replace(hour=4 + index)).timestamp()) for index in range(5)]
    monkeypatch.setattr(
        weather, "load_weather_payload", lambda *args, **kwargs: weather_payload(values)
    )
    resolved = window("America/New_York", date(2025, 11, 2), time(1), date(2025, 11, 2), time(2), 0)
    result = fetch_observing_weather_strict(
        latitude_deg=40.7, longitude_deg=-74.0, elevation_m=0, window=resolved
    )
    checks = (
        len(result.points) == 3,
        result.points[0].utc_datetime == datetime(2025, 11, 2, 5, tzinfo=UTC),
        result.points[-1].utc_datetime == datetime(2025, 11, 2, 7, tzinfo=UTC),
        all(point.utc_datetime is not None for point in result.points),
        result.points[0].local_datetime.fold == 0,
        result.points[1].local_datetime.fold == 1,
        result.points[0].utc_datetime < result.points[1].utc_datetime,
        result.provider_timeformat == "unixtime",
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(5))
def test_legacy_weather_compatibility(monkeypatch: pytest.MonkeyPatch, case: int) -> None:
    """The old callable retains ordinary behavior and rejects unsafe endpoints."""

    values = [
        int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) + index * 3600 for index in range(48)
    ]
    monkeypatch.setattr(
        weather, "load_weather_payload", lambda *args, **kwargs: weather_payload(values)
    )
    if case < 2:
        result = fetch_observing_weather(
            latitude_deg=35,
            longitude_deg=139,
            elevation_m=0,
            timezone_name="Asia/Tokyo",
            local_date=date(2025, 1, 1),
            start_time=time(20),
            end_time=time(22 if case == 0 else 4),
        )
        assert bool(result.points) is True
    elif case == 2:
        with pytest.raises(ValueError, match="Ambiguous"):
            fetch_observing_weather(
                latitude_deg=40,
                longitude_deg=-74,
                elevation_m=0,
                timezone_name="America/New_York",
                local_date=date(2025, 11, 2),
                start_time=time(1, 30),
                end_time=time(3),
            )
    elif case == 3:
        with pytest.raises(ValueError, match="Nonexistent"):
            fetch_observing_weather(
                latitude_deg=40,
                longitude_deg=-74,
                elevation_m=0,
                timezone_name="America/New_York",
                local_date=date(2025, 3, 9),
                start_time=time(2, 30),
                end_time=time(4),
            )
    else:
        assert "timeformat=iso8601" in build_weather_forecast_url(
            latitude_deg=0,
            longitude_deg=0,
            elevation_m=0,
            timezone_name="UTC",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
        )


@pytest.mark.parametrize("case", range(9))
def test_transition_regressions(case: int) -> None:
    """Unix conversion preserves folds and gaps without local-label inference."""

    scenarios = (
        (
            "America/New_York",
            [int(datetime(2025, 3, 9, 7, tzinfo=UTC).timestamp())],
            "2025-03-09T03:00:00-04:00",
        ),
        (
            "America/New_York",
            [
                int(datetime(2025, 11, 2, 5, tzinfo=UTC).timestamp()),
                int(datetime(2025, 11, 2, 6, tzinfo=UTC).timestamp()),
            ],
            "2025-11-02T01:00:00-05:00",
        ),
        (
            "Europe/London",
            [
                int(datetime(2025, 10, 26, 0, tzinfo=UTC).timestamp()),
                int(datetime(2025, 10, 26, 1, tzinfo=UTC).timestamp()),
            ],
            "2025-10-26T01:00:00+00:00",
        ),
        (
            "Australia/Lord_Howe",
            [int(datetime(2025, 4, 5, 15, tzinfo=UTC).timestamp())],
            "2025-04-06T01:30:00+10:30",
        ),
        (
            "Australia/Lord_Howe",
            [int(datetime(2025, 10, 4, 16, tzinfo=UTC).timestamp())],
            "2025-10-05T03:00:00+11:00",
        ),
    )
    if case < 5:
        zone, values, expected = scenarios[case]
        points, _ = parse_weather_unix_payload(weather_payload(values), zone)
        assert points[-1].local_datetime.isoformat() == expected
    elif case == 5:
        unsafe = weather_payload([1])
        unsafe["timezone"] = "America/New_York"
        unsafe["hourly"]["time"] = ["2025-11-02T01:30"]
        with pytest.raises(WeatherServiceError, match="unsafe"):
            parse_weather_payload(unsafe, "America/New_York")
    elif case == 6:
        unsafe = weather_payload([1])
        unsafe["timezone"] = "America/New_York"
        unsafe["hourly"]["time"] = ["2025-03-09T02:30"]
        with pytest.raises(WeatherServiceError, match="unsafe"):
            parse_weather_payload(unsafe, "America/New_York")
    elif case == 7:
        assert (
            window(
                "Australia/Lord_Howe", date(2025, 4, 6), time(1, 30), date(2025, 4, 6), time(2), 1
            ).start_utc.isoformat()
            == "2025-04-05T15:00:00+00:00"
        )
    else:
        assert (
            window(
                "America/New_York", date(2025, 11, 2), time(1), date(2025, 11, 2), time(2), 1
            ).start_utc.isoformat()
            == "2025-11-02T06:00:00+00:00"
        )


@pytest.mark.parametrize("case", range(2))
def test_chart_identity_properties(case: int) -> None:
    """Chart ordering relies on UTC identity; display retains aware local values."""

    points, _ = (
        parse_weather_unix_payload(
            weather_payload([1_762_065_000, 1_762_061_400]), "America/New_York"
        )
        if False
        else parse_weather_unix_payload(
            weather_payload([1_762_061_400, 1_762_065_000]), "America/New_York"
        )
    )
    assert (
        (points[0].utc_datetime < points[1].utc_datetime)
        if case == 0
        else (points[0].local_datetime.fold == 0 and points[1].local_datetime.fold == 1)
    )


@pytest.mark.parametrize("language", ("en", "ja", "ko", "th"))
def test_weather_transition_localization(language: str) -> None:
    """Every new weather transition key is localized in every supported language."""

    keys = (
        "weather_start_date",
        "weather_end_date",
        "weather_ambiguous_start",
        "weather_ambiguous_end",
        "weather_fold_selection_start",
        "weather_fold_selection_end",
        "weather_candidate_utc_offset",
        "weather_nonexistent_start",
        "weather_nonexistent_end",
    )
    assert all(translate(key, language) != key for key in keys)
