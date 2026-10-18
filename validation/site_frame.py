"""Offline scaled spatial-component audit and exact polynomial inverse certificate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import socket
import subprocess
from decimal import Context, Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/site_frame_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/site_frame_v1.json"
MANIFEST = ROOT / "validation/manifests/site_frame_v1.json"
EXPECTED_MANIFEST_SHA256 = "0348cbaf4482789341ea3b58ad01748b0b7ca21a0eef0c9bf7d20ddf8155998f"
C = F(299792458)
FB = 1 - F("1.550519768e-8")
FG = 1 - F("6.969290134e-10")
BODY_IDS = [10, 1, 2, 4, 5, 6, 7, 8, 9, 301]
RADIUS = F(13000000)


class SiteFrameError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SiteFrameError(message)


def rat(value):
    require(
        isinstance(value, str)
        and len(value) <= 256
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value),
        "finite_decimal_string_required",
    )
    number = F(value)
    require(abs(number) <= 10**24, "numeric_domain")
    return number


def vec(values):
    require(isinstance(values, list) and len(values) == 3, "vector_shape")
    return [rat(x) for x in values]


def dot(a, b):
    return sum((x * y for x, y in zip(a, b, strict=True)), F(0))


def l1(v):
    return sum(map(abs, v), F(0))


def difference(a, b):
    return [x - y for x, y in zip(a, b, strict=True)]


def display(value):
    with localcontext(Context(prec=70)):
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def upward(value):
    """Exact ceiling to a decimal 1e-36 m grid, independent of Decimal context."""
    require(value >= 0, "negative_bound")
    numerator = value.numerator * 10**36
    n = -(-numerator // value.denominator)
    whole, fraction = divmod(n, 10**36)
    return f"{whole}.{fraction:036d}"


def correction(r, v, w, a):
    vr, ar, rr = dot(v, r), dot(a, r), dot(r, r)
    return [
        (vi * vr / 2 + w * ri + ri * ar - ai * rr / 2) / C**2
        for ri, vi, ai in zip(r, v, a, strict=True)
    ]


def certificate(x, v, w, a, z):
    """Banach residual certificate for H(r)=r+P(r)/c² on a declared L1 ball.

    Inputs and residuals are exact rationals. This certifies the polynomial
    inversion, not its physical adequacy or the uncertainty of supplied inputs.
    """
    require(len(x) == len(v) == len(a) == len(z) == 3, "vector_shape")
    v1, a1 = l1(v), l1(a)
    require(v1 <= 70000 and a1 <= F("0.03") and 0 <= w <= 2000000000, "coefficient_domain")
    q = (v1**2 / 2 + abs(w) + 3 * a1 * RADIUS) / C**2
    margin = ((v1**2 / 2 + abs(w)) * RADIUS + 3 * a1 * RADIUS**2 / 2) / C**2
    require(q < 1, "not_contractive")
    require(l1(x) + margin <= RADIUS, "ball_not_invariant")
    require(l1(z) <= RADIUS, "point_outside_ball")
    residual = l1([zi + pi - xi for zi, pi, xi in zip(z, correction(z, v, w, a), x, strict=True)])
    bound = residual / (1 - q)
    return dict(
        q=q,
        residual=residual,
        exact_bound=bound,
        upper_bound_m=upward(bound),
        root_unique_in_ball=True,
        bound_scope="declared_polynomial_supplied_inputs_only",
    )


def candidate_inverse(position, velocity, potential, acceleration):
    """Live NumPy spatial component; TT-compatible input, TDB-compatible output."""
    import numpy as np

    fb, fg = 1.0 - 1.550519768e-8, 1.0 - 6.969290134e-10
    x = np.array(position, dtype=float) / fg
    v = np.array(velocity, dtype=float)
    a = np.array(acceleration, dtype=float) * fb
    w = float(potential)
    matrix = np.outer(v, v) / 2 + w * np.eye(3)
    r = x.copy()
    first = None
    for _ in range(4):
        r = x - (matrix @ r + r * np.dot(a, r) - a * np.dot(r, r) / 2) / 299792458.0**2
        if first is None:
            first = r.copy()
    return first * fb, r * fb


def float_vector(values):
    require(
        len(values) == 3 and all(math.isfinite(float(v)) for v in values), "candidate_nonfinite"
    )
    # Certificate covers the actual binary64 point, not only its 17-digit display.
    return [F.from_float(float(v)) for v in values]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    require(sha(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest_checksum")
    for name, digest in json.loads(MANIFEST.read_text())["files"].items():
        require(sha(ROOT / name) == digest, "input_checksum")
    return [
        json.loads(p.read_text())
        for p in (
            POLICY,
            FIXTURE,
            ROOT / "validation/fixtures/site_clock_v1.json",
            ROOT / "validation/results/site_clock_reference_run.json",
        )
    ]


def replay_gravity(bodies):
    """Independent Decimal coefficient replay from archived vectors and exact GMs."""
    with localcontext(Context(prec=90)):
        w, a = Decimal(0), [Decimal(0)] * 3
        for body in bodies:
            mu = Decimal(body["gm_km3_s2"]) * 10**9
            p = [Decimal(t) for t in body["displacement_tdb_m"]]
            radius = sum(t * t for t in p).sqrt()
            require(radius > 0 and mu > 0, "gravity_domain")
            w += mu / radius
            a = [ai + mu * pi / radius**3 for ai, pi in zip(a, p, strict=True)]
        return F(w), [F(t) for t in a]


def validate_reference(reference, x, v, w, a):
    trace = reference["tcb_trace_m"]
    require(len(trace) == 4, "reference_trace_count")
    previous = x
    for encoded in trace:
        r = vec(encoded)
        expected = difference(x, correction(previous, v, w, a))
        require(l1(difference(r, expected)) <= F("1e-29"), "reference_trace_update")
        previous = r
    first, last = vec(trace[0]), vec(trace[-1])
    require(
        l1(difference(vec(reference["tdb_first_order_m"]), [FB * t for t in first])) <= F("1e-29")
        and l1(difference(vec(reference["tdb_inverse_m"]), [FB * t for t in last])) <= F("1e-29"),
        "output_scale",
    )
    check = certificate(x, v, w, a, last)
    require(check["residual"] <= F("1e-20"), "reference_residual")
    return first, last, check


def summarize(values, units):
    return dict(
        count=len(values),
        minimum=display(min(values)),
        maximum=display(max(values)),
        maximum_absolute=display(max(map(abs, values))),
        units=units,
        interpretation="component_diagnostic_not_physical_uncertainty",
    )


def evaluate_inputs(policy, fixture, historical, prior, candidate=candidate_inverse):
    require(
        policy["model_id"] == fixture["model_id"] == "iau2000-scaled-spatial-1pn-tenbody-v1",
        "model_identity",
    )
    require(
        policy["selected_arrival_convention_id"] == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    require(
        policy["constants"] == dict(c_m_s="299792458", L_B="1.550519768e-8", L_G="6.969290134e-10"),
        "scale_constants",
    )
    limits = dict(
        historical_sites=48,
        zero_controls=12,
        iterations=4,
        reference_grid_m="1e-30",
        candidate_reference_l1_m="2e-8",
        potential_replay_m2_s2="1e-6",
        acceleration_replay_l1_m_s2="1e-16",
        earth_velocity_replay_l1_m_s="1e-6",
        reference_trace_l1_m="1e-29",
        reference_residual_l1_m="1e-20",
        ball_radius_l1_m="13000000",
        max_velocity_l1_m_s="70000",
        max_acceleration_l1_m_s2="0.03",
        max_potential_m2_s2="2000000000",
        display_bound_grid_m="1e-36",
    )
    require(all(policy["design"][k] == val for k, val in limits.items()), "frozen_design")
    require(policy["gravity"]["ids"] == BODY_IDS, "body_inventory")
    require(
        fixture["forbidden_imports"] == []
        and fixture["packages"] == policy["reference_packages"]
        and fixture["cspice_toolkit"] == "CSPICE_N0067",
        "reference_boundary",
    )
    require(
        fixture["kernel_sha256"] == policy["kernel"]["sha256"]
        and fixture["gm_source_sha256"] == policy["gravity"]["gm_sha256"],
        "source_provenance",
    )
    require(
        fixture["source_position_assumption"] == "TT-compatible nominal WGS84 rotated vector",
        "station_scale_assumption",
    )
    require(
        fixture["coefficient_model"]
        == "ten-body Newtonian monopoles; supplied decimal coefficients",
        "gravity_claim",
    )
    require(
        fixture["physical_spatial_bound_m"] is None and fixture["observing_eligible"] is False,
        "false_qualification",
    )
    require(
        policy["gate"]
        == dict(
            spatial_component_status="declared_truncated_model_only",
            physical_spatial_bound_m=None,
            physical_site_clock_bound_seconds=None,
            physical_arrival_bound_seconds=None,
            observing_eligible=False,
            combined_executed=0,
            combined_blocked=288,
        ),
        "gate_changed",
    )
    require(
        [s["id"] for s in policy["sources"]]
        == [
            "iau2000_b13",
            "klioner_scaling",
            "iers_station_scale",
            "iau2000_b15",
            "iau2006_b3",
            "park2021",
        ],
        "evidence_inventory",
    )
    require(
        all(s["numeric_physical_bound_seconds"] is None for s in policy["sources"]),
        "unsupported_bound_transfer",
    )
    old = {r["id"]: r for r in historical["cases"]}
    cases = fixture["cases"]
    require(
        len(cases) == 48
        and len({r["id"] for r in cases}) == 48
        and {r["id"] for r in cases} == set(old),
        "site_inventory",
    )
    rows, coefficients = [], {}
    raw_values = {
        k: []
        for k in (
            "scale_only_l1_m",
            "pn_only_l1_m",
            "total_l1_m",
            "frame_only_clock_change_seconds",
            "first_order_inverse_difference_l1_m",
        )
    }
    for row in cases:
        source = old[row["id"]]
        require(
            row["position_tt_m"] == source["site_position_gcrs_m"]
            and row["velocity_m_s"] == source["earth_velocity_m_s"]
            and row["site"] == source["site"]
            and row["geocentric_id"] == source["geocentric_id"]
            and row["et_seconds"] == source["solution"]["trace"][-1]["et_seconds"],
            "frozen_event_context",
        )
        require([b["id"] for b in row["bodies"]] == BODY_IDS, "body_inventory")
        for body in row["bodies"]:
            rat(body["gm_km3_s2"])
            vec(body["displacement_tdb_m"])
        w_replay, a_replay = replay_gravity(row["bodies"])
        xtt, v, atdb = (
            vec(row["position_tt_m"]),
            vec(row["velocity_m_s"]),
            vec(row["acceleration_tdb_m_s2"]),
        )
        x, a, w = [t / FG for t in xtt], [FB * t for t in atdb], rat(row["potential_m2_s2"])
        gravity_ok = abs(w_replay - w) <= F("1e-6") and l1(difference(a_replay, atdb)) <= F("1e-16")
        velocity_ok = l1(difference(v, vec(row["fresh_earth_velocity_m_s"]))) <= F("1e-6")
        first, last, ref_cert = validate_reference(row["reference"], x, v, w, a)
        first_cert = certificate(x, v, w, a, first)
        cfirst, clast = [
            float_vector(t)
            for t in candidate(
                row["position_tt_m"],
                row["velocity_m_s"],
                row["potential_m2_s2"],
                row["acceleration_tdb_m_s2"],
            )
        ]
        candidate_cert = certificate(x, v, w, a, [t / FB for t in clast])
        reference_tdb = [FB * t for t in last]
        first_error = l1(difference(cfirst, [FB * t for t in first]))
        last_error = l1(difference(clast, reference_tdb))
        numerical_ok = gravity_ok and velocity_ok and max(first_error, last_error) <= F("2e-8")
        scale_only = [FB * t for t in x]
        measurements = dict(
            scale_only_l1_m=l1(difference(scale_only, xtt)),
            pn_only_l1_m=l1(difference(reference_tdb, scale_only)),
            total_l1_m=l1(difference(reference_tdb, xtt)),
            frame_only_clock_change_seconds=dot(v, difference(reference_tdb, xtt)) / C**2,
            first_order_inverse_difference_l1_m=l1(difference(first, last)),
        )
        for k, val in measurements.items():
            raw_values[k].append(val)
        rows.append(
            dict(
                id=row["id"],
                numerical_checks_passed=numerical_ok,
                diagnostics={k: display(val) for k, val in measurements.items()},
                candidate_reference_l1_m=display(last_error),
                potential_replay_difference_m2_s2=display(w_replay - w),
                acceleration_replay_l1_m_s2=display(l1(difference(a_replay, atdb))),
                q=display(ref_cert["q"]),
                reference_inverse_error_upper_m=ref_cert["upper_bound_m"],
                first_order_inverse_error_upper_m=first_cert["upper_bound_m"],
                candidate_inverse_error_upper_m=candidate_cert["upper_bound_m"],
                certificate_frame="unscaled TCB-compatible displacement, L1 metres",
                bound_scope=ref_cert["bound_scope"],
                physical_spatial_bound_m=None,
                observing_eligible=False,
            )
        )
        coefficients[row["id"]] = (v, w, a)
    controls = fixture["zero_controls"]
    require(
        len(controls) == 12
        and len({r["id"] for r in controls}) == 12
        and {r["id"] for r in controls} == {r["geocentric_id"] for r in cases},
        "control_inventory",
    )
    for control in controls:
        source = old[control["source_site_id"]]
        require(control["id"] == source["geocentric_id"], "control_context")
        first, last, _ = validate_reference(
            control["reference"], [F(0)] * 3, *coefficients[control["source_site_id"]]
        )
        require(l1(first) == l1(last) == 0, "nonzero_control")
    require(
        prior["combined_counts"]
        == dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48),
        "combined_gate",
    )
    return dict(
        schema_version="1.0",
        benchmark_id="site-frame-mapping-v1",
        model_id=policy["model_id"],
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        audit_passed=all(r["numerical_checks_passed"] for r in rows),
        cases=rows,
        zero_control_count=12,
        reference_case_count=48,
        diagnostics={
            k: summarize(vals, "s" if k.endswith("seconds") else "m")
            for k, vals in raw_values.items()
        },
        certificate_scope="unique root of declared spatial polynomial for supplied decimal inputs",
        physical_spatial_bound_m=None,
        physical_site_clock_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
        combined_counts=prior["combined_counts"],
        full_clock_recomputed=False,
        source_evidence=policy["sources"],
        qualification_outcome="physical_evidence_incomplete",
        unresolved_components=[
            "geocentric_time_ephemeris",
            "earth_velocity",
            "station_coordinates",
            "earth_orientation",
            "spatial_higher_order_terms",
            "omitted_gravity_and_force_terms",
            "spacetime_coupling",
        ],
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Site-frame audit must be offline")


def evaluate():
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = evaluate_inputs(*load_inputs())
    result.update(
        manifest_sha256=sha(MANIFEST),
        policy_sha256=sha(POLICY),
        fixture_sha256=sha(FIXTURE),
        python_version=platform.python_version(),
        numpy_version=importlib.metadata.version("numpy"),
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result.update(
        implementation_commit=os.getenv("ASTROSCOPE_IMPLEMENTATION_COMMIT", head),
        checkout_commit=os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", head),
        working_tree_dirty=bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({k: result[k] for k in ("audit_passed", "diagnostics", "qualification_outcome")})
    )
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
