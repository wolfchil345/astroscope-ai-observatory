"""Offline INPOP21a extraction, independent of Astropy/ERFA and DE440t values.

Acquire the checksum-pinned original kernel separately. This generator never
downloads, uses a leap-second kernel, or imports Astropy/ERFA/production code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import socket
import sys
from datetime import date
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

import spiceypy as spice
from jplephem.spk import SPK

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/cross_model_time_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/cross_model_time_v1.json"
MANIFEST = ROOT / "validation/manifests/cross_model_time_v1.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def serial(value):
    if not math.isfinite(value):
        raise ValueError("Nonfinite reference output")
    return format(float(value), ".17g")


def samples(policy, historical):
    """Calendar arithmetic is independent of the archived Astropy TT inputs."""
    rows = []
    epoch = date(2000, 1, 1).toordinal()
    for day in historical["dates"]:
        if not day.startswith("2024-"):
            raise ValueError("UTC evidence restricted to historical 2024")
        for hour in historical["hours"]:
            seconds = (date.fromisoformat(day).toordinal() - epoch) * 86400 + hour * 3600 - 43200
            rows.append(
                dict(
                    id=f"{day}_{hour:02}",
                    kind="historical",
                    utc=f"{day}T{hour:02}:00:00",
                    tt_seconds_from_j2000=str(Decimal(seconds) + Decimal("69.184")),
                )
            )
    for probe in policy["sample_design"]["tt_epoch_probes"]:
        rows.append(
            dict(
                id=probe["id"],
                kind="tt_epoch_probe",
                utc=None,
                tt_seconds_from_j2000=str((Decimal(probe["tt_jd"]) - 2451545) * 86400),
            )
        )
    return rows


def solve(reader, tt, method, contract):
    delta = 0.0
    trace = []
    for _ in range(contract["max_iterations"]):
        value, derivative, argument = reader(tt, delta)
        residual = delta + value
        next_delta = -value if method == "fixed_point" else delta - residual / (1.0 + derivative)
        trace.append(
            dict(
                delta_seconds=serial(delta),
                tt_minus_tdb_seconds=serial(value),
                derivative_seconds_per_second=serial(derivative),
                equation_residual_seconds=serial(residual),
                next_delta_seconds=serial(next_delta),
                **argument,
            )
        )
        if abs(residual) <= float(contract["convergence_seconds"]):
            return dict(method=method, converged=True, delta_seconds=serial(delta), trace=trace)
        delta = next_delta
    return dict(method=method, converged=False, delta_seconds=serial(delta), trace=trace)


def generate(path):
    policy = json.loads(POLICY.read_text())
    kernel = policy["kernel"]
    if path.stat().st_size != kernel["size_bytes"] or sha(path) != kernel["sha256"]:
        raise ValueError("Original kernel size/checksum mismatch; no fallback")
    for name, digest in policy["frozen_inputs"].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen input mismatch: {name}")
    packages = {name: importlib.metadata.version(name) for name in policy["reference_packages"]}
    if packages != policy["reference_packages"]:
        raise ValueError("Reference package version mismatch")
    if spice.tkvrsn("TOOLKIT") != policy["cspice_toolkit"]:
        raise ValueError("CSPICE version mismatch")
    historical = json.loads(
        (ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text()
    )
    # Verify the independent historical leap fact rather than deriving it from a candidate.
    leaps = json.loads((ROOT / "validation/fixtures/observer_arrival_leaps_v1.json").read_text())[
        "rows"
    ]
    if leaps[-1]["tai_utc"] != 37 or (leaps[-1]["year"], leaps[-1]["month"]) != (2017, 1):
        raise ValueError("Pinned historical leap evidence changed")
    with SPK.open(str(path)) as spk:
        selected = [
            s for s in spk.segments if s.center == kernel["center"] and s.target == kernel["target"]
        ]
        if len(selected) != 1:
            raise ValueError("Unique time segment required")
        segment = selected[0]
        metadata = dict(
            center=segment.center,
            target=segment.target,
            frame=segment.frame,
            spk_type=segment.data_type,
            source=segment.source.decode(),
            coverage_jd_tdb=[serial(segment.start_jd), serial(segment.end_jd)],
        )
        if any(metadata[k] != kernel[k] for k in metadata):
            raise ValueError("Time segment descriptor mismatch")
        spice.furnsh(str(path))
        try:

            def cspice_reader(tt, delta):
                requested = tt + Decimal.from_float(delta)
                et = float(requested)
                handle, descriptor, ident = spice.spksfs(kernel["target"], et, 128)
                target, center, frame, kind, start, end, _, _ = spice.spkuds(descriptor)
                if (
                    (target, center, frame, kind)
                    != (kernel["target"], kernel["center"], kernel["frame"], 2)
                    or ident != kernel["source"]
                    or not start <= et <= end
                ):
                    raise ValueError("CSPICE selected wrong segment")
                frame, state, center = spice.spkpvn(handle, descriptor, et)
                if frame != 1 or center != kernel["center"]:
                    raise ValueError("CSPICE return context mismatch")
                # For the special TT-TDB segment these are seconds and seconds/second,
                # NOT km and km/s. Only the first coordinate is defined as the clock.
                return (
                    float(state[0]),
                    float(state[3]),
                    dict(
                        argument_et_seconds=str(Decimal.from_float(et)),
                        argument_quantization_seconds=str(Decimal.from_float(et) - requested),
                    ),
                )

            def jplephem_reader(tt, delta):
                requested = tt + Decimal.from_float(delta)
                days, remainder = divmod(requested, Decimal(86400))
                jd1, jd2 = float(2451545 + days), float(remainder / 86400)
                value, derivative = segment.compute_and_differentiate(jd1, jd2)
                represented = (Decimal.from_float(jd1) - 2451545 + Decimal.from_float(jd2)) * 86400
                return (
                    float(value[0]),
                    float(derivative[0] / 86400),
                    dict(
                        argument_jd_parts=[
                            str(Decimal.from_float(jd1)),
                            str(Decimal.from_float(jd2)),
                        ],
                        argument_quantization_seconds=str(represented - requested),
                    ),
                )

            rows = samples(policy, historical)
            for row in rows:
                tt = Decimal(row["tt_seconds_from_j2000"])
                row["cspice"] = solve(cspice_reader, tt, "fixed_point", policy["reader_contract"])
                row["jplephem"] = solve(jplephem_reader, tt, "newton", policy["reader_contract"])
        finally:
            spice.unload(str(path))
    forbidden = ("astropy", "erfa", "pint", "skyfield", "astroscope")
    imported = sorted(n for n in sys.modules if n.split(".")[0] in forbidden)
    if imported:
        raise ValueError(f"Candidate/reference boundary violated: {imported}")
    return dict(
        schema_version="1.0",
        evidence_kind="integrated_geocentric_model_evaluation",
        model_id=policy["reference_model_id"],
        policy_sha256=sha(POLICY),
        generator_sha256=sha(Path(__file__)),
        kernel_sha256=kernel["sha256"],
        kernel_size_bytes=path.stat().st_size,
        segment=metadata,
        archive_sha256=policy["archive"]["sha256"],
        physical_model_family="INPOP",
        numerical_algorithms="Adapted from Mission 42; shared readers and solver design",
        units="seconds",
        quantity="TT_minus_TDB",
        argument_scale="TDB",
        origin="geocentre",
        packages=packages,
        cspice_toolkit=spice.tkvrsn("TOOLKIT"),
        python_version=platform.python_version(),
        forbidden_imports=imported,
        network="socket connect/connect_ex/create_connection blocked",
        same_kernel_for_both_readers=True,
        raw_coefficients_vendored=False,
        physical_geocentric_clock_bound_seconds=None,
        observing_eligible=False,
        cases=rows,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Reference generation must be offline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    with (
        localcontext(Context(prec=70)),
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = generate(args.kernel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.output.resolve() == FIXTURE.resolve():
        policy = json.loads(POLICY.read_text())
        paths = [
            POLICY,
            FIXTURE,
            Path(__file__),
            ROOT / policy["reference_environment"],
            ROOT / policy["evidence_ledger"],
        ]
        files = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        files.update(policy["frozen_inputs"])
        MANIFEST.write_text(json.dumps(dict(schema_version="1.0", files=files), indent=2) + "\n")
    print(
        json.dumps(
            dict(
                cases=len(result["cases"]),
                converged=sum(
                    r[k]["converged"] for r in result["cases"] for k in ("cspice", "jplephem")
                ),
            )
        )
    )


if __name__ == "__main__":
    main()
