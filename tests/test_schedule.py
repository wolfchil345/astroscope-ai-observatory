"""Tests for night timelines and observation schedules."""

import subprocess
import sys
from datetime import UTC, date, datetime, time
from pathlib import Path

import pytest
from astropy.utils import iers

from astroscope import schedule as schedule_module
from astroscope.planner import ObservationPlanEntry, ObservationPlanResult
from astroscope.schedule import (
    ObservationScheduleResult,
    TimelinePoint,
    calculate_observation_schedule,
    create_local_time_grid,
)

iers.conf.auto_download = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _entry(
    object_key: str,
    *,
    altitude_degrees: float,
    azimuth_degrees: float,
    moon_separation_degrees: float,
    total_score: float,
    rating: str = "good",
    recommended: bool = True,
) -> ObservationPlanEntry:
    return ObservationPlanEntry(
        object_key=object_key,
        category="catalog",
        altitude_degrees=altitude_degrees,
        azimuth_degrees=azimuth_degrees,
        cardinal_direction="S",
        airmass=1.2,
        moon_separation_degrees=moon_separation_degrees,
        status="observable",
        altitude_score=30.0,
        airmass_score=15.0,
        moon_separation_score=10.0,
        darkness_score=10.0,
        total_score=total_score,
        rating=rating,
        recommended=recommended,
    )


@pytest.fixture
def controlled_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ObservationScheduleResult, list[dict[str, object]]]:
    plans = (
        ObservationPlanResult(
            entries=(
                _entry(
                    "alpha",
                    altitude_degrees=80.0,
                    azimuth_degrees=101.0,
                    moon_separation_degrees=41.0,
                    total_score=60.0,
                ),
                _entry(
                    "beta",
                    altitude_degrees=85.0,
                    azimuth_degrees=201.0,
                    moon_separation_degrees=51.0,
                    total_score=60.0,
                ),
            ),
            sun_altitude_degrees=-18.0,
            recommended_count=2,
            total_target_count=2,
            utc_datetime_iso="2024-01-01T11:00:00+00:00",
        ),
        ObservationPlanResult(
            entries=(
                _entry(
                    "alpha",
                    altitude_degrees=89.0,
                    azimuth_degrees=102.0,
                    moon_separation_degrees=42.0,
                    total_score=65.0,
                ),
                _entry(
                    "beta",
                    altitude_degrees=50.0,
                    azimuth_degrees=202.0,
                    moon_separation_degrees=52.0,
                    total_score=70.0,
                    rating="very_good",
                ),
            ),
            sun_altitude_degrees=-19.0,
            recommended_count=2,
            total_target_count=2,
            utc_datetime_iso="2024-01-01T12:00:00+00:00",
        ),
        ObservationPlanResult(
            entries=(
                _entry(
                    "alpha",
                    altitude_degrees=89.0,
                    azimuth_degrees=103.0,
                    moon_separation_degrees=43.0,
                    total_score=65.0,
                ),
                _entry(
                    "beta",
                    altitude_degrees=80.0,
                    azimuth_degrees=203.0,
                    moon_separation_degrees=53.0,
                    total_score=70.0,
                    rating="excellent",
                ),
            ),
            sun_altitude_degrees=-20.0,
            recommended_count=2,
            total_target_count=2,
            utc_datetime_iso="2024-01-01T13:00:00+00:00",
        ),
        ObservationPlanResult(
            entries=(
                _entry(
                    "alpha",
                    altitude_degrees=70.0,
                    azimuth_degrees=104.0,
                    moon_separation_degrees=44.0,
                    total_score=55.0,
                ),
                _entry(
                    "beta",
                    altitude_degrees=75.0,
                    azimuth_degrees=204.0,
                    moon_separation_degrees=54.0,
                    total_score=68.0,
                    rating="very_good",
                ),
            ),
            sun_altitude_degrees=-21.0,
            recommended_count=2,
            total_target_count=2,
            utc_datetime_iso="2024-01-01T14:00:00+00:00",
        ),
    )
    planner_calls: list[dict[str, object]] = []

    def fake_calculate_observation_plan(**kwargs: object) -> ObservationPlanResult:
        planner_calls.append(kwargs)
        return plans[len(planner_calls) - 1]

    monkeypatch.setattr(
        schedule_module,
        "calculate_observation_plan",
        fake_calculate_observation_plan,
    )

    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(23, 0),
        interval_minutes=60,
        minimum_altitude_degrees=25.0,
        minimum_moon_separation_degrees=35.0,
        minimum_score=45.0,
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    return result, planner_calls


def test_time_grid_crosses_midnight() -> None:
    grid = create_local_time_grid(
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(0, 0),
        timezone_name="Asia/Tokyo",
        interval_minutes=60,
    )

    assert len(grid) == 5
    assert [value.isoformat(timespec="minutes") for value in grid] == [
        "2024-01-01T20:00+09:00",
        "2024-01-01T21:00+09:00",
        "2024-01-01T22:00+09:00",
        "2024-01-01T23:00+09:00",
        "2024-01-02T00:00+09:00",
    ]


def test_time_grid_includes_exact_end_time() -> None:
    grid = create_local_time_grid(
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(23, 30),
        timezone_name="Asia/Tokyo",
        interval_minutes=60,
    )

    assert grid[-1].time().hour == 23
    assert grid[-1].time().minute == 30


