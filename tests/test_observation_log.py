"""Tests for structured astronomical observation logs."""

import csv
import json
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import pytest

from astroscope.observation_log import (
    EquipmentSnapshot,
    ObservationLogError,
    ObservationSession,
    TargetObservation,
    calculate_session_summary,
    session_from_json,
    session_observations_to_csv,
    session_to_json,
)

TOKYO = ZoneInfo("Asia/Tokyo")


def create_equipment() -> EquipmentSnapshot:
    """Create deterministic observing equipment."""

    return EquipmentSnapshot(
        telescope_name="130 mm reflector",
        aperture_mm=130.0,
        focal_length_mm=650.0,
        eyepiece_name="25 mm Plossl",
        camera_name="APS-C camera",
        pixel_size_um=3.76,
        mount_name="Equatorial mount",
        filters=("UV/IR cut", "Dual narrowband"),
    )


def create_observation(
    *,
    observation_id: str = "obs-001",
    object_key: str = "m31",
    display_name: str = "Andromeda Galaxy",
    start_hour: int = 20,
    end_hour: int = 21,
    outcome: str = "observed",
    quality_rating: int = 4,
    exposure_seconds: float = 120.0,
    frames_captured: int = 30,
    frames_accepted: int = 24,
) -> TargetObservation:
    """Create one deterministic target observation."""

    return TargetObservation(
        observation_id=observation_id,
        object_key=object_key,
        display_name=display_name,
        category="deep_sky",
        started_at_local=datetime(
            2026,
            10,
            1,
            start_hour,
            0,
            tzinfo=TOKYO,
        ),
        ended_at_local=datetime(
            2026,
            10,
            1,
            end_hour,
            0,
            tzinfo=TOKYO,
        ),
        outcome=outcome,
        quality_rating=quality_rating,
        altitude_degrees=55.0,
        notes="Clear spiral core.",
        exposure_seconds=exposure_seconds,
        frames_captured=frames_captured,
        frames_accepted=frames_accepted,
    )


def create_session(
    observations: tuple[
        TargetObservation,
        ...,
    ]
    | None = None,
) -> ObservationSession:
    """Create one deterministic observing session."""

    if observations is None:
        observations = (create_observation(),)

    return ObservationSession(
        session_id="session-2026-10-01",
        title="Autumn galaxy night",
        observer="Test Observer",
        location_name="Osaka",
        latitude_degrees=34.6937,
        longitude_degrees=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        started_at_local=datetime(
            2026,
            10,
            1,
            19,
            0,
            tzinfo=TOKYO,
        ),
        ended_at_local=datetime(
            2026,
            10,
            1,
            23,
            0,
            tzinfo=TOKYO,
        ),
        mode="mixed",
        equipment=create_equipment(),
        observations=observations,
        seeing_arcseconds=2.0,
        transparency_rating=4,
        cloud_cover_percent=10.0,
        general_notes="Stable conditions.",
    )


def test_equipment_snapshot_accepts_valid_values() -> None:
    equipment = create_equipment()

    assert equipment.aperture_mm == 130.0
    assert len(equipment.filters) == 2


def test_target_observation_calculates_metrics() -> None:
    observation = create_observation()

    assert observation.duration_minutes == (pytest.approx(60.0))

    assert observation.accepted_integration_seconds == pytest.approx(2880.0)


def test_session_summary_calculates_totals() -> None:
    observations = (
        create_observation(
            observation_id="obs-001",
            outcome="observed",
            quality_rating=5,
            frames_captured=30,
            frames_accepted=24,
        ),
        create_observation(
            observation_id="obs-002",
            object_key="m42",
            display_name="Orion Nebula",
            start_hour=21,
            end_hour=22,
            outcome="partial",
            quality_rating=3,
            exposure_seconds=60.0,
            frames_captured=20,
            frames_accepted=10,
        ),
    )

    summary = calculate_session_summary(create_session(observations))

    assert summary.session_duration_minutes == 240.0
    assert summary.observation_count == 2
    assert summary.observed_count == 1
    assert summary.partial_count == 1

    assert summary.weighted_completion_percent == 75.0

    assert summary.average_quality_rating == 4.0
    assert summary.captured_frames == 50
    assert summary.accepted_frames == 34
    assert summary.frame_acceptance_percent == 68.0

    assert summary.accepted_integration_seconds == pytest.approx(3480.0)


def test_json_round_trip_preserves_session() -> None:
    original = create_session()

    exported = session_to_json(original)

    imported = session_from_json(exported)

    assert imported == original


def test_json_export_contains_summary() -> None:
    payload = json.loads(session_to_json(create_session()))

    assert payload["schema_version"] == 2

    assert payload["summary"]["observation_count"] == 1

    assert payload["summary"]["accepted_integration_seconds"] == 2880.0


def test_csv_export_contains_target_row() -> None:
    csv_text = session_observations_to_csv(create_session())

    rows = list(csv.DictReader(StringIO(csv_text)))

    assert len(rows) == 1
    assert rows[0]["object_key"] == "m31"

    assert rows[0]["accepted_integration_seconds"] == "2880.0"


