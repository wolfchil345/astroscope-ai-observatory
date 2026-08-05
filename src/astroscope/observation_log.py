"""Structured astronomical observation logs and exports."""

import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from io import StringIO
from math import isfinite
from typing import Any, Final, Literal

from astroscope.observer import (
    CivilTimeStatus,
    classify_local_datetime,
    get_timezone,
    resolve_local_datetime,
)

SessionMode = Literal[
    "visual",
    "imaging",
    "mixed",
]

ObservationOutcome = Literal[
    "observed",
    "partial",
    "not_observed",
]

VALID_SESSION_MODES: Final[set[str]] = {
    "visual",
    "imaging",
    "mixed",
}

VALID_OBSERVATION_OUTCOMES: Final[set[str]] = {
    "observed",
    "partial",
    "not_observed",
}

OBSERVATION_LOG_SCHEMA_VERSION: Final[int] = 2

CSV_FIELDNAMES: Final[tuple[str, ...]] = (
    "session_id",
    "session_title",
    "observer",
    "location_name",
    "timezone_name",
    "session_mode",
    "session_start",
    "session_end",
    "observation_id",
    "object_key",
    "display_name",
    "category",
    "observation_start",
    "observation_end",
    "duration_minutes",
    "outcome",
    "quality_rating",
    "altitude_degrees",
    "exposure_seconds",
    "frames_captured",
    "frames_accepted",
    "accepted_integration_seconds",
    "notes",
    "schema_version",
    "session_start_fold",
    "session_end_fold",
    "session_start_utc",
    "session_end_utc",
    "observation_start_fold",
    "observation_end_fold",
    "observation_start_utc",
    "observation_end_utc",
)


class ObservationLogError(ValueError):
    """Raised when observation-log data cannot be parsed."""


@dataclass(frozen=True, slots=True)
class ObservationLogCivilEndpoint:
    """One requested civil endpoint before strict named-zone resolution."""

    local_date: date
    local_time: time
    fold: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.local_date, date):
            raise ValueError("Observation endpoint date must be a date.")
        if not isinstance(self.local_time, time):
            raise ValueError("Observation endpoint time must be a time.")
        if self.fold is not None and (type(self.fold) is not int or self.fold not in (0, 1)):
            raise ValueError("Observation endpoint fold must be None, 0, or 1.")


@dataclass(frozen=True, slots=True)
class ResolvedObservationLogEndpoint:
    """A civil endpoint with named-zone provenance and canonical UTC."""

    request: ObservationLogCivilEndpoint
    timezone_name: str
    local_datetime: datetime
    utc_datetime: datetime


@dataclass(frozen=True, slots=True)
class ResolvedObservationLogInterval:
    """One UTC-authoritative, half-open observation-log interval."""

    timezone_name: str
    start: ResolvedObservationLogEndpoint
    end: ResolvedObservationLogEndpoint

    def __post_init__(self) -> None:
        if (
            self.start.timezone_name != self.timezone_name
            or self.end.timezone_name != self.timezone_name
        ):
            raise ValueError("Observation interval endpoints must use the session timezone.")
        if self.end.utc_datetime <= self.start.utc_datetime:
            raise ValueError(
                "Observation interval end must be later than observation interval start."
            )

    @property
    def elapsed(self) -> timedelta:
        """Return the physical elapsed duration in UTC."""

        return self.end.utc_datetime - self.start.utc_datetime


