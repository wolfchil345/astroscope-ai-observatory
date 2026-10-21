"""Independent exact rational basis-transform reference; standard library only."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from decimal import Context, Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/ephemeris_covariance_policy_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matmul(a, b):
    return [
        [sum(x * y for x, y in zip(row, col, strict=True)) for col in zip(*b, strict=True)]
        for row in a
    ]


def transpose(a):
    return list(map(list, zip(*a, strict=True)))


def encode(x):
    with localcontext(Context(prec=100)):
        return format(Decimal(x.numerator) / Decimal(x.denominator), "f")


def generate():
    policy = json.loads(POLICY.read_text())
    for path, expected in policy["frozen_inputs"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("frozen_input_checksum")
    rows = []
    for case in policy["controls"]:
        c = [list(map(Q, row)) for row in case["covariance"]]
        j = list(map(Q, case["jacobian"]))
        # Construct the full map, independently of candidate index operations.
        a = [[Q(0) for _ in j] for _ in j]
        inverse = [[Q(0) for _ in j] for _ in j]
        for row, column in enumerate(case["order"]):
            a[row][column] = Q(case["scales"][row])
            inverse[column][row] = 1 / a[row][column]
        transformed = matmul(matmul(a, c), transpose(a))
        response = matmul([j], inverse)[0]
        # Independent diagonal/cross-term expansion, not the candidate sum.
        variance = sum(j[i] ** 2 * c[i][i] for i in range(len(j))) + 2 * sum(
            j[i] * j[k] * c[i][k] for i in range(len(j)) for k in range(i + 1, len(j))
        )
        rows.append(
            dict(
                id=case["id"],
                covariance=[[encode(v) for v in row] for row in transformed],
                jacobian=[encode(v) for v in response],
                variance=encode(variance),
            )
        )
    return dict(
        schema_version="1.0",
        model_id=policy["model_id"],
        policy_sha256=digest(POLICY),
        generator_sha256=digest(Path(__file__)),
        independent_physical_reference=False,
        controls=rows,
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
