"""Characterization tests for transit-schedule application helpers."""

import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

from astroscope.transit_schedule import (
    DEFAULT_MAXIMUM_EVENTS_PER_TARGET,
    DEFAULT_MAXIMUM_TOTAL_EVENTS,
    TransitScheduleRequest,
    TransitScheduleTarget,
)
from astroscope.transit_schedule_application import (
    TransitDashboardTargetInput,
    build_schedule_request,
    build_schedule_target,
    utc_datetime_to_julian_date,
)
from astroscope.transit_scheduler import TransitEphemeris
from astroscope.transit_visibility import TransitTarget


def test_utc_datetime_to_julian_date_converts_aware_value_to_utc() -> None:
    japan_standard_time = timezone(timedelta(hours=9))
    value = datetime(
        2000,
        1,
        1,
        21,
        0,
        tzinfo=japan_standard_time,
    )

    result = utc_datetime_to_julian_date(value)

    assert result == pytest.approx(2_451_545.0)


def test_utc_datetime_to_julian_date_rejects_naive_value() -> None:
    with pytest.raises(
        ValueError,
        match="Datetime must include timezone information.",
    ):
        utc_datetime_to_julian_date(
            datetime(
                2026,
                1,
                1,
                0,
                0,
            )
        )


def test_build_schedule_request_uses_inclusive_utc_date_boundaries() -> None:
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 2)

    request = build_schedule_request(
        start_date,
        end_date,
        baseline_before_hours=1.0,
        baseline_after_hours=2.0,
        uncertainty_sigma_multiplier=2.0,
        visibility_sample_count=31,
        minimum_altitude_degrees=25.0,
        darkness_sun_altitude_degrees=-12.0,
    )

    expected_start = utc_datetime_to_julian_date(
        datetime.combine(
            start_date,
            time.min,
            tzinfo=UTC,
        )
    )
    expected_end = utc_datetime_to_julian_date(
        datetime.combine(
            end_date,
            time.max,
            tzinfo=UTC,
        )
    )

    assert request.start_jd == expected_start
    assert request.end_jd == expected_end
    assert request.end_jd - request.start_jd == pytest.approx(
        2.0,
        abs=1e-8,
    )


def test_build_schedule_request_rejects_reversed_dates() -> None:
    with pytest.raises(
        ValueError,
        match="End date must not be earlier than start date.",
    ):
        build_schedule_request(
            date(2026, 1, 2),
            date(2026, 1, 1),
            baseline_before_hours=1.0,
            baseline_after_hours=1.0,
            uncertainty_sigma_multiplier=1.0,
            visibility_sample_count=25,
            minimum_altitude_degrees=20.0,
            darkness_sun_altitude_degrees=-18.0,
        )


def test_build_schedule_request_maps_every_field() -> None:
    request = build_schedule_request(
        date(2026, 2, 3),
        date(2026, 2, 4),
        baseline_before_hours=1.25,
        baseline_after_hours=2.5,
        uncertainty_sigma_multiplier=3.0,
        visibility_sample_count=41,
        minimum_altitude_degrees=27.5,
        darkness_sun_altitude_degrees=-15.0,
    )

    assert isinstance(request, TransitScheduleRequest)
    assert request.start_jd == utc_datetime_to_julian_date(
        datetime.combine(
            date(2026, 2, 3),
            time.min,
            tzinfo=UTC,
        )
    )
    assert request.end_jd == utc_datetime_to_julian_date(
        datetime.combine(
            date(2026, 2, 4),
            time.max,
            tzinfo=UTC,
        )
    )
    assert request.baseline_before_hours == 1.25
    assert request.baseline_after_hours == 2.5
    assert request.uncertainty_sigma_multiplier == 3.0
    assert request.visibility_sample_count == 41
    assert request.minimum_altitude_degrees == 27.5
    assert request.darkness_sun_altitude_degrees == -15.0
    assert request.maximum_events_per_target == DEFAULT_MAXIMUM_EVENTS_PER_TARGET
    assert request.maximum_total_events == DEFAULT_MAXIMUM_TOTAL_EVENTS


def test_build_schedule_target_maps_every_input_field() -> None:
    input_values = {
        "planet_name": "Test b",
        "host_star_name": "Test Star",
        "right_ascension_degrees": 120.0,
        "declination_degrees": 30.0,
        "orbital_period_days": 4.5,
        "reference_mid_transit_jd": 2_460_000.25,
        "transit_duration_hours": 2.5,
        "period_uncertainty_days": 0.0001,
        "reference_epoch_uncertainty_days": 0.001,
        "transit_depth_ppm": 1_500.0,
        "host_magnitude": 10.5,
    }
    target_input = TransitDashboardTargetInput(**input_values)

    target = build_schedule_target(target_input)

    expected_ephemeris = TransitEphemeris(
        planet_name="Test b",
        orbital_period_days=4.5,
        reference_mid_transit_jd=2_460_000.25,
        transit_duration_hours=2.5,
        period_uncertainty_days=0.0001,
        reference_epoch_uncertainty_days=0.001,
    )
    expected_target = TransitTarget(
        name="Test Star",
        right_ascension_degrees=120.0,
        declination_degrees=30.0,
    )
    expected_schedule_target = TransitScheduleTarget(
        ephemeris=expected_ephemeris,
        target=expected_target,
        transit_depth_ppm=1_500.0,
        host_magnitude=10.5,
    )

    assert asdict(target_input) == input_values
    assert isinstance(target.ephemeris, TransitEphemeris)
    assert isinstance(target.target, TransitTarget)
    assert isinstance(target, TransitScheduleTarget)
    assert target.ephemeris == expected_ephemeris
    assert target.target == expected_target
    assert target == expected_schedule_target


def test_application_import_does_not_load_ui_dependencies() -> None:
    script = """
import sys

sys.path.insert(0, sys.argv[1])

import astroscope.transit_schedule_application

for dependency in ("streamlit", "plotly"):
    assert dependency not in sys.modules, dependency
"""

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(Path(__file__).resolve().parents[1] / "src"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
