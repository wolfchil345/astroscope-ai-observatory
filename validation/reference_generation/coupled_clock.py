"""Independent Decimal/CSPICE/Skyfield coupled site-clock reference experiment."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import socket
import sys
from decimal import Context, localcontext
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import numpy as np
import spiceypy as spice
from jplephem.spk import SPK
from skyfield import timelib
from skyfield.api import wgs84
from skyfield.timelib import Timescale

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/coupled_clock_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/coupled_clock_v1.json"
MANIFEST = ROOT / "validation/manifests/coupled_clock_v1.json"
C = D(299792458)
FB = D(1) - D("1.550519768e-8")
FG = D(1) - D("6.969290134e-10")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def serial(value):
    if not math.isfinite(value):
        raise ValueError("Nonfinite external state")
    return format(float(value), ".17g")


def encode(value):
    if isinstance(value, D):
        return "0" if value == 0 else str(value)
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def local_mapping(state):
    """Componentwise Decimal implementation, with no candidate imports."""
    v = [D(t) for t in state["earth_velocity_m_s"]]
    x = [D(t) / FG for t in state["position_tt_m"]]
    w = D(0)
    a, vector_w, jerk = ([D(0)] * 3 for _ in range(3))
    grad = [[D(0)] * 3 for _ in range(3)]
    wdot = D(0)
    for body in state["bodies"]:
        mu = D(body["gm_km3_s2"]) * 10**9
        d = [D(t) for t in body["displacement_tdb_m"]]
        vb = [D(t) for t in body["barycentric_velocity_m_s"]]
        u = [vb[i] - v[i] for i in range(3)]
        radius = sum(t * t for t in d).sqrt()
        du = sum(d[i] * u[i] for i in range(3))
        w += mu / radius
        wdot -= FB * mu * du / radius**3
        for i in range(3):
            a[i] += FB * mu * d[i] / radius**3
            vector_w[i] += mu * vb[i] / radius
            jerk[i] += FB**2 * mu * (u[i] / radius**3 - 3 * d[i] * du / radius**5)
            for j in range(3):
                grad[i][j] += FB * mu * vb[i] * d[j] / radius**3
    speed2 = sum(t * t for t in v)
    bi = [-speed2 * v[i] / 2 + 4 * vector_w[i] - 3 * v[i] * w for i in range(3)]
    bij = [
        [2 * grad[i][j] - v[i] * a[j] + (wdot / 2 if i == j else 0) for j in range(3)]
        for i in range(3)
    ]
    r, trace = x, []
    for _ in range(4):
        vr = sum(v[i] * r[i] for i in range(3))
        ar = sum(a[i] * r[i] for i in range(3))
        rr = sum(t * t for t in r)
        r = [x[i] - (v[i] * vr / 2 + w * r[i] + r[i] * ar - a[i] * rr / 2) / C**2 for i in range(3)]
        trace.append(r)
    terms = dict(
        leading=FG * sum(v[i] * r[i] for i in range(3)) / C**2,
        linear_c4=-FG * sum(bi[i] * r[i] for i in range(3)) / C**4,
        quadratic_c4=-FG * sum(bij[i][j] * r[i] * r[j] for i in range(3) for j in range(3)) / C**4,
        cubic_c4=FG * sum(t * t for t in r) * sum(jerk[i] * r[i] for i in range(3)) / (10 * C**4),
    )
    return dict(
        coefficients=dict(
            potential=w,
            acceleration=a,
            vector_potential=vector_w,
            gradient_vector_potential=grad,
            potential_total_derivative=wdot,
            jerk=jerk,
            B_vector=bi,
            B_matrix=bij,
        ),
        spatial_trace_tcb_m=trace,
        displacement_tdb_m=[FB * t for t in r],
        terms_seconds=terms,
        site_shift_seconds=sum(terms.values()),
    )


def deny(*args, **kwargs):
    raise RuntimeError("Offline reference: network and approximate clock forbidden")


def generate(kernel, gm_file):
    policy = json.loads(POLICY.read_text())
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen input changed: {name}")
    for file, key in ((kernel, "kernel"), (gm_file, "gm")):
        if sha(file) != policy[key]["sha256"] or file.stat().st_size != policy[key]["size_bytes"]:
            raise ValueError("Wrong external source")
    packages = {n: importlib.metadata.version(n) for n in policy["reference_packages"]}
    if packages != policy["reference_packages"] or spice.tkvrsn("TOOLKIT") != "CSPICE_N0067":
        raise ValueError("Reference environment mismatch")
    old = json.loads((ROOT / "validation/fixtures/site_clock_v1.json").read_text())
    means = json.loads((ROOT / "validation/fixtures/solar_lunar_eop_v1.json").read_text())["rows"]
    leaps = json.loads((ROOT / "validation/fixtures/observer_arrival_leaps_v1.json").read_text())[
        "rows"
    ]
    gm = {
        int(n): v.replace("D", "E")
        for n, v in re.findall(r"BODY(\d+)_GM\s*=\s*\(\s*([\d.E+D-]+)\s*\)", gm_file.read_text())
    }
    tt_grid = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in means])
    dt_grid = np.array([69.184 - r["UT1_UTC"] for r in means])

    def delta_t(jd):
        if not tt_grid[0] <= jd <= tt_grid[-1]:
            raise ValueError("No EOP extrapolation")
        return np.interp(jd, tt_grid, dt_grid)

    ts = Timescale(
        delta_t,
        np.array([r["mjd"] + 2400000.5 for r in leaps]),
        np.array([r["tai_utc"] for r in leaps]),
    )
    ts.polar_motion_table = (
        tt_grid,
        np.array([r["PM_x"] for r in means]),
        np.array([r["PM_y"] for r in means]),
    )
    spice.furnsh(str(kernel))
    try:
        with SPK.open(str(kernel)) as spk, patch.object(timelib, "tdb_minus_tt", deny):
            segment = spk[1000000000, 1000000001]

            def state_at(tt, et, site):
                handle, descriptor, ident = spice.spksfs(1000000001, et, 128)
                target, center, frame, kind, start, end, _, _ = spice.spkuds(descriptor)
                if (target, center, frame, kind, ident) != (
                    1000000001,
                    1000000000,
                    1,
                    2,
                    "DE-0440LE-0440",
                ) or not start <= et <= end:
                    raise ValueError("Clock segment/domain mismatch")
                _, clock, _ = spice.spkpvn(handle, descriptor, et)
                earth, _ = spice.spkez(399, et, "J2000", "NONE", 0)
                velocity = earth[3:] * 1000
                days, remainder = divmod(tt, D(86400))
                t = ts.tt_jd(float(2451545 + days), float(remainder / 86400))
                # Orientation and all external fields use the SAME actual ET.
                t.tdb_fraction = t.tt_fraction + float(D.from_float(et) - tt) / 86400
                position = (
                    np.zeros(3)
                    if site is None
                    else wgs84.latlon(
                        site["latitude_deg"], site["longitude_deg"], elevation_m=site["elevation_m"]
                    )
                    .at(t)
                    .position.m
                )
                bodies = []
                for ident in policy["body_ids"]:
                    state, _ = spice.spkez(ident, et, "J2000", "NONE", 399)
                    bodies.append(
                        dict(
                            id=ident,
                            gm_km3_s2=gm[ident],
                            displacement_tdb_m=[serial(v * 1000) for v in state[:3]],
                            barycentric_velocity_m_s=[
                                serial(v * 1000 + ve)
                                for v, ve in zip(state[3:], velocity, strict=True)
                            ],
                        )
                    )
                days, remainder = divmod(D.from_float(et), D(86400))
                jd1, jd2 = float(2451545 + days), float(remainder / 86400)
                jclock = segment.compute(jd1, jd2)[0]
                jv = (
                    (
                        spk[0, 3].compute_and_differentiate(jd1, jd2)[1]
                        + spk[3, 399].compute_and_differentiate(jd1, jd2)[1]
                    )
                    * 1000
                    / 86400
                )
                state = dict(
                    et_seconds=str(D.from_float(et)),
                    clock_tt_minus_tdb_seconds=serial(clock[0]),
                    clock_derivative=serial(clock[3]),
                    position_tt_m=[serial(v) for v in position],
                    earth_velocity_m_s=[serial(v) for v in velocity],
                    bodies=bodies,
                    reader_check=dict(
                        clock_seconds=serial(jclock),
                        velocity_m_s=[serial(v) for v in jv],
                        jd_parts=[str(D.from_float(jd1)), str(D.from_float(jd2))],
                        argument_error_seconds=str(
                            (D.from_float(jd1) - 2451545 + D.from_float(jd2)) * 86400
                            - D.from_float(et)
                        ),
                    ),
                )
                state["reference"] = encode(local_mapping(state))
                return state

            def solve(source, site):
                tt = D(source["tt_seconds_from_j2000"])
                delta, trace, states = D(0), [], {}
                converged = False
                for _ in range(policy["design"]["max_iterations"]):
                    requested = tt + delta
                    et = float(requested)
                    key = str(D.from_float(et))
                    if key not in states:
                        states[key] = state_at(tt, et, site)
                    s = states[key]
                    d, shift = (
                        D(s["clock_tt_minus_tdb_seconds"]),
                        D(s["reference"]["site_shift_seconds"]),
                    )
                    residual = delta + d - shift
                    following = shift - d
                    trace.append(
                        dict(
                            delta_seconds=str(delta),
                            et_seconds=key,
                            argument_error_seconds=str(D.from_float(et) - requested),
                            residual_seconds=str(residual),
                            next_delta_seconds=str(following),
                        )
                    )
                    if abs(residual) <= D(policy["design"]["solver_residual_seconds"]):
                        converged = True
                        break
                    delta = following
                return dict(
                    id=source["id"],
                    geocentric_id=source["geocentric_id"],
                    utc=source["utc"],
                    site=site,
                    tt_seconds_from_j2000=source["tt_seconds_from_j2000"],
                    states=list(states.values()),
                    solution=dict(converged=converged, delta_seconds=str(delta), trace=trace),
                )

            cases = [solve(row, row["site"]) for row in old["cases"]]
            controls, seen = [], set()
            for row in old["cases"]:
                if row["geocentric_id"] not in seen:
                    seen.add(row["geocentric_id"])
                    control = solve(row, None)
                    control["id"] = row["geocentric_id"]
                    controls.append(control)
    finally:
        spice.unload(str(kernel))
    forbidden = sorted(
        n
        for n in sys.modules
        if n.split(".")[0] in {"astropy", "erfa", "astroscope", "pint"}
        or n == "validation.coupled_clock"
    )
    if forbidden:
        raise ValueError("Reference independence violated")
    return dict(
        schema_version="1.0",
        model_id=policy["model_id"],
        policy_sha256=sha(POLICY),
        generator_sha256=sha(Path(__file__)),
        kernel_sha256=sha(kernel),
        gm_sha256=sha(gm_file),
        packages=packages,
        python_version=platform.python_version(),
        cspice_toolkit="CSPICE_N0067",
        forbidden_imports=forbidden,
        network="socket connect/connect_ex/create_connection blocked",
        approximate_skyfield_clock="disabled_with_raising_patch",
        frame="TT-compatible nominal station; TCB-compatible local polynomial",
        coefficient_model="ten Newtonian monopoles; Q=0; total potential derivative",
        physical_site_clock_bound_seconds=None,
        observing_eligible=False,
        cases=cases,
        geocentric_controls=controls,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--gm-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (
        localcontext(Context(prec=90)),
        patch.object(socket.socket, "connect", deny),
        patch.object(socket.socket, "connect_ex", deny),
        patch.object(socket, "create_connection", deny),
    ):
        result = generate(args.kernel, args.gm_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        files = {
            str(p.relative_to(ROOT)): sha(p)
            for p in (
                POLICY,
                FIXTURE,
                Path(__file__),
                ROOT / "validation/reference_generation/coupled-clock-requirements.txt",
            )
        }
        files.update(json.loads(POLICY.read_text())["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(
        json.dumps(
            dict(
                cases=len(result["cases"]),
                controls=len(result["geocentric_controls"]),
                converged=sum(
                    r["solution"]["converged"]
                    for r in result["cases"] + result["geocentric_controls"]
                ),
            )
        )
    )


if __name__ == "__main__":
    main()
