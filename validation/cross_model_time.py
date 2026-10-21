"""Offline cross-model diagnostics; agreement never establishes physical accuracy."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
from decimal import Context, localcontext
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from validation.time_ephemeris import (
    TimeEphemerisError,
    candidate_clock,
    expected_samples,
    number,
    require,
    sha,
    summary,
    validate_trace,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/cross_model_time_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/cross_model_time_v1.json"
EVIDENCE = ROOT / "docs/research/evidence/cross_model_time_evidence_v1.json"
MANIFEST = ROOT / "validation/manifests/cross_model_time_v1.json"
EXPECTED_MANIFEST_SHA256 = "6eac9b8f7294e4207c7ef1a8f31e3d56a2957ca9b0472784bc7bb4109419353d"
COMPONENTS = [
    "geocentric_time_ephemeris",
    "earth_state",
    "station_coordinates",
    "earth_orientation",
    "omitted_physics_and_coefficient_model",
    "higher_order_remainder",
]
COUNTS = dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48)
BOUND_KEYS = (
    "physical_geocentric_clock_bound_seconds",
    "physical_site_clock_bound_seconds",
    "physical_arrival_bound_seconds",
)
CLAIMS = dict(
    release_distribution="distribution_contract",
    integrated_method="family_method",
    historical_time_comparison="other_model_relative_comparison",
    release_model_evidence="release_model_and_orbit_comparison",
    reader_conventions="implementation_contract",
    cross_model_interpretation="project_inference",
)
INDEPENDENCE = dict(
    distinct_ephemeris_families=True,
    independent_of_candidate_fb90_series=True,
    statistically_independent_errors_established=False,
    readers_shared_between_models=True,
    same_kernel_within_each_reader_pair=True,
    independent_observation_clock_validation=False,
)
LIMITS = dict(
    historical_candidate_replay_seconds="1e-12",
    epoch_closure_seconds="1e-12",
    triangle_closure_seconds="1e-12",
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
                ROOT / "validation/manifests/observer_arrival_policy_v1.json",
                ROOT / "validation/fixtures/time_ephemeris_v1.json",
                ROOT / "validation/results/time_ephemeris_reference_run.json",
                ROOT / "validation/results/time_normalization_reference_run.json",
            )
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise TimeEphemerisError("input_unavailable_or_invalid") from exc


def check_evidence(evidence):
    claims = evidence["claims"]
    require(len(claims) == len(CLAIMS), "evidence_inventory")
    require([c["id"] for c in claims] == list(CLAIMS), "evidence_inventory")
    for claim in claims:
        require(claim["kind"] == CLAIMS[claim["id"]], "evidence_category")
        require(
            claim["source_url"].startswith("https://")
            and claim["location"]
            and claim["finding"]
            and claim["applicability"],
            "evidence_provenance",
        )
        require(claim["applicable_physical_bound_seconds"] is None, "unsupported_physical_bound")
    require(evidence["independence"] == INDEPENDENCE, "independence_claim")


def check_fixture(policy, fixture):
    kernel = policy["kernel"]
    require(
        policy["reference_model_id"] == fixture["model_id"] == "inpop21a-geocentric-tt-tdb-v1",
        "reference_model",
    )
    require(fixture["physical_model_family"] == "INPOP", "reference_model")
    require(
        fixture["policy_sha256"] == sha(POLICY)
        and fixture["generator_sha256"]
        == sha(ROOT / "validation/reference_generation/cross_model_time.py"),
        "fixture_provenance",
    )
    require(
        fixture["archive_sha256"] == policy["archive"]["sha256"]
        and fixture["kernel_sha256"] == kernel["sha256"]
        and fixture["kernel_size_bytes"] == kernel["size_bytes"],
        "kernel_identity",
    )
    for key, expected in dict(
        quantity="TT_minus_TDB", units="seconds", argument_scale="TDB", origin="geocentre"
    ).items():
        require(kernel[key] == fixture[key] == expected, "kernel_convention")
    keys = ("center", "target", "frame", "spk_type", "source", "coverage_jd_tdb")
    require(fixture["segment"] == {k: kernel[k] for k in keys}, "segment_identity")
    require(
        kernel["center"] == 1000000000
        and kernel["target"] == 1000000001
        and kernel["frame"] == 1
        and kernel["spk_type"] == 2,
        "segment_identity",
    )
    require(
        fixture["packages"] == policy["reference_packages"]
        and fixture["cspice_toolkit"] == policy["cspice_toolkit"] == "CSPICE_N0067",
        "reference_environment",
    )
    require(
        fixture["forbidden_imports"] == []
        and fixture["same_kernel_for_both_readers"] is True
        and fixture["raw_coefficients_vendored"] is False,
        "reference_boundary",
    )
    require(
        fixture["physical_geocentric_clock_bound_seconds"] is None
        and fixture["observing_eligible"] is False,
        "unsupported_physical_bound",
    )


def evaluate_inputs(
    policy,
    fixture,
    evidence,
    historical,
    de_fixture,
    de_record,
    normalization,
    candidate=candidate_clock,
):
    with localcontext(Context(prec=70)):
        return _evaluate(
            policy, fixture, evidence, historical, de_fixture, de_record, normalization, candidate
        )


def _evaluate(
    policy, fixture, evidence, historical, de_fixture, de_record, normalization, candidate
):
    check_fixture(policy, fixture)
    check_evidence(evidence)
    require(
        policy["selected_arrival_convention_id"] == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    require(policy["limits"] == LIMITS, "frozen_tolerances")
    require(
        policy["unresolved_components"] == normalization["unresolved_components"] == COMPONENTS,
        "uncertainty_components",
    )
    for record in (policy["expected_limits"], evidence, de_record, normalization):
        require(all(record[k] is None for k in BOUND_KEYS), "unsupported_physical_bound")
        require(record["observing_eligible"] is False, "unsupported_eligibility")
    require(
        de_record["audit_passed"] is True and normalization["audit_passed"] is True,
        "prior_audit_failed",
    )
    require(
        de_record["combined_counts"] == normalization["combined_counts"] == COUNTS,
        "prior_combined_gate",
    )
    require(
        de_fixture["model_id"] == "de440t-geocentric-tt-tdb-v1"
        and de_fixture["kernel_sha256"] != fixture["kernel_sha256"],
        "distinct_models",
    )
    contract = policy["reader_contract"]
    expected_contract = dict(
        convergence_seconds="1e-15",
        offset_agreement_seconds="1e-12",
        derivative_agreement_seconds_per_second="1e-15",
        equation_residual_seconds="1e-15",
        historical_tt_input_agreement_seconds="1e-9",
    )
    require(
        all(contract[k] == v for k, v in expected_contract.items())
        and contract["max_iterations"] == 8,
        "frozen_tolerances",
    )
    require(
        len(fixture["cases"]) == len(de_fixture["cases"]) == len(de_record["cases"]) == 14,
        "sample_count",
    )
    rows = []
    for row, de, old, expected in zip(
        fixture["cases"],
        de_fixture["cases"],
        de_record["cases"],
        expected_samples(policy, historical),
        strict=True,
    ):
        require(all(row[k] == de[k] == old[k] == expected[k] for k in expected), "sample_context")
        tt = number(row["tt_seconds_from_j2000"])
        lo, hi = map(number, fixture["segment"]["coverage_jd_tdb"])
        checks, quantization = [], {}
        for reader in ("cspice", "jplephem"):
            converged, q = validate_trace(row[reader], reader, tt, contract)
            checks.append(converged)
            quantization[reader] = str(q)
            # Coverage includes the actual TDB argument, not just the TT epoch.
            for entry in row[reader]["trace"]:
                b = (
                    number(entry["argument_et_seconds"]) / 86400 + 2451545
                    if reader == "cspice"
                    else sum(map(number, entry["argument_jd_parts"]))
                )
                require(lo <= b <= hi, "argument_coverage")
        delta = number(row["cspice"]["delta_seconds"])
        delta2 = number(row["jplephem"]["delta_seconds"])
        reader_difference = delta2 - delta
        derivative_difference = number(
            row["jplephem"]["trace"][-1]["derivative_seconds_per_second"]
        ) - number(row["cspice"]["trace"][-1]["derivative_seconds_per_second"])
        checks += [abs(reader_difference) <= D("1e-12"), abs(derivative_difference) <= D("1e-15")]
        de_delta = number(de["cspice"]["delta_seconds"])
        require(de_delta == number(old["reference_tdb_minus_tt_seconds"]), "de440t_input_changed")
        current = candidate(tt)
        require(isinstance(current, D) and current.is_finite(), "candidate_nonfinite")
        replay = current - number(old["candidate_tdb_minus_tt_seconds"])
        checks.append(abs(replay) <= D(LIMITS["historical_candidate_replay_seconds"]))
        cross = delta - de_delta
        candidate_difference = current - delta
        # Independent historical edge closes against the two newly computed edges.
        triangle = candidate_difference + cross - number(old["candidate_minus_reference_seconds"])
        checks.append(abs(triangle) <= D(LIMITS["triangle_closure_seconds"]))
        epoch_error = delta - D("-0.0000655") if row["id"] == "iau_epoch_tt" else None
        if epoch_error is not None:
            checks.append(abs(epoch_error) <= D(LIMITS["epoch_closure_seconds"]))
        rows.append(
            dict(
                **expected,
                numerical_checks_passed=all(checks),
                inpop21a_tdb_minus_tt_seconds=str(delta),
                de440t_tdb_minus_tt_seconds=str(de_delta),
                candidate_tdb_minus_tt_seconds=str(current),
                inpop21a_minus_de440t_seconds=str(cross),
                candidate_minus_inpop21a_seconds=str(candidate_difference),
                archived_candidate_minus_de440t_seconds=old["candidate_minus_reference_seconds"],
                candidate_replay_difference_seconds=str(replay),
                triangle_closure_seconds=str(triangle),
                iau_epoch_closure_seconds=None if epoch_error is None else str(epoch_error),
                jplephem_minus_cspice_seconds=str(reader_difference),
                reader_derivative_difference_seconds_per_second=str(derivative_difference),
                max_argument_quantization_seconds=quantization,
                iterations={k: len(row[k]["trace"]) for k in ("cspice", "jplephem")},
            )
        )
    diagnostics = {}
    for name, subset in (("historical", rows[:12]), ("epoch_probes", rows[12:]), ("all", rows)):
        diagnostics[name] = {
            key: summary([number(r[key]) for r in subset], "model_difference_no_accuracy_threshold")
            for key in ("inpop21a_minus_de440t_seconds", "candidate_minus_inpop21a_seconds")
        }
    passed = all(r["numerical_checks_passed"] for r in rows)
    return dict(
        schema_version="1.0",
        benchmark_id="cross-model-time-ephemeris-v1",
        audit_passed=passed,
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        cross_model_status=(
            "qualified_for_sampled_geocentric_diagnostics_only"
            if passed
            else "numerical_qualification_failed"
        ),
        full_reference_status="unqualified",
        independence=INDEPENDENCE.copy(),
        evidence=dict(claims_reviewed=len(CLAIMS), applicable_physical_bounds=0),
        diagnostics=diagnostics,
        cases=rows,
        unresolved_components=COMPONENTS.copy(),
        site_clocks_unqualified=48,
        combined_counts=COUNTS.copy(),
        **{k: None for k in BOUND_KEYS},
        observing_eligible=False,
        next_gate=policy["next_gate"],
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Cross-model audit must be offline")


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
    print(json.dumps({k: result[k] for k in ("audit_passed", "diagnostics", "combined_counts")}))
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
