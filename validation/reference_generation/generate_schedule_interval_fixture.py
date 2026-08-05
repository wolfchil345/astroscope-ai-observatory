# ruff: noqa: E501
"""Generate independent IANA schedule-interval reference evidence.

Stage A accepts the pinned IANA 2026c archives, builds their ``zic`` and
``zdump`` tools, and turns the resulting transition evidence into the 37
canonical civil-interval cases.  It deliberately has no AstroScope or Python
timezone-oracle dependency: every UTC endpoint is derived by plain arithmetic
from the offsets reported by ``zdump``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

TZCODE_SHA256 = "b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8"
TZDATA_SHA256 = "e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4"
ZONES = ("Asia/Tokyo", "America/New_York", "Europe/London", "Australia/Lord_Howe")
REQUIRED_CODE_FILES = ("Makefile", "zic.c", "zdump.c")
REQUIRED_DATA_FILES = ("northamerica", "europe", "asia", "australasia")
_ZDUMP_LINE = re.compile(
    r"^(?P<zone>\S+)\s+(?P<utc>\w{3}\s+\w{3}\s+\d{1,2}\s+\d\d:\d\d:\d\d\s+\d{4})"
    r" UT = .+ gmtoff=(?P<offset>[+-]?\d+)$"
)

# This captured 2026c ``zdump -v -c 2025,2027`` subset is deliberately input
# evidence, not a table of expected AstroScope results.  CI uses it when the
# two source archives are unavailable; archive mode regenerates equivalent
# evidence using freshly built IANA tools.
CAPTURED_ZDUMP_2026C = """\
Asia/Tokyo  Thu Jan  1 00:00:00 2026 UT = Thu Jan  1 09:00:00 2026 JST isdst=0 gmtoff=32400
Asia/Tokyo  Thu Jan  1 00:00:00 2027 UT = Thu Jan  1 09:00:00 2027 JST isdst=0 gmtoff=32400
America/New_York  Thu Jan  1 00:00:00 2026 UT = Wed Dec 31 19:00:00 2025 EST isdst=0 gmtoff=-18000
America/New_York  Sun Mar  8 06:59:59 2026 UT = Sun Mar  8 01:59:59 2026 EST isdst=0 gmtoff=-18000
America/New_York  Sun Mar  8 07:00:00 2026 UT = Sun Mar  8 03:00:00 2026 EDT isdst=1 gmtoff=-14400
America/New_York  Sun Nov  1 05:59:59 2026 UT = Sun Nov  1 01:59:59 2026 EDT isdst=1 gmtoff=-14400
America/New_York  Sun Nov  1 06:00:00 2026 UT = Sun Nov  1 01:00:00 2026 EST isdst=0 gmtoff=-18000
Europe/London  Thu Jan  1 00:00:00 2026 UT = Thu Jan  1 00:00:00 2026 GMT isdst=0 gmtoff=0
Europe/London  Sun Mar 29 00:59:59 2026 UT = Sun Mar 29 00:59:59 2026 GMT isdst=0 gmtoff=0
Europe/London  Sun Mar 29 01:00:00 2026 UT = Sun Mar 29 02:00:00 2026 BST isdst=1 gmtoff=3600
Europe/London  Sun Oct 25 00:59:59 2026 UT = Sun Oct 25 01:59:59 2026 BST isdst=1 gmtoff=3600
Europe/London  Sun Oct 25 01:00:00 2026 UT = Sun Oct 25 01:00:00 2026 GMT isdst=0 gmtoff=0
Australia/Lord_Howe  Thu Jan  1 00:00:00 2026 UT = Thu Jan  1 11:00:00 2026 +11 isdst=1 gmtoff=39600
Australia/Lord_Howe  Sat Apr  4 14:59:59 2026 UT = Sun Apr  5 01:59:59 2026 +11 isdst=1 gmtoff=39600
Australia/Lord_Howe  Sat Apr  4 15:00:00 2026 UT = Sun Apr  5 01:30:00 2026 +1030 isdst=0 gmtoff=37800
Australia/Lord_Howe  Sat Oct  3 15:29:59 2026 UT = Sun Oct  4 01:59:59 2026 +1030 isdst=0 gmtoff=37800
Australia/Lord_Howe  Sat Oct  3 15:30:00 2026 UT = Sun Oct  4 02:30:00 2026 +11 isdst=1 gmtoff=39600
"""

# Recipes state only independently selected civil inputs and contractual
# categories.  UTC results, grids, elapsed durations, and fold identities are
# generated below from the parsed zic/zdump offset evidence.
CASE_RECIPES = json.loads(
    """[
 {"id":"tokyo-same-date","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-15T23:00:00",null]},
 {"id":"tokyo-overnight","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-16T02:00:00",null]},
 {"id":"tokyo-utc-crossing","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T08:00:00",null],"end":["2026-01-15T10:00:00",null]},
 {"id":"tokyo-precision","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:30.123456",null],"end":["2026-01-15T20:01:31.654321",null]},
 {"id":"equal-utc","category":"expected_rejection","timezone":"America/New_York","start":["2026-11-01T01:30:00",0],"end":["2026-11-01T01:30:00",0],"error":"ValueError"},
 {"id":"reversed-utc","category":"expected_rejection","timezone":"America/New_York","start":["2026-11-01T01:30:00",1],"end":["2026-11-01T01:45:00",0],"error":"ValueError"},
 {"id":"over-18-hours","category":"expected_rejection","timezone":"Asia/Tokyo","start":["2026-01-15T00:00:00",null],"end":["2026-01-15T18:00:00.000001",null],"error":"ValueError"},
 {"id":"ny-gap-start","category":"expected_rejection","timezone":"America/New_York","start":["2026-03-08T02:15:00",null],"end":["2026-03-08T03:30:00",null],"error":"NonexistentCivilTimeError"},
 {"id":"ny-gap-end","category":"expected_rejection","timezone":"America/New_York","start":["2026-03-08T01:30:00",null],"end":["2026-03-08T02:15:00",null],"error":"NonexistentCivilTimeError"},
 {"id":"ny-spring-span","category":"passed","timezone":"America/New_York","start":["2026-03-08T01:30:00",null],"end":["2026-03-08T03:30:00",null]},
 {"id":"ny-start-fold-0","category":"passed","timezone":"America/New_York","start":["2026-11-01T01:15:00",0],"end":["2026-11-01T02:15:00",null]},
 {"id":"ny-start-fold-1","category":"passed","timezone":"America/New_York","start":["2026-11-01T01:15:00",1],"end":["2026-11-01T02:15:00",null]},
 {"id":"ny-end-fold-0","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T01:30:00",0]},
 {"id":"ny-end-fold-1","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T01:30:00",1]},
 {"id":"ny-missing-fold","category":"expected_rejection","timezone":"America/New_York","start":["2026-11-01T01:30:00",null],"end":["2026-11-01T02:30:00",null],"error":"AmbiguousCivilTimeError"},
 {"id":"ny-fall-span","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T03:30:00",null]},
 {"id":"ny-repeated-grid","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T03:30:00",null],"grid_minutes":60,"include_folds":true},
 {"id":"london-fold-0","category":"passed","timezone":"Europe/London","start":["2026-10-25T01:30:00",0],"end":["2026-10-25T02:30:00",null]},
 {"id":"london-fold-1","category":"passed","timezone":"Europe/London","start":["2026-10-25T01:30:00",1],"end":["2026-10-25T02:30:00",null]},
 {"id":"london-span","category":"passed","timezone":"Europe/London","start":["2026-10-25T00:30:00",null],"end":["2026-10-25T02:30:00",null]},
 {"id":"london-grid-order","category":"passed","timezone":"Europe/London","start":["2026-10-25T00:30:00",null],"end":["2026-10-25T02:30:00",null],"grid_minutes":60,"include_folds":true},
 {"id":"lord-howe-gap","category":"expected_rejection","timezone":"Australia/Lord_Howe","start":["2026-10-04T02:15:00",null],"end":["2026-10-04T02:45:00",null],"error":"NonexistentCivilTimeError"},
 {"id":"lord-howe-fold-0","category":"passed","timezone":"Australia/Lord_Howe","start":["2026-04-05T01:45:00",0],"end":["2026-04-05T02:15:00",null]},
 {"id":"lord-howe-fold-1","category":"passed","timezone":"Australia/Lord_Howe","start":["2026-04-05T01:45:00",1],"end":["2026-04-05T02:15:00",null]},
 {"id":"lord-howe-fall-span","category":"passed","timezone":"Australia/Lord_Howe","start":["2026-04-05T01:15:00",null],"end":["2026-04-05T02:15:00",null]},
 {"id":"lord-howe-spring-span","category":"passed","timezone":"Australia/Lord_Howe","start":["2026-10-04T01:45:00",null],"end":["2026-10-04T02:45:00",null]},
 {"id":"spring-fixed-step","category":"passed","timezone":"America/New_York","start":["2026-03-08T01:30:00",null],"end":["2026-03-08T03:30:00",null],"grid_minutes":15},
 {"id":"fall-fixed-step","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T03:30:00",null],"grid_minutes":60},
 {"id":"final-sentinel","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-15T22:30:00",null],"grid_minutes":60},
 {"id":"half-open-start","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-15T22:00:00",null],"occupancy":"all","expected_block_count":1},
 {"id":"half-open-end","category":"passed","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-15T22:00:00",null],"occupancy":"sentinel_only","expected_block_count":0},
 {"id":"utc-continuity","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T03:30:00",null],"occupancy":"all","expected_block_count":1},
 {"id":"physical-aggregate","category":"passed","timezone":"America/New_York","start":["2026-11-01T00:30:00",null],"end":["2026-11-01T03:30:00",null],"occupancy":"all","expected_block_count":1},
 {"id":"legacy-same-date","category":"passed","operation":"legacy","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-15T23:00:00",null]},
 {"id":"legacy-overnight","category":"passed","operation":"legacy","timezone":"Asia/Tokyo","start":["2026-01-15T20:00:00",null],"end":["2026-01-16T02:00:00",null]},
 {"id":"legacy-ambiguous","category":"expected_rejection","operation":"legacy","timezone":"America/New_York","start":["2026-11-01T01:30:00",null],"end":["2026-11-01T03:30:00",null],"error":"AmbiguousCivilTimeError"},
 {"id":"legacy-gap","category":"expected_rejection","operation":"legacy","timezone":"America/New_York","start":["2026-03-08T01:30:00",null],"end":["2026-03-08T02:15:00",null],"error":"NonexistentCivilTimeError"}
]"""
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_archives(tzcode: Path, tzdata: Path) -> None:
    if tzcode.name != "tzcode2026c.tar.gz" or sha256(tzcode) != TZCODE_SHA256:
        raise ValueError("tzcode archive is not the pinned IANA 2026c input.")
    if tzdata.name != "tzdata2026c.tar.gz" or sha256(tzdata) != TZDATA_SHA256:
        raise ValueError("tzdata archive is not the pinned IANA 2026c input.")


def require_root_level_archive_layout(code_dir: Path, data_dir: Path) -> None:
    """Reject archive layouts that do not expose the IANA files at their root."""

    missing = [
        *(
            str(code_dir / filename)
            for filename in REQUIRED_CODE_FILES
            if not (code_dir / filename).is_file()
        ),
        *(
            str(data_dir / filename)
            for filename in REQUIRED_DATA_FILES
            if not (data_dir / filename).is_file()
        ),
    ]
    if missing:
        raise ValueError(
            "IANA archives must extract their expected files at archive root: " + ", ".join(missing)
        )


def parse_zdump_transition_evidence(text: str) -> dict[str, list[tuple[datetime, int]]]:
    """Parse UTC offset samples emitted by the pinned ``zdump`` executable."""

    evidence: dict[str, list[tuple[datetime, int]]] = {zone: [] for zone in ZONES}
    for line in text.splitlines():
        match = _ZDUMP_LINE.match(line.strip())
        if match is None or match["zone"] not in evidence:
            continue
        instant = datetime.strptime(match["utc"], "%a %b %d %H:%M:%S %Y").replace(tzinfo=UTC)
        evidence[match["zone"]].append((instant, int(match["offset"])))
    for zone, samples in evidence.items():
        samples.sort()
        if len(samples) < 2:
            raise ValueError(f"zdump evidence is incomplete for {zone}.")
    return evidence


def _offset_at(
    evidence: dict[str, list[tuple[datetime, int]]], zone: str, instant: datetime
) -> int:
    applicable = [offset for observed, offset in evidence[zone] if observed <= instant]
    if not applicable:
        raise ValueError(f"No prior zdump offset sample for {zone} at {instant.isoformat()}.")
    return applicable[-1]


def _candidates(
    evidence: dict[str, list[tuple[datetime, int]]], zone: str, local: datetime
) -> list[datetime]:
    values = {
        (local - timedelta(seconds=offset)).replace(tzinfo=UTC) for _, offset in evidence[zone]
    }
    return sorted(
        value
        for value in values
        if _offset_at(evidence, zone, value)
        == int((local - value.replace(tzinfo=None)).total_seconds())
    )


def _resolve_endpoint(
    evidence: dict[str, list[tuple[datetime, int]]], zone: str, endpoint: list[Any]
) -> tuple[datetime | None, str | None]:
    local = datetime.fromisoformat(endpoint[0])
    candidates = _candidates(evidence, zone, local)
    requested_fold = endpoint[1]
    if not candidates:
        return None, "NonexistentCivilTimeError"
    if len(candidates) == 2 and requested_fold is None:
        return None, "AmbiguousCivilTimeError"
    if requested_fold is not None:
        if requested_fold not in (0, 1) or requested_fold >= len(candidates):
            return None, "AmbiguousCivilTimeError"
        return candidates[requested_fold], None
    return candidates[0], None


def _fold_at(evidence: dict[str, list[tuple[datetime, int]]], zone: str, instant: datetime) -> int:
    local = instant.astimezone(UTC).replace(tzinfo=None) + timedelta(
        seconds=_offset_at(evidence, zone, instant)
    )
    return _candidates(evidence, zone, local).index(instant)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def build_fixture_from_transition_evidence(text: str) -> dict[str, Any]:
    """Turn independent zdump evidence and local case recipes into the fixture."""

    evidence = parse_zdump_transition_evidence(text)
    cases: list[dict[str, Any]] = []
    for recipe in CASE_RECIPES:
        case = {key: value for key, value in recipe.items() if key != "include_folds"}
        start, start_error = _resolve_endpoint(evidence, case["timezone"], case["start"])
        end, end_error = _resolve_endpoint(evidence, case["timezone"], case["end"])
        derived_error = start_error or end_error
        if derived_error is None and start is not None and end is not None:
            if end <= start or end - start > timedelta(hours=18):
                derived_error = "ValueError"
        if case["category"] == "expected_rejection":
            if derived_error != case["error"]:
                raise ValueError(
                    f"{case['id']} recipe disagrees with zdump evidence: {derived_error}"
                )
            cases.append(case)
            continue
        if derived_error is not None or start is None or end is None:
            raise ValueError(f"{case['id']} unexpectedly rejected: {derived_error}")
        case.update(
            {
                "start_utc": _iso(start),
                "end_utc": _iso(end),
                "elapsed_seconds": (end - start).total_seconds(),
            }
        )
        if "grid_minutes" in case:
            step = timedelta(minutes=case["grid_minutes"])
            grid = []
            current = start
            while current < end:
                grid.append(current)
                current += step
            grid.append(end)
            case["grid_utc"] = [_iso(value) for value in grid]
            if recipe.get("include_folds"):
                case["local_folds"] = [
                    _fold_at(evidence, case["timezone"], value) for value in grid
                ]
        if case.get("occupancy"):
            case["scheduled_minutes"] = (
                0
                if case["occupancy"] == "sentinel_only"
                else int((end - start).total_seconds() // 60)
            )
        cases.append(case)
    if len(cases) != 37:
        raise ValueError("Expected exactly 37 generated schedule-interval cases.")
    return {
        "schema_version": "1.0",
        "fixture_id": "schedule-interval-reference-v1",
        "iana_release": "2026c",
        "claim_boundary": "Independent IANA civil-interval evidence only; not astronomy, visibility, planner-quality, weather, or observation-log validation.",
        "reference_provenance_id": "iana-tzdb-2026c-independent-zic-zdump-schedule-interval-v1",
        "cases": cases,
    }


def canonical_fixture_bytes(text: str) -> bytes:
    return (
        json.dumps(build_fixture_from_transition_evidence(text), indent=2, sort_keys=True) + "\n"
    ).encode()


def _offset_seconds(value: str) -> int:
    sign = -1 if value.startswith("-") else 1
    hours_and_minutes = value[1:].replace(":", "")
    hours = int(hours_and_minutes[:2])
    minutes = int(hours_and_minutes[2:] or "0")
    return sign * (hours * 3600 + minutes * 60)


def _fixed_zone_samples(zdump_interval_output: str) -> str:
    """Convert ``zdump -i`` fixed-offset records into parser input samples."""

    samples: list[str] = []
    current_zone: str | None = None
    for line in zdump_interval_output.splitlines():
        if line.startswith('TZ="') and line.endswith('"'):
            current_zone = line[4:-1]
            continue
        if current_zone not in ZONES or not line.startswith("-\t-\t"):
            continue
        offset_value = line.split("\t")[2]
        offset_seconds = _offset_seconds(offset_value)
        utc = datetime(2026, 1, 1, tzinfo=UTC)
        local = utc + timedelta(seconds=offset_seconds)
        samples.append(
            f"{current_zone}  {utc.strftime('%a %b %d %H:%M:%S %Y')} UT = "
            f"{local.strftime('%a %b %d %H:%M:%S %Y')} zic-zdump "
            f"isdst=0 gmtoff={offset_seconds}"
        )
    return "\n".join(samples)


def build_tools_and_compile_zones(tzcode: Path, tzdata: Path, workdir: Path) -> str:
    """Build 2026c tools, compile the required zones, and return zdump output."""

    code_dir = workdir / "tzcode"
    data_dir = workdir / "tzdata"
    code_dir.mkdir()
    data_dir.mkdir()
    with tarfile.open(tzcode) as archive:
        archive.extractall(code_dir, filter="data")
    with tarfile.open(tzdata) as archive:
        archive.extractall(data_dir, filter="data")
    require_root_level_archive_layout(code_dir, data_dir)
    environment = {**os.environ, "LC_ALL": "C"}
    subprocess.run(["make", "zic", "zdump"], cwd=code_dir, check=True, env=environment)
    output = workdir / "zoneinfo"
    output.mkdir()
    subprocess.run(
        [
            str(code_dir / "zic"),
            "-d",
            str(output),
            *(str(data_dir / name) for name in REQUIRED_DATA_FILES),
        ],
        check=True,
        env=environment,
    )
    transition_output = subprocess.check_output(
        [str(code_dir / "zdump"), "-v", "-c", "2025,2027", *ZONES],
        text=True,
        env={**environment, "TZDIR": str(output)},
    )
    interval_output = subprocess.check_output(
        [str(code_dir / "zdump"), "-i", "-c", "2025,2027", *ZONES],
        text=True,
        env={**environment, "TZDIR": str(output)},
    )
    return "\n".join((transition_output, _fixed_zone_samples(interval_output)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tzcode-archive", type=Path)
    parser.add_argument("--tzdata-archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--captured-reference",
        action="store_true",
        help="Use the checked-in parsed 2026c zdump capture when archives are unavailable.",
    )
    args = parser.parse_args(argv)
    locale.setlocale(locale.LC_ALL, "C")
    if args.captured_reference:
        transition_text = CAPTURED_ZDUMP_2026C
    else:
        if args.tzcode_archive is None or args.tzdata_archive is None:
            parser.error(
                "both pinned IANA archives are required unless --captured-reference is used"
            )
        verify_archives(args.tzcode_archive, args.tzdata_archive)
        with tempfile.TemporaryDirectory() as temporary:
            transition_text = build_tools_and_compile_zones(
                args.tzcode_archive, args.tzdata_archive, Path(temporary)
            )
    args.output.write_bytes(canonical_fixture_bytes(transition_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
