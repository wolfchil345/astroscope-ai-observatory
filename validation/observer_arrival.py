"""Offline research conversion benchmark and retained evidence (Mission 38)."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import subprocess
from pathlib import Path

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time

from validation.observer_arrival_model import (
    MANIFEST,
    ROOT,
    context_coordinates,
    frozen_converter,
    load_inputs,
    sha,
    time_from_jd,
)


def finite_abs_seconds(a: Time, b: Time) -> float:
    value = abs(float((a - b).to_value(u.s)))
    if not math.isfinite(value):
        raise ValueError("Nonfinite benchmark residual")
    return value


def evaluate() -> dict:
    policy, fixture = load_inputs()
    limits = policy["tolerances_seconds"]
    geometric, leap = [], []
    mutants = {name: [] for name in ["wrong_sign", "scale_only", "omitted_site"]}
    with frozen_converter() as converter:
        for row in fixture["cases"]:
            tai = time_from_jd(row["observer_tai_jd"], "tai")
            loc, coord = context_coordinates(row["site"], row["target"])
            expected_b = time_from_jd(row["geometric_tdb_jd"], "tdb", loc)
            actual_b = converter.forward(tai, row["site"], row["target"])
            inverse = converter.inverse(row["geometric_tdb_jd"], row["site"], row["target"])
            forward_error = finite_abs_seconds(actual_b, expected_b)
            inverse_error = finite_abs_seconds(inverse.tai, tai)
            geometric.append(
                dict(
                    id=row["id"],
                    forward_error_seconds=forward_error,
                    inverse_error_seconds=inverse_error,
                    solver_residual_seconds=abs(inverse.residual_seconds),
                    iterations=inverse.iterations,
                    passed=(
                        forward_error <= limits["geometric_forward"]
                        and inverse_error <= limits["geometric_inverse"]
                        and abs(inverse.residual_seconds) <= limits["solver_residual"]
                    ),
                )
            )
            t = Time(tai.jd1, tai.jd2, format="jd", scale="tai", location=loc)
            geo = Time(
                tai.jd1,
                tai.jd2,
                format="jd",
                scale="tai",
                location=EarthLocation.from_geocentric(0, 0, 0, unit=u.m),
            )
            mutated = dict(
                wrong_sign=t.tdb - t.light_travel_time(coord, ephemeris="builtin"),
                scale_only=t.tdb,
                omitted_site=geo.tdb + geo.light_travel_time(coord, ephemeris="builtin"),
            )
            for name, result in mutated.items():
                error = finite_abs_seconds(result, expected_b)
                mutants[name].append(
                    dict(
                        id=row["id"],
                        error_seconds=error,
                        detected=error > limits["geometric_forward"],
                    )
                )
        for row in fixture["leap_cases"]:
            expected_tai = time_from_jd(row["observer_tai_jd"], "tai")
            utc = converter.observer_utc(row["observer_tai_jd"])
            reverse_error = finite_abs_seconds(Time(row["utc"], scale="utc").tai, expected_tai)
            leap.append(
                dict(
                    id=row["id"],
                    expected_utc=row["utc"],
                    actual_utc=utc.isot,
                    reverse_error_seconds=reverse_error,
                    passed=(utc.isot == row["utc"] and reverse_error <= limits["observer_tai_utc"]),
                )
            )
    mutation_summary = {
        name: dict(
            tested_count=len(rows),
            detected_count=sum(r["detected"] for r in rows),
            max_error_seconds=max(r["error_seconds"] for r in rows),
            cases=rows,
        )
        for name, rows in mutants.items()
    }
    passed = all(r["passed"] for r in geometric + leap) and all(
        v["detected_count"] > 0 for v in mutation_summary.values()
    )
    return dict(
        schema_version="1.0",
        benchmark_id="observer-arrival-v1",
        passed=passed,
        claim="Sampled cross-implementation geometric-model agreement and historical scale checks",
        observing_eligible=False,
        model_id=policy["model_id"],
        omissions=policy["omissions"],
        counts=dict(
            geometric=288,
            leap=5,
            geometric_passed=sum(r["passed"] for r in geometric),
            leap_passed=sum(r["passed"] for r in leap),
            excluded=0,
        ),
        maxima_seconds=dict(
            forward=max(r["forward_error_seconds"] for r in geometric),
            inverse=max(r["inverse_error_seconds"] for r in geometric),
            solver_residual=max(r["solver_residual_seconds"] for r in geometric),
            leap_reverse=max(r["reverse_error_seconds"] for r in leap),
        ),
        max_iterations=max(r["iterations"] for r in geometric),
        correction_sign_counts=dict(
            positive=sum(r["correction_seconds"] > 0 for r in fixture["cases"]),
            negative=sum(r["correction_seconds"] < 0 for r in fixture["cases"]),
        ),
        tolerances_seconds=limits,
        manifest_sha256=sha(MANIFEST),
        source_sha256={
            p: sha(ROOT / p)
            for p in ["validation/observer_arrival.py", "validation/observer_arrival_model.py"]
        },
        environment=dict(
            python=platform.python_version(),
            packages={p: importlib.metadata.version(p) for p in ["astropy", "numpy", "pyerfa"]},
            network="socket connections blocked",
            frozen_eop_and_leaps=True,
        ),
        geometric_cases=geometric,
        leap_cases=leap,
        mutation_checks=mutation_summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = evaluate()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    record["implementation_commit"] = os.getenv("ASTROSCOPE_IMPLEMENTATION_COMMIT", head)
    record["checkout_commit"] = os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", head)
    record["working_tree_dirty"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: record[k] for k in ["passed", "counts", "maxima_seconds"]}))
    if not record["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
