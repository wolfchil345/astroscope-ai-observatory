"""Freeze independent leading-order site-clock evidence, not a physical oracle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import socket
import sys
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

import numpy as np
import spiceypy as spice
from jplephem.spk import SPK
from skyfield import timelib
from skyfield.api import wgs84
from skyfield.timelib import Timescale

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/site_clock_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/site_clock_v1.json"
MANIFEST = ROOT / "validation/manifests/site_clock_v1.json"
C = 299792458.0


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def serial(value):
    if not math.isfinite(value):
        raise ValueError("Nonfinite reference output")
    return format(float(value), ".17g")


def vector(value):
    return [serial(x) for x in value]


def deny(*args, **kwargs):
    raise RuntimeError("Offline reference: network/approximate clock fallback forbidden")


def extract_eop(path, policy, historical, means):
    if sha(path) != policy["eop_evidence"]["source_sha256"]:
        raise ValueError("Wrong original IERS source")
    dates = set(historical["dates"])
    selected = set()
    tokens = [line.split() for line in path.read_text().splitlines() if not line.startswith("#")]
    for fields in tokens:
        day = f"{int(fields[0]):04}-{int(fields[1]):02}-{int(fields[2]):02}"
        if day in dates:
            selected.update((int(float(fields[4])), int(float(fields[4])) + 1))
    output = []
    for f in tokens:
        if int(float(f[4])) not in selected:
            continue
        if len(f) != 21 or f[3] != "0":
            raise ValueError("Unexpected IERS source format")
        row = dict(mjd=f[4], xp_arcsec=f[5], yp_arcsec=f[6], dut1_seconds=f[7],
                   dx_arcsec=f[8], dy_arcsec=f[9],
                   formal_errors=dict(xp_arcsec=f[13], yp_arcsec=f[14], dut1_seconds=f[15],
                                      dx_arcsec=f[16], dy_arcsec=f[17]))
        old = next(r for r in means if r["MJD"] == float(f[4]))
        if [float(f[i]) for i in (5, 6, 7)] != [old[k] for k in ("PM_x", "PM_y", "UT1_UTC")]:
            raise ValueError("Pinned EOP means do not match original source")
        output.append(row)
    if len(output) != 8:
        raise ValueError("Expected eight bracketing EOP records")
    return output


def generate(kernel_path, eop_source):
    policy = json.loads(POLICY.read_text())
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen input changed: {name}")
    if (kernel_path.stat().st_size != policy["kernel_size_bytes"]
            or sha(kernel_path) != policy["kernel_sha256"]):
        raise ValueError("Wrong DE440t kernel")
    packages = {n: importlib.metadata.version(n) for n in policy["reference_packages"]}
    if packages != policy["reference_packages"] or spice.tkvrsn("TOOLKIT") != "CSPICE_N0067":
        raise ValueError("Reference environment mismatch")
    historical = json.loads(
        (ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text())
    geocentres = json.loads(
        (ROOT / "validation/fixtures/time_ephemeris_v1.json").read_text())["cases"][:12]
    means = json.loads((ROOT / "validation/fixtures/solar_lunar_eop_v1.json").read_text())["rows"]
    leaps = json.loads(
        (ROOT / "validation/fixtures/observer_arrival_leaps_v1.json").read_text())["rows"]
    eop_records = extract_eop(eop_source, policy, historical, means)
    tt_grid = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in means])
    dt_grid = np.array([69.184 - r["UT1_UTC"] for r in means])

    def delta_t(jd):
        if not tt_grid[0] <= jd <= tt_grid[-1]:
            raise ValueError("No EOP extrapolation")
        return np.interp(jd, tt_grid, dt_grid)

    timescales = {}
    for mode in ("nominal", "utc_as_ut1", "no_polar_motion"):
        ts = Timescale((lambda jd: 69.184) if mode == "utc_as_ut1" else delta_t,
                       np.array([r["mjd"] + 2400000.5 for r in leaps]),
                       np.array([r["tai_utc"] for r in leaps]))
        if mode != "no_polar_motion":
            ts.polar_motion_table = (tt_grid, np.array([r["PM_x"] for r in means]),
                                    np.array([r["PM_y"] for r in means]))
        timescales[mode] = ts

    def position(tt, delta, site, mode="nominal"):
        days, remainder = divmod(tt, Decimal(86400))
        t = timescales[mode].tt_jd(float(2451545 + days), float(remainder / 86400))
        # Skyfield orientation routines consult TDB. Supply the integrated trial
        # coordinate explicitly; its default seven-term clock is disabled below.
        t.tdb_fraction = t.tt_fraction + delta / 86400
        if site is None:
            return np.zeros(3)
        location = wgs84.latlon(site["latitude_deg"], site["longitude_deg"],
                               elevation_m=site["elevation_m"])
        return location.at(t).position.m

    def state(tt, delta, site):
        et = float(tt + Decimal.from_float(delta))
        handle, descriptor, ident = spice.spksfs(1000000001, et, 128)
        target, center, frame, kind, start, end, _, _ = spice.spkuds(descriptor)
        if ((target, center, frame, kind, ident) !=
                (1000000001, 1000000000, 1, 2, "DE-0440LE-0440") or not start <= et <= end):
            raise ValueError("Time segment identity/domain mismatch")
        _, clock, _ = spice.spkpvn(handle, descriptor, et)
        earth, _ = spice.spkez(399, et, "J2000", "NONE", 0)
        velocity = earth[3:] * 1000
        r = position(tt, delta, site)
        term = float(np.dot(velocity, r) / C**2)
        return float(clock[0]), velocity, r, term, et

    def solve(tt, site):
        delta = 0.0
        trace = []
        for _ in range(policy["design"]["solver_max_iterations"]):
            d, v, r, term, et = state(tt, delta, site)
            residual = delta + d - term
            next_delta = term - d
            trace.append(dict(delta_seconds=serial(delta), tt_minus_tdb_seconds=serial(d),
                              site_term_seconds=serial(term), residual_seconds=serial(residual),
                              next_delta_seconds=serial(next_delta), et_seconds=serial(et)))
            if abs(residual) <= float(policy["design"]["solver_residual_seconds"]):
                return dict(converged=True, delta_seconds=serial(delta), trace=trace), v, r, et
            delta = next_delta
        return dict(converged=False, delta_seconds=serial(delta), trace=trace), v, r, et

    cases, controls = [], []
    spice.furnsh(str(kernel_path))
    try:
        with SPK.open(str(kernel_path)) as spk, patch.object(timelib, "tdb_minus_tt", deny):
            for geo in geocentres:
                tt = Decimal(geo["tt_seconds_from_j2000"])
                control, _, _, _ = solve(tt, None)
                controls.append(dict(id=geo["id"], solution=control))
                for site in historical["sites"]:
                    solution, velocity, r, et = solve(tt, site)
                    delta = float(solution["delta_seconds"])
                    # Match the *actual binary64 ET* supplied to CSPICE, not a
                    # second physical ephemeris or a hidden different epoch.
                    days, remainder = divmod(Decimal.from_float(et), Decimal(86400))
                    jd1, jd2 = float(2451545 + days), float(remainder / 86400)
                    vj = (spk[0, 3].compute_and_differentiate(jd1, jd2)[1]
                          + spk[3, 399].compute_and_differentiate(jd1, jd2)[1]) * 1000 / 86400
                    variants = {}
                    for mode in ("utc_as_ut1", "no_polar_motion"):
                        p = position(tt, delta, site, mode)
                        variants[mode] = dict(position_m=vector(p),
                                              site_term_seconds=serial(np.dot(velocity, p) / C**2))
                    cases.append(dict(
                        id=geo["id"].rsplit("_", 1)[0] + f"_{site['name']}_" + geo["id"][-2:],
                        geocentric_id=geo["id"], utc=geo["utc"], site={**site, "datum": "WGS84"},
                        tt_seconds_from_j2000=geo["tt_seconds_from_j2000"], solution=solution,
                        earth_velocity_m_s=vector(velocity), jplephem_velocity_m_s=vector(vj),
                        site_position_gcrs_m=vector(r), variants=variants,
                    ))
    finally:
        spice.unload(str(kernel_path))
    forbidden = sorted(n for n in sys.modules if n.split(".")[0]
                       in {"astropy", "erfa", "astroscope", "pint"})
    if forbidden:
        raise ValueError("Candidate imports in independent reference process")
    return dict(
        schema_version="1.0", model_id=policy["research_model_id"], policy_sha256=sha(POLICY),
        generator_sha256=sha(Path(__file__)), kernel_sha256=sha(kernel_path),
        packages=packages, python_version=platform.python_version(), cspice_toolkit="CSPICE_N0067",
        units=dict(position="m", velocity="m/s", clock="s"),
        position_frame="GCRS_leading_order_surrogate_not_scaled_BCRS_difference",
        forbidden_imports=forbidden, approximate_skyfield_clock="disabled_with_raising_patch",
        network="socket connect/connect_ex/create_connection blocked",
        eop_source_sha256=sha(eop_source), eop_records=eop_records,
        eop_formal_errors_are_hard_bounds=False, observed_dx_dy_applied=False,
        physical_site_clock_bound_seconds=None, observing_eligible=False,
        cases=cases, geocentric_controls=controls,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--eop-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (localcontext(Context(prec=70)), patch.object(socket.socket, "connect", deny),
          patch.object(socket.socket, "connect_ex", deny),
          patch.object(socket, "create_connection", deny)):
        result = generate(args.kernel, args.eop_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        policy = json.loads(POLICY.read_text())
        paths = [POLICY, FIXTURE, Path(__file__), ROOT / policy["reference_environment"]]
        files = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        files.update(policy["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(json.dumps(dict(cases=len(result["cases"]), controls=len(result["geocentric_controls"]),
                         converged=sum(r["solution"]["converged"] for r in result["cases"]))))


if __name__ == "__main__":
    main()
