"""Tests for transit-schedule export formats."""

import csv
import io
import json

import pytest

from astroscope.transit_ranking import (
    RankedTransit,
    TransitObservationCandidate,
    score_transit_candidate,
)
from astroscope.transit_schedule import (
    TransitScheduleRequest,
    TransitScheduleResult,
)
from astroscope.transit_schedule_exports import (
    CSV_FIELDNAMES,
    TransitScheduleExportError,
    transit_schedule_rows,
    transit_schedule_to_csv,
    transit_schedule_to_ics,
    transit_schedule_to_json,
)
from astroscope.transit_scheduler import (
    TransitEvent,
)
from astroscope.transit_visibility import (
    ObserverSite,
    TransitVisibilitySample,
    TransitVisibilitySummary,
)


def make_ranked_transit(
    *,
    planet_name: str = "Example b",
) -> RankedTransit:
    """Create one deterministic ranked transit."""

    event = TransitEvent(
        planet_name=planet_name,
        transit_number=7,
        mid_transit_jd=2_460_000.20,
        ingress_jd=2_460_000.15,
        egress_jd=2_460_000.25,
        observation_start_jd=2_460_000.10,
        observation_end_jd=2_460_000.30,
        timing_uncertainty_days=0.002,
    )

    sample = TransitVisibilitySample(
        julian_date=event.mid_transit_jd,
        target_altitude_degrees=65.0,
        target_azimuth_degrees=180.0,
        airmass=1.1,
        sun_altitude_degrees=-25.0,
        moon_altitude_degrees=15.0,
        moon_separation_degrees=110.0,
        moon_illumination_fraction=0.3,
        target_above_minimum_altitude=True,
        is_astronomical_dark=True,
    )

    visibility = TransitVisibilitySummary(
        planet_name=planet_name,
        target_name="Example Star",
        site_name="Osaka Observatory",
        samples=(sample,),
        midpoint_sample=sample,
        minimum_target_altitude_degrees=65.0,
        maximum_target_altitude_degrees=65.0,
        maximum_airmass=1.1,
        minimum_moon_separation_degrees=110.0,
        altitude_sample_fraction=1.0,
        dark_sample_fraction=1.0,
        observable_sample_fraction=1.0,
        full_observation_window_visible=True,
    )

    candidate = TransitObservationCandidate(
        event=event,
        visibility=visibility,
        transit_depth_ppm=2_500.0,
        host_magnitude=9.5,
    )

    return RankedTransit(
        rank=1,
        candidate=candidate,
        score=score_transit_candidate(candidate),
    )


def make_result(
    ranked_transits: tuple[RankedTransit, ...],
    *,
    site_name: str = "Osaka Observatory",
) -> TransitScheduleResult:
    """Create one deterministic schedule result."""

    return TransitScheduleResult(
        site=ObserverSite(
            name=site_name,
            latitude_degrees=34.6937,
            longitude_degrees=135.5023,
            elevation_meters=15.0,
        ),
        request=TransitScheduleRequest(
            start_jd=2_460_000.0,
            end_jd=2_460_001.0,
            baseline_before_hours=1.0,
            baseline_after_hours=1.5,
            uncertainty_sigma_multiplier=2.0,
            visibility_sample_count=25,
            minimum_altitude_degrees=20.0,
            darkness_sun_altitude_degrees=-18.0,
        ),
        target_count=1,
        predicted_event_count=len(ranked_transits),
        ranked_transits=ranked_transits,
        targets_without_events=(),
    )


def test_rows_contain_scientific_schedule_values() -> None:
    rows = transit_schedule_rows(make_result((make_ranked_transit(),)))

    assert len(rows) == 1

    row = rows[0]

    assert row["rank"] == 1
    assert row["planet_name"] == "Example b"
    assert row["transit_number"] == 7
    assert row["site_name"] == "Osaka Observatory"
    assert row["observable_fraction"] == 1.0
    assert row["full_window_visible"] is True
    assert row["midpoint_altitude_degrees"] == 65.0
    assert row["minimum_moon_separation_degrees"] == 110.0
    assert row["timing_uncertainty_hours"] == pytest.approx(0.048)
    assert row["mid_transit_utc"].endswith("Z")


