"""Markdown reports for astronomical observation sessions."""

from collections.abc import Mapping
from dataclasses import dataclass

from astroscope.observation_log import (
    ObservationSession,
    calculate_session_summary,
)


@dataclass(frozen=True, slots=True)
class ObservationReportLabels:
    """Translated labels used by observation reports."""

    title: str
    session_details: str
    conditions: str
    equipment: str
    observations: str
    summary: str
    session_id: str
    observer: str
    location: str
    mode: str
    start: str
    end: str
    session_duration: str
    seeing: str
    transparency: str
    cloud_cover: str
    telescope: str
    aperture: str
    focal_length: str
    eyepiece: str
    camera: str
    pixel_size: str
    mount: str
    filters: str
    object_name: str
    category: str
    observation_time: str
    duration_minutes: str
    outcome: str
    quality: str
    altitude: str
    exposure: str
    frames: str
    accepted_integration: str
    notes: str
    no_observations: str
    observation_count: str
    completion: str
    average_quality: str
    target_time: str
    frame_acceptance: str
    not_recorded: str


def _escape_markdown_cell(value: object) -> str:
    """Escape text used inside a Markdown table cell."""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def _optional_value(
    value: object | None,
    *,
    suffix: str,
    not_recorded: str,
) -> str:
    """Format an optional report value."""

    if value is None or value == "":
        return not_recorded

    return f"{value}{suffix}"


def create_markdown_report(
    session: ObservationSession,
    *,
    labels: ObservationReportLabels,
    mode_names: Mapping[str, str],
    outcome_names: Mapping[str, str],
    category_names: Mapping[str, str],
) -> str:
    """Create a human-readable Markdown observing report."""

    summary = calculate_session_summary(session)

    seeing_value = _optional_value(
        session.seeing_arcseconds,
        suffix="″",
        not_recorded=labels.not_recorded,
    )

    transparency_value = _optional_value(
        session.transparency_rating,
        suffix="/5",
        not_recorded=labels.not_recorded,
    )

    cloud_cover_value = _optional_value(
        session.cloud_cover_percent,
        suffix="%",
        not_recorded=labels.not_recorded,
    )

    aperture_value = _optional_value(
        session.equipment.aperture_mm,
        suffix=" mm",
        not_recorded=labels.not_recorded,
    )

    focal_length_value = _optional_value(
        session.equipment.focal_length_mm,
        suffix=" mm",
        not_recorded=labels.not_recorded,
    )

    pixel_size_value = _optional_value(
        session.equipment.pixel_size_um,
        suffix=" μm",
        not_recorded=labels.not_recorded,
    )

    filter_names = ", ".join(
        _escape_markdown_cell(filter_name) for filter_name in session.equipment.filters
    )

    if not filter_names:
        filter_names = labels.not_recorded

    lines = [
        f"# {labels.title}: {_escape_markdown_cell(session.title)}",
        "",
        f"## {labels.session_details}",
        "",
        f"- **{labels.session_id}:** {_escape_markdown_cell(session.session_id)}",
        f"- **{labels.observer}:** {_escape_markdown_cell(session.observer)}",
        f"- **{labels.location}:** "
        f"{_escape_markdown_cell(session.location_name)} "
        f"({session.latitude_degrees:.4f}°, "
        f"{session.longitude_degrees:.4f}°)",
        f"- **{labels.mode}:** {mode_names.get(session.mode, session.mode)}",
        f"- **{labels.start}:** {session.started_at_local.isoformat()}",
        f"- **{labels.end}:** {session.ended_at_local.isoformat()}",
        f"- **{labels.session_duration}:** {summary.session_duration_minutes:.1f} min",
        "",
        f"## {labels.conditions}",
        "",
        f"- **{labels.seeing}:** {seeing_value}",
        f"- **{labels.transparency}:** {transparency_value}",
        f"- **{labels.cloud_cover}:** {cloud_cover_value}",
        "",
        f"## {labels.equipment}",
        "",
        f"- **{labels.telescope}:** "
        f"{_escape_markdown_cell(session.equipment.telescope_name) or labels.not_recorded}",
        f"- **{labels.aperture}:** {aperture_value}",
        f"- **{labels.focal_length}:** {focal_length_value}",
        f"- **{labels.eyepiece}:** "
        f"{_escape_markdown_cell(session.equipment.eyepiece_name) or labels.not_recorded}",
        f"- **{labels.camera}:** "
        f"{_escape_markdown_cell(session.equipment.camera_name) or labels.not_recorded}",
        f"- **{labels.pixel_size}:** {pixel_size_value}",
        f"- **{labels.mount}:** "
        f"{_escape_markdown_cell(session.equipment.mount_name) or labels.not_recorded}",
        f"- **{labels.filters}:** {filter_names}",
        "",
        f"## {labels.observations}",
        "",
    ]

    if not session.observations:
        lines.extend(
            [
                labels.no_observations,
                "",
            ]
        )
    else:
        lines.extend(
            [
                (
                    f"| {labels.object_name} | {labels.category} | "
                    f"{labels.observation_time} | "
                    f"{labels.duration_minutes} | "
                    f"{labels.outcome} | {labels.quality} | "
                    f"{labels.altitude} | {labels.exposure} | "
                    f"{labels.frames} | "
                    f"{labels.accepted_integration} | "
                    f"{labels.notes} |"
                ),
                ("|---|---|---|---:|---|---:|---:|---:|---:|---:|---|"),
            ]
        )

        for observation in session.observations:
            altitude = (
                labels.not_recorded
                if observation.altitude_degrees is None
                else f"{observation.altitude_degrees:.1f}°"
            )

            frame_text = f"{observation.frames_accepted}/{observation.frames_captured}"

            time_text = (
                f"{observation.started_at_local.strftime('%H:%M')}"
                "–"
                f"{observation.ended_at_local.strftime('%H:%M')}"
            )

            lines.append(
                "| "
                f"{_escape_markdown_cell(observation.display_name)} | "
                f"{category_names.get(observation.category, observation.category)} | "
                f"{time_text} | "
                f"{observation.duration_minutes:.1f} | "
                f"{outcome_names.get(observation.outcome, observation.outcome)} | "
                f"{observation.quality_rating}/5 | "
                f"{altitude} | "
                f"{observation.exposure_seconds:.1f} s | "
                f"{frame_text} | "
                f"{observation.accepted_integration_seconds:.1f} s | "
                f"{_escape_markdown_cell(observation.notes) or labels.not_recorded} |"
            )

        lines.append("")

    lines.extend(
        [
            f"## {labels.summary}",
            "",
            f"- **{labels.observation_count}:** {summary.observation_count}",
            f"- **{labels.completion}:** {summary.weighted_completion_percent:.1f}%",
            f"- **{labels.average_quality}:** {summary.average_quality_rating:.2f}/5",
            f"- **{labels.target_time}:** {summary.total_target_time_minutes:.1f} min",
            f"- **{labels.frame_acceptance}:** {summary.frame_acceptance_percent:.1f}%",
            f"- **{labels.accepted_integration}:** {summary.accepted_integration_seconds:.1f} s",
        ]
    )

    if session.general_notes.strip():
        lines.extend(
            [
                "",
                f"## {labels.notes}",
                "",
                session.general_notes.strip(),
            ]
        )

    return "\n".join(lines).strip() + "\n"
