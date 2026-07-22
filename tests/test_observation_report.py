"""Tests for Markdown observation reports."""

from datetime import datetime
from zoneinfo import ZoneInfo

from astroscope.observation_log import (
    EquipmentSnapshot,
    ObservationSession,
    TargetObservation,
)
from astroscope.observation_report import (
    ObservationReportLabels,
    create_markdown_report,
)

TOKYO = ZoneInfo("Asia/Tokyo")


def create_labels() -> ObservationReportLabels:
    """Create deterministic English report labels."""

    return ObservationReportLabels(
        title="Observation report",
        session_details="Session details",
        conditions="Conditions",
        equipment="Equipment",
        observations="Observations",
        summary="Summary",
        session_id="Session ID",
        observer="Observer",
        location="Location",
        mode="Mode",
        start="Start",
        end="End",
        session_duration="Session duration",
        seeing="Seeing",
        transparency="Transparency",
        cloud_cover="Cloud cover",
        telescope="Telescope",
        aperture="Aperture",
        focal_length="Focal length",
        eyepiece="Eyepiece",
        camera="Camera",
        pixel_size="Pixel size",
        mount="Mount",
        filters="Filters",
        object_name="Object",
        category="Category",
        observation_time="Time",
        duration_minutes="Minutes",
        outcome="Outcome",
        quality="Quality",
        altitude="Altitude",
        exposure="Exposure",
        frames="Accepted/captured",
        accepted_integration="Accepted integration",
        notes="Notes",
        no_observations="No observations recorded.",
        observation_count="Observation count",
        completion="Completion",
        average_quality="Average quality",
        target_time="Target time",
        frame_acceptance="Frame acceptance",
        not_recorded="Not recorded",
    )


def create_session(
    *,
    observations: tuple[TargetObservation, ...],
) -> ObservationSession:
    """Create one deterministic report session."""

    return ObservationSession(
        session_id="session-001",
        title="Galaxy night",
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
        equipment=EquipmentSnapshot(
            telescope_name="130 mm reflector",
            aperture_mm=130.0,
            focal_length_mm=650.0,
            camera_name="APS-C camera",
            filters=("UV/IR cut",),
        ),
        observations=observations,
        seeing_arcseconds=2.0,
        transparency_rating=4,
        cloud_cover_percent=10.0,
        general_notes="Stable conditions.",
    )


def test_report_contains_session_and_observation() -> None:
    observation = TargetObservation(
        observation_id="obs-001",
        object_key="m31",
        display_name="Andromeda Galaxy",
        category="galaxy",
        started_at_local=datetime(
            2026,
            10,
            1,
            20,
            0,
            tzinfo=TOKYO,
        ),
        ended_at_local=datetime(
            2026,
            10,
            1,
            21,
            0,
            tzinfo=TOKYO,
        ),
        outcome="observed",
        quality_rating=4,
        exposure_seconds=120.0,
        frames_captured=30,
        frames_accepted=24,
        notes="Bright core.",
    )

    report = create_markdown_report(
        create_session(observations=(observation,)),
        labels=create_labels(),
        mode_names={"mixed": "Mixed"},
        outcome_names={"observed": "Observed"},
        category_names={"galaxy": "Galaxy"},
    )

    assert "# Observation report: Galaxy night" in report
    assert "Andromeda Galaxy" in report
    assert "Galaxy" in report
    assert "80.0%" in report
    assert "2880.0 s" in report


def test_empty_report_contains_no_observations_message() -> None:
    report = create_markdown_report(
        create_session(observations=()),
        labels=create_labels(),
        mode_names={"mixed": "Mixed"},
        outcome_names={},
        category_names={},
    )

    assert "No observations recorded." in report
    assert "Observation count:** 0" in report


def test_report_escapes_table_characters() -> None:
    observation = TargetObservation(
        observation_id="obs-pipe",
        object_key="test",
        display_name="Target | Region",
        category="other",
        started_at_local=datetime(
            2026,
            10,
            1,
            20,
            0,
            tzinfo=TOKYO,
        ),
        ended_at_local=datetime(
            2026,
            10,
            1,
            20,
            30,
            tzinfo=TOKYO,
        ),
        outcome="partial",
        quality_rating=3,
        notes="Line one\nLine | two",
    )

    report = create_markdown_report(
        create_session(observations=(observation,)),
        labels=create_labels(),
        mode_names={"mixed": "Mixed"},
        outcome_names={"partial": "Partial"},
        category_names={"other": "Other"},
    )

    assert "Target \\| Region" in report
    assert "Line \\| two" in report
    assert "Line one Line" in report