def _utc_iso(value: datetime) -> str:
    """Serialize one UTC datetime using the canonical Z suffix."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc_iso(value: object, label: str) -> datetime:
    """Parse a canonical UTC field accepted by schema version 2."""

    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    _validate_aware_datetime(parsed, label)
    if parsed.utcoffset() != timedelta(0):
        raise ObservationLogError(f"{label} must use UTC.")
    return parsed.astimezone(UTC)


def _endpoint_from_civil(
    endpoint: ObservationLogCivilEndpoint,
    timezone_name: str,
) -> ResolvedObservationLogEndpoint:
    """Resolve one strict civil endpoint through the Mission 26 authority."""

    classification = classify_local_datetime(
        local_date=endpoint.local_date,
        local_time=endpoint.local_time,
        timezone_name=timezone_name,
    )
    if classification.status is CivilTimeStatus.NORMAL and endpoint.fold is not None:
        raise ValueError("A normal observation endpoint must not specify a fold.")
    utc_datetime = resolve_local_datetime(
        local_date=endpoint.local_date,
        local_time=endpoint.local_time,
        timezone_name=timezone_name,
        fold=endpoint.fold,
    )
    return ResolvedObservationLogEndpoint(
        request=endpoint,
        timezone_name=timezone_name,
        local_datetime=utc_datetime.astimezone(get_timezone(timezone_name)),
        utc_datetime=utc_datetime,
    )


def resolve_observation_log_interval(
    *,
    timezone_name: str,
    start: ObservationLogCivilEndpoint,
    end: ObservationLogCivilEndpoint,
) -> ResolvedObservationLogInterval:
    """Resolve a strict, UTC-authoritative observation-log interval."""

    return ResolvedObservationLogInterval(
        timezone_name=timezone_name,
        start=_endpoint_from_civil(start, timezone_name),
        end=_endpoint_from_civil(end, timezone_name),
    )


def _validate_non_empty_string(
    value: str,
    label: str,
) -> None:
    """Require a non-empty text value."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be empty.")


def _validate_positive_optional(
    value: float | None,
    label: str,
) -> None:
    """Validate an optional positive finite number."""

    if value is None:
        return

    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be a positive finite number.")


def _validate_non_negative_float(
    value: float,
    label: str,
) -> None:
    """Validate a finite value greater than or equal to zero."""

    if not isfinite(value) or value < 0.0:
        raise ValueError(f"{label} must be a non-negative finite number.")


