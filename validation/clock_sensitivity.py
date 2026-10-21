"""Offline local clock sensitivities; no inferred physical uncertainty or eligibility."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import socket
import subprocess
from decimal import Context, localcontext
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import numpy as np

from validation.time_ephemeris import TimeEphemerisError, require, sha

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/clock_sensitivity_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/clock_sensitivity_v1.json"
EVIDENCE = ROOT / "docs/research/evidence/clock_sensitivity_evidence_v1.json"
MANIFEST = ROOT / "validation/manifests/clock_sensitivity_v1.json"
EXPECTED_MANIFEST_SHA256 = "19a99e72f5d4ace6031b0bad206b6c1eb76d74245258ff70a157a24054d833ed"
BODY_IDS = [10, 1, 2, 4, 5, 6, 7, 8, 9, 301]
IDS = [
    f"2024-{date}_{hour}"
    for date in ("03-20", "06-21", "09-22", "12-21")
    for hour in ("10", "12", "14")
]
COMPONENTS = [
    "geocentric_time_ephemeris",
    "earth_state",
    "station_coordinates",
    "earth_orientation",
    "omitted_physics_and_coefficient_model",
    "higher_order_remainder",
]
BOUND_KEYS = (
    "physical_geocentric_clock_bound_seconds",
    "physical_site_clock_bound_seconds",
    "physical_arrival_bound_seconds",
)
COUNTS = dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48)
LIMITS = dict(
    partial_absolute="1e-45",
    partial_relative="5e-13",
    rate_seconds_per_second="1e-22",
    mapping_absolute="1e-60",
    covariance_absolute="1e-60",
    minimum_mapping_denominator="0.5",
)
AVAILABILITY = dict(
    nominal_states_and_gm="archived",
    nominal_clock_derivatives="archived",
    complete_fitted_covariance="not_established",
    cross_epoch_state_covariance="not_established",
    parameter_trajectory_jacobian="not_established",
    model_discrepancy_bound="not_established",
    nonlinear_remainder_bound="not_established",
)


def number(value):
    # Unlike the earlier clock-only parser, this accepts outer-planet metres
    # and SI gravitational parameters. This is an input/resource domain guard,
    # not an uncertainty or comparison tolerance.
    require(
        isinstance(value, str)
        and len(value) <= 160
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value),
        "finite_decimal_string_required",
    )
    result = D(value)
    require(abs(result) <= D("1e30"), "numeric_domain")
    return result


def load_inputs():
    try:
        require(sha(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest_checksum")
        for path, digest in json.loads(MANIFEST.read_text())["files"].items():
            require(sha(ROOT / path) == digest, "input_checksum")
        return [
            json.loads(p.read_text())
            for p in (
                POLICY,
                FIXTURE,
                EVIDENCE,
                ROOT / "validation/fixtures/coupled_clock_v1.json",
                ROOT / "validation/fixtures/time_ephemeris_v1.json",
                ROOT / "validation/fixtures/cross_model_time_v1.json",
                ROOT / "validation/results/cross_model_time_reference_run.json",
            )
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise TimeEphemerisError("input_unavailable_or_invalid") from exc


def state_vector(state):
    """SI vector: v[3], then each body's d[3], mu[1]."""
    require([b["id"] for b in state["bodies"]] == BODY_IDS, "body_inventory")
    require(len(state["earth_velocity_m_s"]) == 3, "vector_shape")
    values = list(map(number, state["earth_velocity_m_s"]))
    for body in state["bodies"]:
        require(len(body["displacement_tdb_m"]) == 3, "vector_shape")
        d = list(map(number, body["displacement_tdb_m"]))
        mu = number(body["gm_km3_s2"]) * 10**9
        require(any(d) and mu > 0, "state_domain")
        values.extend([*d, mu])
    vector = np.array(values, dtype=float)
    require(np.isfinite(vector).all(), "state_nonfinite")
    return vector


def scalar_rate(vector):
    """Analytic complex extension: deliberately no conjugate or absolute values."""
    v = vector[:3]
    bodies = vector[3:].reshape(10, 4)
    radii = np.sqrt(np.sum(bodies[:, :3] ** 2, axis=1))
    energy = np.sum(v * v) / 2 + np.sum(bodies[:, 3] / radii)
    return (1 + 1.550519768e-8 - 6.969290134e-10) * (
        1.550519768e-8 - energy / 299792458**2
    ) - 6.969290134e-10


