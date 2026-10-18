"""Offline, supplied-input solar component qualification; no arrival resolver."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/source_reference_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/source_reference_v1.json"
MANIFEST = ROOT / "validation/manifests/source_reference_v1.json"
EXPECTED_MANIFEST_SHA256 = "416188065b985415c0f6e560eae138910e2d0a1dd39c504f6a1b013a9bdee454"
C = Decimal("299792458")
GM = Decimal("132712440018000000000")
CONVENTION = {
    "convention_id": "astroscope-tdb-solar-au-v1",
    "scale": "tdb",
    "reference_position": "ssb",
    "target_model": "fixed_icrs_at_infinity",
    "clock_model": "tt_tai_erfa_dtdb_site",
    "topocentric_einstein": "included_once_in_clock",
    "solar_model": "first_order_solar_distance_au",
    "input_state": "source_coordinate",
}
PROVENANCE = {"source_id", "algorithm_version", "data_identity"}


class ReferenceError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def number(value):
    if (
        not isinstance(value, str)
        or len(value) > 80
        or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value)
    ):
        raise ReferenceError("finite_decimal_string_required")
    result = Decimal(value)
    if result.copy_abs() > Decimal("1e40"):
        raise ReferenceError("numeric_domain")
    return result


def domain_reasons(radius_au, cosine):
    radius, mu = number(radius_au), number(cosine)
    reasons = []
    if not Decimal("0.9") <= radius <= Decimal("1.1"):
        reasons.append("radius_outside_component_domain")
    if not Decimal("-1") <= mu <= Decimal("0.8"):
        reasons.append("solar_elongation_outside_component_domain")
    return reasons


def solar_correction(radius_au, cosine):
    """Additive source-coordinate term, given radius/au and geometric cosine.

    This is a scalar component only. It does not calculate observer/Sun vectors,
    convert clocks, authenticate source metadata or grant observing eligibility.
    """
    if domain_reasons(radius_au, cosine):
        raise ReferenceError("outside_component_domain")
    with localcontext(Context(prec=70)):
        radius, mu = number(radius_au), number(cosine)
        return 2 * GM / C**3 * (radius * (1 - mu)).ln()


def source_compatibility(descriptor):
    """Validate declarations for the selected study, without authenticating evidence."""
    if not isinstance(descriptor, dict) or set(descriptor) != set(CONVENTION) | PROVENANCE:
        raise ReferenceError("explicit_source_descriptor_required")
    for field, expected in CONVENTION.items():
        if descriptor[field] != expected:
            raise ReferenceError(f"incompatible_{field}")
    if any(not isinstance(descriptor[p], str) or not descriptor[p].strip() for p in PROVENANCE):
        raise ReferenceError("source_provenance_required")
    return dict(
        status="compatible_declarations_for_study_only",
        evidence_authenticated=False,
        observing_eligible=False,
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    try:
        if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
            raise ReferenceError("manifest_checksum")
        manifest = json.loads(MANIFEST.read_text())
        for name, digest in manifest["files"].items():
            if sha(ROOT / name) != digest:
                raise ReferenceError("input_checksum")
    except OSError as exc:
        raise ReferenceError("input_unavailable") from exc
    policy, fixture = json.loads(POLICY.read_text()), json.loads(FIXTURE.read_text())
    if policy["convention"]["source_descriptor_required"] != CONVENTION:
        raise ReferenceError("convention_mismatch")
    if fixture["convention_id"] != CONVENTION["convention_id"]:
        raise ReferenceError("fixture_convention")
    return policy, fixture


def check_vectors(row, tolerance):
    """Check serialization consistency only; tolerance is not an angular accuracy bound."""
    vectors = [row["observer_to_sun_au"], row["direction_icrs"]]
    if any(not isinstance(v, list) or len(v) != 3 for v in vectors):
        raise ReferenceError("three_component_vector_required")
    with localcontext(Context(prec=70)):
        r, n = [[number(x) for x in v] for v in vectors]
        norm = sum(x * x for x in r).sqrt()
        if not norm or abs(sum(x * x for x in n) - 1) > tolerance:
            raise ReferenceError("invalid_reference_vector")
        mu = sum(a * b for a, b in zip(r, n, strict=True)) / norm
        if (
            abs(norm - number(row["radius_au"])) > tolerance
            or abs(mu - number(row["cosine"])) > tolerance
        ):
            raise ReferenceError("inconsistent_reference_scalars")


def check_inventory(policy, fixture):
    synthetic = {}
    for radius in policy["synthetic_grid"]["radii_au"]:
        for cosine, _ in policy["synthetic_grid"]["cosine_sine_pairs"]:
            for axis in policy["synthetic_grid"]["axes"]:
                synthetic[f"synthetic_{radius}_{cosine}_{axis}"] = (radius, cosine, axis)
    old = json.loads((ROOT / policy["historical_census"]["policy"]).read_text())
    historical = {}
    for date in old["dates"]:
        for site in old["sites"]:
            for ti, target in enumerate(old["targets"]):
                for hour in old["hours"]:
                    historical[f"{date}_{site['name']}_{ti}_{hour}"] = (
                        f"{date}T{hour:02}:00:00+00:00",
                        site,
                        target,
                        ti,
                    )
    for cohort, expected in [("synthetic", synthetic), ("historical", historical)]:
        rows = fixture[cohort]
        if len(rows) != len(expected) or {r["id"] for r in rows} != set(expected):
            raise ReferenceError("case_inventory")
        for row in rows:
            fields = (
                ("radius_au", "cosine", "axis")
                if cohort == "synthetic"
                else ("utc", "site", "target", "target_index")
            )
            if tuple(row[k] for k in fields) != expected[row["id"]]:
                raise ReferenceError("case_context")


def evaluate():
    policy, fixture = load_inputs()
    check_inventory(policy, fixture)
    tolerance = number(policy["numeric_policy"]["comparison_tolerance_seconds"])
    vector_tolerance = number(policy["numeric_policy"]["vector_scalar_consistency_tolerance"])
    results, summaries = [], {}
    mutation = {
        name: dict(detected=0, undetected_ids=[]) for name in policy["mutation_policy"]["faults"]
    }
    with localcontext(Context(prec=70)):
        for cohort in ("synthetic", "historical"):
            counts = dict(total=len(fixture[cohort]), compared=0, excluded=0, failed=0)
            maximum = Decimal(0)
            for row in fixture[cohort]:
                check_vectors(row, vector_tolerance)
                reasons = domain_reasons(row["radius_au"], row["cosine"])
                status = "excluded" if reasons else "eligible_component_input"
                if row["status"] != status or row["exclusion_reasons"] != reasons:
                    raise ReferenceError("domain_classification_mismatch")
                if reasons:
                    if row["pint_propagation_delay_seconds"] is not None:
                        raise ReferenceError("excluded_reference_not_null")
                    counts["excluded"] += 1
                    results.append(
                        dict(
                            id=row["id"],
                            cohort=cohort,
                            status="excluded",
                            reasons=reasons,
                            difference_seconds=None,
                        )
                    )
                    continue
                expected = -number(row["pint_propagation_delay_seconds"])
                candidate = solar_correction(row["radius_au"], row["cosine"])
                difference = abs(candidate - expected)
                counts["compared"] += 1
                counts["failed"] += int(difference > tolerance)
                maximum = max(maximum, difference)
                wrong = {
                    "wrong_sign": -candidate,
                    "omit_radial_normalization": solar_correction("1", row["cosine"]),
                }
                for name, value in wrong.items():
                    if abs(value - expected) > tolerance:
                        mutation[name]["detected"] += 1
                    else:
                        mutation[name]["undetected_ids"].append(row["id"])
                results.append(
                    dict(
                        id=row["id"],
                        cohort=cohort,
                        status="compared",
                        correction_seconds=str(candidate),
                        reference_correction_seconds=str(expected),
                        difference_seconds=str(difference),
                        passed=difference <= tolerance,
                    )
                )
            counts["max_difference_seconds"] = str(maximum)
            summaries[cohort] = counts
        # Model-to-model convention difference, not a physical uncertainty estimate.
        radial = [solar_correction(radius, "0") for radius in ("0.9", "1.1")]
        radial_max = max(abs(x) for x in radial)
    denominator = sum(s["compared"] for s in summaries.values())
    for values in mutation.values():
        values["denominator"] = denominator
        values["undetected"] = len(values["undetected_ids"])
    passed = all(s["failed"] == 0 and s["compared"] > 0 for s in summaries.values()) and all(
        v["detected"] > 0 for v in mutation.values()
    )
    return dict(
        schema_version="1.0",
        audit_id="source-reference-v1",
        passed=passed,
        pass_meaning="Supplied-input component agreement and domain accounting only",
        convention_id=CONVENTION["convention_id"],
        summaries=summaries,
        mutations=mutation,
        comparison_tolerance_seconds=str(tolerance),
        reference_qualification=(
            policy["qualification"]["component_status_if_pass"]
            if passed
            else "failed_component_comparison"
        ),
        full_reference_status="unqualified",
        physical_reference_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
        blockers=policy["qualification"]["blockers"],
        radial_vs_angular_max_over_declared_radius_seconds=str(radial_max),
        radial_difference_meaning="Convention difference 2GM/c^3 ln(R/au); not timing error",
        full_pint_timing_pipeline_executed=False,
        rows=results,
        manifest_sha256=sha(MANIFEST),
        implementation_sha256=sha(Path(__file__)),
        environment=dict(
            python=platform.python_version(),
            numeric_engine="stdlib Decimal, 70 digits",
            network="socket connections blocked",
            astronomy_imports_required=False,
        ),
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Source-reference audit must be offline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
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
            {
                k: result[k]
                for k in ("passed", "summaries", "full_reference_status", "observing_eligible")
            }
        )
    )
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
