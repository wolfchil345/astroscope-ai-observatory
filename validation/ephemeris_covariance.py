"""Offline covariance provenance review and synthetic receipt qualification only."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import socket
import subprocess
from decimal import Context, localcontext
from pathlib import Path
from unittest.mock import patch

from validation.clock_sensitivity import BOUND_KEYS, COMPONENTS, COUNTS, number, propagate
from validation.time_ephemeris import TimeEphemerisError, require, sha

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/ephemeris_covariance_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/ephemeris_covariance_v1.json"
EVIDENCE = ROOT / "docs/research/evidence/ephemeris_covariance_evidence_v1.json"
MANIFEST = ROOT / "validation/manifests/ephemeris_covariance_v1.json"
EXPECTED_MANIFEST_SHA256 = "2effc0268a24542bfb3ac119a0e219aaa21932ce758747fbc85c2f9a780633f3"
CONTEXT_KEYS = {
    "solution_id",
    "kernel_sha256",
    "quantity",
    "origin",
    "frame",
    "time_scale",
    "reference_epoch_jd",
    "validity_jd",
    "parameters",
    "response_kind",
    "anchor_kind",
}
CONTROL_IDS = ["identity", "permutation", "si_permutation", "singular_si_permutation"]
REQUIREMENTS = [
    "covariance_payload",
    "parameter_basis_and_units",
    "reference_epoch_and_scale",
    "nominal_solution_link",
    "full_correlations",
    "estimated_and_consider_parameters",
    "integrated_trajectory_response",
    "clock_anchor_and_cross_covariance",
    "validity_interval",
]
SOURCE_IDS = [
    "jpl_export",
    "park2021",
    "inpop21a_catalog",
    "inpop21a_note",
    "fienga2024",
    "rambaux2026",
    "rambaux2026_cds",
    "sbdb",
    "horizons",
]


def synthetic_receipt(context, case):
    return dict(
        synthetic=True,
        representation="full_covariance",
        covariance_context=copy.deepcopy(context),
        response_context=copy.deepcopy(context),
        covariance=copy.deepcopy(case["covariance"]),
        jacobian=case["jacobian"].copy(),
    )


def validate_receipt(receipt, expected):
    """Reject physical inputs: this is a bounded synthetic contract, not an adapter."""
    require(isinstance(receipt, dict), "receipt_schema")
    require(isinstance(expected, dict), "context_schema")
    require(
        set(receipt)
        == {
            "synthetic",
            "representation",
            "covariance_context",
            "response_context",
            "covariance",
            "jacobian",
        },
        "receipt_schema",
    )
    require(receipt["synthetic"] is True, "physical_receipt_not_supported")
    require(receipt["representation"] == "full_covariance", "unsupported_representation")
    require(set(expected) == CONTEXT_KEYS, "context_schema")
    for context in [expected, receipt["covariance_context"], receipt["response_context"]]:
        require(isinstance(context, dict) and set(context) == CONTEXT_KEYS, "context_schema")
        require(context == expected, "context_mismatch")
        require(
            context["solution_id"] == "synthetic-fit-v1" and context["kernel_sha256"] == "0" * 64,
            "synthetic_identity",
        )
        require(
            context["quantity"] == "TT_minus_TDB_seconds"
            and context["origin"] == "geocentre"
            and context["frame"] == "BCRS"
            and context["time_scale"] == "TDB",
            "synthetic_convention",
        )
        require(
            context["response_kind"] == "integrated_parameter_response"
            and context["anchor_kind"] == "fixed_conventional",
            "response_or_anchor_unknown",
        )
        interval = context["validity_jd"]
        require(isinstance(interval, list) and len(interval) == 2, "interval_shape")
        start, end = map(number, interval)
        require(
            start <= number(context["reference_epoch_jd"]) <= end and start < end,
            "invalid_validity_interval",
        )
        params = context["parameters"]
        require(isinstance(params, list) and len(params) == 3, "parameter_inventory")
        require(
            all(isinstance(p, dict) and set(p) == {"id", "unit", "role"} for p in params),
            "parameter_schema",
        )
        require(
            all(isinstance(p["id"], str) and p["id"] for p in params)
            and len({p["id"] for p in params}) == 3,
            "parameter_identity",
        )
        require([p["unit"] for p in params] == ["km", "km/s", "km^3/s^2"], "parameter_units")
        require(all(p["role"] in {"estimated", "consider"} for p in params), "parameter_role")
    require(
        isinstance(receipt["jacobian"], list) and len(receipt["jacobian"]) == 3, "response_shape"
    )
    variance, _ = propagate(receipt["jacobian"], receipt["covariance"], None)
    require(variance is not None, "complete_covariance_required")
    return variance


def transform(receipt, expected, order, scales):
    with localcontext(Context(prec=70)):
        before = validate_receipt(receipt, expected)
        require(
            isinstance(order, list)
            and len(order) == 3
            and all(type(i) is int for i in order)
            and sorted(order) == [0, 1, 2],
            "invalid_permutation",
        )
        require(isinstance(scales, list) and len(scales) == 3, "scale_shape")
        s = list(map(number, scales))
        require(all(v > 0 for v in s), "nonpositive_scale")
        c = [[number(v) for v in row] for row in receipt["covariance"]]
        j = list(map(number, receipt["jacobian"]))
        out_c = [
            [format(s[i] * s[k] * c[order[i]][order[k]], "f") for k in range(3)] for i in range(3)
        ]
        out_j = [format(j[order[i]] / s[i], "f") for i in range(3)]
        after, _ = propagate(out_j, out_c, None)
        require(before == after, "variance_not_invariant")
        return dict(
            covariance=out_c,
            jacobian=out_j,
            variance=format(after, "f"),
            original_variance=format(before, "f"),
        )


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
                ROOT / "validation/results/clock_sensitivity_reference_run.json",
            )
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise TimeEphemerisError("input_unavailable_or_invalid") from exc


def same_numbers(a, b):
    return len(a) == len(b) and all(number(x) == number(y) for x, y in zip(a, b, strict=True))


def evaluate_inputs(policy, fixture, evidence, prior):
    require(
        policy["model_id"] == fixture["model_id"] == "ephemeris-covariance-qualification-v1",
        "model_identity",
    )
    require(
        fixture["policy_sha256"] == sha(POLICY)
        and fixture["generator_sha256"]
        == sha(ROOT / "validation/reference_generation/ephemeris_covariance.py"),
        "fixture_provenance",
    )
    require(fixture["independent_physical_reference"] is False, "independence_claim")
    for record in [policy, evidence, prior]:
        require(all(record[k] is None for k in BOUND_KEYS), "unsupported_physical_bound")
        require(record["observing_eligible"] is False, "unsupported_eligibility")
        require(record["unresolved_components"] == COMPONENTS, "unresolved_components")
    require(
        prior["audit_passed"] is True
        and prior["combined_counts"] == COUNTS
        and prior["site_clocks_unqualified"] == 48
        and prior["full_reference_status"] == "unqualified"
        and prior["physical_covariance_propagated"] is False,
        "prior_gate",
    )
    require(
        policy["selected_arrival_convention_id"]
        == prior["selected_arrival_convention_id"]
        == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    require(
        evidence["physical_covariance_acquired"] is False
        and evidence["physical_covariance_propagated"] is False,
        "unsupported_covariance",
    )
    require(policy["requirements"] == REQUIREMENTS, "requirement_inventory")
    require(
        policy["source_ids"] == SOURCE_IDS and [s["id"] for s in evidence["sources"]] == SOURCE_IDS,
        "source_inventory",
    )
    require(
        all(
            all(
                isinstance(s[k], str) and s[k]
                for k in [
                    "url",
                    "location",
                    "classification",
                    "finding",
                    "limitation",
                    "review_date_utc",
                ]
            )
            for s in evidence["sources"]
        ),
        "source_evidence_missing",
    )
    require(
        policy["targets"] == evidence["targets"]
        and [t["id"] for t in policy["targets"]] == ["DE440t", "INPOP21a"],
        "target_inventory",
    )
    targets = []
    for target, name in zip(policy["targets"], ["time_ephemeris", "cross_model_time"], strict=True):
        kernel = json.loads((ROOT / f"validation/manifests/{name}_policy_v1.json").read_text())[
            "kernel"
        ]
        require(
            target["kernel_sha256"] == kernel["sha256"]
            and target["quantity"] == kernel["quantity"] == "TT_minus_TDB"
            and target["units"] == "seconds"
            and target["origin"] == "geocentre"
            and target["time_scale"] == "TDB",
            "nominal_product_identity",
        )
        require(target["requirements"] == dict.fromkeys(REQUIREMENTS), "unsupported_receipt")
        targets.append(
            dict(
                id=target["id"],
                status="not_qualified",
                missing_requirements=REQUIREMENTS.copy(),
                kernel_sha256=target["kernel_sha256"],
            )
        )
    require(
        [c["id"] for c in policy["controls"]] == CONTROL_IDS
        and [c["id"] for c in fixture["controls"]] == CONTROL_IDS,
        "control_inventory",
    )
    controls = []
    for case, reference in zip(policy["controls"], fixture["controls"], strict=True):
        result = transform(
            synthetic_receipt(policy["synthetic_context"], case),
            policy["synthetic_context"],
            case["order"],
            case["scales"],
        )
        require(len(reference["covariance"]) == 3, "reference_shape")
        passed = all(
            same_numbers(a, b)
            for a, b in zip(result["covariance"], reference["covariance"], strict=True)
        )
        passed &= same_numbers(result["jacobian"], reference["jacobian"])
        passed &= number(result["variance"]) == number(reference["variance"])
        controls.append(dict(id=case["id"], **result, passed=bool(passed)))
    return dict(
        schema_version="1.0",
        mission=49,
        model_id=policy["model_id"],
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        audit_passed=all(c["passed"] for c in controls),
        counts=dict(
            reviewed_sources=9,
            target_products=2,
            qualified_physical_products=0,
            missing_target_requirements=18,
            synthetic_controls=4,
        ),
        targets=targets,
        controls=controls,
        physical_covariance_acquired=False,
        physical_covariance_propagated=False,
        physical_linearization_domain_established=False,
        full_reference_status="unqualified",
        site_clocks_unqualified=48,
        combined_counts=COUNTS.copy(),
        unresolved_components=COMPONENTS.copy(),
        **dict.fromkeys(BOUND_KEYS),
        observing_eligible=False,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Covariance qualification must be offline")


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
