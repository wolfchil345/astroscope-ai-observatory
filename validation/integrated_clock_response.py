"""Manufactured integrated clock responses, never physical ephemeris qualification."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import socket
import subprocess
from decimal import Context, localcontext
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from validation.clock_sensitivity import BOUND_KEYS, COMPONENTS, COUNTS, number, propagate
from validation.time_ephemeris import TimeEphemerisError, require, sha

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/integrated_clock_response_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/integrated_clock_response_v1.json"
EVIDENCE = ROOT / "docs/research/evidence/integrated_clock_response_evidence_v1.json"
MANIFEST = ROOT / "validation/manifests/integrated_clock_response_v1.json"
PRIOR = ROOT / "validation/results/ephemeris_covariance_reference_run.json"
EXPECTED_MANIFEST_SHA256 = "650ecae469f622fc208b65a6e085592e126808e0a863fa3590384122286d34ab"
FAMILIES = ("constant_acceleration", "forced_oscillator")
IDS = [
    f"{family}:{label}"
    for family in FAMILIES
    for label in ("zero", "forward", "backward", "shifted_anchor")
]
GRIDS = [16, 32, 64, 128]
MODES = ["correlated", "fixed", "unknown_cross"]
LAMBDA, BETA, OMEGA2 = D("0.002"), D("0.003"), D("0.25")
LIMITS = dict(
    state_absolute="1e-7",
    clock_absolute="1e-9",
    state_sensitivity_absolute="1e-7",
    clock_sensitivity_absolute="1e-8",
    implicit_argument_absolute="1e-8",
    implicit_sensitivity_absolute="1e-8",
    variance_absolute="1e-10",
    equation_residual_seconds="1e-35",
    minimum_denominator="0.5",
    oscillator_refinement_ratio_min="8",
    oscillator_refinement_ratio_max="32",
    polynomial_roundoff_absolute="1e-45",
)


def decimal_text(value):
    return "0" if value == 0 else str(value)


def validate_case(case):
    require(
        isinstance(case, dict)
        and set(case)
        == {"id", "family", "anchor_b_seconds", "span_seconds", "parameters", "synthetic"},
        "case_schema",
    )
    require(case["synthetic"] is True, "physical_model_not_supported")
    require(case["family"] in FAMILIES, "unknown_dynamics")
    require(
        isinstance(case["parameters"], list) and len(case["parameters"]) == 5, "parameter_shape"
    )
    p = list(map(number, case["parameters"]))
    require(all(abs(x) <= 10 for x in p), "parameter_domain")
    require(abs(number(case["anchor_b_seconds"])) <= 1000, "anchor_domain")
    require(abs(number(case["span_seconds"])) <= 4, "span_domain")
    return p


def initial(p):
    return [
        p[0],
        p[1],
        p[4],
        D(1),
        D(0),
        D(0),
        D(0),
        D(0),
        D(0),
        D(1),
        D(0),
        D(0),
        D(0),
        D(0),
        D(0),
        D(0),
        D(0),
        D(1),
    ]


def rhs(y, p, family):
    w2 = OMEGA2 if family == "forced_oscillator" else D(0)
    x, v = y[:2]
    sx, sv = y[3:8], y[8:13]
    return [
        v,
        p[2] - w2 * x,
        p[3] + LAMBDA * x + BETA * v * v,
        *sv,
        *[-w2 * sx[i] + int(i == 2) for i in range(5)],
        *[LAMBDA * sx[i] + 2 * BETA * v * sv[i] + int(i == 3) for i in range(5)],
    ]


def advance(y, span, steps, p, family):
    """Autonomous augmented system; retain sensitivities when chaining segments."""
    h = span / steps
    y = y.copy()
    for _ in range(steps):
        k1 = rhs(y, p, family)
        k2 = rhs([v + h * k / 2 for v, k in zip(y, k1, strict=True)], p, family)
        k3 = rhs([v + h * k / 2 for v, k in zip(y, k2, strict=True)], p, family)
        k4 = rhs([v + h * k for v, k in zip(y, k3, strict=True)], p, family)
        y = [
            v + h * (a + 2 * b + 2 * c + d) / 6
            for v, a, b, c, d in zip(y, k1, k2, k3, k4, strict=True)
        ]
    return y


def integrate(case, span, steps=128):
    with localcontext(Context(prec=60)):
        p = validate_case(case)
        require(type(steps) is int and steps in GRIDS, "step_inventory")
        require(isinstance(span, (str, D)), "span_type")
        span = number("0" if isinstance(span, D) and span == 0 else str(span))
        require(abs(span) <= 4, "span_domain")
        return advance(initial(p), span, steps, p, case["family"])


def solve(case, tt, max_iterations=12):
    with localcontext(Context(prec=60)):
        p = validate_case(case)
        require(type(max_iterations) is int and 1 <= max_iterations <= 12, "iteration_domain")
        tt = number(tt)
        b = tt - p[4]
        anchor = number(case["anchor_b_seconds"])
        for iteration in range(max_iterations):
            y = integrate(case, b - anchor)
            rate = rhs(y, p, case["family"])[2]
            denominator = 1 + rate
            require(denominator > D("0.5"), "implicit_denominator")
            residual = b + y[2] - tt
            if abs(residual) <= D("1e-35"):
                return dict(
                    b=b,
                    state=y,
                    jacobian=[-v / denominator for v in y[13:18]],
                    residual=residual,
                    iterations=iteration + 1,
                    denominator=denominator,
                )
            b -= residual / denominator
        raise TimeEphemerisError("implicit_no_convergence")


def covariance_mode(raw, mode):
    require(mode in MODES, "unknown_anchor_mode")
    require(
        isinstance(raw, list)
        and len(raw) == 5
        and all(isinstance(row, list) and len(row) == 5 for row in raw),
        "covariance_shape",
    )
    # Validate the supplied joint matrix before imposing a declared anchor assumption.
    propagate(["1"] * 5, raw, None)
    cov = copy.deepcopy(raw)
    if mode == "fixed":
        for i in range(5):
            cov[i][4] = cov[4][i] = "0"
    elif mode == "unknown_cross":
        cov[0][4] = cov[4][0] = None
    return cov


def variance(j, cov):
    value, _ = propagate([decimal_text(v) for v in j], cov, None)
    return value


def errors(actual, expected, size):
    require(isinstance(expected, list) and len(actual) == len(expected) == size, "reference_shape")
    return [abs(a - number(b)) for a, b in zip(actual, expected, strict=True)]


def evaluate_case(case, reference, cov):
    with localcontext(Context(prec=60)):
        require(reference["id"] == case["id"], "reference_identity")
        require([c["mode"] for c in reference["covariances"]] == MODES, "mode_inventory")
        span = number(case["span_seconds"])
        require(
            number(reference["b_seconds"]) == number(case["anchor_b_seconds"]) + span,
            "reference_endpoint",
        )
        with localcontext(Context(prec=100)):
            require(
                number(reference["tt_seconds"])
                == number(reference["b_seconds"]) + number(reference["augmented_state"][2]),
                "reference_tt_coordinate",
            )
        rows = []
        for steps in GRIDS:
            y = integrate(case, span, steps)
            err = errors(y, reference["augmented_state"], 18)
            rows.append(dict(steps=steps, state=y, absolute_errors=err))
        y, err = rows[-1]["state"], rows[-1]["absolute_errors"]
        limits = [D("1e-7")] * 2 + [D("1e-9")] + [D("1e-7")] * 10 + [D("1e-8")] * 5
        finest_ok = all(e <= limit for e, limit in zip(err, limits, strict=True))
        ratios = []
        if case["family"] == "constant_acceleration" or span == 0:
            refinement_ok = all(e <= D("1e-45") for row in rows for e in row["absolute_errors"])
            refinement_kind = "polynomial_roundoff" if span else "exact_initial_conditions"
        else:
            xerr = [row["absolute_errors"][0] for row in rows]
            require(all(e > 0 for e in xerr), "undefined_refinement_ratio")
            ratios = [a / b for a, b in zip(xerr[:-1], xerr[1:], strict=True)]
            refinement_ok = all(D(8) <= r <= D(32) for r in ratios)
            refinement_kind = "oscillator_fourth_order"
        root = solve(case, reference["tt_seconds"])
        root_error = abs(root["b"] - number(reference["b_seconds"]))
        root_errors = errors(root["jacobian"], reference["implicit_jacobian"], 5)
        implicit_ok = root_error <= D("1e-8") and all(e <= D("1e-8") for e in root_errors)
        covariance_results = []
        for expected in reference["covariances"]:
            mode = expected["mode"]
            matrix = covariance_mode(cov, mode)
            actual = [variance(y[13:18], matrix), variance(root["jacobian"], matrix)]
            comparison = []
            passed = True
            for v, key in zip(actual, ["clock_variance", "implicit_variance"], strict=True):
                if expected[key] is None:
                    passed &= v is None
                    comparison.append(None)
                else:
                    require(v is not None, "unexpected_unknown_covariance")
                    difference = abs(v - number(expected[key]))
                    passed &= difference <= D("1e-10")
                    comparison.append(str(difference))
            covariance_results.append(
                dict(
                    mode=mode,
                    clock_variance=None if actual[0] is None else str(actual[0]),
                    implicit_variance=None if actual[1] is None else str(actual[1]),
                    absolute_errors=comparison,
                    passed=bool(passed),
                )
            )
        return dict(
            id=case["id"],
            augmented_state=[str(v) for v in y],
            absolute_errors=[str(v) for v in err],
            refinements=[
                dict(steps=r["steps"], x_absolute_error=str(r["absolute_errors"][0])) for r in rows
            ],
            refinement_kind=refinement_kind,
            refinement_ratios=[str(v) for v in ratios],
            refinement_passed=bool(refinement_ok),
            implicit=dict(
                b_seconds=str(root["b"]),
                argument_absolute_error=str(root_error),
                jacobian=[str(v) for v in root["jacobian"]],
                absolute_errors=[str(v) for v in root_errors],
                equation_residual_seconds=str(root["residual"]),
                iterations=root["iterations"],
                denominator=str(root["denominator"]),
            ),
            covariances=covariance_results,
            passed=bool(
                finest_ok
                and refinement_ok
                and implicit_ok
                and all(c["passed"] for c in covariance_results)
            ),
        )


def load_inputs():
    try:
        require(sha(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest_checksum")
        for path, digest in json.loads(MANIFEST.read_text())["files"].items():
            require(sha(ROOT / path) == digest, "input_checksum")
        return [json.loads(p.read_text()) for p in (POLICY, FIXTURE, EVIDENCE, PRIOR)]
    except (OSError, json.JSONDecodeError) as exc:
        raise TimeEphemerisError("input_unavailable_or_invalid") from exc


def evaluate_inputs(policy, fixture, evidence, prior):
    for r in (policy, evidence, prior):
        require(all(r[k] is None for k in BOUND_KEYS), "unsupported_physical_bound")
        require(r["observing_eligible"] is False, "unsupported_eligibility")
        require(r["unresolved_components"] == COMPONENTS, "unresolved_components")
        require(
            r["physical_covariance_acquired"] is False
            and r["physical_covariance_propagated"] is False,
            "unsupported_covariance",
        )
    require(policy == json.loads(POLICY.read_text()), "frozen_policy_changed")
    require(policy["limits"] == LIMITS and policy["steps"] == GRIDS, "frozen_numerics")
    require(prior == json.loads(PRIOR.read_text()), "prior_record_changed")
    require(
        prior["audit_passed"] is True
        and prior["combined_counts"] == COUNTS
        and prior["full_reference_status"] == "unqualified"
        and prior["counts"]["missing_target_requirements"] == 18,
        "prior_gate",
    )
    require(evidence == json.loads(EVIDENCE.read_text()), "evidence_changed")
    require(
        fixture["model_id"] == policy["model_id"] == "integrated-clock-parameter-response-v1"
        and fixture["policy_sha256"] == sha(POLICY)
        and fixture["generator_sha256"]
        == sha(ROOT / "validation/reference_generation/integrated_clock_response.py"),
        "fixture_provenance",
    )
    require(fixture["independent_physical_reference"] is False, "independence_claim")
    require(
        [c["id"] for c in policy["cases"]] == [c["id"] for c in fixture["cases"]] == IDS,
        "case_inventory",
    )
    cases = [
        evaluate_case(c, r, policy["synthetic_covariance"])
        for c, r in zip(policy["cases"], fixture["cases"], strict=True)
    ]
    return dict(
        schema_version="1.0",
        mission=50,
        model_id=policy["model_id"],
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        audit_passed=all(c["passed"] for c in cases),
        counts=dict(
            synthetic_cases=8,
            integration_grids=32,
            augmented_values_per_case=18,
            endpoint_parameter_partials=120,
            implicit_parameter_partials=40,
            covariance_mode_pairs=24,
            known_variance_values=32,
            unknown_variance_values=16,
        ),
        cases=cases,
        physical_covariance_acquired=False,
        physical_covariance_propagated=False,
        physical_linearization_domain_established=False,
        full_reference_status="unqualified",
        inherited_unestablished_receipt_requirements=18,
        site_clocks_unqualified=48,
        combined_counts=COUNTS.copy(),
        unresolved_components=COMPONENTS.copy(),
        **dict.fromkeys(BOUND_KEYS),
        observing_eligible=False,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Integrated clock response audit must be offline")


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
        evidence_sha256=sha(EVIDENCE),
        python_version=platform.python_version(),
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
    print(json.dumps({k: result[k] for k in ["audit_passed", "counts", "combined_counts"]}))
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
