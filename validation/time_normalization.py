"""Offline normalization evidence audit; no physical clock qualification."""

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

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/time_normalization_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/time_normalization_v1.json"
EVIDENCE = ROOT / "docs/research/evidence/time_normalization_evidence_v1.json"
MANIFEST = ROOT / "validation/manifests/time_normalization_v1.json"
EXPECTED_MANIFEST_SHA256 = "87d5ee056efc868c7e921e2e71bc10cbb1d107cce46c5554381f2361269ccba5"
CONSTANTS = dict(
    LB="1.550519768e-8",
    LG="6.969290134e-10",
    T0_jd="2443144.5003725",
    TDB0_seconds="-0.0000655",
    seconds_per_day="86400",
    j2000_jd="2451545",
)
LIMITS = dict(
    decimal_replay_seconds="1e-50",
    erfa_affine_seconds="4e-11",
    historical_candidate_replay_seconds="1e-12",
    de440t_epoch_closure_seconds="1e-12",
)
CONTROL_INPUTS = [
    "-3155760000",
    "-86400",
    "-1",
    "0",
    "1",
    "86400",
    "31557600",
    "3155760000",
    "31557600000",
]
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
KINDS = dict(
    iau2006_definition="definition",
    iau2000_tt="definition",
    iau2006_drift="expected_secular_behavior",
    erfa_drift="expected_secular_behavior",
    erfa_de405_accuracy="model_relative_comparison",
    iau2000_formulation="conditional_formulation_accuracy",
    park_de440_model="physical_model_specification",
    same_kernel_readers="numerical_agreement",
)
AFFINE_NAMES = (
    "tdb_minus_tcb_seconds",
    "tt_minus_tcg_seconds",
    "tcb_minus_tdb_seconds",
    "tcg_minus_tt_seconds",
)


class NormalizationError(ValueError):
    pass


def require(value, message):
    if not value:
        raise NormalizationError(message)


def number(value):
    require(
        isinstance(value, str)
        and len(value) <= 160
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,3})?", value),
        "finite_decimal_string_required",
    )
    result = D(value)
    require(abs(result) <= D("1e12"), "numeric_domain")
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
                ROOT / "validation/results/time_ephemeris_reference_run.json",
                ROOT / "validation/results/coupled_clock_reference_run.json",
            )
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise NormalizationError("input_unavailable_or_invalid") from exc


def affine_offsets(x):
    """Offsets for independent input TCB, TCG, TDB and TT at T0+x."""
    lb, lg, d0 = D(CONSTANTS["LB"]), D(CONSTANTS["LG"]), D(CONSTANTS["TDB0_seconds"])
    return dict(
        zip(
            AFFINE_NAMES,
            (d0 - lb * x, -lg * x, (lb * x - d0) / (1 - lb), lg * x / (1 - lg)),
            strict=True,
        )
    )


def historical_offsets(tt, delta):
    origin = (D(CONSTANTS["T0_jd"]) - 2451545) * 86400
    lb, lg, d0 = D(CONSTANTS["LB"]), D(CONSTANTS["LG"]), D(CONSTANTS["TDB0_seconds"])
    x = tt - origin
    c = (x + delta - d0) / (1 - lb)
    g = x / (1 - lg)
    return dict(
        tdb_minus_tcb_seconds=x + delta - c, tcb_minus_tcg_seconds=c - g, tcg_minus_tt_seconds=g - x
    )


def split_seconds(seconds):
    days = math.floor(seconds / 86400)
    return float(2451545 + days), float((seconds - days * 86400) / 86400)


def actual_seconds(parts):
    return (D.from_float(float(parts[0])) - 2451545 + D.from_float(float(parts[1]))) * 86400


def erfa_offsets(x):
    """Check changes in two-part coordinates, retaining actual input quantization."""
    import erfa

    origin = (D(CONSTANTS["T0_jd"]) - 2451545) * 86400
    parts = split_seconds(origin + x)
    actual = actual_seconds(parts)
    expected = affine_offsets(actual - origin)
    values = {}
    for key, func in zip(
        AFFINE_NAMES, (erfa.tcbtdb, erfa.tcgtt, erfa.tdbtcb, erfa.tttcg), strict=True
    ):
        output = func(*parts)
        require(all(math.isfinite(v) for v in output), "nonfinite_library_output")
        change = (
            sum(
                (
                    D.from_float(float(o)) - D.from_float(i)
                    for o, i in zip(output, parts, strict=True)
                ),
                D(0),
            )
            * 86400
        )
        values[key] = dict(
            offset_seconds=str(change),
            minus_exact_at_actual_input_seconds=str(change - expected[key]),
        )
    return dict(
        input_jd_parts=[str(D.from_float(v)) for v in parts],
        argument_quantization_seconds=str(actual - origin - x),
        checks=values,
    )


