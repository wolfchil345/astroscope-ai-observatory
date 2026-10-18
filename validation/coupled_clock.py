"""Offline audit of the declared coupled spatial and local time polynomial."""

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
from decimal import Context, localcontext
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/coupled_clock_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/coupled_clock_v1.json"
MANIFEST = ROOT / "validation/manifests/coupled_clock_v1.json"
EXPECTED_MANIFEST_SHA256 = "f206e6b26ac7133300cb98ab3f0025e4d822001affa7670d4c9c0d85557eb6cb"
MODEL = "de440t-iau2000-coupled-tenbody-c4-local-v1"
BODY_IDS = [10, 1, 2, 4, 5, 6, 7, 8, 9, 301]
FB, FG, C = 1 - 1.550519768e-8, 1 - 6.969290134e-10, 299792458.0
BUDGET = [
    "geocentric_time_ephemeris",
    "earth_state",
    "station_coordinates",
    "earth_orientation",
    "omitted_physics_and_coefficient_model",
    "higher_order_remainder",
]
DESIGN = dict(
    historical_sites=48,
    geocentric_controls=12,
    max_iterations=8,
    spatial_updates=4,
    solver_residual_seconds="1e-18",
    candidate_reference_seconds="2e-18",
    component_arithmetic_seconds="2e-18",
    spatial_replay_l1_m="2e-8",
    coefficient_relative_tolerance="5e-14",
    coefficient_absolute_tolerance="1e-25",
    reader_clock_seconds="1e-12",
    reader_velocity_l1_m_s="1e-6",
    historical_clock_replay_seconds="1e-12",
    argument_quantization_seconds="1e-7",
    max_abs_delta_seconds="0.01",
    reference_decimal_precision=90,
    engineering_limits_only=True,
)
GATE = dict(
    numerical_coupling_scope="declared_quantized_model_only",
    physical_site_clock_bound_seconds=None,
    physical_arrival_bound_seconds=None,
    observing_eligible=False,
    combined_executed=0,
    combined_blocked=288,
)


class CoupledClockError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise CoupledClockError(reason)


def number(value):
    require(
        isinstance(value, str)
        and len(value) <= 256
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value),
        "finite_decimal_string_required",
    )
    result = D(value)
    require(abs(result) <= D("1e24"), "numeric_domain")
    return result


def vector(values, dtype=float):
    require(isinstance(values, list) and len(values) == 3, "vector_shape")
    return np.array([str(number(v)) for v in values], dtype=dtype)


def serial(value):
    require(math.isfinite(float(value)), "nonfinite_candidate")
    return format(float(value), ".17g")


def coefficients(state):
    """Independent array implementation from archived positions and velocities."""
    # Small B_ij entries subtract much larger contributions. Retain guard bits
    # from the supplied decimals through this coefficient calculation, then
    # round once to binary64 for the spatial map and clock solver.
    require(np.finfo(np.longdouble).nmant >= 63, "extended_precision_unavailable")
    fb = np.longdouble(1) - np.longdouble("1.550519768e-8")
    require([b["id"] for b in state["bodies"]] == BODY_IDS, "body_inventory")
    v = vector(state["earth_velocity_m_s"], np.longdouble)
    d = np.array([vector(b["displacement_tdb_m"], np.longdouble) for b in state["bodies"]])
    vb = np.array([vector(b["barycentric_velocity_m_s"], np.longdouble) for b in state["bodies"]])
    mu = (
        np.array([str(number(b["gm_km3_s2"])) for b in state["bodies"]], dtype=np.longdouble)
        * 10**9
    )
    radii = np.linalg.norm(d, axis=1)
    require(np.all(radii > 0) and np.all(mu > 0), "gravity_domain")
    require(np.abs(v).sum() <= 70000, "velocity_domain")
    u = vb - v
    du = np.einsum("ij,ij->i", d, u)
    weights = mu / radii**3
    w = np.sum(mu / radii)
    a = fb * (weights @ d)
    vw = (mu / radii) @ vb
    grad = fb * np.einsum("k,ki,kj->ij", weights, vb, d)
    wdot = -fb * np.dot(weights, du)
    jerk = fb**2 * np.sum(weights[:, None] * (u - 3 * d * (du / radii**2)[:, None]), axis=0)
    require(0 <= w <= 2e9 and np.abs(a).sum() <= 0.03, "coefficient_domain")
    b = -(np.dot(v, v) / 2 + 3 * w) * v + 4 * vw
    matrix = 2 * grad - np.outer(v, a) + np.eye(3) * wdot / 2
    values = dict(
        potential=w,
        acceleration=a,
        vector_potential=vw,
        gradient_vector_potential=grad,
        potential_total_derivative=wdot,
        jerk=jerk,
        B_vector=b,
        B_matrix=matrix,
    )
    return {
        k: float(v) if np.isscalar(v) else np.asarray(v, dtype=float) for k, v in values.items()
    }


