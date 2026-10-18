"""Offline Mission 41 clock qualification audit, including an unsuccessful result.

A successful audit means the retained evidence and blocking decisions are
consistent. It never means an independent physical timing reference passed.
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
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/clock_reference_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/clock_reference_v1.json"
MANIFEST = ROOT / "validation/manifests/clock_reference_v1.json"
EXPECTED_MANIFEST_SHA256 = "901e8e323427ed0c15c3be66731c3e23ca241e170e003c25a868fd6f4e2eb3c7"
COLUMNS = (
    "astropy_site_seconds",
    "astropy_geocentric_seconds",
    "pint_default_seconds",
    "skyfield_geocentric_seconds",
    "erfa_utc_seconds",
    "erfa_ut1_seconds",
)
ROUTE_IDS = ("pint_default", "pint_ephemeris", "skyfield_geocentric", "erfa_explicit")


class ClockReferenceError(ValueError):
    pass


def number(value):
    if (
        not isinstance(value, str)
        or len(value) > 80
        or not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value)
    ):
        raise ClockReferenceError("finite_decimal_string_required")
    parsed = Decimal(value)
    if parsed.copy_abs() > Decimal("1e10"):
        raise ClockReferenceError("numeric_domain")
    return parsed


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    try:
        if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
            raise ClockReferenceError("manifest_checksum")
        manifest = json.loads(MANIFEST.read_text())
        for name, digest in manifest["files"].items():
            if sha(ROOT / name) != digest:
                raise ClockReferenceError("input_checksum")
        return (
            json.loads(POLICY.read_text()),
            json.loads(FIXTURE.read_text()),
            json.loads((ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text()),
            json.loads((ROOT / "validation/fixtures/source_reference_v1.json").read_text()),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ClockReferenceError("input_unavailable_or_invalid") from exc


def qualify_routes(policy, fixture):
    """Classify only these pinned, inspected routes; declarations cannot self-qualify."""
    if [r["id"] for r in policy["routes"]] != list(ROUTE_IDS):
        raise ClockReferenceError("route_inventory")
    if fixture["method_sha256"] != policy["source_method_sha256"]:
        raise ClockReferenceError("upstream_identity")
    if fixture["topo_default_inherited"] is not True:
        raise ClockReferenceError("pint_inheritance_changed")
    if fixture["skyfield_parameters"] != ["jd_tdb", "fraction_tdb"]:
        raise ClockReferenceError("skyfield_interface_changed")
    if fixture["ephemeris_probe"] != dict(
        outcome="unsupported",
        exception_type="NotImplementedError",
        message="",
        fallback_used=False,
        result=None,
    ):
        raise ClockReferenceError("ephemeris_outcome_changed_requalification_required")
    if (
        fixture["evidence_kind"] != "clock_route_diagnostics_not_independent_reference"
        or fixture["physical_clock_bound_seconds"] is not None
        or fixture["observing_eligible"] is not False
    ):
        raise ClockReferenceError("unsupported_evidence_claim")
    # These facts derive from the pinned source audit and executed dispatch probes.
    # Independence is an implementation distinction, not a package-name distinction.
    facts = [
        (True, True, False, ["same_astropy_erfa_backend"]),
        (False, None, None, ["installed_method_not_implemented"]),
        (True, False, True, ["geocentric_only", "different_clock_approximation"]),
        (True, True, False, ["same_erfa_backend"]),
    ]
    return [
        dict(
            id=route,
            executable=executable,
            matches_selected_site_clock_convention=matches,
            independent_of_candidate_clock_backend=independent,
            reference_uncertainty_established_for_domain=False,
            physical_reference_bound_seconds=None,
            qualified=False,
            reasons=[*reasons, "reference_uncertainty_unestablished"],
        )
        for route, (executable, matches, independent, reasons) in zip(ROUTE_IDS, facts, strict=True)
    ]


def validate_rows(fixture, historical):
    expected = {
        f"{date}_{s['name']}_{hour:02}": (f"{date}T{hour:02}:00:00", {**s, "datum": "WGS84"})
        for date in historical["dates"]
        for s in historical["sites"]
        for hour in historical["hours"]
    }
    rows = fixture["cases"]
    if len(rows) != 48 or len({r["id"] for r in rows}) != 48:
        raise ClockReferenceError("clock_denominator")
    if {r["id"] for r in rows} != set(expected):
        raise ClockReferenceError("clock_inventory")
    geocentric = {}
    for row in rows:
        if (row["utc"], row["site"]) != expected[row["id"]]:
            raise ClockReferenceError("clock_context")
        for key in COLUMNS:
            if abs(number(row[key])) > Decimal("0.01"):
                raise ClockReferenceError("clock_diagnostic_range")
        parts, site = row["tt_jd_parts"], row["site_arguments"]
        if len(parts) != 2 or len(site) != 3:
            raise ClockReferenceError("clock_argument_shape")
        for value in [
            *parts,
            *site,
            row["dut1_seconds"],
            row["utc_day_fraction"],
            row["ut1_day_fraction"],
        ]:
            number(value)
        calls = row["pint_dtdb_calls"]
        if len(calls) != 1 or len(calls[0]) != 6:
            raise ClockReferenceError("pint_dispatch_count_or_shape")
        args = calls[0]
        for value in args:
            number(value)
        # Astropy's day_frac uses a signed remainder; ERFA is periodic in UT.
        if (
            [number(v) for v in args[:2]] != [number(v) for v in parts]
            or [number(v) for v in args[3:]] != [number(v) for v in site]
            or float(args[2]) % 1 != float(row["utc_day_fraction"])
        ):
            raise ClockReferenceError("pint_dispatch_arguments")
        if not (
            0 <= number(row["utc_day_fraction"]) < 1 and 0 <= number(row["ut1_day_fraction"]) < 1
        ):
            raise ClockReferenceError("day_fraction_domain")
        geo = tuple(row[k] for k in ("astropy_geocentric_seconds", "skyfield_geocentric_seconds"))
        if row["utc"] in geocentric and geocentric[row["utc"]] != geo:
            raise ClockReferenceError("geocentric_site_dependence")
        geocentric[row["utc"]] = geo
    if len(geocentric) != 12:
        raise ClockReferenceError("geocentric_denominator")
    return rows


def blocked_combined_inventory(solar, historical):
    expected = {
        f"{date}_{s['name']}_{idx}_{hour}": (
            f"{date}T{hour:02}:00:00+00:00",
            s,
            target,
            idx,
        )
        for date in historical["dates"]
        for s in historical["sites"]
        for idx, target in enumerate(historical["targets"])
        for hour in historical["hours"]
    }
    rows = solar["historical"]
    if (
        len(rows) != 288
        or len({r["id"] for r in rows}) != 288
        or {r["id"] for r in rows} != set(expected)
    ):
        raise ClockReferenceError("combined_inventory")
    output = []
    for row in rows:
        if (row["utc"], row["site"], row["target"], row["target_index"]) != expected[row["id"]]:
            raise ClockReferenceError("combined_context")
        radius, mu = number(row["radius_au"]), number(row["cosine"])
        reasons = []
        if not Decimal("0.9") <= radius <= Decimal("1.1"):
            reasons.append("radius_outside_component_domain")
        if not -1 <= mu <= Decimal("0.8"):
            reasons.append("solar_elongation_outside_component_domain")
        expected_status = "excluded" if reasons else "eligible_component_input"
        if row["status"] != expected_status or row["exclusion_reasons"] != reasons:
            raise ClockReferenceError("solar_domain_evidence")
        output.append(
            dict(
                id=row["id"],
                status="blocked_before_combined_evaluation",
                clock_case_id=row["id"].rsplit("_", 2)[0] + "_" + row["id"].rsplit("_", 1)[1],
                solar_component_eligible=not reasons,
                reasons=["no_qualified_independent_matched_clock_reference", *reasons],
                reference_coordinate_jd=None,
                candidate_coordinate_jd=None,
                residual_seconds=None,
                observing_eligible=False,
            )
        )
    return output


def evaluate_inputs(policy, fixture, historical, solar):
    if (
        policy["convention_id"] != solar["convention_id"]
        or policy["convention_id"] != "astroscope-tdb-solar-au-v1"
    ):
        raise ClockReferenceError("convention_mismatch")
    routes = qualify_routes(policy, fixture)
    rows = validate_rows(fixture, historical)
    with localcontext(Context(prec=70)):
        tolerance = number(
            policy["diagnostic_design"]["shared_backend_reproduction_tolerance_seconds"]
        )
        if tolerance != Decimal("1e-12"):
            raise ClockReferenceError("frozen_tolerance_changed")
        differences = []
        unique_geo = {}
        for row in rows:
            values = {key: number(row[key]) for key in COLUMNS}
            d = dict(
                pint_minus_astropy=values["pint_default_seconds"] - values["astropy_site_seconds"],
                explicit_utc_minus_astropy=values["erfa_utc_seconds"]
                - values["astropy_site_seconds"],
                skyfield_minus_astropy_geocentre=(
                    values["skyfield_geocentric_seconds"] - values["astropy_geocentric_seconds"]
                ),
                site_minus_geocentre=values["astropy_site_seconds"]
                - values["astropy_geocentric_seconds"],
                ut1_minus_utc=values["erfa_ut1_seconds"] - values["erfa_utc_seconds"],
            )
            unique_geo[row["utc"]] = d["skyfield_minus_astropy_geocentre"]
            passed = all(
                abs(d[key]) <= tolerance
                for key in (
                    "pint_minus_astropy",
                    "explicit_utc_minus_astropy",
                )
            )
            differences.append(
                dict(
                    id=row["id"],
                    shared_backend_controls_passed=passed,
                    differences_seconds={k: str(v) for k, v in d.items()},
                )
            )
        summaries = {}
        for key in differences[0]["differences_seconds"]:
            values = (
                list(unique_geo.values())
                if key == "skyfield_minus_astropy_geocentre"
                else [number(r["differences_seconds"][key]) for r in differences]
            )
            summaries[key] = dict(
                count=len(values),
                minimum_seconds=str(min(values)),
                maximum_seconds=str(max(values)),
                maximum_absolute_seconds=str(max(map(abs, values))),
                interpretation=(
                    "shared_backend_reproduction_only"
                    if key
                    in (
                        "pint_minus_astropy",
                        "explicit_utc_minus_astropy",
                    )
                    else "diagnostic_difference_no_accuracy_threshold"
                ),
            )
    combined = blocked_combined_inventory(solar, historical)
    if {r["clock_case_id"] for r in combined} != {r["id"] for r in rows}:
        raise ClockReferenceError("clock_combined_mapping")
    return dict(
        schema_version="1.0",
        benchmark_id="clock-reference-qualification-v1",
        audit_passed=all(r["shared_backend_controls_passed"] for r in differences),
        clock_qualification_outcome="unsuccessful",
        full_reference_status="unqualified",
        qualified_route_count=0,
        routes=routes,
        diagnostics=summaries,
        diagnostic_rows=differences,
        combined_counts=dict(
            candidates=len(combined),
            executed=0,
            blocked=len(combined),
            solar_eligible=sum(r["solar_component_eligible"] for r in combined),
            solar_excluded=sum(not r["solar_component_eligible"] for r in combined),
        ),
        combined_cases=combined,
        physical_clock_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
        next_gate=policy["next_gate_if_unsuccessful"],
    )


def evaluate():
    result = evaluate_inputs(*load_inputs())
    result.update(
        manifest_sha256=sha(MANIFEST),
        policy_sha256=sha(POLICY),
        fixture_sha256=sha(FIXTURE),
        python_version=platform.python_version(),
    )
    return result


def deny_network(*args, **kwargs):
    raise RuntimeError("Clock qualification evaluation must be offline")


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
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
        ).strip()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "audit_passed",
                    "clock_qualification_outcome",
                    "combined_counts",
                    "observing_eligible",
                )
            }
        )
    )
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