def _validate_non_negative_integer(
    value: int,
    label: str,
) -> None:
    """Validate a non-negative integer."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer.")


def _validate_aware_datetime(
    value: datetime,
    label: str,
) -> None:
    """Require a timezone-aware datetime."""

    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware.")


def _endpoint_from_aware_datetime(
    value: datetime,
    *,
    timezone_name: str,
    label: str,
) -> ResolvedObservationLogEndpoint:
    """Interpret one legacy aware datetime against its named-zone provenance.

    Legacy datetimes are instant-bearing.  Their offset and wall label must
    nevertheless match exactly one real candidate in the session's named zone.
    """

    _validate_aware_datetime(value, label)
    timezone_info = get_timezone(timezone_name)
    requested_local = value.replace(tzinfo=None)
    utc_datetime = value.astimezone(UTC)
    named_local = utc_datetime.astimezone(timezone_info)

    if (
        named_local.replace(tzinfo=None) != requested_local
        or named_local.utcoffset() != value.utcoffset()
    ):
        raise ValueError(f"{label} is inconsistent with timezone {timezone_name}.")

    classification = classify_local_datetime(
        local_date=requested_local.date(),
        local_time=requested_local.timetz().replace(tzinfo=None),
        timezone_name=timezone_name,
    )
    if classification.status is CivilTimeStatus.NONEXISTENT:
        raise ValueError(f"{label} is nonexistent in timezone {timezone_name}.")

    fold: int | None
    if classification.status is CivilTimeStatus.AMBIGUOUS:
        matches = [
            candidate
            for candidate in classification.candidates
            if candidate.utc_datetime == utc_datetime and candidate.utc_offset == value.utcoffset()
        ]
        if len(matches) != 1:
            raise ValueError(f"{label} is inconsistent with timezone {timezone_name}.")
        fold = matches[0].fold
    else:
        fold = None

    endpoint = ObservationLogCivilEndpoint(
        local_date=requested_local.date(),
        local_time=requested_local.timetz().replace(tzinfo=None),
        fold=fold,
    )
    resolved = _endpoint_from_civil(endpoint, timezone_name)
    if resolved.utc_datetime != utc_datetime:
        raise ValueError(f"{label} is inconsistent with timezone {timezone_name}.")
    return resolved


def _interval_from_aware_datetimes(
    *,
    timezone_name: str,
    started_at_local: datetime,
    ended_at_local: datetime,
    start_label: str,
    end_label: str,
) -> ResolvedObservationLogInterval:
    """Build strict interval state from compatibility-aware datetimes."""

    return ResolvedObservationLogInterval(
        timezone_name=timezone_name,
        start=_endpoint_from_aware_datetime(
            started_at_local,
            timezone_name=timezone_name,
            label=start_label,
        ),
        end=_endpoint_from_aware_datetime(
            ended_at_local,
            timezone_name=timezone_name,
            label=end_label,
        ),
    )


@dataclass(frozen=True, slots=True)
class EquipmentSnapshot:
    """Equipment used during one observing session."""

    telescope_name: str = ""
    aperture_mm: float | None = None
    focal_length_mm: float | None = None
    eyepiece_name: str = ""
    camera_name: str = ""
    pixel_size_um: float | None = None
    mount_name: str = ""
    filters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_positive_optional(
            self.aperture_mm,
            "Telescope aperture",
        )

        _validate_positive_optional(
            self.focal_length_mm,
            "Telescope focal length",
        )

        _validate_positive_optional(
            self.pixel_size_um,
            "Camera pixel size",
        )

        for filter_name in self.filters:
            _validate_non_empty_string(
                filter_name,
                "Filter name",
            )


@dataclass(frozen=True, slots=True)
class TargetObservation:
    """One target observation inside a session."""

    observation_id: str
    object_key: str
    display_name: str
    category: str
    started_at_local: datetime
    ended_at_local: datetime
    outcome: ObservationOutcome
    quality_rating: int
    altitude_degrees: float | None = None
    notes: str = ""
    exposure_seconds: float = 0.0
    frames_captured: int = 0
    frames_accepted: int = 0
    interval: ResolvedObservationLogInterval | None = None

    def __post_init__(self) -> None:
        text_values = {
            "Observation ID": self.observation_id,
            "Object key": self.object_key,
            "Display name": self.display_name,
            "Category": self.category,
        }

        for label, value in text_values.items():
            _validate_non_empty_string(
                value,
                label,
            )

        _validate_aware_datetime(
            self.started_at_local,
            "Observation start",
        )

        _validate_aware_datetime(
            self.ended_at_local,
            "Observation end",
        )

        if self.ended_at_local.astimezone(UTC) <= self.started_at_local.astimezone(UTC):
            raise ValueError("Observation end must be later than observation start.")

        if self.interval is not None:
            if (
                self.interval.start.local_datetime != self.started_at_local
                or self.interval.end.local_datetime != self.ended_at_local
            ):
                raise ValueError("Observation interval does not match its local endpoints.")

        if self.outcome not in VALID_OBSERVATION_OUTCOMES:
            raise ValueError(f"Unsupported observation outcome: {self.outcome!r}")

        if (
            isinstance(self.quality_rating, bool)
            or not isinstance(self.quality_rating, int)
            or not 1 <= self.quality_rating <= 5
        ):
            raise ValueError("Quality rating must be an integer between 1 and 5.")

        if self.altitude_degrees is not None:
            if not isfinite(self.altitude_degrees) or not -90.0 <= self.altitude_degrees <= 90.0:
                raise ValueError("Altitude must be between -90 and 90 degrees.")

        _validate_non_negative_float(
            self.exposure_seconds,
            "Exposure duration",
        )

        _validate_non_negative_integer(
            self.frames_captured,
            "Captured frames",
        )

        _validate_non_negative_integer(
            self.frames_accepted,
            "Accepted frames",
        )

        if self.frames_accepted > self.frames_captured:
            raise ValueError("Accepted frames cannot exceed captured frames.")

    @property
    def duration_minutes(self) -> float:
        """Return target-observation duration in minutes."""

        if self.interval is not None:
            duration_seconds = self.interval.elapsed.total_seconds()
        else:
            duration_seconds = (
                self.ended_at_local.astimezone(UTC) - self.started_at_local.astimezone(UTC)
            ).total_seconds()

        return duration_seconds / 60.0

    @property
    def accepted_integration_seconds(self) -> float:
        """Return accepted imaging integration time."""

        return self.exposure_seconds * self.frames_accepted


@dataclass(frozen=True, slots=True)
class ObservationSession:
    """One complete astronomical observing session."""

    session_id: str
    title: str
    observer: str
    location_name: str
    latitude_degrees: float
    longitude_degrees: float
    elevation_m: float
    timezone_name: str
    started_at_local: datetime
    ended_at_local: datetime
    mode: SessionMode
    equipment: EquipmentSnapshot
    observations: tuple[TargetObservation, ...] = ()
    seeing_arcseconds: float | None = None
    transparency_rating: int | None = None
    cloud_cover_percent: float | None = None
    general_notes: str = ""
    interval: ResolvedObservationLogInterval | None = None

    def __post_init__(self) -> None:
        text_values = {
            "Session ID": self.session_id,
            "Session title": self.title,
            "Observer": self.observer,
            "Location name": self.location_name,
            "Timezone name": self.timezone_name,
        }

        for label, value in text_values.items():
            _validate_non_empty_string(
                value,
                label,
            )

        if not isfinite(self.latitude_degrees) or not -90.0 <= self.latitude_degrees <= 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees.")

        if not isfinite(self.longitude_degrees) or not -180.0 <= self.longitude_degrees <= 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees.")

        if not isfinite(self.elevation_m):
            raise ValueError("Elevation must be finite.")

        _validate_aware_datetime(
            self.started_at_local,
            "Session start",
        )

        _validate_aware_datetime(
            self.ended_at_local,
            "Session end",
        )

        resolved_interval = self.interval or _interval_from_aware_datetimes(
            timezone_name=self.timezone_name,
            started_at_local=self.started_at_local,
            ended_at_local=self.ended_at_local,
            start_label="Session start",
            end_label="Session end",
        )
        if resolved_interval.timezone_name != self.timezone_name:
            raise ValueError("Session interval timezone must match timezone name.")
        object.__setattr__(self, "interval", resolved_interval)
        object.__setattr__(self, "started_at_local", resolved_interval.start.local_datetime)
        object.__setattr__(self, "ended_at_local", resolved_interval.end.local_datetime)

        if self.mode not in VALID_SESSION_MODES:
            raise ValueError(f"Unsupported session mode: {self.mode!r}")

        _validate_positive_optional(
            self.seeing_arcseconds,
            "Atmospheric seeing",
        )

        if self.transparency_rating is not None:
            if (
                isinstance(
                    self.transparency_rating,
                    bool,
                )
                or not isinstance(
                    self.transparency_rating,
                    int,
                )
                or not 1 <= self.transparency_rating <= 5
            ):
                raise ValueError("Transparency rating must be an integer between 1 and 5.")

        if self.cloud_cover_percent is not None:
            if (
                not isfinite(self.cloud_cover_percent)
                or not 0.0 <= self.cloud_cover_percent <= 100.0
            ):
                raise ValueError("Cloud cover must be between 0 and 100 percent.")

        observation_ids: set[str] = set()

        for observation in self.observations:
            if observation.observation_id in (observation_ids):
                raise ValueError("Observation IDs must be unique within a session.")

            observation_ids.add(observation.observation_id)

            observation_interval = observation.interval or _interval_from_aware_datetimes(
                timezone_name=self.timezone_name,
                started_at_local=observation.started_at_local,
                ended_at_local=observation.ended_at_local,
                start_label="Observation start",
                end_label="Observation end",
            )
            if observation_interval.timezone_name != self.timezone_name:
                raise ValueError("Every target observation must use the session timezone.")
            object.__setattr__(observation, "interval", observation_interval)
            object.__setattr__(
                observation, "started_at_local", observation_interval.start.local_datetime
            )
            object.__setattr__(
                observation, "ended_at_local", observation_interval.end.local_datetime
            )

            if (
                observation_interval.start.utc_datetime < resolved_interval.start.utc_datetime
                or observation_interval.end.utc_datetime > resolved_interval.end.utc_datetime
            ):
                raise ValueError("Every target observation must occur within the session.")


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Calculated summary of one observation session."""

    session_duration_minutes: float
    observation_count: int
    observed_count: int
    partial_count: int
    not_observed_count: int
    weighted_completion_percent: float
    average_quality_rating: float
    total_target_time_minutes: float
    captured_frames: int
    accepted_frames: int
    frame_acceptance_percent: float
    accepted_integration_seconds: float


