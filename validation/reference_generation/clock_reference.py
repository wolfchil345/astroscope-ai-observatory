"""Freeze clock-route diagnostic evidence; this is not an independent clock oracle.

Run in the pinned Mission 40 reference environment. No production/candidate
imports, online clocks, default data refresh, or fallback from failed routes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import platform
import socket
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import astropy.units as u
import erfa
import numpy as np
from astropy.coordinates import EarthLocation
from astropy.table import QTable
from astropy.time import Time
from astropy.utils import iers
from pint.observatory import Observatory
from pint.observatory.topo_obs import TopoObs
from skyfield.timelib import tdb_minus_tt

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/clock_reference_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/clock_reference_v1.json"
MANIFEST = ROOT / "validation/manifests/clock_reference_v1.json"
METHODS = {
    "pint_dispatch": Observatory.get_TDBs,
    "pint_default": Observatory._get_TDB_default,
    "pint_ephem": Observatory._get_TDB_ephem,
    "skyfield_clock": tdb_minus_tt,
    "astropy_clock": Time._get_delta_tdb_tt,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deny_network(*args, **kwargs):
    raise RuntimeError("Clock-reference audit must be offline")


def scalar(value):
    return float(np.asarray(value).reshape(-1)[0])


def decimal(value):
    return format(scalar(value), ".17g")


def fraction_of_day(t):
    # A fraction modulo one day; avoids collapse of the full Julian date.
    return ((t.jd1 - 0.5) % 1 + t.jd2) % 1


@contextmanager
def frozen_tables():
    rows = json.loads((ROOT / "validation/fixtures/solar_lunar_eop_v1.json").read_text())["rows"]
    table = QTable()
    for name, unit in [("MJD", u.day), ("UT1_UTC", u.s), ("PM_x", u.arcsec), ("PM_y", u.arcsec)]:
        table[name] = [row[name] for row in rows] * unit
    leaps = json.loads((ROOT / "validation/fixtures/observer_arrival_leaps_v1.json").read_text())
    pinned = np.array(
        [(r["year"], r["month"], r["tai_utc"]) for r in leaps["rows"]],
        dtype=[("year", "i4"), ("month", "i4"), ("tai_utc", "f8")],
    )
    previous = erfa.leap_seconds.get().copy()
    with (
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("iers_degraded_accuracy", "error"),
        iers.earth_orientation_table.set(iers.IERS(table)),
    ):
        try:
            _ = Time("2024-01-01", scale="tai").utc
            erfa.leap_seconds.set(pinned)
            yield
        finally:
            erfa.leap_seconds.set(previous)


def generate():
    policy = json.loads(POLICY.read_text())
    for path, digest in policy["frozen_inputs"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Frozen input checksum mismatch")
    methods = {
        name: hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()
        for name, fn in METHODS.items()
    }
    if methods != policy["source_method_sha256"]:
        raise ValueError("Upstream method identity changed")
    lock = ROOT / policy["reference_environment"]
    versions = {}
    for line in lock.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        versions[name] = importlib.metadata.version(name)
        if versions[name] != expected:
            raise ValueError(f"Reference dependency differs: {name}")
    historical = json.loads(
        (ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text()
    )
    obs = Observatory("astroscope_m41_audit", apply_gps2utc=False, overwrite=True)
    rows = []
    original_dtdb = erfa.dtdb
    with frozen_tables():
        for date in historical["dates"]:
            for site in historical["sites"]:
                loc = EarthLocation.from_geodetic(
                    site["longitude_deg"] * u.deg,
                    site["latitude_deg"] * u.deg,
                    site["elevation_m"] * u.m,
                )
                lon = loc.lon.to_value(u.rad)
                rxy = np.hypot(loc.x, loc.y).to_value(u.km)
                z = loc.z.to_value(u.km)
                for hour in historical["hours"]:
                    utc = f"{date}T{hour:02}:00:00"
                    tt = Time(utc, scale="utc", location=loc).tt
                    geocentre = Time(tt.jd1, tt.jd2, format="jd", scale="tt")
                    site_delta = tt.delta_tdb_tt
                    geo_delta = geocentre.delta_tdb_tt
                    calls = []

                    def capture(*args, captured=calls):
                        captured.append([decimal(arg) for arg in args])
                        return original_dtdb(*args)

                    fresh = Time(tt.jd1, tt.jd2, format="jd", scale="tt", location=loc)
                    with patch.object(erfa, "dtdb", capture):
                        pint_tdb = obs.get_TDBs(fresh, method="default")
                    if len(calls) != 1:
                        raise ValueError("Unexpected PINT clock dispatch count")
                    utc_fraction = fraction_of_day(tt.utc)
                    ut1_fraction = fraction_of_day(tt.ut1)
                    args = [tt.jd1, tt.jd2, utc_fraction, lon, rxy, z]
                    rows.append(
                        dict(
                            id=f"{date}_{site['name']}_{hour:02}",
                            utc=utc,
                            site={**site, "datum": "WGS84"},
                            tt_jd_parts=[decimal(tt.jd1), decimal(tt.jd2)],
                            utc_day_fraction=decimal(utc_fraction),
                            ut1_day_fraction=decimal(ut1_fraction),
                            dut1_seconds=decimal(tt.delta_ut1_utc),
                            site_arguments=[decimal(lon), decimal(rxy), decimal(z)],
                            pint_dtdb_calls=calls,
                            astropy_site_seconds=decimal(site_delta),
                            astropy_geocentric_seconds=decimal(geo_delta),
                            pint_default_seconds=decimal(pint_tdb.delta_tdb_tt),
                            skyfield_geocentric_seconds=decimal(tdb_minus_tt(tt.jd1, tt.jd2)),
                            erfa_utc_seconds=decimal(original_dtdb(*args)),
                            erfa_ut1_seconds=decimal(
                                original_dtdb(
                                    tt.jd1,
                                    tt.jd2,
                                    ut1_fraction,
                                    lon,
                                    rxy,
                                    z,
                                )
                            ),
                        )
                    )
        probe = Time("2024-03-20T12:00:00", scale="tt")
        try:
            obs.get_TDBs(probe, method="ephemeris", ephem="DE421")
        except NotImplementedError as exc:
            ephemeris_probe = dict(
                outcome="unsupported",
                exception_type=type(exc).__name__,
                message=str(exc),
                fallback_used=False,
                result=None,
            )
        else:
            raise ValueError("Ephemeris method behavior changed; requalify, do not auto-promote")
    return dict(
        schema_version="1.0",
        evidence_kind="clock_route_diagnostics_not_independent_reference",
        policy_sha256=sha(POLICY),
        generator_sha256=sha(Path(__file__)),
        packages=versions,
        python_version=platform.python_version(),
        method_sha256=methods,
        topo_default_inherited=TopoObs._get_TDB_default is Observatory._get_TDB_default,
        erfa_doc_sha256=hashlib.sha256(erfa.dtdb.__doc__.encode()).hexdigest(),
        skyfield_parameters=list(inspect.signature(tdb_minus_tt).parameters),
        ephemeris_probe=ephemeris_probe,
        cases=rows,
        network="socket connect/connect_ex/create_connection blocked",
        physical_clock_bound_seconds=None,
        observing_eligible=False,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        policy = json.loads(POLICY.read_text())
        paths = [POLICY, FIXTURE, Path(__file__)]
        files = {str(path.relative_to(ROOT)): sha(path) for path in paths}
        files.update(policy["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(json.dumps({"cases": len(result["cases"]), "ephemeris_probe": result["ephemeris_probe"]}))


if __name__ == "__main__":
    main()
