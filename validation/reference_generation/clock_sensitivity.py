"""Independent supplied-input reference: standard library only, no candidate imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from decimal import Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/clock_sensitivity_policy_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_fraction(value):
    return str(Decimal(value.numerator) / Decimal(value.denominator))


def generate():
    with localcontext(Context(prec=100)):
        return _generate()


def _generate():
    policy = json.loads(POLICY.read_text())
    for path, expected in policy["frozen_inputs"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("frozen_input_checksum")
    # Independently transcribed defining constants and analytic partials.
    c2 = Decimal(299792458) ** 2
    lb, lg = Decimal("1.550519768e-8"), Decimal("6.969290134e-10")
    a = 1 + lb - lg
    old = json.loads((ROOT / "validation/fixtures/coupled_clock_v1.json").read_text())
    rates = []
    for case in old["geocentric_controls"]:
        et = case["solution"]["trace"][-1]["et_seconds"]
        selected = [s for s in case["states"] if s["et_seconds"] == et]
        if len(selected) != 1 or case["site"] is not None:
            raise ValueError("unique_geocentric_state")
        state = selected[0]
        velocity = [Decimal(x) for x in state["earth_velocity_m_s"]]
        energy = sum(v * v for v in velocity) / 2
        partials = [{"id": f"v_{i}", "value": str(-a * v / c2)} for i, v in enumerate(velocity)]
        for body in state["bodies"]:
            mu = Decimal(body["gm_km3_s2"]) * 10**9
            d = [Decimal(x) for x in body["displacement_tdb_m"]]
            r = sum(x * x for x in d).sqrt()
            energy += mu / r
            partials.extend(
                {"id": f"d_{body['id']}_{i}", "value": str(a * mu * x / (c2 * r**3))}
                for i, x in enumerate(d)
            )
            partials.append({"id": f"mu_{body['id']}", "value": str(-a / (c2 * r))})
        rates.append(
            dict(
                id=case["id"],
                et_seconds=et,
                rate_seconds_per_second=str(a * (lb - energy / c2) - lg),
                partials=partials,
            )
        )
    mappings = []
    for model, filename in (("DE440t", "time_ephemeris"), ("INPOP21a", "cross_model_time")):
        old = json.loads((ROOT / f"validation/fixtures/{filename}_v1.json").read_text())
        for case in old["cases"]:
            derivative = case["cspice"]["trace"][-1]["derivative_seconds_per_second"]
            f = Fraction(derivative)
            mappings.append(
                dict(
                    id=f"{model}:{case['id']}",
                    derivative_seconds_per_second=derivative,
                    delta_per_clock_perturbation=encode_fraction(-1 / (1 + f)),
                    delta_per_tt=encode_fraction(-f / (1 + f)),
                    tdb_per_tt=encode_fraction(1 / (1 + f)),
                )
            )
    controls = []
    for case in policy["controls"]:
        j = list(map(Fraction, case["jacobian"]))
        cov, bounds = case["covariance"], case["box_bounds"]
        variance = None
        if cov is not None and all(x is not None for row in cov for x in row):
            # Reference expands diagonal and pairwise cross terms explicitly.
            variance = sum(j[i] ** 2 * Fraction(cov[i][i]) for i in range(len(j)))
            variance += 2 * sum(
                j[i] * j[k] * Fraction(cov[i][k])
                for i in range(len(j))
                for k in range(i + 1, len(j))
            )
        bound = (
            None
            if bounds is None
            else sum(abs(x) * Fraction(b) for x, b in zip(j, bounds, strict=True))
        )
        controls.append(
            dict(
                id=case["id"],
                linearized_variance_seconds_squared=(
                    None if variance is None else encode_fraction(variance)
                ),
                linearized_box_bound_seconds=(None if bound is None else encode_fraction(bound)),
            )
        )
    return dict(
        schema_version="1.0",
        model_id="geocentric-clock-sensitivity-v1",
        policy_sha256=digest(POLICY),
        generator_sha256=digest(Path(__file__)),
        arithmetic=policy["reference_arithmetic"],
        independent_physical_reference=False,
        rates=rates,
        mappings=mappings,
        controls=controls,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Sensitivity reference must be offline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
