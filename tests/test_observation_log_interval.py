"""Strict interval and provenance characterization for observation logs."""

import csv
from datetime import date, time
from io import StringIO

import pytest

from astroscope.observation_log import (
    CSV_FIELDNAMES,
    EquipmentSnapshot,
    ObservationLogCivilEndpoint,
    ObservationLogError,
    ObservationSession,
    TargetObservation,
    calculate_session_summary,
    resolve_observation_log_interval,
    session_from_dict,
    session_from_json,
    session_observations_to_csv,
    session_to_dict,
    session_to_json,
)
from astroscope.observation_report import ObservationReportLabels, create_markdown_report
from astroscope.observer import AmbiguousCivilTimeError, NonexistentCivilTimeError


def endpoint(day: date, clock: time, fold: int | None = None) -> ObservationLogCivilEndpoint:
    """Build one exact civil endpoint for the test matrix."""

    return ObservationLogCivilEndpoint(day, clock, fold)


def interval(
    zone: str,
    start_day: date,
    start_time: time,
    end_day: date,
    end_time: time,
    start_fold: int | None = None,
    end_fold: int | None = None,
):
    """Resolve one interval through production code."""

    return resolve_observation_log_interval(
        timezone_name=zone,
        start=endpoint(start_day, start_time, start_fold),
        end=endpoint(end_day, end_time, end_fold),
    )


def target(resolved, observation_id: str = "obs-001") -> TargetObservation:
    """Create a target backed by a resolved interval."""

    return TargetObservation(
        observation_id=observation_id,
        object_key="target",
        display_name="Target",
        category="other",
        started_at_local=resolved.start.local_datetime,
        ended_at_local=resolved.end.local_datetime,
        outcome="observed",
        quality_rating=4,
        interval=resolved,
    )


def session(resolved, observations: tuple[TargetObservation, ...] = ()) -> ObservationSession:
    """Create a session backed by a resolved interval."""

    return ObservationSession(
        session_id="session-001",
        title="Interval session",
        observer="Observer",
        location_name="Location",
        latitude_degrees=35.0,
        longitude_degrees=135.0,
        elevation_m=10.0,
        timezone_name=resolved.timezone_name,
        started_at_local=resolved.start.local_datetime,
        ended_at_local=resolved.end.local_datetime,
        mode="visual",
        equipment=EquipmentSnapshot(),
        observations=observations,
        interval=resolved,
    )


TOKYO_DAY = date(2026, 1, 15)
NEW_YORK_FALL = date(2026, 11, 1)
NEW_YORK_SPRING = date(2026, 3, 8)


def test_ordinary_tokyo_aware_constructor_compatibility() -> None:
    resolved = interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21))
    legacy = TargetObservation(
        "legacy",
        "target",
        "Target",
        "other",
        resolved.start.local_datetime,
        resolved.end.local_datetime,
        "observed",
        4,
    )
    assert session(resolved, (legacy,)).observations[0].duration_minutes == 60.0


def test_explicit_tokyo_overnight_interval() -> None:
    resolved = interval("Asia/Tokyo", TOKYO_DAY, time(20), date(2026, 1, 16), time(2))
    assert resolved.elapsed.total_seconds() == 21_600


def test_new_york_fall_back_session_duration_is_300_minutes() -> None:
    resolved = interval("America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(4))
    assert calculate_session_summary(session(resolved)).session_duration_minutes == 300.0


def test_new_york_repeated_hour_target_fold_zero_to_one_is_60_minutes() -> None:
    resolved = interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(1), 0, 1)
    assert target(resolved).duration_minutes == 60.0


@pytest.mark.parametrize("fold", [0, 1])
def test_ambiguous_session_start_fold_is_independent(fold: int) -> None:
    resolved = interval(
        "America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), fold, None
    )
    assert session(resolved).interval.start.request.fold == fold


@pytest.mark.parametrize("fold", [0, 1])
def test_ambiguous_session_end_fold_is_independent(fold: int) -> None:
    resolved = interval(
        "America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(1), None, fold
    )
    assert session(resolved).interval.end.request.fold == fold


@pytest.mark.parametrize("fold", [0, 1])
def test_ambiguous_target_start_fold_is_independent(fold: int) -> None:
    resolved = interval(
        "America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), fold, None
    )
    assert target(resolved).interval.start.request.fold == fold


