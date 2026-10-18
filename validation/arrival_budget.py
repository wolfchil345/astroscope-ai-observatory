"""Conditional analytic budget audit; never a physical timing certificate.

Only the standard library is needed. Exact rational results are authoritative.
The interval primitive is a contract probe, not a production schedule selector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/arrival_budget_policy_v1.json"
LEDGER = ROOT / "validation/manifests/observer_arrival_error_ledger_v1.json"
CONTRACT = ROOT / "validation/manifests/resolved_event_contract_v1.json"
MANIFEST = ROOT / "validation/manifests/arrival_budget_v1.json"
EXPECTED_MANIFEST_SHA256 = "38b716c50b4a8fecf3f65b8da6be04d038daedeafb7ab0ee766daaff17d35285"
C = Fraction(299792458)
REQUIRED = (
    "ephemeris_vector",
    "site_vector",
    "earth_orientation",
    "target_direction_motion",
    "finite_distance",
    "clock_model",
    "solar_shapiro",
    "other_relativistic",
    "numeric_evaluation",
)


class BudgetError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def number(value: str, *, nonnegative: bool = True) -> Fraction:
    if (
        not isinstance(value, str)
        or len(value) > 80
        or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value)
    ):
        raise BudgetError("finite_decimal_string_required")
    result = Fraction(value)
    if abs(result) > 10**40 or (nonnegative and result < 0):
        raise BudgetError("numeric_domain")
    return result


def vector_bound(error_m: str) -> Fraction:
    return number(error_m) / C


def direction_bound(radius_m: str, angle_rad_upper: str) -> Fraction:
    """Cauchy-Schwarz and unit-vector chord <= angular separation."""
    return number(radius_m) * min(number(angle_rad_upper), Fraction(2)) / C


def finite_distance_bound(radius_m: str, distance_lower_m: str) -> Fraction:
    """Exact geometric remainder bounded by R²/[2c(d_min-R)], d_min>R."""
    radius, distance = number(radius_m), number(distance_lower_m)
    if distance <= radius:
        raise BudgetError("distance_must_exceed_radius")
    return radius**2 / (2 * C * (distance - radius))


def einstein_amplitude_bound(site_radius_m: str, earth_speed_m_per_s: str) -> Fraction:
    """Magnitude of r.v/c² under supplied inequalities, not remaining model error."""
    return number(site_radius_m) * number(earth_speed_m_per_s) / C**2


def inverse_bound(
    forward: Fraction | None, residual_s: str, slope_lower: str | None, output_bound_s: str
) -> Fraction | None:
    """Conditional mean-value bound; existence/common bracket are external prerequisites."""
    residual, output = number(residual_s), number(output_bound_s)
    if forward is not None and (not isinstance(forward, Fraction) or forward < 0):
        raise BudgetError("absolute_forward_fraction_required")
    slope = None if slope_lower is None else number(slope_lower)
    if slope == 0:
        raise BudgetError("positive_slope_required")
    if forward is None or slope is None:
        return None
    return (forward + residual) / slope + output


def encoded_bound(value: Fraction | None) -> dict | None:
    if value is None:
        return None
    if value < 0:
        raise BudgetError("negative_bound")
    # Integer ceiling guarantees an outward-rounded nonnegative decimal bound.
    scale = 10**12
    units = (value.numerator * scale + value.denominator - 1) // value.denominator
    return dict(
        numerator=str(value.numerator),
        denominator=str(value.denominator),
        seconds_upper_12dp=f"{units // scale}.{units % scale:012d}",
    )


def assess_forward_ledger(terms: list[dict], domain: str) -> dict:
    if not isinstance(domain, str) or not domain.strip():
        raise BudgetError("domain_required")
    ids = [t.get("id") for t in terms]
    if len(ids) != len(set(ids)) or set(ids) != set(REQUIRED):
        raise BudgetError("required_terms_exactly_once")
    unknown, subtotal = [], Fraction(0)
    for term in terms:
        if term.get("domain") != domain:
            raise BudgetError("evidence_domain_mismatch")
        if not isinstance(term.get("evidence"), str) or not term["evidence"].strip():
            raise BudgetError("evidence_required")
        if term.get("kind") == "unknown":
            if term.get("value_seconds") is not None or not term.get("reason"):
                raise BudgetError("unknown_requires_null_and_reason")
            unknown.append(term["id"])
        elif term.get("kind") == "conditional_absolute_bound":
            subtotal += number(term.get("value_seconds"))
        else:
            raise BudgetError("not_an_absolute_bound")
    return dict(
        status="incomplete" if unknown else "complete_conditional_only",
        conditional_subtotal=encoded_bound(subtotal),
        forward_total=encoded_bound(None if unknown else subtotal),
        unknown_terms=sorted(unknown),
        observing_eligible=False,
        evidence_authentication="not_performed; declarations alone are not certification",
    )


def interval_membership(lower: str, upper: str, start: str, end: str, closure: str) -> str:
    """Classify a closed nominal error interval against an exact query, without epsilon."""
    lo, hi, a, b = [number(x, nonnegative=False) for x in (lower, upper, start, end)]
    if lo > hi or a > b:
        raise BudgetError("reversed_interval")
    if closure not in ("closed", "half_open"):
        raise BudgetError("unsupported_closure")
    if closure == "half_open":
        if a == b or hi < a or lo >= b:
            return "outside"
        if lo >= a and hi < b:
            return "inside"
    else:
        if hi < a or lo > b:
            return "outside"
        if lo >= a and hi <= b:
            return "inside"
    return "boundary_indeterminate"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs() -> tuple[dict, dict, dict]:
    try:
        if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
            raise BudgetError("manifest_checksum")
        manifest = json.loads(MANIFEST.read_text())
        for name, digest in manifest["files"].items():
            if sha(ROOT / name) != digest:
                raise BudgetError("input_checksum")
    except OSError as exc:
        raise BudgetError("input_unavailable") from exc
    policy, ledger, contract = [json.loads(p.read_text()) for p in (POLICY, LEDGER, CONTRACT)]
    if tuple(policy["required_forward_terms"]) != REQUIRED:
        raise BudgetError("term_inventory_mismatch")
    if contract["kind"] != "prospective_contract_not_runtime_schema":
        raise BudgetError("contract_kind")
    if contract["eligibility_enabled"] is not False:
        raise BudgetError("unexpected_eligibility")
    scenarios = contract["scenarios"]
    if {s["id"] for s in scenarios} != {f"RE{i:02d}" for i in range(1, 21)}:
        raise BudgetError("contract_scenario_inventory")
    if len(scenarios) != 20 or any(
        s["execution_status"] != "not_executed_in_production" for s in scenarios
    ):
        raise BudgetError("contract_execution_claim")
    return policy, ledger, contract


def deny_network(*args, **kwargs):
    raise RuntimeError("Budget audit must be offline")


def evaluate() -> dict:
    policy, ledger, contract = load_inputs()
    examples = []
    for row in policy["conditional_examples"]:
        kind = row["kind"]
        if kind == "vector":
            bound = vector_bound(row["error_m"])
        elif kind == "direction":
            bound = direction_bound(row["radius_m"], row["angle_rad_upper"])
        elif kind == "finite_distance":
            bound = finite_distance_bound(row["radius_m"], row["distance_lower_m"])
        elif kind == "einstein_amplitude":
            bound = einstein_amplitude_bound(row["site_radius_m"], row["earth_speed_m_per_s"])
        elif kind == "inverse":
            bound = inverse_bound(
                number(row["forward_bound_s"]),
                row["residual_s"],
                row["slope_lower"],
                row["output_bound_s"],
            )
        else:
            raise BudgetError("unknown_example")
        examples.append(dict(id=row["id"], inputs=row, conditional_bound=encoded_bound(bound)))
    assessment = assess_forward_ledger(ledger["terms"], ledger["scope_id"])
    source = json.loads((ROOT / ledger["non_bound_evidence"]["mission38_result"]).read_text())
    return dict(
        schema_version="1.0",
        audit_id="arrival-budget-v1",
        passed=(
            assessment["status"] == "incomplete"
            and assessment["forward_total"] is None
            and not assessment["observing_eligible"]
        ),
        pass_meaning="Evidence classification and fail-closed budget audit; not physical accuracy",
        ledger_assessment=assessment,
        conditional_examples=examples,
        physical_arrival_bound=None,
        observing_eligible=False,
        unchanged_mission38_sample_maxima_seconds=source["maxima_seconds"],
        sample_maxima_classification="sampled_discrepancy_not_absolute_bound",
        prospective_contract_scenario_count=len(contract["scenarios"]),
        prospective_contract_execution="not_executed_in_production",
        manifest_sha256=sha(MANIFEST),
        implementation_sha256=sha(Path(__file__)),
        environment=dict(
            python=platform.python_version(),
            numeric_engine="stdlib Fraction",
            network="socket connections blocked",
            astronomy_imports_required=False,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        result = evaluate()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["implementation_commit"] = os.getenv("ASTROSCOPE_IMPLEMENTATION_COMMIT", head)
    result["checkout_commit"] = os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", head)
    result["working_tree_dirty"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ["passed", "physical_arrival_bound", "observing_eligible"]}
        )
    )
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
