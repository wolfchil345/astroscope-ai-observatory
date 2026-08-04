"""Regression coverage for strict observation-schedule interval resolution."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from astroscope import schedule as schedule_module
from astroscope.observer import (
    AmbiguousCivilTimeError,
    NonexistentCivilTimeError,
)
from astroscope.planner import ObservationPlanEntry, ObservationPlanResult
from astroscope.schedule import (
    ScheduleCivilEndpoint,
    ScheduleIntervalRequest,
    calculate_observation_schedule,
    calculate_observation_schedule_strict,
    create_resolved_schedule_time_grid,
    resolve_schedule_interval,
)


def _request(
    timezone_name: str,
    start_date: date,
    start_time: time,
    end_date: date,
    end_time: time,
    *,
    start_fold: int | None = None,
    end_fold: int | None = None,
) -> ScheduleIntervalRequest:
    return ScheduleIntervalRequest(
        timezone_name=timezone_name,
        start=ScheduleCivilEndpoint(start_date, start_time, start_fold),
        end=ScheduleCivilEndpoint(end_date, end_time, end_fold),
    )


def _entry() -> ObservationPlanEntry:
    return ObservationPlanEntry(
        object_key="forced",
        category="catalog",
        altitude_degrees=60.0,
        azimuth_degrees=100.0,
        cardinal_direction="S",
        airmass=1.2,
        moon_separation_degrees=60.0,
        status="observable",
        altitude_score=30.0,
        airmass_score=15.0,
        moon_separation_score=10.0,
        darkness_score=10.0,
        total_score=70.0,
        rating="very_good",
        recommended=True,
    )


def _controlled_result(
    monkeypatch: pytest.MonkeyPatch,
    interval: ScheduleIntervalRequest,
    *,
    include_targets: bool = True,
) -> tuple[object, list[dict[str, object]]]:
    calls: list[dict[str, object]] = []

    def fake_plan(**kwargs: object) -> ObservationPlanResult:
        calls.append(kwargs)
        local_datetime = datetime.combine(
            kwargs["local_date"],  # type: ignore[arg-type]
            kwargs["local_time"],  # type: ignore[arg-type]
        )
        return ObservationPlanResult(
            entries=(_entry(),),
            sun_altitude_degrees=-20.0,
            recommended_count=1,
            total_target_count=1,
            utc_datetime_iso=local_datetime.isoformat(),
        )

    monkeypatch.setattr(schedule_module, "calculate_observation_plan", fake_plan)
    result = calculate_observation_schedule_strict(
        latitude_deg=40.7128,
        longitude_deg=-74.006,
        elevation_m=10.0,
        interval=resolve_schedule_interval(interval),
        interval_minutes=60,
        minimum_altitude_degrees=0.0,
        minimum_moon_separation_degrees=0.0,
        minimum_score=0.0,
        include_catalog_targets=include_targets,
        include_solar_system_targets=False,
    )
    return result, calls


def test_tokyo_ordinary_strict_interval() -> None:
    interval = resolve_schedule_interval(
        _request("Asia/Tokyo", date(2026, 1, 1), time(20), date(2026, 1, 1), time(22))
    )
    assert interval.elapsed.total_seconds() == 7200


def test_tokyo_explicit_overnight_interval() -> None:
    interval = resolve_schedule_interval(
        _request("Asia/Tokyo", date(2026, 1, 1), time(20), date(2026, 1, 2), time(2))
    )
    assert interval.elapsed.total_seconds() == 21600


def test_grid_keeps_exact_final_endpoint_sentinel() -> None:
    interval = resolve_schedule_interval(
        _request("Asia/Tokyo", date(2026, 1, 1), time(20), date(2026, 1, 1), time(21, 30))
    )
    assert create_resolved_schedule_time_grid(interval, 60)[-1].time() == time(21, 30)


def test_new_york_fall_back_grid_has_six_samples() -> None:
    interval = resolve_schedule_interval(
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        )
    )
    grid = create_resolved_schedule_time_grid(interval, 60)
    assert len(grid) == 6
    assert [value.astimezone(UTC).hour for value in grid] == [4, 5, 6, 7, 8, 9]


def test_new_york_repeated_samples_retain_offsets_and_folds() -> None:
    interval = resolve_schedule_interval(
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        )
    )
    first, second = create_resolved_schedule_time_grid(interval, 60)[1:3]
    assert (first.isoformat(), first.fold) == ("2026-11-01T01:00:00-04:00", 0)
    assert (second.isoformat(), second.fold) == ("2026-11-01T01:00:00-05:00", 1)


@pytest.mark.parametrize(
    ("start_fold", "end_fold", "expected_minutes"),
    [
        (0, None, 120.0),
        (1, None, 60.0),
        (None, 0, 60.0),
        (None, 1, 120.0),
    ],
)
def test_ambiguous_endpoint_folds_resolve_independently(
    start_fold: int | None,
    end_fold: int | None,
    expected_minutes: float,
) -> None:
    start = time(1) if start_fold is not None else time(0)
    end = time(1) if end_fold is not None else time(2)
    interval = resolve_schedule_interval(
        _request(
            "America/New_York",
            date(2026, 11, 1),
            start,
            date(2026, 11, 1),
            end,
            start_fold=start_fold,
            end_fold=end_fold,
        )
    )
    assert interval.elapsed.total_seconds() / 60.0 == expected_minutes


def test_ambiguous_endpoint_without_fold_rejects() -> None:
    with pytest.raises(AmbiguousCivilTimeError):
        resolve_schedule_interval(
            _request(
                "America/New_York", date(2026, 11, 1), time(1), date(2026, 11, 1), time(2)
            )
        )


@pytest.mark.parametrize("endpoint", ["start", "end"])
def test_new_york_nonexistent_endpoint_rejects(endpoint: str) -> None:
    start_time = time(2) if endpoint == "start" else time(1, 30)
    end_time = time(3) if endpoint == "start" else time(2)
    with pytest.raises(NonexistentCivilTimeError):
        resolve_schedule_interval(
            _request(
                "America/New_York",
                date(2026, 3, 8),
                start_time,
                date(2026, 3, 8),
                end_time,
            )
        )


def test_valid_new_york_spring_interval_spans_transition() -> None:
    interval = resolve_schedule_interval(
        _request(
            "America/New_York", date(2026, 3, 8), time(1, 30), date(2026, 3, 8), time(3)
        )
    )
    assert interval.elapsed.total_seconds() == 1800


def test_london_fold_is_not_sorted_by_wall_clock() -> None:
    interval = resolve_schedule_interval(
        _request(
            "Europe/London",
            date(2026, 10, 25),
            time(1, 30),
            date(2026, 10, 25),
            time(1, 30),
            start_fold=0,
            end_fold=1,
        )
    )
    assert interval.elapsed.total_seconds() == 3600


def test_lord_howe_half_hour_fold() -> None:
    interval = resolve_schedule_interval(
        _request(
            "Australia/Lord_Howe",
            date(2026, 4, 5),
            time(1, 45),
            date(2026, 4, 5),
            time(1, 45),
            start_fold=0,
            end_fold=1,
        )
    )
    assert interval.elapsed.total_seconds() == 1800


def test_lord_howe_half_hour_gap_rejects() -> None:
    with pytest.raises(NonexistentCivilTimeError):
        resolve_schedule_interval(
            _request(
                "Australia/Lord_Howe",
                date(2026, 10, 4),
                time(2, 15),
                date(2026, 10, 4),
                time(3),
            )
        )


def test_seconds_are_preserved_in_strict_grid() -> None:
    interval = resolve_schedule_interval(
        _request(
            "Asia/Tokyo", date(2026, 1, 1), time(20, 0, 1), date(2026, 1, 1), time(20, 1, 2)
        )
    )
    assert create_resolved_schedule_time_grid(interval, 15)[0].second == 1


def test_microseconds_are_preserved_in_strict_grid() -> None:
    interval = resolve_schedule_interval(
        _request(
            "Asia/Tokyo",
            date(2026, 1, 1),
            time(20, 0, 1, 123456),
            date(2026, 1, 1),
            time(20, 1, 2, 654321),
        )
    )
    assert create_resolved_schedule_time_grid(interval, 15)[-1].microsecond == 654321


@pytest.mark.parametrize(
    ("start", "end", "start_fold", "end_fold"),
    [
        (time(1), time(1), 0, 0),
        (time(1), time(1), 1, 0),
    ],
)
def test_zero_or_reversed_utc_interval_rejects(
    start: time,
    end: time,
    start_fold: int,
    end_fold: int,
) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        resolve_schedule_interval(
            _request(
                "America/New_York",
                date(2026, 11, 1),
                start,
                date(2026, 11, 1),
                end,
                start_fold=start_fold,
                end_fold=end_fold,
            )
        )


def test_physical_interval_over_eighteen_hours_rejects() -> None:
    with pytest.raises(ValueError, match="cannot exceed 18 hours"):
        resolve_schedule_interval(
            _request("UTC", date(2026, 1, 1), time(0), date(2026, 1, 1), time(18, 1))
        )


def test_empty_categories_preserve_valid_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request("Asia/Tokyo", date(2026, 1, 1), time(20), date(2026, 1, 1), time(22)),
        include_targets=False,
    )
    assert result.sample_count == 3
    assert result.schedule_blocks == ()
    assert result.scheduled_minutes == 0.0
    assert result.top_target_key is None


def test_fall_back_block_merges_by_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        ),
    )
    assert len(result.schedule_blocks) == 1
    assert result.schedule_blocks[0].duration_minutes == 300.0


def test_fall_back_scheduled_minutes_are_physical(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        ),
    )
    assert result.scheduled_minutes == 300.0


def test_timeline_utc_values_are_chronological(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        ),
    )
    values = [point.utc_datetime_iso for point in result.timeline_points]
    assert values == sorted(values)


def test_timeline_local_labels_keep_repeated_hour_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        ),
    )
    assert [point.local_datetime_iso for point in result.timeline_points][1:3] == [
        "2026-11-01T01:00-04:00",
        "2026-11-01T01:00-05:00",
    ]


def test_legacy_ordinary_call_remains_compatible() -> None:
    grid = schedule_module.create_local_time_grid(
        date(2026, 1, 1), time(20), time(0), "Asia/Tokyo", 60
    )
    assert [value.isoformat(timespec="minutes") for value in grid] == [
        "2026-01-01T20:00+09:00",
        "2026-01-01T21:00+09:00",
        "2026-01-01T22:00+09:00",
        "2026-01-01T23:00+09:00",
        "2026-01-02T00:00+09:00",
    ]


def test_legacy_ambiguous_call_rejects_safely() -> None:
    with pytest.raises(AmbiguousCivilTimeError):
        schedule_module.create_local_time_grid(
            date(2026, 11, 1), time(1), time(2), "America/New_York", 60
        )


def test_legacy_gap_call_rejects_safely() -> None:
    with pytest.raises(NonexistentCivilTimeError):
        calculate_observation_schedule(
            latitude_deg=40.7128,
            longitude_deg=-74.006,
            elevation_m=10.0,
            timezone_name="America/New_York",
            local_date=date(2026, 3, 8),
            start_time=time(1, 30),
            end_time=time(2),
        )


def test_blocks_store_aware_normalized_utc_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _controlled_result(
        monkeypatch,
        _request(
            "America/New_York", date(2026, 11, 1), time(0), date(2026, 11, 1), time(4)
        ),
    )
    block = result.schedule_blocks[0]
    assert block.start_utc == datetime(2026, 11, 1, 4, tzinfo=UTC)
    assert block.end_utc == datetime(2026, 11, 1, 9, tzinfo=UTC)


def test_strict_interval_uses_utc_not_naive_wall_ordering() -> None:
    interval = resolve_schedule_interval(
        _request(
            "America/New_York",
            date(2026, 11, 1),
            time(1),
            date(2026, 11, 1),
            time(1),
            start_fold=0,
            end_fold=1,
        )
    )
    assert interval.elapsed.total_seconds() == 3600