def calculate_session_summary(
    session: ObservationSession,
) -> SessionSummary:
    """Calculate aggregate values for one session."""

    if session.interval is None:
        raise ValueError("Observation session has no resolved interval.")
    session_duration_minutes = session.interval.elapsed.total_seconds() / 60.0

    observed_count = sum(observation.outcome == "observed" for observation in session.observations)

    partial_count = sum(observation.outcome == "partial" for observation in session.observations)

    not_observed_count = sum(
        observation.outcome == "not_observed" for observation in session.observations
    )

    observation_count = len(session.observations)

    if observation_count:
        weighted_completion_percent = (
            (observed_count + partial_count * 0.5) / observation_count * 100.0
        )

        average_quality_rating = (
            sum(observation.quality_rating for observation in session.observations)
            / observation_count
        )
    else:
        weighted_completion_percent = 0.0
        average_quality_rating = 0.0

    total_target_time_minutes = sum(
        observation.duration_minutes for observation in session.observations
    )

    captured_frames = sum(observation.frames_captured for observation in session.observations)

    accepted_frames = sum(observation.frames_accepted for observation in session.observations)

    if captured_frames:
        frame_acceptance_percent = accepted_frames / captured_frames * 100.0
    else:
        frame_acceptance_percent = 0.0

    accepted_integration_seconds = sum(
        observation.accepted_integration_seconds for observation in session.observations
    )

    return SessionSummary(
        session_duration_minutes=round(
            session_duration_minutes,
            2,
        ),
        observation_count=observation_count,
        observed_count=observed_count,
        partial_count=partial_count,
        not_observed_count=(not_observed_count),
        weighted_completion_percent=round(
            weighted_completion_percent,
            2,
        ),
        average_quality_rating=round(
            average_quality_rating,
            2,
        ),
        total_target_time_minutes=round(
            total_target_time_minutes,
            2,
        ),
        captured_frames=captured_frames,
        accepted_frames=accepted_frames,
        frame_acceptance_percent=round(
            frame_acceptance_percent,
            2,
        ),
        accepted_integration_seconds=round(
            accepted_integration_seconds,
            2,
        ),
    )


