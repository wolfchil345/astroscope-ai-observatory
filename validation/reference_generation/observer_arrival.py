"""Freeze independent geometric timing pairs; never import candidate astronomy code.

Run explicitly in the reference environment. CI consumes the committed JSON.
The coordinate is the declared geometric model, not a complete relativistic BJD.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import socket
import sys
from contextlib import closing
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import numpy as np
from skyfield.api import load_file, wgs84
from skyfield.timelib import Timescale
from skyfield_data import get_skyfield_data_path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/observer_arrival_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/observer_arrival_v1.json"
MANIFEST = ROOT / "validation/manifests/observer_arrival_v1.json"
EOP = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
LEAPS = ROOT / "validation/fixtures/observer_arrival_leaps_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal_sum(*values: float) -> str:
    with localcontext() as ctx:
        ctx.prec = 60
        return str(sum((Decimal.from_float(float(v)) for v in values), Decimal(0)))


def rational_string(value: Fraction) -> str:
    with localcontext() as ctx:
        ctx.prec = 60
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def deny_network(*args, **kwargs):
    raise RuntimeError("Reference generation must be offline")


def generate() -> dict:
    if any(n.split(".")[0] in {"astropy", "erfa", "astroscope"} for n in sys.modules):
        raise RuntimeError("Candidate astronomy imports in independent reference environment")
    policy = json.loads(POLICY.read_text())
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen input checksum mismatch")
    rows = json.loads(EOP.read_text())["rows"]
    leaps = json.loads(LEAPS.read_text())["rows"]
    tt = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in rows])
    delta_t = np.array([69.184 - r["UT1_UTC"] for r in rows])
    ts = Timescale(
        lambda x: np.interp(x, tt, delta_t),
        np.array([r["mjd"] + 2400000.5 for r in leaps]),
        np.array([r["tai_utc"] for r in leaps]),
    )
    ts.polar_motion_table = (
        tt,
        np.array([r["PM_x"] for r in rows]),
        np.array([r["PM_y"] for r in rows]),
    )
    kernel = Path(get_skyfield_data_path()) / "de421.bsp"
    # Same DE421 payload already archived by Mission 34's reference provenance.
    if sha(kernel) != "a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc":
        raise ValueError("Unexpected DE421 kernel checksum")
    cases = []
    with closing(load_file(str(kernel))) as eph:
        for date in policy["dates"]:
            for s in policy["sites"]:
                site = {**s, "datum": "WGS84"}
                observer = eph["earth"] + wgs84.latlon(
                    s["latitude_deg"], s["longitude_deg"], elevation_m=s["elevation_m"]
                )
                for target_index, direction in enumerate(policy["targets"]):
                    target = {
                        **direction,
                        "frame": "ICRS",
                        "coordinate_epoch": policy["coordinate_epoch"],
                        "motion_assumption": policy["motion_assumption"],
                    }
                    ra, dec = map(math.radians, [direction["ra_deg"], direction["dec_deg"]])
                    unit = np.array(
                        [math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)]
                    )
                    for role, hour in zip(policy["roles"], policy["hours"], strict=True):
                        dt = datetime.fromisoformat(f"{date}T{hour:02}:00:00+00:00")
                        t = ts.from_datetime(dt)
                        # SI km/s, independent dot product: no astrometric observe() delay.
                        correction_s = float(np.dot(observer.at(t).position.km, unit) / 299792.458)
                        # Never collapse the Julian date to one float.
                        b = decimal_sum(t.whole, t.tdb_fraction, correction_s / 86400)
                        # Gregorian ordinal + historical IERS 37 s, independent of Skyfield TAI.
                        tai = Fraction(dt.date().toordinal()) + Fraction(3442849, 2)
                        tai += Fraction(hour * 3600 + 37, 86400)
                        cases.append(
                            dict(
                                id=f"{date}_{s['name']}_{target_index}_{role}",
                                utc=dt.isoformat(),
                                site=site,
                                target=target,
                                role=role,
                                geometric_tdb_jd=b,
                                observer_tai_jd=rational_string(tai),
                                correction_seconds=correction_s,
                            )
                        )
    # Bulletin C52: 23:59:59, :60, 00:00:00 correspond to TAI +35, +36, +37 s
    # relative to Gregorian midnight 2017-01-01. Fractional leap probes are explicit.
    leap_cases = []
    for label, seconds in [
        ("2016-12-31T23:59:59.000000000", "35"),
        ("2016-12-31T23:59:60.000000000", "36"),
        ("2016-12-31T23:59:60.250000000", "36.25"),
        ("2016-12-31T23:59:60.999000000", "36.999"),
        ("2017-01-01T00:00:00.000000000", "37"),
    ]:
        tai = Fraction(4915509, 2) + Fraction(seconds) / 86400
        leap_cases.append(
            dict(id=f"leap_{seconds}", utc=label, observer_tai_jd=rational_string(tai))
        )
    result = dict(
        schema_version="1.0",
        model_id=policy["model_id"],
        cases=cases,
        leap_cases=leap_cases,
        reference=dict(
            generator_sha256=sha(Path(__file__)),
            policy_sha256=sha(POLICY),
            packages={
                p: importlib.metadata.version(p)
                for p in ["skyfield", "skyfield-data", "numpy", "jplephem", "sgp4"]
            },
            kernel="de421.bsp",
            kernel_sha256=sha(kernel),
            kernel_source="https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
            kernel_distribution="skyfield-data 7.0.0 (data sources recorded by package)",
            independence=policy["independence"],
            network="socket connections blocked",
        ),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = generate()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    # Alternative outputs support bitwise regeneration checks without changing the manifest.
    if args.output.resolve() == FIXTURE.resolve():
        inputs = [FIXTURE, EOP, LEAPS, POLICY, Path(__file__)]
        manifest = dict(
            schema_version="1.0",
            benchmark_id="observer-arrival-v1",
            files={str(p.relative_to(ROOT)): sha(p) for p in inputs},
            expected_geometric_case_count=288,
            expected_leap_case_count=5,
        )
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "geometric_pairs": len(result["cases"]),
                "leap_pairs": len(result["leap_cases"]),
                "sha256": sha(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