def spatial_inverse(position_tt, velocity, coeff):
    x = np.asarray(position_tt, dtype=float) / FG
    require(np.isfinite(x).all() and np.abs(x).sum() < 13000000, "position_domain")
    v, a, w = velocity, coeff["acceleration"], coeff["potential"]
    matrix = np.outer(v, v) / 2 + np.eye(3) * w
    r, trace = x.copy(), []
    for _ in range(4):
        r = x - (matrix @ r + r * (a @ r) - a * (r @ r) / 2) / C**2
        trace.append(r.copy())
    return r, trace


def time_terms(r, v, coeff):
    return dict(
        leading=FG * (v @ r) / C**2,
        linear_c4=-FG * (coeff["B_vector"] @ r) / C**4,
        quadratic_c4=-FG * (r @ coeff["B_matrix"] @ r) / C**4,
        cubic_c4=FG * (r @ r) * (coeff["jerk"] @ r) / (10 * C**4),
    )


def local_mapping(state):
    coeff = coefficients(state)
    v = vector(state["earth_velocity_m_s"])
    r, trace = spatial_inverse(vector(state["position_tt_m"]), v, coeff)
    terms = time_terms(r, v, coeff)
    return dict(
        coefficients=coeff,
        spatial_trace_tcb_m=trace,
        displacement_tdb_m=FB * r,
        terms_seconds=terms,
        site_shift_seconds=sum(terms.values()),
    )


def solve(tt_seconds, reader, mapper=local_mapping, max_iterations=8, tolerance=1e-18):
    """Solve the declared quantized-oracle equation; no continuous-root claim."""
    require(isinstance(max_iterations, int) and 1 <= max_iterations <= 8, "iteration_domain")
    require(math.isfinite(tolerance) and 0 < tolerance <= 1e-18, "tolerance_domain")
    tt = number(tt_seconds)
    delta, trace, converged = 0.0, [], False
    with localcontext(Context(prec=90)):
        for _ in range(max_iterations):
            require(math.isfinite(delta) and abs(delta) <= 0.01, "delta_domain")
            requested = tt + D.from_float(delta)
            et = float(requested)
            key = str(D.from_float(et))
            state = reader(key)
            require(state["et_seconds"] == key, "state_epoch_mismatch")
            d = float(number(state["clock_tt_minus_tdb_seconds"]))
            shift = float(mapper(state)["site_shift_seconds"])
            require(math.isfinite(shift), "nonfinite_candidate")
            residual, following = delta + d - shift, shift - d
            trace.append(
                dict(
                    delta_seconds=serial(delta),
                    et_seconds=key,
                    argument_error_seconds=str(D.from_float(et) - requested),
                    residual_seconds=serial(residual),
                    next_delta_seconds=serial(following),
                )
            )
            if abs(residual) <= tolerance:
                converged = True
                break
            delta = following
    return dict(converged=converged, delta_seconds=serial(delta), trace=trace)


def frozen_reader(states):
    index = {s["et_seconds"]: s for s in states}
    require(len(index) == len(states) and 1 <= len(states) <= 8, "state_inventory")

    def read(key):
        require(key in index, "missing_state_no_interpolation")
        return index[key]

    return read


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
            ROOT / "validation/fixtures/time_ephemeris_v1.json",
            ROOT / "validation/fixtures/site_frame_v1.json",
        )
    ]


