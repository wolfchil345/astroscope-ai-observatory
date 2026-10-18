"""Offline site-clock surrogate and uncertainty audit; no production eligibility."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import socket
import subprocess
from datetime import date
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/site_clock_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/site_clock_v1.json"
MANIFEST = ROOT / "validation/manifests/site_clock_v1.json"
EXPECTED_MANIFEST_SHA256 = "58fcf843f88f16f23f0e9c694a029ae61fdc9e531532d6f77241384d4aee8579"
BUDGET_IDS = (
    "geocentric_time_ephemeris",
    "earth_velocity",
    "station_coordinates",
    "earth_orientation",
    "frame_scale_mapping",
    "higher_order_remainder",
)


class SiteClockError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise SiteClockError(reason)


def number(value):
    require(
        isinstance(value, str)
        and len(value) <= 100
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value),
        "finite_decimal_string_required",
    )
    n = Decimal(value)
    require(n.copy_abs() <= Decimal("1e12"), "numeric_domain")
    return n


def vector(values):
    require(isinstance(values, list) and len(values) == 3, "vector_shape")
    return [number(v) for v in values]


def dot(a, b):
    return sum((x * y for x, y in zip(a, b, strict=True)), Decimal(0))


def norm(a):
    return dot(a, a).sqrt()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    require(sha(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest_checksum")
    for name, digest in json.loads(MANIFEST.read_text())["files"].items():
        require(sha(ROOT / name) == digest, "input_checksum")
    names = [
        POLICY,
        FIXTURE,
        ROOT / "validation/manifests/observer_arrival_policy_v1.json",
        ROOT / "validation/fixtures/time_ephemeris_v1.json",
        ROOT / "validation/fixtures/clock_reference_v1.json",
        ROOT / "validation/results/clock_reference_reference_run.json",
        ROOT / "validation/fixtures/solar_lunar_eop_v1.json",
    ]
    return [json.loads(p.read_text()) for p in names]


def conditional_sensitivity(example):
    """Conditional norm inequalities, not measured uncertainty or a total budget."""
    with localcontext(Context(prec=70)):
        v, r, dr, dv, potential = [
            number(example[k]) for k in ("V_m_s", "R_m", "delta_r_m", "delta_v_m_s", "U_m2_s2")
        ]
        require(all(x >= 0 for x in (v, r, dr, dv, potential)), "negative_bound_input")
        c = Decimal(299792458)
        return dict(
            status="hypothetical_inputs_not_established_reference_uncertainty",
            vector_perturbation_envelope_seconds=str((v * dr + r * dv + dv * dr) / c**2),
            c4_station_term_envelope_seconds=str((3 * potential + v**2 / 2) * v * r / c**4),
            physical_total_bound_seconds=None,
            observing_eligible=False,
        )


def validate_solution(solution, tt):
    trace = solution["trace"]
    require(1 <= len(trace) <= 8, "trace_count")
    previous = Decimal(0)
    for index, row in enumerate(trace):
        delta, d, s, residual, following = [
            number(row[k])
            for k in (
                "delta_seconds",
                "tt_minus_tdb_seconds",
                "site_term_seconds",
                "residual_seconds",
                "next_delta_seconds",
            )
        ]
        require(delta == previous, "trace_continuity")
        require(abs(delta + d - s - residual) <= Decimal("1e-18"), "mapping_sign_or_algebra")
        require(abs(following - (s - d)) <= Decimal("1e-18"), "mapping_update")
        expected_et = format(float(tt + Decimal.from_float(float(delta))), ".17g")
        require(row["et_seconds"] == expected_et, "tdb_argument")
        if index < len(trace) - 1:
            require(abs(residual) > Decimal("1e-15"), "late_stop")
        previous = following
    converged = abs(number(trace[-1]["residual_seconds"])) <= Decimal("1e-15")
    require(solution["converged"] is converged, "false_convergence")
    require(converged or len(trace) == 8, "early_failure")
    require(
        number(solution["delta_seconds"])
        == number(trace[-1]["delta_seconds"] if converged else trace[-1]["next_delta_seconds"]),
        "solution_trace",
    )
    return converged


def live_candidate(historical):
    import astropy.units as u
    from astropy.coordinates import EarthLocation
    from astropy.time import Time

    from validation.observer_arrival_model import frozen_converter

    output = {}
    with frozen_converter():
        for day in historical["dates"]:
            for site in historical["sites"]:
                loc = EarthLocation.from_geodetic(
                    site["longitude_deg"] * u.deg,
                    site["latitude_deg"] * u.deg,
                    site["elevation_m"] * u.m,
                )
                for hour in historical["hours"]:
                    t = Time(f"{day}T{hour:02}:00:00", scale="utc", location=loc).tt
                    geo = Time(t.jd1, t.jd2, format="jd", scale="tt")
                    output[f"{day}_{site['name']}_{hour:02}"] = dict(
                        site=format(float(t.delta_tdb_tt), ".17g"),
                        geocentre=format(float(geo.delta_tdb_tt), ".17g"),
                    )
    return output


def summarize(values):
    return dict(
        count=len(values),
        minimum_seconds=str(min(values)),
        maximum_seconds=str(max(values)),
        maximum_absolute_seconds=str(max(map(abs, values))),
        interpretation="diagnostic_model_difference_not_physical_error_bound",
    )


def evaluate_inputs(policy, fixture, historical, geo_fixture, archive, prior, eop, candidates):
    with localcontext(Context(prec=70)):
        return _evaluate(policy, fixture, historical, geo_fixture, archive, prior, eop, candidates)


def _evaluate(policy, fixture, historical, geo_fixture, archive, prior, eop, candidates):
    require(
        policy["research_model_id"]
        == fixture["model_id"]
        == "de440t-skyfield-gcrs-c2-site-surrogate-v1",
        "model_identity",
    )
    require(
        policy["selected_arrival_convention_id"] == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    require(number(policy["model"]["c_m_s"]) == 299792458, "speed_of_light")
    require(
        fixture["units"] == dict(position="m", velocity="m/s", clock="s")
        and fixture["position_frame"] == "GCRS_leading_order_surrogate_not_scaled_BCRS_difference",
        "frame_or_units",
    )
    require(
        fixture["forbidden_imports"] == []
        and fixture["approximate_skyfield_clock"] == "disabled_with_raising_patch",
        "reference_boundary",
    )
    require(
        fixture["kernel_sha256"] == policy["kernel_sha256"]
        and fixture["packages"] == policy["reference_packages"]
        and fixture["cspice_toolkit"] == "CSPICE_N0067",
        "reference_provenance",
    )
    require(
        fixture["eop_formal_errors_are_hard_bounds"] is False
        and fixture["observed_dx_dy_applied"] is False,
        "eop_claim",
    )
    require(
        fixture["physical_site_clock_bound_seconds"] is None
        and fixture["observing_eligible"] is False,
        "unsupported_qualification",
    )
    for name, value in dict(
        solver_residual_seconds="1e-15",
        supplied_vector_arithmetic_seconds="1e-15",
        velocity_reader_agreement_m_s="1e-6",
        geocentre_reproduction_seconds="1e-12",
        candidate_archival_reproduction_seconds="1e-12",
    ).items():
        require(number(policy["design"][name]) == Decimal(value), "frozen_threshold")
    require(policy["design"]["solver_max_iterations"] == 8, "frozen_iterations")
    require(
        [b["id"] for b in policy["physical_budget_components"]] == list(BUDGET_IDS),
        "budget_inventory",
    )
    # This closed experiment has no approved complete physical bound. A new
    # declaration or a hypothetical norm input cannot promote it to one.
    require(
        all(b["hard_bound_seconds"] is None for b in policy["physical_budget_components"]),
        "unevidenced_bound_requires_requalification",
    )
    require(
        policy["gate"]
        == dict(
            site_reference_status="unqualified",
            physical_site_clock_bound_seconds=None,
            physical_arrival_bound_seconds=None,
            observing_eligible=False,
            combined_executed=0,
            combined_blocked=288,
        ),
        "gate_changed",
    )

    expected_mjd = set()
    for day in historical["dates"]:
        mjd = (date.fromisoformat(day) - date(1858, 11, 17)).days
        expected_mjd.update((Decimal(mjd), Decimal(mjd + 1)))
    records = fixture["eop_records"]
    require(
        len(records) == 8 and {number(r["mjd"]) for r in records} == expected_mjd, "eop_inventory"
    )
    require(
        fixture["eop_source_sha256"] == policy["eop_evidence"]["source_sha256"], "eop_provenance"
    )
    for row in records:
        original = next(r for r in eop["rows"] if Decimal(str(r["MJD"])) == number(row["mjd"]))
        for field, old in (
            ("xp_arcsec", "PM_x"),
            ("yp_arcsec", "PM_y"),
            ("dut1_seconds", "UT1_UTC"),
        ):
            require(number(row[field]) == Decimal(str(original[old])), "eop_mean_changed")
        require(
            set(row["formal_errors"])
            == {"xp_arcsec", "yp_arcsec", "dut1_seconds", "dx_arcsec", "dy_arcsec"},
            "formal_error_inventory",
        )
        require(all(number(x) >= 0 for x in row["formal_errors"].values()), "negative_formal_error")
        number(row["dx_arcsec"])
        number(row["dy_arcsec"])

    geos = {r["id"]: r for r in geo_fixture["cases"] if r["kind"] == "historical"}
    controls = fixture["geocentric_controls"]
    require(len(controls) == 12 and {r["id"] for r in controls} == set(geos), "control_inventory")
    control_checks = []
    for control in controls:
        g = geos[control["id"]]
        solution = control["solution"]
        require(
            all(number(r["site_term_seconds"]) == 0 for r in solution["trace"]),
            "nonzero_geocentre_site_term",
        )
        control_checks.append(
            validate_solution(solution, number(g["tt_seconds_from_j2000"]))
            and abs(number(solution["delta_seconds"]) - number(g["cspice"]["delta_seconds"]))
            <= Decimal("1e-12")
        )
    archived = {r["id"]: r for r in archive["cases"]}
    cases = fixture["cases"]
    require(
        len(cases) == 48
        and len({r["id"] for r in cases}) == 48
        and {r["id"] for r in cases} == set(archived) == set(candidates),
        "site_inventory",
    )
    output = []
    for row in cases:
        old = archived[row["id"]]
        require(row["site"] == old["site"] and row["utc"] == old["utc"], "site_context")
        require(row["geocentric_id"] == row["utc"][:10] + "_" + row["utc"][11:13], "geo_mapping")
        g = geos[row["geocentric_id"]]
        require(row["tt_seconds_from_j2000"] == g["tt_seconds_from_j2000"], "tt_context")
        solved = validate_solution(row["solution"], number(row["tt_seconds_from_j2000"]))
        velocity, other, position = map(
            vector,
            (row["earth_velocity_m_s"], row["jplephem_velocity_m_s"], row["site_position_gcrs_m"]),
        )
        term = dot(velocity, position) / Decimal(299792458) ** 2
        supplied_term = number(row["solution"]["trace"][-1]["site_term_seconds"])
        velocity_error = norm([a - b for a, b in zip(velocity, other, strict=True)])
        arithmetic = abs(term - supplied_term) <= Decimal("1e-15")
        variations = {}
        require(set(row["variants"]) == {"utc_as_ut1", "no_polar_motion"}, "variant_inventory")
        for name, variant in row["variants"].items():
            check = dot(velocity, vector(variant["position_m"])) / Decimal(299792458) ** 2
            arithmetic &= abs(check - number(variant["site_term_seconds"])) <= Decimal("1e-15")
            variations[name] = str(number(variant["site_term_seconds"]) - supplied_term)
        csite, cgeo = (
            number(candidates[row["id"]]["site"]),
            number(candidates[row["id"]]["geocentre"]),
        )
        candidate_reproduced = abs(csite - number(old["astropy_site_seconds"])) <= Decimal(
            "1e-12"
        ) and abs(cgeo - number(old["astropy_geocentric_seconds"])) <= Decimal("1e-12")
        reference = number(row["solution"]["delta_seconds"])
        geocentric = number(g["cspice"]["delta_seconds"])
        output.append(
            dict(
                id=row["id"],
                geocentric_id=row["geocentric_id"],
                numerical_checks_passed=solved
                and arithmetic
                and velocity_error <= Decimal("1e-6")
                and candidate_reproduced,
                site_reference_status="unqualified_surrogate",
                surrogate_clock_seconds=str(reference),
                surrogate_increment_seconds=str(reference - geocentric),
                candidate_minus_surrogate_seconds=str(csite - reference),
                geocentric_model_difference_seconds=str(cgeo - geocentric),
                site_increment_difference_seconds=str((csite - cgeo) - (reference - geocentric)),
                variant_minus_nominal_site_term_seconds=variations,
                velocity_reader_difference_m_s=str(velocity_error),
                vector_arithmetic_difference_seconds=str(term - supplied_term),
                max_et_argument_quantization_seconds=str(
                    max(
                        abs(
                            Decimal.from_float(float(t["et_seconds"]))
                            - number(row["tt_seconds_from_j2000"])
                            - Decimal.from_float(float(t["delta_seconds"]))
                        )
                        for t in row["solution"]["trace"]
                    )
                ),
                nominal_radius_m=str(norm(position)),
                nominal_speed_m_s=str(norm(velocity)),
                observing_eligible=False,
            )
        )
    require(
        prior["combined_counts"]
        == dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48),
        "combined_gate",
    )
    return dict(
        schema_version="1.0",
        benchmark_id="site-clock-mapping-qualification-v1",
        audit_passed=all(control_checks) and all(r["numerical_checks_passed"] for r in output),
        model_id=fixture["model_id"],
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        site_reference_status="unqualified",
        qualification_outcome="incomplete_evidence_retained",
        diagnostics={
            k: summarize([number(r[k]) for r in output])
            for k in ("candidate_minus_surrogate_seconds", "site_increment_difference_seconds")
        },
        cases=output,
        geocentric_control_count=len(controls),
        geocentric_controls_passed=all(control_checks),
        formal_eop_record_count=len(records),
        formal_errors_are_hard_bounds=False,
        physical_budget_components=policy["physical_budget_components"],
        missing_bound_components=list(BUDGET_IDS),
        conditional_sensitivity=conditional_sensitivity(policy["conditional_sensitivity_example"]),
        combined_counts=prior["combined_counts"],
        combined_inventory_source="validation/results/clock_reference_reference_run.json",
        physical_site_clock_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Site-clock audit must be offline")


def evaluate():
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        inputs = load_inputs()
        result = evaluate_inputs(*inputs, live_candidate(inputs[2]))
    result.update(
        manifest_sha256=sha(MANIFEST),
        fixture_sha256=sha(FIXTURE),
        policy_sha256=sha(POLICY),
        python_version=platform.python_version(),
        candidate_packages={
            p: importlib.metadata.version(p) for p in ("astropy", "numpy", "pyerfa")
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
        json.dumps({k: result[k] for k in ("audit_passed", "diagnostics", "site_reference_status")})
    )
    if not result["audit_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