def test_csv_contains_header_and_event() -> None:
    output = transit_schedule_to_csv(make_result((make_ranked_transit(),)))

    reader = csv.DictReader(io.StringIO(output))
    rows = list(reader)

    assert tuple(reader.fieldnames or ()) == CSV_FIELDNAMES

    assert len(rows) == 1
    assert rows[0]["planet_name"] == "Example b"
    assert rows[0]["rank"] == "1"
    assert rows[0]["full_window_visible"] == "True"


def test_empty_csv_contains_only_header() -> None:
    output = transit_schedule_to_csv(make_result(()))

    rows = list(csv.DictReader(io.StringIO(output)))

    assert rows == []


def test_json_contains_metadata_and_events() -> None:
    output = transit_schedule_to_json(make_result((make_ranked_transit(),)))

    payload = json.loads(output)

    assert payload["schema_version"] == 1
    assert payload["generated_by"] == ("AstroScope AI Observatory")
    assert payload["site"]["name"] == "Osaka Observatory"
    assert payload["summary"]["predicted_event_count"] == 1
    assert payload["summary"]["observable_event_count"] == 1
    assert payload["events"][0]["planet_name"] == "Example b"


@pytest.mark.parametrize(
    "invalid_indent",
    [
        -1,
        True,
        1.5,
    ],
)
def test_json_rejects_invalid_indentation(
    invalid_indent: object,
) -> None:
    with pytest.raises(TransitScheduleExportError):
        transit_schedule_to_json(
            make_result(()),
            indent=invalid_indent,  # type: ignore[arg-type]
        )


def test_ics_contains_valid_calendar_structure() -> None:
    output = transit_schedule_to_ics(make_result((make_ranked_transit(),)))

    assert output.startswith("BEGIN:VCALENDAR\r\n")
    assert output.endswith("END:VCALENDAR\r\n")

    assert output.count("BEGIN:VEVENT\r\n") == 1
    assert output.count("END:VEVENT\r\n") == 1

    assert "SUMMARY:Transit: Example b" in output
    assert "LOCATION:Osaka Observatory" in output
    assert "STATUS:TENTATIVE" in output
    assert "X-ASTROSCOPE-RANK:1" in output
    assert "DTSTART:" in output
    assert "DTEND:" in output


def test_ics_identifier_is_deterministic() -> None:
    result = make_result((make_ranked_transit(),))

    first = transit_schedule_to_ics(result)
    second = transit_schedule_to_ics(result)

    first_uid = next(line for line in first.splitlines() if line.startswith("UID:"))
    second_uid = next(line for line in second.splitlines() if line.startswith("UID:"))

    assert first_uid == second_uid


def test_ics_escapes_calendar_text() -> None:
    output = transit_schedule_to_ics(
        make_result(
            (make_ranked_transit(planet_name="Planet, Alpha; b"),),
            site_name="Osaka; Rooftop",
        )
    )

    assert "SUMMARY:Transit: Planet\\, Alpha\\; b" in output
    assert "LOCATION:Osaka\\; Rooftop" in output


def test_ics_lines_do_not_exceed_75_octets() -> None:
    long_name = "超長い惑星名" * 15 + " b"

    output = transit_schedule_to_ics(make_result((make_ranked_transit(planet_name=long_name),)))

    for line in output.splitlines():
        assert len(line.encode("utf-8")) <= 75


def test_empty_ics_contains_no_events() -> None:
    output = transit_schedule_to_ics(make_result(()))

    assert "BEGIN:VCALENDAR" in output
    assert "END:VCALENDAR" in output
    assert "BEGIN:VEVENT" not in output
