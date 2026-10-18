"""Offline integrated geocentric clock audit; never a production converter.

CI checks derived reference evidence and evaluates the live Astropy geocentric
candidate. Raw DE440t is needed only to regenerate the independently made fixture.
"""

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
from datetime import datetime
from decimal import Context, Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "validation/manifests/time_ephemeris_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/time_ephemeris_v1.json"
MANIFEST = ROOT / "validation/manifests/time_ephemeris_v1.json"
EXPECTED_MANIFEST_SHA256 = "0f185bd28ed24bfa30ea71dc0743b1fb9f6110ad602f92963491e2a8ab386519"


class TimeEphemerisError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise TimeEphemerisError(reason)


def number(value):
    require(
        isinstance(value, str)
        and len(value) <= 160
        and re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d{1,2})?", value),
        "finite_decimal_string_required",
    )
    result = Decimal(value)
    require(abs(result) <= Decimal("1e12"), "numeric_domain")
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    try:
        require(sha(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest_checksum")
        manifest = json.loads(MANIFEST.read_text())
        for name, digest in manifest["files"].items():
            require(sha(ROOT / name) == digest, "input_checksum")
        return (
            json.loads(POLICY.read_text()),
            json.loads(FIXTURE.read_text()),
            json.loads((ROOT / "validation/manifests/observer_arrival_policy_v1.json").read_text()),
            json.loads((ROOT / "validation/fixtures/clock_reference_v1.json").read_text()),
            json.loads(
                (ROOT / "validation/results/clock_reference_reference_run.json").read_text()
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise TimeEphemerisError("input_unavailable_or_invalid") from exc


def expected_samples(policy, historical):
    rows = []
    for day in historical["dates"]:
        require(day.startswith("2024-"), "historical_domain")
        for hour in historical["hours"]:
            utc = f"{day}T{hour:02}:00:00"
            elapsed = datetime.fromisoformat(utc) - datetime(2000, 1, 1, 12)
            seconds = Decimal(elapsed.days * 86400 + elapsed.seconds) + Decimal("69.184")
            rows.append(
                dict(
                    id=f"{day}_{hour:02}",
                    utc=utc,
                    kind="historical",
                    tt_seconds_from_j2000=str(seconds),
                )
            )
    for probe in policy["sample_design"]["tt_epoch_probes"]:
        rows.append(
            dict(
                id=probe["id"],
                utc=None,
                kind="tt_epoch_probe",
                tt_seconds_from_j2000=str((number(probe["tt_jd"]) - 2451545) * 86400),
            )
        )
    require(len(rows) == 14 and len({r["id"] for r in rows}) == 14, "expected_inventory")
    return rows


def validate_trace(result, reader, tt, contract):
    method = {"cspice": "fixed_point", "jplephem": "newton"}[reader]
    require(result["method"] == method, "solver_method")
    trace = result["trace"]
    require(1 <= len(trace) <= 8, "trace_length")
    previous_next = Decimal(0)
    max_quantization = Decimal(0)
    for index, row in enumerate(trace):
        delta = number(row["delta_seconds"])
        value = number(row["tt_minus_tdb_seconds"])
        derivative = number(row["derivative_seconds_per_second"])
        residual = number(row["equation_residual_seconds"])
        next_delta = number(row["next_delta_seconds"])
        require(delta == previous_next, "trace_continuity")
        require(abs(residual - (delta + value)) <= Decimal("1e-18"), "equation_sign")
        require(abs(1 + derivative) > Decimal("0.5"), "singular_clock_mapping")
        expected_next = -value if reader == "cspice" else delta - (delta + value) / (1 + derivative)
        require(abs(next_delta - expected_next) <= Decimal("1e-18"), "solver_update")
        # The generator added the exact binary64 delta, not its display string.
        requested = tt + Decimal.from_float(float(delta))
        if reader == "cspice":
            argument = number(row["argument_et_seconds"])
            expected_argument = Decimal.from_float(float(requested))
            require(argument == expected_argument, "tdb_argument")
        else:
            parts = row["argument_jd_parts"]
            require(isinstance(parts, list) and len(parts) == 2, "jd_parts")
            days, remainder = divmod(requested, Decimal(86400))
            require(
                [number(p) for p in parts]
                == [
                    Decimal.from_float(float(2451545 + days)),
                    Decimal.from_float(float(remainder / 86400)),
                ],
                "tdb_argument",
            )
            argument = (number(parts[0]) - 2451545 + number(parts[1])) * 86400
        quantization = number(row["argument_quantization_seconds"])
        require(
            abs(argument - requested - quantization) <= Decimal("1e-55"), "argument_quantization"
        )
        max_quantization = max(max_quantization, abs(quantization))
        if index < len(trace) - 1:
            require(abs(residual) > number(contract["convergence_seconds"]), "late_stop")
        previous_next = next_delta
    converged = abs(number(trace[-1]["equation_residual_seconds"])) <= Decimal("1e-15")
    require(result["converged"] is converged, "convergence_claim")
    require(
        number(result["delta_seconds"])
        == number(trace[-1]["delta_seconds"] if converged else trace[-1]["next_delta_seconds"]),
        "solution_trace",
    )
    return converged, max_quantization


def candidate_clock(tt):
    """Live candidate only; never called by the independent fixture generator."""
    from astropy.time import Time
    from astropy.utils import iers

    days, remainder = divmod(tt, Decimal(86400))
    with iers.conf.set_temp("auto_download", False):
        time = Time(float(2451545 + days), float(remainder / 86400), format="jd", scale="tt")
        result = float(time.delta_tdb_tt)
    require(math.isfinite(result), "candidate_nonfinite")
    return Decimal(format(result, ".17g"))


def summary(values, interpretation):
    return dict(
        count=len(values),
        minimum_seconds=str(min(values)),
        maximum_seconds=str(max(values)),
        maximum_absolute_seconds=str(max(map(abs, values))),
        interpretation=interpretation,
    )


def evaluate_inputs(policy, fixture, historical, archived, prior, candidate=candidate_clock):
    with localcontext(Context(prec=70)):
        return _evaluate(policy, fixture, historical, archived, prior, candidate)


def _evaluate(policy, fixture, historical, archived, prior, candidate):
    require(
        policy["reference_model_id"] == fixture["model_id"] == "de440t-geocentric-tt-tdb-v1",
        "reference_model",
    )
    require(
        policy["selected_arrival_convention_id"] == "astroscope-tdb-solar-au-v1",
        "selected_convention",
    )
    kernel = policy["kernel"]
    for key, expected in dict(
        quantity="TT_minus_TDB", units="seconds", argument_scale="TDB", origin="geocentre"
    ).items():
        require(kernel[key] == fixture[key] == expected, "kernel_convention")
    require(
        fixture["kernel_sha256"] == kernel["sha256"]
        and fixture["kernel_size_bytes"] == kernel["size_bytes"],
        "kernel_identity",
    )
    require(
        all(fixture["segment"][k] == kernel[k] for k in fixture["segment"])
        and fixture["segment"]["target"] == 1000000001
        and fixture["segment"]["center"] == 1000000000,
        "segment_identity",
    )
    require(
        fixture["packages"] == policy["reference_packages"]
        and fixture["cspice_toolkit"] == "CSPICE_N0067",
        "reference_environment",
    )
    require(
        fixture["forbidden_imports"] == []
        and fixture["same_kernel_for_both_readers"] is True
        and fixture["raw_coefficients_vendored"] is False,
        "independence_boundary",
    )
    require(
        fixture["physical_geocentric_clock_bound_seconds"] is None
        and fixture["observing_eligible"] is False,
        "unsupported_reference_claim",
    )
    contract = policy["reader_contract"]
    for key, expected in dict(
        convergence_seconds="1e-15",
        offset_agreement_seconds="1e-12",
        derivative_agreement_seconds_per_second="1e-15",
        equation_residual_seconds="1e-15",
        historical_tt_input_agreement_seconds="1e-9",
    ).items():
        require(number(contract[key]) == Decimal(expected), "frozen_tolerance")
    require(contract["max_iterations"] == 8, "frozen_iterations")
    require(len(fixture["cases"]) == 14, "sample_count")
    rows = []
    for row, expected in zip(fixture["cases"], expected_samples(policy, historical), strict=True):
        require(all(row[k] == expected[k] for k in expected), "sample_context")
        tt = number(row["tt_seconds_from_j2000"])
        passed, quantization = [], {}
        for reader in ("cspice", "jplephem"):
            converged, q = validate_trace(row[reader], reader, tt, contract)
            passed.append(converged)
            quantization[reader] = str(q)
        primary, secondary = row["cspice"], row["jplephem"]
        delta = number(primary["delta_seconds"])
        offset_difference = number(secondary["delta_seconds"]) - delta
        derivative_difference = number(
            secondary["trace"][-1]["derivative_seconds_per_second"]
        ) - number(primary["trace"][-1]["derivative_seconds_per_second"])
        passed += [
            abs(offset_difference) <= Decimal("1e-12"),
            abs(derivative_difference) <= Decimal("1e-15"),
        ]
        current = candidate(tt)
        require(isinstance(current, Decimal) and current.is_finite(), "candidate_nonfinite")
        archival_difference = None
        if row["kind"] == "historical":
            matches = [r for r in archived["cases"] if r["utc"] == row["utc"]]
            require(
                len(matches) == 4 and len({r["astropy_geocentric_seconds"] for r in matches}) == 1,
                "historical_geocentre_inventory",
            )
            for old in matches:
                jd1, jd2 = map(number, old["tt_jd_parts"])
                require(
                    abs((jd1 - 2451545 + jd2) * 86400 - tt) <= Decimal("1e-9"),
                    "historical_tt_input",
                )
            archival_difference = str(current - number(matches[0]["astropy_geocentric_seconds"]))
        rows.append(
            dict(
                **expected,
                numerical_checks_passed=all(passed),
                reference_tdb_minus_tt_seconds=str(delta),
                candidate_tdb_minus_tt_seconds=str(current),
                candidate_minus_reference_seconds=str(current - delta),
                jplephem_minus_cspice_seconds=str(offset_difference),
                reader_derivative_difference_seconds_per_second=str(derivative_difference),
                candidate_minus_m41_archived_seconds=archival_difference,
                max_argument_quantization_seconds=quantization,
                iterations={k: len(row[k]["trace"]) for k in ("cspice", "jplephem")},
            )
        )
    require(
        prior["combined_counts"]
        == dict(candidates=288, executed=0, blocked=288, solar_eligible=240, solar_excluded=48)
        and len(prior["combined_cases"]) == 288
        and prior["observing_eligible"] is False,
        "prior_combined_gate",
    )
    site_rows = [
        dict(
            id=r["id"],
            geocentric_case_id=r["utc"][:10] + "_" + r["utc"][11:13],
            status="blocked_site_mapping_and_uncertainty",
            observing_eligible=False,
        )
        for r in archived["cases"]
    ]
    require(len(site_rows) == 48 and len({r["id"] for r in site_rows}) == 48, "site_inventory")
    return dict(
        schema_version="1.0",
        benchmark_id="time-ephemeris-clock-mapping-v1",
        audit_passed=all(r["numerical_checks_passed"] for r in rows),
        reference_model_id=fixture["model_id"],
        selected_arrival_convention_id=policy["selected_arrival_convention_id"],
        geocentric_model_status="independent_integrated_model_evaluated_not_accuracy_qualified",
        full_reference_status="unqualified",
        same_kernel_reader_check=True,
        diagnostics=dict(
            historical_candidate_minus_reference=summary(
                [number(r["candidate_minus_reference_seconds"]) for r in rows[:12]],
                "model_difference_no_physical_accuracy_threshold",
            ),
            epoch_probe_candidate_minus_reference=summary(
                [number(r["candidate_minus_reference_seconds"]) for r in rows[12:]],
                "normalization_probes_no_fitted_offset",
            ),
            reader_offset_difference=summary(
                [number(r["jplephem_minus_cspice_seconds"]) for r in rows],
                "shared_kernel_interpolation_and_mapping_check_only",
            ),
        ),
        cases=rows,
        site_mapping_cases=site_rows,
        combined_counts=prior["combined_counts"],
        combined_inventory_source="validation/results/clock_reference_reference_run.json",
        physical_geocentric_clock_bound_seconds=None,
        physical_site_clock_bound_seconds=None,
        physical_arrival_bound_seconds=None,
        observing_eligible=False,
        next_gate=policy["next_gate"],
    )


def deny_network(*args, **kwargs):
    raise RuntimeError("Time-ephemeris audit must be offline")


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