@pytest.mark.parametrize("fold", [0, 1])
def test_ambiguous_target_end_fold_is_independent(fold: int) -> None:
    resolved = interval(
        "America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(1), None, fold
    )
    assert target(resolved).interval.end.request.fold == fold


def test_missing_session_fold_rejects() -> None:
    with pytest.raises(AmbiguousCivilTimeError):
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2))


def test_missing_target_fold_rejects() -> None:
    with pytest.raises(AmbiguousCivilTimeError):
        interval("America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(1))


@pytest.mark.parametrize("is_start", [True, False])
def test_new_york_nonexistent_session_endpoint_rejects(is_start: bool) -> None:
    args = (time(2, 30), time(3, 30)) if is_start else (time(1, 30), time(2, 30))
    with pytest.raises(NonexistentCivilTimeError):
        interval("America/New_York", NEW_YORK_SPRING, args[0], NEW_YORK_SPRING, args[1])


@pytest.mark.parametrize("is_start", [True, False])
def test_new_york_nonexistent_target_endpoint_rejects(is_start: bool) -> None:
    args = (time(2, 30), time(3, 30)) if is_start else (time(1, 30), time(2, 30))
    with pytest.raises(NonexistentCivilTimeError):
        interval("America/New_York", NEW_YORK_SPRING, args[0], NEW_YORK_SPRING, args[1])


def test_new_york_spring_forward_target_duration_is_60_minutes() -> None:
    resolved = interval(
        "America/New_York", NEW_YORK_SPRING, time(1, 30), NEW_YORK_SPRING, time(3, 30)
    )
    assert target(resolved).duration_minutes == 60.0


def test_london_fallback_interval_uses_utc() -> None:
    resolved = interval(
        "Europe/London", date(2026, 10, 25), time(1, 30), date(2026, 10, 25), time(1, 30), 0, 1
    )
    assert resolved.elapsed.total_seconds() == 3_600


def test_lord_howe_fold_is_30_minutes() -> None:
    resolved = interval(
        "Australia/Lord_Howe", date(2026, 4, 5), time(1, 45), date(2026, 4, 5), time(1, 45), 0, 1
    )
    assert target(resolved).duration_minutes == 30.0


@pytest.mark.parametrize("is_start", [True, False])
def test_lord_howe_gap_endpoint_rejects(is_start: bool) -> None:
    args = (time(2, 15), time(3)) if is_start else (time(1, 30), time(2, 15))
    with pytest.raises(NonexistentCivilTimeError):
        interval("Australia/Lord_Howe", date(2026, 10, 4), args[0], date(2026, 10, 4), args[1])


def test_utc_zero_length_rejects() -> None:
    with pytest.raises(ValueError, match="later"):
        interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(20))


def test_utc_reversed_interval_rejects() -> None:
    with pytest.raises(ValueError, match="later"):
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(1), 1, 0)


def test_physical_utc_containment_accepts_interior_target() -> None:
    outer = interval("America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(3))
    inner = interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), 1, None)
    assert session(outer, (target(inner),)).observations[0].interval == inner


def test_backward_transition_false_local_containment_rejects() -> None:
    outer = interval(
        "America/New_York", NEW_YORK_FALL, time(1, 30), NEW_YORK_FALL, time(2), 1, None
    )
    inner = interval(
        "America/New_York", NEW_YORK_FALL, time(1, 45), NEW_YORK_FALL, time(2), 0, None
    )
    with pytest.raises(ValueError, match="within the session"):
        session(outer, (target(inner),))


def test_half_open_session_start_boundary_is_allowed() -> None:
    outer = interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(22))
    inner = interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21))
    assert session(outer, (target(inner),)).observations


def test_half_open_session_end_boundary_is_allowed() -> None:
    outer = interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(22))
    inner = interval("Asia/Tokyo", TOKYO_DAY, time(21), TOKYO_DAY, time(22))
    assert session(outer, (target(inner),)).observations


def test_seconds_are_preserved() -> None:
    resolved = interval("Asia/Tokyo", TOKYO_DAY, time(20, 0, 1), TOKYO_DAY, time(20, 1, 2))
    assert resolved.start.local_datetime.second == 1