def _endpoint_provenance(
    endpoint: ResolvedObservationLogEndpoint,
) -> dict[str, object]:
    """Return append-only schema-v2 provenance for one endpoint."""

    return {
        "fold": endpoint.request.fold,
        "utc": _utc_iso(endpoint.utc_datetime),
    }


def _require_observation_interval(
    observation: TargetObservation,
) -> ResolvedObservationLogInterval:
    """Return a target interval after session construction normalized it."""

    if observation.interval is None:
        raise ValueError("Target observation has no resolved interval.")
    return observation.interval


def session_to_dict(
    session: ObservationSession,
) -> dict[str, Any]:
    """Convert one observation session into JSON-safe data."""

    summary = calculate_session_summary(session)

    if session.interval is None:
        raise ValueError("Observation session has no resolved interval.")

    return {
        "schema_version": (OBSERVATION_LOG_SCHEMA_VERSION),
        "session": {
            "session_id": session.session_id,
            "title": session.title,
            "observer": session.observer,
            "location_name": (session.location_name),
            "latitude_degrees": (session.latitude_degrees),
            "longitude_degrees": (session.longitude_degrees),
            "elevation_m": session.elevation_m,
            "timezone_name": (session.timezone_name),
            "started_at_local": (session.started_at_local.isoformat()),
            "ended_at_local": (session.ended_at_local.isoformat()),
            "started_at_provenance": _endpoint_provenance(session.interval.start),
            "ended_at_provenance": _endpoint_provenance(session.interval.end),
            "mode": session.mode,
            "seeing_arcseconds": (session.seeing_arcseconds),
            "transparency_rating": (session.transparency_rating),
            "cloud_cover_percent": (session.cloud_cover_percent),
            "general_notes": (session.general_notes),
        },
        "equipment": {
            "telescope_name": (session.equipment.telescope_name),
            "aperture_mm": (session.equipment.aperture_mm),
            "focal_length_mm": (session.equipment.focal_length_mm),
            "eyepiece_name": (session.equipment.eyepiece_name),
            "camera_name": (session.equipment.camera_name),
            "pixel_size_um": (session.equipment.pixel_size_um),
            "mount_name": (session.equipment.mount_name),
            "filters": list(session.equipment.filters),
        },
        "observations": [
            {
                "observation_id": (observation.observation_id),
                "object_key": (observation.object_key),
                "display_name": (observation.display_name),
                "category": observation.category,
                "started_at_local": (observation.started_at_local.isoformat()),
                "ended_at_local": (observation.ended_at_local.isoformat()),
                "started_at_provenance": _endpoint_provenance(
                    _require_observation_interval(observation).start
                ),
                "ended_at_provenance": _endpoint_provenance(
                    _require_observation_interval(observation).end
                ),
                "outcome": observation.outcome,
                "quality_rating": (observation.quality_rating),
                "altitude_degrees": (observation.altitude_degrees),
                "notes": observation.notes,
                "exposure_seconds": (observation.exposure_seconds),
                "frames_captured": (observation.frames_captured),
                "frames_accepted": (observation.frames_accepted),
            }
            for observation in session.observations
        ],
        "summary": {
            "session_duration_minutes": (summary.session_duration_minutes),
            "observation_count": (summary.observation_count),
            "observed_count": (summary.observed_count),
            "partial_count": (summary.partial_count),
            "not_observed_count": (summary.not_observed_count),
            "weighted_completion_percent": (summary.weighted_completion_percent),
            "average_quality_rating": (summary.average_quality_rating),
            "total_target_time_minutes": (summary.total_target_time_minutes),
            "captured_frames": (summary.captured_frames),
            "accepted_frames": (summary.accepted_frames),
            "frame_acceptance_percent": (summary.frame_acceptance_percent),
            "accepted_integration_seconds": (summary.accepted_integration_seconds),
        },
    }


