"""Explicit offline PINT component fixtures and Skyfield historical domain census.

No AstroScope candidate is imported. PINT supplies a single propagation term,
not a full BJD converter; its Astropy units dependency is explicitly shared.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import math
import platform
import socket
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/source_reference_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/source_reference_v1.json"
MANIFEST = ROOT / "validation/manifests/source_reference_v1.json"
REQUIREMENTS = ROOT / "validation/reference_generation/source-reference-requirements.txt"
ADAPTER = ROOT / "docs/research/evidence/pint_reference_input_audit_v1.json"
KERNEL_SHA = "a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_float(value):
    return format(float(value), ".17g")


def deny_network(*args, **kwargs):
    raise RuntimeError("Reference generation must be offline")


def generate():
    import astropy.constants as const
    import astropy.units as u
    import numpy as np
    import pint
    from astropy.table import Column
    from pint.models.astrometry import AstrometryEquatorial
    from pint.models.solar_system_shapiro import SolarSystemShapiro
    from pint.models.timing_model import TimingModel
    from pint.toa import TOAs
    from skyfield.api import load_file, wgs84
    from skyfield.timelib import Timescale
    from skyfield_data import get_skyfield_data_path

    if any(
        n == "validation.source_reference" or n.split(".")[0] == "astroscope" for n in sys.modules
    ):
        raise RuntimeError("Candidate imported in reference process")
    policy = json.loads(POLICY.read_text())
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen input checksum mismatch")
    method = SolarSystemShapiro.ss_obj_shapiro_delay
    hashes = {
        "method_sha256": hashlib.sha256(inspect.getsource(method).encode()).hexdigest(),
        "barycentric_method_sha256": hashlib.sha256(
            inspect.getsource(TimingModel.get_barycentric_toas).encode()
        ).hexdigest(),
    }
    if any(value != policy["reference"][key] for key, value in hashes.items()):
        raise ValueError("Unreviewed PINT method")
    adapter = json.loads(ADAPTER.read_text())
    if (
        hashlib.sha256(inspect.getsource(TOAs.compute_posvels).encode()).hexdigest()
        != adapter["upstream_compute_posvels_sha256"]
    ):
        raise ValueError("Unreviewed PINT input contract")
    if (
        hashlib.sha256(inspect.getsource(AstrometryEquatorial.xyz_from_radec).encode()).hexdigest()
        != adapter["upstream_direction_method_sha256"]
    ):
        raise ValueError("Unreviewed PINT direction input")
    versions = {}
    for line in REQUIREMENTS.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        versions[name] = importlib.metadata.version(name)
        if versions[name] != expected:
            raise ValueError(f"Reference version mismatch: {name}")
    if pint.GMsun.to_value(u.m**3 / u.s**2) != float(
        policy["constants"]["gm_sun_m3_per_s2"]
    ) or const.au.value != float(policy["constants"]["au_m"]):
        raise ValueError("Reference constant mismatch")

    def row(identifier, vector, direction, radius, cosine, **context):
        # This independent generator's classification is checked again by the audit.
        reasons = []
        if not 0.9 <= float(radius) <= 1.1:
            reasons.append("radius_outside_component_domain")
        if not -1 <= float(cosine) <= 0.8:
            reasons.append("solar_elongation_outside_component_domain")
        delay = (
            None
            if reasons
            else text_float(
                method(
                    Column(np.array([vector]), unit=u.au),
                    np.array([direction]) * u.dimensionless_unscaled,
                    pint.Tsun.value,
                )[0]
            )
        )
        return dict(
            id=identifier,
            observer_to_sun_au=[text_float(x) for x in vector],
            direction_icrs=[text_float(x) for x in direction],
            radius_au=radius,
            cosine=cosine,
            status="excluded" if reasons else "eligible_component_input",
            exclusion_reasons=reasons,
            pint_propagation_delay_seconds=delay,
            **context,
        )

    synthetic = []
    for radius in policy["synthetic_grid"]["radii_au"]:
        for cosine, sine in policy["synthetic_grid"]["cosine_sine_pairs"]:
            for axis in policy["synthetic_grid"]["axes"]:
                vector, direction = [0.0] * 3, [0.0] * 3
                vector[axis] = float(radius)
                direction[axis], direction[(axis + 1) % 3] = float(cosine), float(sine)
                synthetic.append(
                    row(
                        f"synthetic_{radius}_{cosine}_{axis}",
                        vector,
                        direction,
                        radius,
                        cosine,
                        axis=axis,
                    )
                )

    old = json.loads((ROOT / policy["historical_census"]["policy"]).read_text())
    eop = json.loads((ROOT / "validation/fixtures/solar_lunar_eop_v1.json").read_text())["rows"]
    leaps = json.loads((ROOT / "validation/fixtures/observer_arrival_leaps_v1.json").read_text())[
        "rows"
    ]
    tt = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in eop])
    delta_t = np.array([69.184 - r["UT1_UTC"] for r in eop])
    ts = Timescale(
        lambda x: np.interp(x, tt, delta_t),
        np.array([r["mjd"] + 2400000.5 for r in leaps]),
        np.array([r["tai_utc"] for r in leaps]),
    )
    ts.polar_motion_table = (
        tt,
        np.array([r["PM_x"] for r in eop]),
        np.array([r["PM_y"] for r in eop]),
    )
    kernel = Path(get_skyfield_data_path()) / "de421.bsp"
    if sha(kernel) != KERNEL_SHA:
        raise ValueError("DE421 checksum mismatch")
    historical = []
    with closing(load_file(str(kernel))) as eph:
        for date in old["dates"]:
            for site in old["sites"]:
                observer = eph["earth"] + wgs84.latlon(
                    site["latitude_deg"], site["longitude_deg"], elevation_m=site["elevation_m"]
                )
                for target_index, target in enumerate(old["targets"]):
                    ra, dec = map(math.radians, (target["ra_deg"], target["dec_deg"]))
                    direction = np.array(
                        [math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)]
                    )
                    for hour in old["hours"]:
                        utc = f"{date}T{hour:02}:00:00+00:00"
                        t = ts.from_datetime(datetime.fromisoformat(utc))
                        # Simultaneous geometric vectors, deliberately no observe()/apparent().
                        vector = eph["sun"].at(t).position.au - observer.at(t).position.au
                        radius = float(np.linalg.norm(vector))
                        cosine = float(np.dot(vector, direction) / radius)
                        historical.append(
                            row(
                                f"{date}_{site['name']}_{target_index}_{hour}",
                                vector,
                                direction,
                                text_float(radius),
                                text_float(cosine),
                                utc=utc,
                                site=site,
                                target=target,
                                target_index=target_index,
                            )
                        )
    return dict(
        schema_version="1.0",
        convention_id=policy["convention"]["id"],
        synthetic=synthetic,
        historical=historical,
        provenance=dict(
            generator_sha256=sha(Path(__file__)),
            policy_sha256=sha(POLICY),
            requirements_sha256=sha(REQUIREMENTS),
            packages=versions,
            python=platform.python_version(),
            **hashes,
            kernel_sha256=sha(kernel),
            kernel_distribution="skyfield-data 7.0.0",
            pint_tsun_seconds=text_float(pint.Tsun.value),
            network="socket connections blocked",
            full_pint_timing_pipeline_executed=False,
            physical_reference_bound_seconds=None,
            independence=policy["reference"]["independence"],
        ),
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
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        policy = json.loads(POLICY.read_text())
        inputs = [POLICY, FIXTURE, REQUIREMENTS, ADAPTER, Path(__file__)]
        files = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        files.update(policy["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(
        json.dumps(
            {
                "synthetic": len(result["synthetic"]),
                "historical": len(result["historical"]),
                "sha256": sha(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