def test_equal_start_and_end_raise_error() -> None:
    with pytest.raises(ValueError):
        create_local_time_grid(
            local_date=date(2024, 1, 1),
            start_time=time(20, 0),
            end_time=time(20, 0),
            timezone_name="Asia/Tokyo",
            interval_minutes=60,
        )


def test_catalog_schedule_has_timeline_points() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(0, 0),
        interval_minutes=120,
        minimum_altitude_degrees=0.0,
        minimum_moon_separation_degrees=0.0,
        minimum_score=0.0,
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    assert result.sample_count == 3
    assert result.evaluated_target_count == 5
    assert len(result.timeline_points) == 15
    assert result.schedule_blocks


def test_schedule_blocks_do_not_overlap() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(2, 0),
        interval_minutes=120,
        minimum_altitude_degrees=0.0,
        minimum_moon_separation_degrees=0.0,
        minimum_score=0.0,
        include_catalog_targets=True,
        include_solar_system_targets=False,
    )

    for first, second in zip(
        result.schedule_blocks,
        result.schedule_blocks[1:],
        strict=False,
    ):
        assert first.end_local <= second.start_local

    assert all(block.duration_minutes > 0.0 for block in result.schedule_blocks)


def test_empty_categories_return_empty_schedule() -> None:
    result = calculate_observation_schedule(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        start_time=time(20, 0),
        end_time=time(22, 0),
        interval_minutes=60,
        include_catalog_targets=False,
        include_solar_system_targets=False,
    )

    assert result.timeline_points == ()
    assert result.schedule_blocks == ()
    assert result.evaluated_target_count == 0


def test_schedule_forwards_every_planner_argument_once_per_sample(
    controlled_schedule: tuple[ObservationScheduleResult, list[dict[str, object]]],
) -> None:
    result, planner_calls = controlled_schedule

    assert result.sample_count == 4
    assert len(planner_calls) == result.sample_count
    for index, planner_call in enumerate(planner_calls):
        assert planner_call == {
            "latitude_deg": 34.6937,
            "longitude_deg": 135.5023,
            "elevation_m": 15.0,
            "timezone_name": "Asia/Tokyo",
            "local_date": date(2024, 1, 1),
            "local_time": time(20 + index, 0),
            "minimum_altitude_degrees": 25.0,
            "minimum_moon_separation_degrees": 35.0,
            "minimum_score": 45.0,
            "include_catalog_targets": True,
            "include_solar_system_targets": False,
        }


def test_schedule_maps_every_timeline_point_field(
    controlled_schedule: tuple[ObservationScheduleResult, list[dict[str, object]]],
) -> None:
    result, _ = controlled_schedule

    assert result.timeline_points[0] == TimelinePoint(
        object_key="alpha",
        category="catalog",
        local_datetime_iso="2024-01-01T20:00+09:00",
        utc_datetime_iso="2024-01-01T11:00:00+00:00",
        altitude_degrees=80.0,
        azimuth_degrees=101.0,
        moon_separation_degrees=41.0,
        total_score=60.0,
        rating="good",
        status="observable",
        recommended=True,
        sun_altitude_degrees=-18.0,
    )
    assert len(result.timeline_points) == 8


def test_schedule_preserves_greedy_selection_merging_and_aggregates(
    controlled_schedule: tuple[ObservationScheduleResult, list[dict[str, object]]],
) -> None:
    result, _ = controlled_schedule

    assert result.start_local_iso == "2024-01-01T20:00+09:00"
    assert result.end_local_iso == "2024-01-01T23:00+09:00"
    assert result.evaluated_target_count == 2
    assert result.scheduled_minutes == 180.0
    assert result.top_target_key == "beta"
    assert len(result.schedule_blocks) == 1

    block = result.schedule_blocks[0]
    assert block.object_key == "beta"
    assert block.category == "catalog"
    assert block.start_local.isoformat(timespec="minutes") == (
        "2024-01-01T20:00+09:00"
    )
    assert block.end_local.isoformat(timespec="minutes") == "2024-01-01T23:00+09:00"
    assert block.peak_local.isoformat(timespec="minutes") == (
        "2024-01-01T21:00+09:00"
    )
    assert block.start_utc == datetime(2024, 1, 1, 11, tzinfo=UTC)
    assert block.end_utc == datetime(2024, 1, 1, 14, tzinfo=UTC)
    assert block.duration_minutes == 180.0
    assert block.peak_score == 70.0
    assert block.peak_altitude_degrees == 50.0
    assert block.peak_moon_separation_degrees == 52.0
    assert block.rating == "very_good"


def test_clean_schedule_import_does_not_load_plotly_or_visuals() -> None:
    script = """
import importlib.abc
import sys

sys.path.insert(0, sys.argv[1])

class RejectPlotly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "plotly" or fullname.startswith("plotly."):
            raise AssertionError(f"Unexpected Plotly import: {fullname}")
        return None

sys.meta_path.insert(0, RejectPlotly())

from astroscope.schedule import (
    ObservationScheduleResult,
    ScheduleBlock,
    TimelinePoint,
    calculate_observation_schedule,
    create_local_time_grid,
)

assert ObservationScheduleResult
assert ScheduleBlock
assert TimelinePoint
assert calculate_observation_schedule
assert create_local_time_grid
assert not any(name == "plotly" or name.startswith("plotly.") for name in sys.modules)
assert "astroscope.schedule_visuals" not in sys.modules
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPOSITORY_ROOT / "src")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
