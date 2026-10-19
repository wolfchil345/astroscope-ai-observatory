"""Exact affine definitions, independent of candidate time libraries.

Historical inputs are reused Mission 42 outputs, not new ephemeris observations.
Only serialization uses Decimal; every reference operation uses Fraction.
Python 3.12 standard library is the complete reference dependency set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from decimal import Context, Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "validation/manifests/time_normalization_policy_v1.json"


def encode(value):
    with localcontext(Context(prec=90)):
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def generate():
    policy = json.loads(POLICY.read_text())
    for path, digest in policy["frozen_inputs"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen_input_checksum")
    # Literals are independently transcribed from IAU definitions, not obtained
    # from an astronomy package's constants or candidate helper.
    lb, lg, d0 = F("1.550519768e-8"), F("6.969290134e-10"), F("-0.0000655")
    origin = (F("2443144.5003725") - F(2451545)) * 86400
    fb, fg = 1 - lb, 1 - lg
    controls = []
    for text in policy["controls_tcb_or_tcg_seconds_from_T0"]:
        x = F(text)
        controls.append(
            dict(
                seconds_from_T0=text,
                tdb_minus_tcb_seconds=encode(d0 - lb * x),
                tt_minus_tcg_seconds=encode(-lg * x),
                tcb_minus_tdb_seconds=encode((lb * x - d0) / fb),
                tcg_minus_tt_seconds=encode(lg * x / fg),
            )
        )
    prior = json.loads((ROOT / "validation/results/time_ephemeris_reference_run.json").read_text())
    rows = []
    for row in prior["cases"]:
        a = F(row["tt_seconds_from_j2000"])
        delta = F(row["reference_tdb_minus_tt_seconds"])
        b = a + delta
        c = (b - lb * origin - d0) / fb
        g = (a - lg * origin) / fg
        assert (b - c) + (c - g) + (g - a) == delta
        rows.append(
            dict(
                id=row["id"],
                kind=row["kind"],
                tt_seconds_from_j2000=row["tt_seconds_from_j2000"],
                reused_de440t_delta_seconds=row["reference_tdb_minus_tt_seconds"],
                tdb_minus_tcb_seconds=encode(b - c),
                tcb_minus_tcg_seconds=encode(c - g),
                tcg_minus_tt_seconds=encode(g - a),
            )
        )
    return dict(
        schema_version="1.0",
        model_id="iau2006-2000-affine-normalization-v1",
        arithmetic="exact_Fraction_with_90_digit_decimal_serialization",
        independent_physical_time_ephemeris=False,
        constants=policy["constants"],
        controls=controls,
        cases=rows,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Normalization reference must be offline")


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