def validate_reference_solution(row):
    solution, reader = row["solution"], frozen_reader(row["states"])
    trace = solution["trace"]
    require(1 <= len(trace) <= 8, "trace_inventory")
    previous = D(0)
    used = set()
    for i, step in enumerate(trace):
        delta = number(step["delta_seconds"])
        require(delta == previous and abs(delta) <= D(".01"), "trace_continuity")
        requested = number(row["tt_seconds_from_j2000"]) + delta
        key = str(D.from_float(float(requested)))
        require(step["et_seconds"] == key, "trace_epoch")
        quant = D(key) - requested
        require(
            abs(quant - number(step["argument_error_seconds"])) < D("1e-75")
            and abs(quant) <= D("1e-7"),
            "argument_quantization",
        )
        state = reader(key)
        used.add(key)
        shift = number(state["reference"]["site_shift_seconds"])
        residual = delta + number(state["clock_tt_minus_tdb_seconds"]) - shift
        following = shift - number(state["clock_tt_minus_tdb_seconds"])
        require(
            abs(residual - number(step["residual_seconds"])) <= D("1e-75")
            and abs(following - number(step["next_delta_seconds"])) <= D("1e-75"),
            "reference_clock_algebra",
        )
        if i < len(trace) - 1:
            require(abs(residual) > D("1e-18"), "reference_ignored_convergence")
        previous = following
    require(used == {s["et_seconds"] for s in row["states"]}, "unused_state")
    require(
        number(solution["delta_seconds"]) == number(trace[-1]["delta_seconds"])
        or not solution["converged"],
        "solution_trace",
    )
    require(solution["converged"] == (abs(residual) <= D("1e-18")), "false_convergence")
    return reader


def flatten(value):
    if isinstance(value, list):
        return [v for x in value for v in flatten(x)]
    return [number(value)]


def audit_state(state, gm_values):
    key = state["et_seconds"]
    require(key == str(D.from_float(float(number(key)))), "noncanonical_epoch")
    require([b["id"] for b in state["bodies"]] == BODY_IDS, "body_inventory")
    require(all(b["gm_km3_s2"] == gm_values[b["id"]] for b in state["bodies"]), "gm_provenance")
    candidate = local_mapping(state)
    reference = state["reference"]
    checks = []
    for name, value in candidate["coefficients"].items():
        expected = flatten(reference["coefficients"][name])
        actual = np.asarray(value).ravel()
        require(len(expected) == len(actual), "coefficient_shape")
        checks.append(
            all(
                abs(D.from_float(float(a)) - b) <= abs(b) * D("5e-14") + D("1e-25")
                for a, b in zip(actual, expected, strict=True)
            )
        )
    require(len(reference["spatial_trace_tcb_m"]) == 4, "spatial_trace_inventory")
    for actual, expected in zip(
        candidate["spatial_trace_tcb_m"], reference["spatial_trace_tcb_m"], strict=True
    ):
        checks.append(
            sum(
                abs(D.from_float(float(a)) - number(b))
                for a, b in zip(actual, expected, strict=True)
            )
            <= D("2e-8")
        )
    checks.append(
        sum(
            abs(D.from_float(float(a)) - number(b))
            for a, b in zip(
                candidate["displacement_tdb_m"], reference["displacement_tdb_m"], strict=True
            )
        )
        <= D("2e-8")
    )
    require(
        set(reference["terms_seconds"]) == set(candidate["terms_seconds"]), "time_term_inventory"
    )
    checks.extend(
        abs(D.from_float(float(candidate["terms_seconds"][k])) - number(value)) <= D("2e-18")
        for k, value in reference["terms_seconds"].items()
    )
    require(
        abs(
            sum(map(number, reference["terms_seconds"].values()))
            - number(reference["site_shift_seconds"])
        )
        <= D("1e-75"),
        "reference_term_sum",
    )
    r = state["reader_check"]
    clock_diff = number(r["clock_seconds"]) - number(state["clock_tt_minus_tdb_seconds"])
    velocity_diff = sum(
        abs(number(a) - number(b))
        for a, b in zip(r["velocity_m_s"], state["earth_velocity_m_s"], strict=True)
    )
    jd1, jd2 = map(number, r["jd_parts"])
    error = (jd1 - 2451545 + jd2) * 86400 - number(key)
    require(
        abs(error - number(r["argument_error_seconds"])) <= D("1e-75") and abs(error) <= D("1e-7"),
        "reader_epoch",
    )
    checks.extend((abs(clock_diff) <= D("1e-12"), velocity_diff <= D("1e-6")))
    return all(checks)