def rate_gradients(vector):
    a_over_c2 = (1 + 1.550519768e-8 - 6.969290134e-10) / 299792458**2
    bodies = vector[3:].reshape(10, 4)
    radii = np.linalg.norm(bodies[:, :3], axis=1)
    gradient = np.empty(43)
    gradient[:3] = -a_over_c2 * vector[:3]
    tail = gradient[3:].reshape(10, 4)
    tail[:, :3] = a_over_c2 * bodies[:, 3, None] * bodies[:, :3] / radii[:, None] ** 3
    tail[:, 3] = -a_over_c2 / radii
    steps = np.ones(43)
    steps[:3] = 1e-3
    steps[6::4] = vector[6::4] * 1e-12
    complex_gradient = []
    for i, step in enumerate(steps):
        trial = vector.astype(complex)
        trial[i] += 1j * step
        complex_gradient.append(scalar_rate(trial).imag / step)
    return float(scalar_rate(vector)), gradient, np.array(complex_gradient)


def mapping_gains(derivative):
    with localcontext(Context(prec=70)):
        f = number(derivative)
        require(1 + f > D("0.5"), "mapping_denominator")
        inverse = 1 / (1 + f)
        return dict(
            delta_per_clock_perturbation=-inverse, delta_per_tt=-f * inverse, tdb_per_tt=inverse
        )


def covariance_psd(matrix):
    """Exact rational Schur complements; no clipping of negative eigenvalues.

    A zero pivot of a PSD matrix must have a zero residual row. This accepts
    singular PSD covariance while rejecting indefinite zero-pivot matrices.
    """
    residual = [[Fraction(x) for x in row] for row in matrix]
    for i in range(len(residual)):
        pivot = residual[i][i]
        require(pivot >= 0, "covariance_not_psd")
        if pivot == 0:
            require(
                all(residual[i][k] == 0 for k in range(i + 1, len(residual))), "covariance_not_psd"
            )
        else:
            for j in range(i + 1, len(residual)):
                for k in range(j, len(residual)):
                    residual[j][k] -= residual[j][i] * residual[i][k] / pivot
                    residual[k][j] = residual[j][k]


def propagate(jacobian, covariance, box_bounds):
    with localcontext(Context(prec=70)):
        require(isinstance(jacobian, list) and len(jacobian) > 0, "jacobian_shape")
        j = list(map(number, jacobian))
        n = len(j)
        variance, box = None, None
        if covariance is not None:
            require(
                isinstance(covariance, list)
                and len(covariance) == n
                and all(isinstance(row, list) and len(row) == n for row in covariance),
                "covariance_shape",
            )
            matrix = [[None if x is None else number(x) for x in row] for row in covariance]
            require(
                all(matrix[i][k] == matrix[k][i] for i in range(n) for k in range(n)),
                "covariance_asymmetric",
            )
            require(
                all(matrix[i][i] is None or matrix[i][i] >= 0 for i in range(n)),
                "covariance_negative_diagonal",
            )
            if all(x is not None for row in matrix for x in row):
                covariance_psd(matrix)
                variance = sum(j[i] * matrix[i][k] * j[k] for i in range(n) for k in range(n))
                require(variance >= 0, "propagation_negative_variance")
        if box_bounds is not None:
            require(isinstance(box_bounds, list) and len(box_bounds) == n, "box_shape")
            bounds = list(map(number, box_bounds))
            require(all(b >= 0 for b in bounds), "box_negative")
            box = sum(abs(x) * b for x, b in zip(j, bounds, strict=True))
        return variance, box


def evaluate_inputs(
    policy, fixture, evidence, states, de, inpop, previous, candidate=rate_gradients
):
    with localcontext(Context(prec=70)):
        return _evaluate(policy, fixture, evidence, states, de, inpop, previous, candidate)