def test_microseconds_are_preserved() -> None:
    resolved = interval(
        "Asia/Tokyo", TOKYO_DAY, time(20, 0, 1, 123456), TOKYO_DAY, time(20, 1, 2, 654321)
    )
    assert resolved.end.local_datetime.microsecond == 654321


def _v1_payload(value: ObservationSession) -> dict[str, object]:
    payload = session_to_dict(value)
    payload["schema_version"] = 1
    session_data = payload["session"]
    assert isinstance(session_data, dict)
    session_data.pop("started_at_provenance")
    session_data.pop("ended_at_provenance")
    for observation in payload["observations"]:
        observation.pop("started_at_provenance")
        observation.pop("ended_at_provenance")
    return payload


def test_schema_v2_json_round_trip() -> None:
    original = session(interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21)))
    assert session_from_json(session_to_json(original)).interval == original.interval


def test_schema_v2_fold_provenance_round_trip() -> None:
    original = session(
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), 1, None)
    )
    assert session_from_json(session_to_json(original)).interval.start.request.fold == 1


def test_schema_v2_named_zone_provenance_round_trip() -> None:
    original = session(
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), 1, None)
    )
    imported = session_from_json(session_to_json(original))
    assert imported.started_at_local.tzinfo.key == "America/New_York"


def test_schema_v2_canonical_utc_round_trip() -> None:
    original = session(
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), 1, None)
    )
    imported = session_from_json(session_to_json(original))
    assert imported.interval.start.utc_datetime == original.interval.start.utc_datetime


def test_schema_v1_ordinary_import() -> None:
    original = session(interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21)))
    assert session_from_dict(_v1_payload(original)).started_at_local.tzinfo.key == "Asia/Tokyo"


@pytest.mark.parametrize("fold", [0, 1])
def test_schema_v1_ambiguous_fold_is_inferred(fold: int) -> None:
    original = session(
        interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), fold, None)
    )
    assert session_from_dict(_v1_payload(original)).interval.start.request.fold == fold


def test_schema_v1_nonexistent_provenance_rejects() -> None:
    payload = _v1_payload(
        session(interval("America/New_York", NEW_YORK_SPRING, time(1), NEW_YORK_SPRING, time(3)))
    )
    payload["session"]["started_at_local"] = "2026-03-08T02:30:00-05:00"
    with pytest.raises(ObservationLogError, match="provenance"):
        session_from_dict(payload)


def test_schema_v1_inconsistent_offset_zone_rejects() -> None:
    payload = _v1_payload(session(interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21))))
    payload["session"]["started_at_local"] = "2026-01-15T20:00:00+00:00"
    with pytest.raises(ObservationLogError, match="provenance"):
        session_from_dict(payload)


def test_unsupported_schema_version_rejects() -> None:
    payload = session_to_dict(
        session(interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21)))
    )
    payload["schema_version"] = 99
    with pytest.raises(ObservationLogError, match="schema version"):
        session_from_dict(payload)


def test_existing_csv_columns_keep_their_order() -> None:
    value = session(
        interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21)),
        (target(interval("Asia/Tokyo", TOKYO_DAY, time(20), TOKYO_DAY, time(21))),),
    )
    assert next(csv.reader(StringIO(session_observations_to_csv(value))))[:23] == list(
        CSV_FIELDNAMES[:23]
    )


def test_csv_v2_appends_provenance_values() -> None:
    resolved = interval("America/New_York", NEW_YORK_FALL, time(1), NEW_YORK_FALL, time(2), 1, None)
    value = session(resolved, (target(resolved),))
    row = next(csv.DictReader(StringIO(session_observations_to_csv(value))))
    assert row["schema_version"] == "2"
    assert row["session_start_fold"] == "1"
    assert row["session_start_utc"].endswith("Z")


def _labels() -> ObservationReportLabels:
    return ObservationReportLabels(*("Label",) * len(ObservationReportLabels.__dataclass_fields__))


def test_report_uses_utc_duration_with_civil_display() -> None:
    resolved = interval("America/New_York", NEW_YORK_FALL, time(0), NEW_YORK_FALL, time(4))
    report = create_markdown_report(
        session(resolved), labels=_labels(), mode_names={}, outcome_names={}, category_names={}
    )
    assert "300.0 min" in report
    assert "2026-11-01T00:00:00-04:00" in report
