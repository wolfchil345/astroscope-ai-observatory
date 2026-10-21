"""Independent manufactured trajectories and clock antiderivatives; stdlib only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import socket
from decimal import Context, localcontext
from decimal import Decimal as D
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/integrated_clock_response_policy_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal(value):
    return D(value.numerator) / D(value.denominator) if isinstance(value, Q) else D(value)


def encode(value):
    value = decimal(value)
    return "0" if value == 0 else str(value)


def trig(angle):
    sine, cosine, s, c = angle, D(1), angle, D(1)
    for k in range(1, 80):
        s *= -angle * angle / ((2 * k) * (2 * k + 1))
        c *= -angle * angle / ((2 * k - 1) * (2 * k))
        sine += s
        cosine += c
    return sine, cosine


def endpoint(case):
    if case["family"] == "constant_acceleration":
        x0, v0, a, k, d0 = map(Q, case["parameters"])
        u = Q(case["span_seconds"])
        lam, beta = Q("0.002"), Q("0.003")
        x, v = x0 + v0 * u + a * u * u / 2, v0 + a * u
        clock = d0 + (k + lam * x0 + beta * v0 * v0) * u + (lam * v0 / 2 + beta * v0 * a) * u * u
        clock += (lam * a / 6 + beta * a * a / 3) * u**3
        sx, sv = [Q(1), u, u * u / 2, Q(0), Q(0)], [Q(0), Q(1), u, Q(0), Q(0)]
        g = [
            lam * u,
            2 * beta * v0 * u + (lam / 2 + beta * a) * u * u,
            beta * v0 * u * u + (lam / 6 + 2 * beta * a / 3) * u**3,
            u,
            Q(1),
        ]
    else:
        x0, v0, a, k, d0 = map(D, case["parameters"])
        u = D(case["span_seconds"])
        lam, beta, w = D("0.002"), D("0.003"), D("0.5")
        s, c = trig(w * u)
        s2, _ = trig(2 * w * u)
        h = a / (w * w)
        amplitude = x0 - h
        x, v = h + amplitude * c + v0 * s / w, -amplitude * w * s + v0 * c
        left, right = u / 2 - s2 / (4 * w), u / 2 + s2 / (4 * w)
        ix = h * u + amplitude * s / w + v0 * (1 - c) / (w * w)
        iv = amplitude * amplitude * w * w * left + v0 * v0 * right - amplitude * v0 * s * s
        clock = d0 + k * u + lam * ix + beta * iv
        vx = 2 * amplitude * w * w * left - v0 * s * s
        vv = 2 * v0 * right - amplitude * s * s
        g = [
            lam * s / w + beta * vx,
            lam * (1 - c) / (w * w) + beta * vv,
            lam * (u - s / w) / (w * w) - beta * vx / (w * w),
            u,
            D(1),
        ]
        sx, sv = [c, s / w, (1 - c) / (w * w), D(0), D(0)], [-w * s, c, s / w, D(0), D(0)]
    rate = k + lam * x + beta * v * v
    values = [x, v, clock, *sx, *sv, *g]
    # Polynomial arithmetic stays rational through implicit mapping and covariance.
    implicit = [-value / (1 + rate) for value in g]
    return values, rate, g, implicit


def covariance_mode(raw, mode):
    c = copy.deepcopy(raw)
    if mode == "fixed":
        for i in range(5):
            c[i][4] = c[4][i] = "0"
    elif mode == "unknown_cross":
        c[0][4] = c[4][0] = None
    return c


def variance(j, c):
    if any(x is None for row in c for x in row):
        return None
    cast = Q if isinstance(j[0], Q) else D
    matrix = [[cast(x) for x in row] for row in c]
    answer = sum(j[i] ** 2 * matrix[i][i] for i in range(5))
    answer += 2 * sum(j[i] * j[k] * matrix[i][k] for i in range(5) for k in range(i + 1, 5))
    return encode(answer)


def generate():
    with localcontext(Context(prec=100)):
        p = json.loads(POLICY.read_text())
        for f, expected in p["frozen_inputs"].items():
            if digest(ROOT / f) != expected:
                raise ValueError("frozen_input_checksum")
        rows = []
        for case in p["cases"]:
            values, rate, g, implicit = endpoint(case)
            b = D(case["anchor_b_seconds"]) + D(case["span_seconds"])
            rows.append(
                dict(
                    id=case["id"],
                    augmented_state=[encode(x) for x in values],
                    rate=encode(rate),
                    b_seconds=str(b),
                    tt_seconds=str(b + decimal(values[2])),
                    implicit_jacobian=[encode(x) for x in implicit],
                    covariances=[
                        dict(
                            mode=mode,
                            clock_variance=variance(
                                g, covariance_mode(p["synthetic_covariance"], mode)
                            ),
                            implicit_variance=variance(
                                implicit, covariance_mode(p["synthetic_covariance"], mode)
                            ),
                        )
                        for mode in p["anchor_covariance_modes"]
                    ],
                )
            )
        return dict(
            schema_version="1.0",
            model_id=p["model_id"],
            policy_sha256=digest(POLICY),
            generator_sha256=digest(Path(__file__)),
            independent_physical_reference=False,
            cases=rows,
        )


def deny_network(*args, **kwargs):
    raise RuntimeError("Reference generation must be offline")


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
