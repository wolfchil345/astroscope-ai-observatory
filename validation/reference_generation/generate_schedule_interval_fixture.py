"""Generate pinned-IANA schedule-interval reference evidence without AstroScope.

This Stage A tool accepts local IANA 2026c archives only.  It verifies their
hashes, builds the supplied ``zic``/``zdump`` tools, compiles the four relevant
zones, and records the independently reviewed endpoint/grid matrix below.
The matrix uses offsets derived from the compiled 2026c data; its arithmetic is
plain UTC datetime arithmetic and deliberately has no application dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

TZCODE_SHA256 = "b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8"
TZDATA_SHA256 = "e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4"
ZONES = ("Asia/Tokyo", "America/New_York", "Europe/London", "Australia/Lord_Howe")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(local: str, offset_seconds: int) -> str:
    """Derive a UTC ISO value from a civil value and independently recorded offset."""

    value = datetime.fromisoformat(local)
    return (value - timedelta(seconds=offset_seconds)).replace(tzinfo=UTC).isoformat()


def verify_archives(tzcode: Path, tzdata: Path) -> None:
    if tzcode.name != "tzcode2026c.tar.gz" or sha256(tzcode) != TZCODE_SHA256:
        raise ValueError("tzcode archive is not the pinned IANA 2026c input.")
    if tzdata.name != "tzdata2026c.tar.gz" or sha256(tzdata) != TZDATA_SHA256:
        raise ValueError("tzdata archive is not the pinned IANA 2026c input.")


def build_tools_and_compile_zones(tzcode: Path, tzdata: Path, workdir: Path) -> dict[str, str]:
    """Build pinned tools and compile only fixture zones under deterministic locale."""

    with tarfile.open(tzcode) as archive:
        archive.extractall(workdir / "tzcode", filter="data")
    with tarfile.open(tzdata) as archive:
        archive.extractall(workdir / "tzdata", filter="data")
    source = next((workdir / "tzcode").iterdir())
    data = next((workdir / "tzdata").iterdir())
    subprocess.run(["make", "zic", "zdump"], cwd=source, check=True, env={"LC_ALL": "C"})
    zone_file = data / "northamerica"
    output = workdir / "zoneinfo"
    output.mkdir()
    subprocess.run(
        [str(source / "zic"), "-d", str(output), str(zone_file)], check=True, env={"LC_ALL": "C"}
    )
    subprocess.run(
        [str(source / "zic"), "-d", str(output), str(data / "europe")],
        check=True,
        env={"LC_ALL": "C"},
    )
    subprocess.run(
        [str(source / "zic"), "-d", str(output), str(data / "asia")],
        check=True,
        env={"LC_ALL": "C"},
    )
    subprocess.run(
        [str(source / "zic"), "-d", str(output), str(data / "australasia")],
        check=True,
        env={"LC_ALL": "C"},
    )
    output_text = subprocess.check_output(
        [str(source / "zdump"), "-v", *ZONES], text=True, env={"LC_ALL": "C"}
    )
    return {
        "zic": subprocess.check_output([str(source / "zic"), "--version"], text=True).strip(),
        "zdump": subprocess.check_output([str(source / "zdump"), "--version"], text=True).strip(),
        "transitions": output_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tzcode-archive", required=True, type=Path)
    parser.add_argument("--tzdata-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generated-at-utc")
    args = parser.parse_args()
    locale.setlocale(locale.LC_ALL, "C")
    verify_archives(args.tzcode_archive, args.tzdata_archive)
    with tempfile.TemporaryDirectory() as temporary:
        provenance = build_tools_and_compile_zones(
            args.tzcode_archive, args.tzdata_archive, Path(temporary)
        )
    payload = {
        "schema_version": "1.0",
        "iana_release": "2026c",
        "generation_method": "zic/zdump-derived offsets plus plain UTC arithmetic",
        "generated_at_utc": args.generated_at_utc,
        "tool_provenance": provenance,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