def summarize(values):
    return dict(
        count=len(values),
        minimum_seconds=str(min(values)),
        maximum_seconds=str(max(values)),
        maximum_absolute_seconds=str(max(map(abs, values))),
        interpretation="model_or_numerical_diagnostic_not_physical_error_bound",
    )


def evaluate_inputs(
    policy, fixture, historical, prior, geocentres, frames, candidates, mapper=local_mapping
):
    with localcontext(Context(prec=90)):
        return _evaluate(policy, fixture, historical, prior, geocentres, frames, candidates, mapper)


def _evaluate(policy, fixture, historical, prior, geocentres, frames, candidates, mapper):
    require(policy["model_id"] == fixture["model_id"] == MODEL, "model_identity")
    require(policy["selected_arrival_convention_id"] == "astroscope-tdb-solar-au-v1", "convention")
    require(
        policy["constants"] == dict(c_m_s="299792458", L_B="1.550519768e-8", L_G="6.969290134e-10"),
        "scale_constants",
    )
    require(policy["design"] == DESIGN and policy["body_ids"] == BODY_IDS, "frozen_design")
    require(
        policy["gate"] == GATE and policy["unresolved_components"] == BUDGET, "qualification_gate"
    )
    require(
        [s["id"] for s in policy["sources"]]
        == ["iau2000_b13", "klioner_scaling", "park2021", "iau2000_b15"]
        and all(s["physical_bound_seconds"] is None for s in policy["sources"]),
        "source_claim",
    )
    require(
        fixture["forbidden_imports"] == []
        and fixture["cspice_toolkit"] == "CSPICE_N0067"
        and fixture["packages"] == policy["reference_packages"]
        and fixture["kernel_sha256"] == policy["kernel"]["sha256"]
        and fixture["gm_sha256"] == policy["gm"]["sha256"],
        "reference_provenance",
    )
    require(
        fixture["approximate_skyfield_clock"] == "disabled_with_raising_patch"
        and fixture["frame"] == "TT-compatible nominal station; TCB-compatible local polynomial"
        and fixture["coefficient_model"]
        == "ten Newtonian monopoles; Q=0; total potential derivative",
        "reference_contract",
    )
    require(
        fixture["physical_site_clock_bound_seconds"] is None
        and fixture["observing_eligible"] is False,
        "unsupported_qualification",
    )
    old = {r["id"]: r for r in historical["cases"]}
    old_results = {r["id"]: r for r in prior["cases"]}
    rows = fixture["cases"]
    controls = fixture["geocentric_controls"]
    require(
        len(rows) == 48
        and len({r["id"] for r in rows}) == 48
        and {r["id"] for r in rows} == set(old) == set(candidates),
        "case_inventory",
    )
    require(
        len(controls) == 12
        and len({r["id"] for r in controls}) == 12
        and {r["id"] for r in controls} == {r["geocentric_id"] for r in rows},
        "control_inventory",
    )
    geo = {r["id"]: r for r in geocentres["cases"][:12]}
    gm_values = {b["id"]: b["gm_km3_s2"] for b in frames["cases"][0]["bodies"]}
    output, control_output = [], []
    diagnostics = {
        k: []
        for k in (
            "candidate_minus_coupled",
            "coupled_minus_mission43",
            "local_c4",
            "linear_c4",
            "quadratic_c4",
            "cubic_c4",
            "candidate_reference",
            "argument_quantization",
        )
    }
    for row in rows + controls:
        control = row["site"] is None
        source = geo[row["id"]] if control else old[row["id"]]
        require(
            row["utc"] == source["utc"]
            and row["tt_seconds_from_j2000"] == source["tt_seconds_from_j2000"],
            "frozen_epoch",
        )
        if control:
            require(row["geocentric_id"] == row["id"], "control_context")
        else:
            require(
                row["site"] == source["site"] and row["geocentric_id"] == source["geocentric_id"],
                "frozen_site",
            )
        reader = validate_reference_solution(row)
        state_checks = [audit_state(s, gm_values) for s in row["states"]]
        reference_delta = number(row["solution"]["delta_seconds"])
        result = dict(
            id=row["id"],
            numerical_checks_passed=False,
            reference_delta_seconds=str(reference_delta),
            observing_eligible=False,
        )
        try:
            solved = solve(row["tt_seconds_from_j2000"], reader, mapper)
            error = number(solved["delta_seconds"]) - reference_delta
            ok = (
                all(state_checks)
                and row["solution"]["converged"]
                and solved["converged"]
                and abs(error) <= D("2e-18")
            )
            result.update(
                candidate_solution=solved,
                numerical_checks_passed=ok,
                candidate_reference_seconds=str(error),
            )
        except CoupledClockError as exc:
            result.update(candidate_failure=str(exc))
        final = reader(row["solution"]["trace"][-1]["et_seconds"])
        terms = {k: number(v) for k, v in final["reference"]["terms_seconds"].items()}
        result["local_terms_seconds"] = {k: str(v) for k, v in terms.items()}
        if control:
            require(
                all(number(t) == 0 for s in row["states"] for t in s["position_tt_m"])
                and all(v == 0 for v in terms.values()),
                "nonzero_geocentre",
            )
            reproduction = reference_delta - number(source["cspice"]["delta_seconds"])
            result["geocentre_reproduction_seconds"] = str(reproduction)
            result["numerical_checks_passed"] &= abs(reproduction) <= D("1e-12")
            control_output.append(result)
        else:
            legacy = number(old_results[row["id"]]["surrogate_clock_seconds"])
            live = number(candidates[row["id"]]["site"])
            historical_live = legacy + number(
                old_results[row["id"]]["candidate_minus_surrogate_seconds"]
            )
            reproduction = live - historical_live
            result["numerical_checks_passed"] &= abs(reproduction) <= D("1e-12")
            result.update(
                candidate_archival_replay_seconds=str(reproduction),
                live_astropy_minus_reference_seconds=str(live - reference_delta),
                coupled_minus_mission43_seconds=str(reference_delta - legacy),
            )
            output.append(result)
            diagnostics["candidate_minus_coupled"].append(live - reference_delta)
            diagnostics["coupled_minus_mission43"].append(reference_delta - legacy)
            diagnostics["local_c4"].append(sum(v for k, v in terms.items() if k != "leading"))
            for key in ("linear_c4", "quadratic_c4", "cubic_c4"):
                diagnostics[key].append(terms[key])
            if "candidate_reference_seconds" in result:
                diagnostics["candidate_reference"].append(
                    number(result["candidate_reference_seconds"])
                )
            diagnostics["argument_quantization"].extend(
                number(t["argument_error_seconds"]) for t in row["solution"]["trace"]
            )
    require(
        prior["combined_counts"]
        == dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48),
        "combined_gate",
    )
    return dict(
        schema_version="1.0",
        benchmark_id="coupled-site-clock-v1",
        model_id=MODEL,
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        audit_passed=all(r["numerical_checks_passed"] for r in output + control_output),
        cases=output,
        geocentric_controls=control_output,
        diagnostics={k: summarize(v) if v else None for k, v in diagnostics.items()},
        coupling_scope="declared_quantized_model_only",
        continuous_clock_root_bound_seconds=None,
        physical_site_clock_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
        qualification_outcome="physical_evidence_incomplete",
        unresolved_components=BUDGET,
        source_evidence=policy["sources"],
        combined_counts=prior["combined_counts"],
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Coupled-clock audit must be offline")


def evaluate():
    from validation.site_clock import live_candidate

    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        inputs = load_inputs()
        historical = json.loads(
            (ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text()
        )
        result = evaluate_inputs(*inputs, live_candidate(historical))
    result.update(
        manifest_sha256=sha(MANIFEST),
        policy_sha256=sha(POLICY),
        fixture_sha256=sha(FIXTURE),
        python_version=platform.python_version(),
        coefficient_guard_mantissa_bits=np.finfo(np.longdouble).nmant + 1,
        candidate_packages={
            n: importlib.metadata.version(n) for n in ("numpy", "astropy", "pyerfa")
        },
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