def test_empty_session_summary_is_zero() -> None:
    summary = calculate_session_summary(create_session(()))

    assert summary.observation_count == 0
    assert summary.weighted_completion_percent == 0.0
    assert summary.average_quality_rating == 0.0
    assert summary.frame_acceptance_percent == 0.0


def test_empty_session_csv_contains_header_only() -> None:
    csv_text = session_observations_to_csv(create_session(()))

    lines = csv_text.strip().splitlines()

    assert len(lines) == 1
    assert "session_id" in lines[0]


@pytest.mark.parametrize(
    (
        "latitude",
        "longitude",
    ),
    [
        (91.0, 135.0),
        (-91.0, 135.0),
        (35.0, 181.0),
    ],
)
def test_invalid_coordinates_raise_error(
    latitude: float,
    longitude: float,
) -> None:
    with pytest.raises(ValueError):
        ObservationSession(
            session_id="invalid-location",
            title="Invalid",
            observer="Observer",
            location_name="Nowhere",
            latitude_degrees=latitude,
            longitude_degrees=longitude,
            elevation_m=0.0,
            timezone_name="UTC",
            started_at_local=datetime(
                2026,
                1,
                1,
                20,
                0,
                tzinfo=ZoneInfo("UTC"),
            ),
            ended_at_local=datetime(
                2026,
                1,
                1,
                21,
                0,
                tzinfo=ZoneInfo("UTC"),
            ),
            mode="visual",
            equipment=EquipmentSnapshot(),
        )


def test_naive_session_datetime_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ObservationSession(
            session_id="naive-session",
            title="Naive",
            observer="Observer",
            location_name="Osaka",
            latitude_degrees=34.0,
            longitude_degrees=135.0,
            elevation_m=0.0,
            timezone_name="Asia/Tokyo",
            started_at_local=datetime(
                2026,
                1,
                1,
                20,
                0,
            ),
            ended_at_local=datetime(
                2026,
                1,
                1,
                21,
                0,
                tzinfo=TOKYO,
            ),
            mode="visual",
            equipment=EquipmentSnapshot(),
        )


def test_invalid_observation_time_order_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="later",
    ):
        TargetObservation(
            observation_id="invalid-time",
            object_key="mars",
            display_name="Mars",
            category="solar_system",
            started_at_local=datetime(
                2026,
                1,
                1,
                21,
                0,
                tzinfo=TOKYO,
            ),
            ended_at_local=datetime(
                2026,
                1,
                1,
                20,
                0,
                tzinfo=TOKYO,
            ),
            outcome="not_observed",
            quality_rating=1,
        )


def test_accepted_frames_cannot_exceed_captured() -> None:
    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        create_observation(
            frames_captured=10,
            frames_accepted=11,
        )


def test_duplicate_observation_ids_raise_error() -> None:
    first = create_observation(
        observation_id="duplicate",
    )

    second = create_observation(
        observation_id="duplicate",
        object_key="m42",
        display_name="Orion Nebula",
        start_hour=21,
        end_hour=22,
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        create_session(
            (
                first,
                second,
            )
        )


def test_observation_outside_session_raises_error() -> None:
    outside_observation = TargetObservation(
        observation_id="outside",
        object_key="venus",
        display_name="Venus",
        category="solar_system",
        started_at_local=datetime(
            2026,
            10,
            1,
            18,
            0,
            tzinfo=TOKYO,
        ),
        ended_at_local=datetime(
            2026,
            10,
            1,
            18,
            30,
            tzinfo=TOKYO,
        ),
        outcome="observed",
        quality_rating=3,
    )

    with pytest.raises(
        ValueError,
        match="within the session",
    ):
        create_session((outside_observation,))


def test_invalid_json_raises_log_error() -> None:
    with pytest.raises(
        ObservationLogError,
        match="invalid JSON",
    ):
        session_from_json("{broken json")


def test_invalid_schema_version_raises_error() -> None:
    payload = json.loads(session_to_json(create_session()))

    payload["schema_version"] = 999

    with pytest.raises(
        ObservationLogError,
        match="schema version",
    ):
        session_from_json(json.dumps(payload))


def test_invalid_session_mode_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported session mode",
    ):
        ObservationSession(
            session_id="invalid-mode",
            title="Invalid mode",
            observer="Observer",
            location_name="Osaka",
            latitude_degrees=34.0,
            longitude_degrees=135.0,
            elevation_m=0.0,
            timezone_name="Asia/Tokyo",
            started_at_local=datetime(
                2026,
                1,
                1,
                20,
                0,
                tzinfo=TOKYO,
            ),
            ended_at_local=datetime(
                2026,
                1,
                1,
                21,
                0,
                tzinfo=TOKYO,
            ),
            mode="unknown",
            equipment=EquipmentSnapshot(),
        )