def _evaluate(policy, fixture, evidence, states, de, inpop, previous, candidate):
    require(
        policy["model_id"] == fixture["model_id"] == "geocentric-clock-sensitivity-v1",
        "model_identity",
    )
    require(policy["limits"] == LIMITS, "frozen_tolerances")
    require(
        policy["constants"] == dict(c_m_s="299792458", LB="1.550519768e-8", LG="6.969290134e-10"),
        "constants",
    )
    require(
        policy["complex_steps"]
        == dict(velocity_m_s="1e-3", displacement_m="1", gm_relative="1e-12"),
        "frozen_steps",
    )
    require(
        policy["body_ids"] == BODY_IDS
        and policy["state_count"] == 12
        and policy["partials_per_state"] == 43
        and policy["mapping_count"] == 28,
        "sample_design",
    )
    require(
        fixture["policy_sha256"] == sha(POLICY)
        and fixture["generator_sha256"]
        == sha(ROOT / "validation/reference_generation/clock_sensitivity.py"),
        "fixture_provenance",
    )
    require(fixture["independent_physical_reference"] is False, "independence_claim")
    require(
        policy["selected_arrival_convention_id"]
        == previous["selected_arrival_convention_id"]
        == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    for record in (policy, evidence, previous):
        require(all(record[k] is None for k in BOUND_KEYS), "unsupported_physical_bound")
        require(record["observing_eligible"] is False, "unsupported_eligibility")
        require(record["unresolved_components"] == COMPONENTS, "uncertainty_components")
    require(
        previous["audit_passed"] is True
        and previous["combined_counts"] == COUNTS
        and previous["site_clocks_unqualified"] == 48,
        "prior_gate",
    )
    require(
        {r["id"]: r["status"] for r in evidence["inputs"]} == AVAILABILITY
        and len(evidence["inputs"]) == len(AVAILABILITY),
        "evidence_inventory",
    )
    require(len(evidence["sources"]) == 5, "source_inventory")
    for source in evidence["sources"]:
        require(
            source["url"].startswith("https://")
            and source["location"]
            and source["finding"]
            and source["limitation"],
            "source_provenance",
        )
    require(
        [c["id"] for c in states["geocentric_controls"]]
        == IDS
        == [c["id"] for c in fixture["rates"]],
        "state_inventory",
    )
    partial_ids = [f"v_{i}" for i in range(3)]
    for body in BODY_IDS:
        partial_ids.extend([*(f"d_{body}_{i}" for i in range(3)), f"mu_{body}"])
    rates = []
    for case, ref in zip(states["geocentric_controls"], fixture["rates"], strict=True):
        require(case["site"] is None and case["solution"]["converged"] is True, "geocentric_state")
        et = case["solution"]["trace"][-1]["et_seconds"]
        matches = [s for s in case["states"] if s["et_seconds"] == et]
        require(len(matches) == 1 and ref["et_seconds"] == et, "state_argument")
        require([p["id"] for p in ref["partials"]] == partial_ids, "partial_inventory")
        rate, analytic, complex_step = candidate(state_vector(matches[0]))
        require(np.shape(analytic) == np.shape(complex_step) == (43,), "partial_shape")
        require(
            np.isfinite(rate) and np.isfinite(analytic).all() and np.isfinite(complex_step).all(),
            "candidate_nonfinite",
        )
        rate_error = D.from_float(float(rate)) - number(ref["rate_seconds_per_second"])
        partials = []
        for expected, x, y in zip(ref["partials"], analytic, complex_step, strict=True):
            reference = number(expected["value"])
            tolerance = D("1e-45") + D("5e-13") * abs(reference)
            errors = [D.from_float(float(value)) - reference for value in (x, y)]
            partials.append(
                dict(
                    id=expected["id"],
                    reference=str(reference),
                    analytic_minus_reference=str(errors[0]),
                    complex_step_minus_reference=str(errors[1]),
                    tolerance=str(tolerance),
                    passed=all(abs(e) <= tolerance for e in errors),
                )
            )
        rates.append(
            dict(
                id=case["id"],
                et_seconds=et,
                rate_seconds_per_second=str(rate),
                rate_minus_reference=str(rate_error),
                partials=partials,
                passed=abs(rate_error) <= D("1e-22") and all(p["passed"] for p in partials),
            )
        )
    mappings = []
    require(len(fixture["mappings"]) == 28, "mapping_inventory")
    for model_index, (model, archive) in enumerate((("DE440t", de), ("INPOP21a", inpop))):
        require(
            [r["id"] for r in archive["cases"]] == [*IDS, "j2000_tt", "iau_epoch_tt"],
            "mapping_inventory",
        )
        for i, case in enumerate(archive["cases"]):
            ref = fixture["mappings"][model_index * 14 + i]
            derivative = case["cspice"]["trace"][-1]["derivative_seconds_per_second"]
            require(
                ref["id"] == f"{model}:{case['id']}"
                and ref["derivative_seconds_per_second"] == derivative,
                "mapping_context",
            )
            gains = mapping_gains(derivative)
            errors = {key: value - number(ref[key]) for key, value in gains.items()}
            mappings.append(
                dict(
                    id=ref["id"],
                    derivative_seconds_per_second=derivative,
                    gains={k: str(v) for k, v in gains.items()},
                    candidate_minus_reference={k: str(v) for k, v in errors.items()},
                    passed=all(abs(e) <= D("1e-60") for e in errors.values()),
                )
            )
    control_ids = [
        "independent",
        "positive_correlation",
        "negative_correlation",
        "perfect_cancellation",
        "constant_rate_two_intervals",
        "anchor_rate_correlation",
        "zero_variance",
        "unknown_covariance",
        "unknown_cross_covariance",
    ]
    require(
        [c["id"] for c in policy["controls"]]
        == control_ids
        == [c["id"] for c in fixture["controls"]],
        "control_inventory",
    )
    controls = []
    for case, ref in zip(policy["controls"], fixture["controls"], strict=True):
        variance, box = propagate(case["jacobian"], case["covariance"], case["box_bounds"])
        values = dict(
            linearized_variance_seconds_squared=variance, linearized_box_bound_seconds=box
        )
        checks = [
            ref[k] is None
            if v is None
            else ref[k] is not None and abs(v - number(ref[k])) <= D("1e-60")
            for k, v in values.items()
        ]
        controls.append(
            dict(
                id=case["id"],
                **{k: None if v is None else str(v) for k, v in values.items()},
                covariance_status="unknown" if variance is None else "synthetic_known",
                passed=all(checks),
            )
        )
    passed = all(row["passed"] for row in [*rates, *mappings, *controls])
    diagnostics = dict(
        max_absolute_rate_error_seconds_per_second=str(
            max(abs(D(row["rate_minus_reference"])) for row in rates)
        ),
        max_partial_error_fraction_of_tolerance=str(
            max(
                abs(D(p[key])) / D(p["tolerance"])
                for row in rates
                for p in row["partials"]
                for key in ("analytic_minus_reference", "complex_step_minus_reference")
            )
        ),
        max_absolute_mapping_error=str(
            max(abs(D(x)) for row in mappings for x in row["candidate_minus_reference"].values())
        ),
    )
    return dict(
        schema_version="1.0",
        benchmark_id="geocentric-clock-sensitivity-v1",
        audit_passed=passed,
        qualification=("supplied_input_local_algebra_only" if passed else "numerical_audit_failed"),
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        counts=dict(
            states=12,
            partials=516,
            partial_implementation_checks=1032,
            mappings=28,
            synthetic_controls=9,
            known_covariances=7,
            unknown_covariances=2,
        ),
        rates=rates,
        mappings=mappings,
        controls=controls,
        diagnostics=diagnostics,
        evidence_availability=AVAILABILITY.copy(),
        physical_covariance_propagated=False,
        physical_linearization_domain_established=False,
        full_reference_status="unqualified",
        site_clocks_unqualified=48,
        combined_counts=COUNTS.copy(),
        unresolved_components=COMPONENTS.copy(),
        **{k: None for k in BOUND_KEYS},
        observing_eligible=False,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Sensitivity audit must be offline")


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
        candidate_packages={
            n: importlib.metadata.version(n) for n in ("astropy", "pyerfa", "numpy")
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["implementation_commit"] = os.getenv("ASTROSCOPE_IMPLEMENTATION_COMMIT", head)
    result["checkout_commit"] = os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", head)
    result["working_tree_dirty"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("audit_passed", "counts", "combined_counts")}))
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