def session_to_json(
    session: ObservationSession,
    *,
    indent: int = 2,
) -> str:
    """Export one observation session as JSON."""

    return json.dumps(
        session_to_dict(session),
        ensure_ascii=False,
        indent=indent,
    )


def _require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    """Require a mapping while parsing imported data."""

    if not isinstance(value, Mapping):
        raise ObservationLogError(f"{label} must be an object.")

    return value


def session_from_dict(
    payload: Mapping[str, Any],
) -> ObservationSession:
    """Create an observation session from imported data."""

    try:
        schema_version = int(payload["schema_version"])

        if schema_version not in (1, OBSERVATION_LOG_SCHEMA_VERSION):
            raise ObservationLogError(
                f"Unsupported observation-log schema version: {schema_version}"
            )

        session_data = _require_mapping(
            payload["session"],
            "Session",
        )

        equipment_data = _require_mapping(
            payload["equipment"],
            "Equipment",
        )

        observation_values = payload["observations"]

        if not isinstance(
            observation_values,
            list,
        ):
            raise ObservationLogError("Observations must be an array.")

        filter_values = equipment_data.get(
            "filters",
            [],
        )

        if not isinstance(filter_values, list):
            raise ObservationLogError("Equipment filters must be an array.")

        equipment = EquipmentSnapshot(
            telescope_name=str(
                equipment_data.get(
                    "telescope_name",
                    "",
                )
            ),
            aperture_mm=equipment_data.get("aperture_mm"),
            focal_length_mm=equipment_data.get("focal_length_mm"),
            eyepiece_name=str(
                equipment_data.get(
                    "eyepiece_name",
                    "",
                )
            ),
            camera_name=str(
                equipment_data.get(
                    "camera_name",
                    "",
                )
            ),
            pixel_size_um=equipment_data.get("pixel_size_um"),
            mount_name=str(
                equipment_data.get(
                    "mount_name",
                    "",
                )
            ),
            filters=tuple(str(filter_name) for filter_name in filter_values),
        )

        timezone_name = str(session_data["timezone_name"])
        session_interval = _interval_from_imported_values(
            started_at_local=session_data["started_at_local"],
            ended_at_local=session_data["ended_at_local"],
            timezone_name=timezone_name,
            schema_version=schema_version,
            start_provenance=session_data.get("started_at_provenance"),
            end_provenance=session_data.get("ended_at_provenance"),
            start_label="Session start",
            end_label="Session end",
        )

        observations = tuple(
            _observation_from_mapping(
                _require_mapping(observation_data, "Observation"),
                timezone_name=timezone_name,
                schema_version=schema_version,
            )
            for observation_data in observation_values
        )

        return ObservationSession(
            session_id=str(session_data["session_id"]),
            title=str(session_data["title"]),
            observer=str(session_data["observer"]),
            location_name=str(session_data["location_name"]),
            latitude_degrees=float(session_data["latitude_degrees"]),
            longitude_degrees=float(session_data["longitude_degrees"]),
            elevation_m=float(session_data["elevation_m"]),
            timezone_name=timezone_name,
            started_at_local=session_interval.start.local_datetime,
            ended_at_local=session_interval.end.local_datetime,
            mode=str(session_data["mode"]),
            equipment=equipment,
            observations=observations,
            seeing_arcseconds=(session_data.get("seeing_arcseconds")),
            transparency_rating=(session_data.get("transparency_rating")),
            cloud_cover_percent=(session_data.get("cloud_cover_percent")),
            general_notes=str(
                session_data.get(
                    "general_notes",
                    "",
                )
            ),
            interval=session_interval,
        )

    except ObservationLogError:
        raise

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ObservationLogError("Invalid observation-log data.") from error