def candidate_clock(tt):
    from astropy.time import Time
    from astropy.utils import iers

    with iers.conf.set_temp("auto_download", False):
        value = float(Time(*split_seconds(tt), format="jd", scale="tt").delta_tdb_tt)
    require(math.isfinite(value), "candidate_nonfinite")
    return D(format(value, ".17g"))


def validate_evidence(evidence):
    claims = evidence["claims"]
    require(
        len(claims) == len(KINDS) and [c["id"] for c in claims] == list(KINDS), "evidence_inventory"
    )
    for claim in claims:
        require(claim["kind"] == KINDS[claim["id"]], "evidence_category")
        require(claim["applicable_physical_bound_seconds"] is None, "unsupported_physical_bound")
        require(
            all(
                isinstance(claim[k], str) and claim[k]
                for k in ("source_url", "locator", "finding", "reason")
            ),
            "evidence_provenance",
        )
    by_id = {c["id"]: c for c in claims}
    require(
        by_id["iau2006_drift"]["quoted_rate_period"] == "year"
        and by_id["erfa_drift"]["quoted_rate_period"] == "century"
        and all(by_id[k]["quoted_rate_ns"] == "1" for k in ("iau2006_drift", "erfa_drift")),
        "source_discrepancy_erased",
    )
    require(
        evidence["source_discrepancies"]
        == [
            dict(
                id="drift_rate_period",
                claims=["iau2006_drift", "erfa_drift"],
                status="retained_not_resolved_into_bound",
            )
        ],
        "source_discrepancy_erased",
    )
    require(
        all(evidence[k] is None for k in BOUND_KEYS) and evidence["observing_eligible"] is False,
        "unsupported_physical_bound",
    )
    return dict(
        claims_reviewed=len(claims),
        applicable_physical_bounds=0,
        unresolved_source_discrepancies=evidence["source_discrepancies"],
    )


def spread(values):
    """For any constant k, max |r_i+k| >= (max r_i-min r_i)/2.

    This lower bound follows from the triangle inequality for the extreme pair;
    it neither selects a correction nor supplies a physical accuracy criterion.
    """
    lo, hi = min(values), max(values)
    return dict(
        count=len(values),
        minimum_seconds=str(lo),
        maximum_seconds=str(hi),
        range_seconds=str(hi - lo),
        any_constant_shift_max_residual_lower_bound_seconds=str((hi - lo) / 2),
    )


def evaluate_inputs(
    policy,
    fixture,
    evidence,
    prior,
    coupled,
    candidate=candidate_clock,
    affine_library=erfa_offsets,
):
    with localcontext(Context(prec=70)):
        return _evaluate(policy, fixture, evidence, prior, coupled, candidate, affine_library)


