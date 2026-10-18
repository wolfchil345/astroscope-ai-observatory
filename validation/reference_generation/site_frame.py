"""Independent rational spatial inverse for frozen station inputs and DE440t states."""

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
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

import numpy as np
import spiceypy as spice

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/site_frame_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/site_frame_v1.json"
MANIFEST = ROOT / "validation/manifests/site_frame_v1.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def serial(x):
    if not math.isfinite(x):
        raise ValueError("Nonfinite reference value")
    return format(float(x), ".17g")


def grid(x):
    """Round exact rational to 1e-30 m, ties toward positive infinity."""
    n = (2 * x.numerator * 10**30 + x.denominator) // (2 * x.denominator)
    sign = "-" if n < 0 else ""
    whole, fraction = divmod(abs(n), 10**30)
    return f"{sign}{whole}.{fraction:030d}"


def inverse(position, velocity, potential, acceleration, policy):
    c2 = F(policy["constants"]["c_m_s"]) ** 2
    fb = 1 - F(policy["constants"]["L_B"])
    fg = 1 - F(policy["constants"]["L_G"])
    x = [F(t) / fg for t in position]
    v, a = [F(t) for t in velocity], [fb * F(t) for t in acceleration]
    w = F(potential)
    # Component/matrix implementation, separate from the live NumPy candidate
    # and the audit's compact vector expression.
    matrix = [[(v[i] * v[j] / 2 + (w if i == j else 0)) / c2 for j in range(3)] for i in range(3)]
    r = x
    trace = []
    for _ in range(policy["design"]["iterations"]):
        next_r = []
        for i in range(3):
            linear = sum(matrix[i][j] * r[j] for j in range(3))
            quadratic = sum((r[i] * a[j] * r[j] - a[i] * r[j] ** 2 / 2) / c2 for j in range(3))
            next_r.append(grid(x[i] - linear - quadratic))
        trace.append(next_r)
        r = [F(t) for t in next_r]
    return dict(
        tcb_trace_m=trace,
        tdb_first_order_m=[grid(fb * F(t)) for t in trace[0]],
        tdb_inverse_m=[grid(fb * t) for t in r],
    )


def deny(*args, **kwargs):
    raise RuntimeError("Offline spatial reference: network forbidden")


def generate(kernel, gm_file):
    policy = json.loads(POLICY.read_text())
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen input changed: {name}")
    if (
        sha(kernel) != policy["kernel"]["sha256"]
        or kernel.stat().st_size != policy["kernel"]["size_bytes"]
    ):
        raise ValueError("Kernel mismatch")
    if (
        sha(gm_file) != policy["gravity"]["gm_sha256"]
        or gm_file.stat().st_size != policy["gravity"]["gm_size_bytes"]
    ):
        raise ValueError("GM source mismatch")
    packages = {n: importlib.metadata.version(n) for n in policy["reference_packages"]}
    if packages != policy["reference_packages"] or spice.tkvrsn("TOOLKIT") != "CSPICE_N0067":
        raise ValueError("Reference environment mismatch")
    # Retain exact decimal constants from source; SI conversion occurs below.
    gm = {
        int(n): v.replace("D", "E")
        for n, v in re.findall(r"BODY(\d+)_GM\s*=\s*\(\s*([\d.E+D-]+)\s*\)", gm_file.read_text())
    }
    ids = policy["gravity"]["ids"]
    source = json.loads((ROOT / "validation/fixtures/site_clock_v1.json").read_text())
    cases = []
    controls = []
    seen = set()
    spice.furnsh(str(kernel))
    try:
        for old in source["cases"]:
            et_text = old["solution"]["trace"][-1]["et_seconds"]
            et = float(et_text)
            bodies = []
            total_w, total_a = 0.0, np.zeros(3)
            for body in ids:
                state, _ = spice.spkez(body, et, "J2000", "NONE", 399)
                d = state[:3] * 1000
                mu = float(gm[body]) * 1e9
                radius = np.linalg.norm(d)
                if radius <= 0:
                    raise ValueError("Invalid body separation")
                total_w += mu / radius
                total_a += mu * d / radius**3
                bodies.append(
                    dict(id=body, gm_km3_s2=gm[body], displacement_tdb_m=[serial(t) for t in d])
                )
            earth, _ = spice.spkez(399, et, "J2000", "NONE", 0)
            w, a = serial(total_w), [serial(t) for t in total_a]
            common = dict(
                velocity_m_s=old["earth_velocity_m_s"], potential_m2_s2=w, acceleration_tdb_m_s2=a
            )
            result = inverse(old["site_position_gcrs_m"], common["velocity_m_s"], w, a, policy)
            cases.append(
                dict(
                    id=old["id"],
                    geocentric_id=old["geocentric_id"],
                    et_seconds=et_text,
                    site=old["site"],
                    position_tt_m=old["site_position_gcrs_m"],
                    fresh_earth_velocity_m_s=[serial(t * 1000) for t in earth[3:]],
                    bodies=bodies,
                    reference=result,
                    **common,
                )
            )
            if old["geocentric_id"] not in seen:
                seen.add(old["geocentric_id"])
                controls.append(
                    dict(
                        id=old["geocentric_id"],
                        source_site_id=old["id"],
                        meaning="algebraic_zero_site_control_not_new_epoch_sample",
                        reference=inverse(["0"] * 3, common["velocity_m_s"], w, a, policy),
                    )
                )
    finally:
        spice.unload(str(kernel))
    forbidden = sorted(
        n
        for n in sys.modules
        if n.split(".")[0] in {"astropy", "erfa", "astroscope", "pint", "skyfield"}
        or n == "validation.site_frame"
    )
    if forbidden:
        raise ValueError("Forbidden reference dependency")
    return dict(
        schema_version="1.0",
        model_id=policy["model_id"],
        policy_sha256=sha(POLICY),
        generator_sha256=sha(Path(__file__)),
        kernel_sha256=sha(kernel),
        gm_source_sha256=sha(gm_file),
        packages=packages,
        python_version=platform.python_version(),
        cspice_toolkit="CSPICE_N0067",
        forbidden_imports=forbidden,
        network="socket connect/connect_ex/create_connection blocked",
        source_position_assumption="TT-compatible nominal WGS84 rotated vector",
        reference_arithmetic="Fraction matrix inverse; four grid-rounded fixed-point updates",
        coefficient_model="ten-body Newtonian monopoles; supplied decimal coefficients",
        physical_spatial_bound_m=None,
        observing_eligible=False,
        cases=cases,
        zero_controls=controls,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--gm-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny),
        patch.object(socket.socket, "connect_ex", deny),
        patch.object(socket, "create_connection", deny),
    ):
        result = generate(args.kernel, args.gm_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        policy = json.loads(POLICY.read_text())
        paths = [
            POLICY,
            FIXTURE,
            Path(__file__),
            ROOT / "validation/reference_generation/site-frame-requirements.txt",
        ]
        files = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        files.update(policy["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(json.dumps(dict(cases=len(result["cases"]), zero_controls=len(result["zero_controls"]))))


if __name__ == "__main__":
    main()
