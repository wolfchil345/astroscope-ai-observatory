"""Export ranked exoplanet transit schedules."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import UTC, datetime
from typing import Final

from astropy.time import Time

from astroscope.transit_schedule import TransitScheduleResult

CSV_FIELDNAMES: Final[tuple[str, ...]] = (
    "rank",
    "planet_name",
    "transit_number",
    "priority_score",
    "site_name",
    "observation_start_utc",
    "ingress_utc",
    "mid_transit_utc",
    "egress_utc",
    "observation_end_utc",
    "observation_window_hours",
    "timing_uncertainty_hours",
    "observable_fraction",
    "dark_fraction",
    "altitude_fraction",
    "full_window_visible",
    "midpoint_altitude_degrees",
    "minimum_altitude_degrees",
    "maximum_altitude_degrees",
    "minimum_moon_separation_degrees",
    "moon_illumination_fraction",
    "transit_depth_ppm",
    "host_magnitude",
)

ICAL_PRODUCT_IDENTIFIER: Final[str] = (
    "-//AstroScope AI Observatory//Exoplanet Transit Scheduler//EN"
)


class TransitScheduleExportError(ValueError):
    """Raised when a transit schedule cannot be exported."""


def _utc_datetime_from_julian_date(
    julian_date: float,
) -> datetime:
    """Convert a finite Julian date to a UTC datetime."""

    if not math.isfinite(julian_date):
        raise TransitScheduleExportError("Julian date must be finite.")

    return Time(
        julian_date,
        format="jd",
        scale="utc",
    ).to_datetime(timezone=UTC)


def _format_iso_utc(
    julian_date: float,
) -> str:
    """Format a Julian date as an ISO-8601 UTC timestamp."""

    value = _utc_datetime_from_julian_date(julian_date)

    return value.isoformat(timespec="seconds").replace(
        "+00:00",
        "Z",
    )


def _format_ical_utc(
    julian_date: float,
) -> str:
    """Format a Julian date for an iCalendar UTC field."""

    return _utc_datetime_from_julian_date(julian_date).strftime("%Y%m%dT%H%M%SZ")


def transit_schedule_rows(
    result: TransitScheduleResult,
) -> tuple[dict[str, object], ...]:
    """Convert a ranked schedule into export-ready rows."""

    rows: list[dict[str, object]] = []

    for ranked in result.ranked_transits:
        candidate = ranked.candidate
        event = candidate.event
        visibility = candidate.visibility
        midpoint = visibility.midpoint_sample

        rows.append(
            {
                "rank": ranked.rank,
                "planet_name": event.planet_name,
                "transit_number": event.transit_number,
                "priority_score": round(
                    ranked.score.total_score,
                    6,
                ),
                "site_name": result.site.name,
                "observation_start_utc": (_format_iso_utc(event.observation_start_jd)),
                "ingress_utc": _format_iso_utc(event.ingress_jd),
                "mid_transit_utc": _format_iso_utc(event.mid_transit_jd),
                "egress_utc": _format_iso_utc(event.egress_jd),
                "observation_end_utc": (_format_iso_utc(event.observation_end_jd)),
                "observation_window_hours": round(
                    event.observation_window_hours,
                    6,
                ),
                "timing_uncertainty_hours": round(
                    event.timing_uncertainty_hours,
                    6,
                ),
                "observable_fraction": round(
                    visibility.observable_sample_fraction,
                    6,
                ),
                "dark_fraction": round(
                    visibility.dark_sample_fraction,
                    6,
                ),
                "altitude_fraction": round(
                    visibility.altitude_sample_fraction,
                    6,
                ),
                "full_window_visible": (visibility.full_observation_window_visible),
                "midpoint_altitude_degrees": round(
                    midpoint.target_altitude_degrees,
                    6,
                ),
                "minimum_altitude_degrees": round(
                    visibility.minimum_target_altitude_degrees,
                    6,
                ),
                "maximum_altitude_degrees": round(
                    visibility.maximum_target_altitude_degrees,
                    6,
                ),
                "minimum_moon_separation_degrees": round(
                    visibility.minimum_moon_separation_degrees,
                    6,
                ),
                "moon_illumination_fraction": round(
                    midpoint.moon_illumination_fraction,
                    6,
                ),
                "transit_depth_ppm": (candidate.transit_depth_ppm),
                "host_magnitude": (candidate.host_magnitude),
            }
        )

    return tuple(rows)


def transit_schedule_to_csv(
    result: TransitScheduleResult,
) -> str:
    """Serialize a ranked transit schedule as CSV."""

    output = io.StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDNAMES,
        extrasaction="raise",
        lineterminator="\n",
    )

    writer.writeheader()
    writer.writerows(transit_schedule_rows(result))

    return output.getvalue()


def transit_schedule_to_json(
    result: TransitScheduleResult,
    *,
    indent: int = 2,
) -> str:
    """Serialize a ranked transit schedule as structured JSON."""

    if isinstance(indent, bool) or not isinstance(
        indent,
        int,
    ):
        raise TransitScheduleExportError("JSON indentation must be an integer.")

    if indent < 0:
        raise TransitScheduleExportError("JSON indentation must not be negative.")

    payload = {
        "schema_version": 1,
        "generated_by": ("AstroScope AI Observatory"),
        "site": {
            "name": result.site.name,
            "latitude_degrees": (result.site.latitude_degrees),
            "longitude_degrees": (result.site.longitude_degrees),
            "elevation_meters": (result.site.elevation_meters),
        },
        "request": {
            "start_jd": result.request.start_jd,
            "end_jd": result.request.end_jd,
            "baseline_before_hours": (result.request.baseline_before_hours),
            "baseline_after_hours": (result.request.baseline_after_hours),
            "uncertainty_sigma_multiplier": (result.request.uncertainty_sigma_multiplier),
            "visibility_sample_count": (result.request.visibility_sample_count),
            "minimum_altitude_degrees": (result.request.minimum_altitude_degrees),
            "darkness_sun_altitude_degrees": (result.request.darkness_sun_altitude_degrees),
        },
        "summary": {
            "target_count": result.target_count,
            "predicted_event_count": (result.predicted_event_count),
            "observable_event_count": (result.observable_transit_count),
            "fully_visible_event_count": (result.fully_visible_count),
            "targets_without_events": list(result.targets_without_events),
        },
        "events": list(transit_schedule_rows(result)),
    }

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=indent,
            allow_nan=False,
        )
        + "\n"
    )


def _escape_ical_text(
    value: str,
) -> str:
    """Escape text according to iCalendar text rules."""

    return (
        value.replace(
            "\\",
            "\\\\",
        )
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .replace(
            "\n",
            "\\n",
        )
        .replace(
            ";",
            "\\;",
        )
        .replace(
            ",",
            "\\,",
        )
    )


def _fold_ical_line(
    line: str,
) -> tuple[str, ...]:
    """Fold one iCalendar line to at most 75 UTF-8 octets."""

    if not line:
        return ("",)

    folded: list[str] = []
    remaining = line
    first_line = True

    while remaining:
        maximum_bytes = 75 if first_line else 74

        byte_count = 0
        character_count = 0

        for character in remaining:
            character_bytes = len(character.encode("utf-8"))

            if character_count > 0 and byte_count + character_bytes > maximum_bytes:
                break

            byte_count += character_bytes
            character_count += 1

        segment = remaining[:character_count]
        remaining = remaining[character_count:]

        if first_line:
            folded.append(segment)
        else:
            folded.append(f" {segment}")

        first_line = False

    return tuple(folded)


def _event_uid(
    result: TransitScheduleResult,
    *,
    planet_name: str,
    transit_number: int,
    mid_transit_jd: float,
) -> str:
    """Create a deterministic calendar event identifier."""

    source = f"{result.site.name}|{planet_name}|{transit_number}|{mid_transit_jd:.12f}"

    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]

    return f"{digest}@astroscope-ai-observatory"


def _serialize_ical_lines(
    lines: list[str],
) -> str:
    """Serialize and fold iCalendar lines using CRLF."""

    serialized: list[str] = []

    for line in lines:
        serialized.extend(_fold_ical_line(line))

    return "\r\n".join(serialized) + "\r\n"


def transit_schedule_to_ics(
    result: TransitScheduleResult,
) -> str:
    """Serialize a ranked schedule as an iCalendar file."""

    calendar_name = _escape_ical_text(f"AstroScope Transit Schedule - {result.site.name}")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{ICAL_PRODUCT_IDENTIFIER}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{calendar_name}",
    ]

    for ranked in result.ranked_transits:
        candidate = ranked.candidate
        event = candidate.event
        visibility = candidate.visibility

        summary = _escape_ical_text(f"Transit: {event.planet_name}")

        description = _escape_ical_text(
            "\n".join(
                (
                    (f"AstroScope priority score: {ranked.score.total_score:.1f}/100"),
                    (f"Rank: {ranked.rank}"),
                    (f"Observable fraction: {visibility.observable_sample_fraction:.0%}"),
                    (
                        "Midpoint altitude: "
                        f"{visibility.midpoint_sample.target_altitude_degrees:.1f}°"
                    ),
                    (f"Minimum Moon separation: {visibility.minimum_moon_separation_degrees:.1f}°"),
                    (f"Timing uncertainty: {event.timing_uncertainty_hours:.3f} hours"),
                )
            )
        )

        location = _escape_ical_text(result.site.name)

        uid = _event_uid(
            result,
            planet_name=event.planet_name,
            transit_number=event.transit_number,
            mid_transit_jd=(event.mid_transit_jd),
        )

        lines.extend(
            (
                "BEGIN:VEVENT",
                f"UID:{uid}",
                (f"DTSTAMP:{_format_ical_utc(event.observation_start_jd)}"),
                (f"DTSTART:{_format_ical_utc(event.observation_start_jd)}"),
                (f"DTEND:{_format_ical_utc(event.observation_end_jd)}"),
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{location}",
                (f"GEO:{result.site.latitude_degrees:.6f};{result.site.longitude_degrees:.6f}"),
                (f"X-ASTROSCOPE-RANK:{ranked.rank}"),
                (f"X-ASTROSCOPE-SCORE:{ranked.score.total_score:.6f}"),
                (f"X-ASTROSCOPE-MID-TRANSIT-JD:{event.mid_transit_jd:.12f}"),
                "CATEGORIES:ASTRONOMY,EXOPLANET,TRANSIT",
                "STATUS:TENTATIVE",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            )
        )

    lines.append("END:VCALENDAR")

    return _serialize_ical_lines(lines)