def _parse_endpoint_provenance(
    value: object,
    *,
    timezone_name: str,
    local_value: object,
    label: str,
) -> ResolvedObservationLogEndpoint:
    """Parse and consistency-check one schema-v2 endpoint."""

    provenance = _require_mapping(value, f"{label} provenance")
    fold = provenance.get("fold")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ObservationLogError(f"{label} provenance fold must be null, 0, or 1.")
    parsed_local = datetime.fromisoformat(str(local_value))
    _validate_aware_datetime(parsed_local, label)
    endpoint = _endpoint_from_civil(
        ObservationLogCivilEndpoint(
            local_date=parsed_local.date(),
            local_time=parsed_local.timetz().replace(tzinfo=None),
            fold=fold,
        ),
        timezone_name,
    )
    parsed_utc = _parse_utc_iso(provenance["utc"], f"{label} provenance UTC")
    if (
        endpoint.utc_datetime != parsed_utc
        or endpoint.local_datetime.replace(tzinfo=None) != parsed_local.replace(tzinfo=None)
        or endpoint.local_datetime.utcoffset() != parsed_local.utcoffset()
    ):
        raise ObservationLogError(
            f"{label} provenance is inconsistent with timezone {timezone_name}."
        )
    return endpoint


def _interval_from_imported_values(
    *,
    started_at_local: object,
    ended_at_local: object,
    timezone_name: str,
    schema_version: int,
    start_provenance: object,
    end_provenance: object,
    start_label: str,
    end_label: str,
) -> ResolvedObservationLogInterval:
    """Migrate schema v1 or verify schema v2 interval provenance."""

    try:
        if schema_version == 1:
            start = _endpoint_from_aware_datetime(
                datetime.fromisoformat(str(started_at_local)),
                timezone_name=timezone_name,
                label=start_label,
            )
            end = _endpoint_from_aware_datetime(
                datetime.fromisoformat(str(ended_at_local)),
                timezone_name=timezone_name,
                label=end_label,
            )
        else:
            start = _parse_endpoint_provenance(
                start_provenance,
                timezone_name=timezone_name,
                local_value=started_at_local,
                label=start_label,
            )
            end = _parse_endpoint_provenance(
                end_provenance,
                timezone_name=timezone_name,
                local_value=ended_at_local,
                label=end_label,
            )
        return ResolvedObservationLogInterval(timezone_name, start, end)
    except ObservationLogError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationLogError(
            f"{start_label}/{end_label} provenance is invalid or inconsistent."
        ) from error