def _evaluate(policy, fixture, evidence, prior, coupled, candidate, affine_library):
    require(policy["constants"] == fixture["constants"] == CONSTANTS, "defining_constants")
    require(policy["limits"] == LIMITS, "frozen_tolerances")
    require(policy["controls_tcb_or_tcg_seconds_from_T0"] == CONTROL_INPUTS, "control_design")
    require(
        policy["unresolved_components"] == coupled["unresolved_components"] == COMPONENTS,
        "uncertainty_components",
    )
    require(
        policy["selected_arrival_convention_id"]
        == coupled["selected_arrival_convention_id"]
        == prior["selected_arrival_convention_id"]
        == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    require(prior["combined_counts"] == coupled["combined_counts"] == COUNTS, "prior_combined_gate")
    for record in (policy["expected_limits"], prior, evidence):
        require(
            all(record[k] is None for k in BOUND_KEYS) and record["observing_eligible"] is False,
            "unsupported_physical_bound",
        )
    require(
        coupled["physical_site_clock_bound_seconds"] is None
        and coupled["physical_arrival_bound_seconds"] is None
        and coupled["observing_eligible"] is False,
        "unsupported_physical_bound",
    )
    require(
        fixture["model_id"] == "iau2006-2000-affine-normalization-v1"
        and fixture["independent_physical_time_ephemeris"] is False
        and fixture["arithmetic"] == "exact_Fraction_with_90_digit_decimal_serialization",
        "reference_scope",
    )
    evidence_result = validate_evidence(evidence)
    require(
        [r["seconds_from_T0"] for r in fixture["controls"]] == CONTROL_INPUTS, "control_inventory"
    )
    decimal_limit, library_limit = (
        D(LIMITS["decimal_replay_seconds"]),
        D(LIMITS["erfa_affine_seconds"]),
    )
    controls, passed, faults = [], [], dict(omitted_tdb0=0, reversed_lb_sign=0, days_as_seconds=0)
    for row in fixture["controls"]:
        x = number(row["seconds_from_T0"])
        values = affine_offsets(x)
        residuals = {k: values[k] - number(row[k]) for k in AFFINE_NAMES}
        library = affine_library(x)
        require(set(library["checks"]) == set(AFFINE_NAMES), "library_check_inventory")
        number(library["argument_quantization_seconds"])
        library_residuals = [
            number(c["minus_exact_at_actual_input_seconds"]) for c in library["checks"].values()
        ]
        ok = all(abs(v) <= decimal_limit for v in residuals.values()) and all(
            abs(v) <= library_limit for v in library_residuals
        )
        passed.append(ok)
        correct = number(row["tdb_minus_tcb_seconds"])
        lb, d0 = D(CONSTANTS["LB"]), D(CONSTANTS["TDB0_seconds"])
        for key, faulty in dict(
            omitted_tdb0=-lb * x, reversed_lb_sign=d0 + lb * x, days_as_seconds=d0 - lb * x / 86400
        ).items():
            faults[key] += abs(faulty - correct) > library_limit
        controls.append(
            dict(
                seconds_from_T0=str(x),
                numerical_checks_passed=ok,
                decimal_minus_reference_seconds={k: str(v) for k, v in residuals.items()},
                library=library,
            )
        )
    require(len(fixture["cases"]) == len(prior["cases"]) == 14, "sample_count")
    expected_ids = [
        f"{day}_{hour}"
        for day in ("2024-03-20", "2024-06-21", "2024-09-22", "2024-12-21")
        for hour in ("10", "12", "14")
    ] + ["j2000_tt", "iau_epoch_tt"]
    require(
        [r["id"] for r in fixture["cases"]] == [r["id"] for r in prior["cases"]] == expected_ids,
        "sample_identity",
    )
    rows = []
    for row, old in zip(fixture["cases"], prior["cases"], strict=True):
        require(
            row["tt_seconds_from_j2000"] == old["tt_seconds_from_j2000"]
            and row["reused_de440t_delta_seconds"] == old["reference_tdb_minus_tt_seconds"]
            and row["kind"] == old["kind"],
            "historical_input_changed",
        )
        tt, delta = number(row["tt_seconds_from_j2000"]), number(row["reused_de440t_delta_seconds"])
        values = historical_offsets(tt, delta)
        residuals = {k: v - number(row[k]) for k, v in values.items()}
        closure = sum(values.values(), D(0)) - delta
        live = candidate(tt)
        require(isinstance(live, D) and live.is_finite(), "candidate_nonfinite")
        replay = live - number(old["candidate_tdb_minus_tt_seconds"])
        ok = (
            all(abs(v) <= decimal_limit for v in residuals.values())
            and abs(closure) <= decimal_limit
            and abs(replay) <= D(LIMITS["historical_candidate_replay_seconds"])
        )
        passed.append(ok)
        rows.append(
            dict(
                id=row["id"],
                kind=row["kind"],
                numerical_checks_passed=ok,
                tt_seconds_from_j2000=str(tt),
                reference_tdb_minus_tt_seconds=str(delta),
                live_candidate_seconds=str(live),
                candidate_minus_reference_seconds=str(live - delta),
                candidate_minus_archived_seconds=str(replay),
                affine_components_seconds={k: str(v) for k, v in values.items()},
                decimal_minus_reference_seconds={k: str(v) for k, v in residuals.items()},
                affine_closure_residual_seconds=str(closure),
            )
        )
    epoch = rows[-1]
    origin = (D(CONSTANTS["T0_jd"]) - 2451545) * 86400
    require(number(epoch["tt_seconds_from_j2000"]) == origin, "epoch_input")
    reference_epoch = number(epoch["reference_tdb_minus_tt_seconds"]) - D(CONSTANTS["TDB0_seconds"])
    epoch_ok = abs(reference_epoch) <= D(LIMITS["de440t_epoch_closure_seconds"])
    differences = [number(r["candidate_minus_reference_seconds"]) for r in rows]
    return dict(
        schema_version="1.0",
        benchmark_id="mission46-time-normalization-v1",
        audit_passed=all(passed) and epoch_ok,
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        normalization_status="affine_numerical_checks_only",
        independent_physical_time_ephemeris=False,
        controls=controls,
        cases=rows,
        fault_rejections=faults,
        diagnostics=dict(
            historical=spread(differences[:12]),
            all_samples=spread(differences),
            de440t_epoch_minus_tdb0_seconds=str(reference_epoch),
            candidate_epoch_minus_tdb0_seconds=str(
                number(epoch["live_candidate_seconds"]) - D(CONSTANTS["TDB0_seconds"])
            ),
            interpretation=(
                "Model differences; no fitted correction, physical threshold, "
                "continuous-domain bound or causal attribution."
            ),
        ),
        evidence=evidence_result,
        unresolved_components=COMPONENTS,
        combined_counts=COUNTS,
        full_reference_status="unqualified",
        **{k: None for k in BOUND_KEYS},
        observing_eligible=False,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Normalization audit must be offline")


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
    result.update(
        implementation_commit=os.getenv("ASTROSCOPE_IMPLEMENTATION_COMMIT", head),
        checkout_commit=os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", head),
        working_tree_dirty=bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("audit_passed", "diagnostics", "combined_counts")}))
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