def _observation_from_mapping(
    data: Mapping[str, Any],
    *,
    timezone_name: str,
    schema_version: int,
) -> TargetObservation:
    """Parse one target observation."""

    interval = _interval_from_imported_values(
        started_at_local=data["started_at_local"],
        ended_at_local=data["ended_at_local"],
        timezone_name=timezone_name,
        schema_version=schema_version,
        start_provenance=data.get("started_at_provenance"),
        end_provenance=data.get("ended_at_provenance"),
        start_label="Observation start",
        end_label="Observation end",
    )
    return TargetObservation(
        observation_id=str(data["observation_id"]),
        object_key=str(data["object_key"]),
        display_name=str(data["display_name"]),
        category=str(data["category"]),
        started_at_local=interval.start.local_datetime,
        ended_at_local=interval.end.local_datetime,
        outcome=str(data["outcome"]),
        quality_rating=int(data["quality_rating"]),
        altitude_degrees=data.get("altitude_degrees"),
        notes=str(data.get("notes", "")),
        exposure_seconds=float(
            data.get(
                "exposure_seconds",
                0.0,
            )
        ),
        frames_captured=int(
            data.get(
                "frames_captured",
                0,
            )
        ),
        frames_accepted=int(
            data.get(
                "frames_accepted",
                0,
            )
        ),
        interval=interval,
    )


def session_from_json(
    json_text: str,
) -> ObservationSession:
    """Import one observation session from JSON."""

    try:
        payload = json.loads(json_text)

    except json.JSONDecodeError as error:
        raise ObservationLogError("Observation log contains invalid JSON.") from error

    mapping = _require_mapping(
        payload,
        "Observation log",
    )

    return session_from_dict(mapping)


def session_observations_to_csv(
    session: ObservationSession,
) -> str:
    """Export target observations as UTF-8 CSV text."""

    output = StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDNAMES,
        lineterminator="\n",
    )

    writer.writeheader()

    for observation in session.observations:
        session_interval = session.interval
        observation_interval = _require_observation_interval(observation)
        if session_interval is None:
            raise ValueError("Observation session has no resolved interval.")
        writer.writerow(
            {
                "session_id": session.session_id,
                "session_title": session.title,
                "observer": session.observer,
                "location_name": (session.location_name),
                "timezone_name": (session.timezone_name),
                "session_mode": session.mode,
                "session_start": (session.started_at_local.isoformat()),
                "session_end": (session.ended_at_local.isoformat()),
                "observation_id": (observation.observation_id),
                "object_key": (observation.object_key),
                "display_name": (observation.display_name),
                "category": observation.category,
                "observation_start": (observation.started_at_local.isoformat()),
                "observation_end": (observation.ended_at_local.isoformat()),
                "duration_minutes": round(
                    observation.duration_minutes,
                    2,
                ),
                "outcome": observation.outcome,
                "quality_rating": (observation.quality_rating),
                "altitude_degrees": (
                    "" if (observation.altitude_degrees is None) else observation.altitude_degrees
                ),
                "exposure_seconds": (observation.exposure_seconds),
                "frames_captured": (observation.frames_captured),
                "frames_accepted": (observation.frames_accepted),
                "accepted_integration_seconds": (observation.accepted_integration_seconds),
                "notes": observation.notes,
                "schema_version": OBSERVATION_LOG_SCHEMA_VERSION,
                "session_start_fold": (
                    ""
                    if session_interval.start.request.fold is None
                    else session_interval.start.request.fold
                ),
                "session_end_fold": (
                    ""
                    if session_interval.end.request.fold is None
                    else session_interval.end.request.fold
                ),
                "session_start_utc": _utc_iso(session_interval.start.utc_datetime),
                "session_end_utc": _utc_iso(session_interval.end.utc_datetime),
                "observation_start_fold": (
                    ""
                    if observation_interval.start.request.fold is None
                    else observation_interval.start.request.fold
                ),
                "observation_end_fold": (
                    ""
                    if observation_interval.end.request.fold is None
                    else observation_interval.end.request.fold
                ),
                "observation_start_utc": _utc_iso(observation_interval.start.utc_datetime),
                "observation_end_utc": _utc_iso(observation_interval.end.utc_datetime),
            }
        )

    return output.getvalue()
