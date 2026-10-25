"""Mission 57: source-derived phase-bin trace, independent bounds and causal controls.

The bin mapping diagnoses Astropy 8.0.2 bls.c (BSD-3-Clause), credited by the
policy's pinned source URL/hash. It is explicitly not an independent oracle.
No upstream code is patched and no production search is changed.
"""

import argparse
import importlib.metadata
import json
import math
import os
import platform
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from astropy.timeseries import BoxLeastSquares
from astropy.timeseries.periodograms.bls import methods

from validation.celestial_coordinates import sha
from validation.light_curve_campaign import ROOT, git, load_inputs, processed
from validation.light_curve_references import exact_box_snr

POLICY = "validation/manifests/bls_discrepancy_policy_v1.json"
BASELINE = "validation/results/light_curve_campaign_reference_run.json"


def weighted_fit(y, errors, membership):
    """Direct two-level fit; signed depth/SNR retained, no detection claim."""
    w = 1 / np.asarray(errors, dtype=float) ** 2
    y = np.asarray(y, dtype=float) - np.median(y)
    counts = np.asarray(membership, dtype=int)
    if np.any((counts < 0) | (counts > 1)):
        raise ValueError("Membership must be a partition of observations")
    inside = counts.astype(bool)
    wi, wo = w[inside].sum(), w[~inside].sum()
    if wi == 0 or wo == 0:
        return None
    depth = np.average(y[~inside], weights=w[~inside]) - np.average(y[inside], weights=w[inside])
    error = math.sqrt(1 / wi + 1 / wo)
    return {
        "depth": float(depth),
        "depth_error": error,
        "snr": float(depth / error),
        "indices": np.flatnonzero(inside).tolist(),
    }


def bin_membership(times, period, durations, oversample, start_bin, duration, repaired=False):
    """Map bins to original rows, either legacy padding or a controlled intervention.

    Repaired padding preserves the final bin and appends enough bins for the
    longest duration. It still quantizes the circle and is NOT a proposed fix.
    """
    t = np.asarray(times)
    width = min(durations) / oversample
    bins_per_period = math.ceil(period / width)
    # Match the explicit floor/wrap operation in the pinned C implementation.
    elapsed = t - t.min()
    phase = elapsed - period * np.floor(elapsed / period)
    assignment = (phase / width).astype(int) + 1
    max_duration_bins = int(math.floor(max(durations) / width + 0.5))
    pad = max_duration_bins if repaired else oversample
    bins = [np.flatnonzero(assignment == i).tolist() for i in range(bins_per_period + pad + 1)]
    offset = bins_per_period if repaired else bins_per_period - 1
    for j in range(1, pad + 1):
        bins[offset + j] = bins[j].copy()
    length = int(math.floor(duration / width + 0.5))
    ids = [i for bucket in bins[start_bin + 1 : start_bin + length + 1] for i in bucket]
    counts = np.bincount(ids, minlength=len(t))
    return counts, {
        "bin_width": width,
        "bins_per_period": bins_per_period,
        "overwritten_original_indices": np.flatnonzero(assignment == bins_per_period).tolist(),
    }


def trace(times, values, errors, period, durations, oversample, result):
    width = min(durations) / oversample
    duration = float(result.duration[0])
    center = float(result.transit_time[0]) - min(times)
    length = int(math.floor(duration / width + 0.5))
    limit = math.ceil(period / width) + oversample - length
    starts = [
        n
        for n in range(limit + 1)
        if math.isclose((n * width + 0.5 * duration) % period, center, abs_tol=1e-10, rel_tol=0)
    ]
    if len(starts) != 1:
        raise ValueError(f"Ambiguous or missing source bin: {starts}")
    n = starts[0]
    counts, meta = bin_membership(times, period, durations, oversample, n, duration)
    repaired, _ = bin_membership(times, period, durations, oversample, n, duration, True)
    physical = (
        np.abs(
            (np.asarray(times) - float(result.transit_time[0]) + 0.5 * period) % period
            - 0.5 * period
        )
        < 0.5 * duration
    )
    return {
        "start_bin": n,
        **meta,
        "legacy_fit": weighted_fit(values, errors, counts),
        "padding_intervention_fit": weighted_fit(values, errors, repaired),
        "physical_candidate_fit": weighted_fit(values, errors, physical),
        "legacy_vs_physical_changed_indices": np.flatnonzero(counts != physical).tolist(),
        "legacy_vs_intervention_changed_indices": np.flatnonzero(counts != repaired).tolist(),
    }


def measure(t, y, e, period, durations, oversample, policy):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = BoxLeastSquares(t, y, dy=e).power(
            [period], durations, oversample=oversample, objective="snr", method="fast"
        )
        detail = trace(t, y, e, period, durations, oversample, result)
    bound = exact_box_snr(t, y, e, period, float(result.duration[0]))
    snr = float(result.depth_snr[0])
    error = abs(snr - detail["legacy_fit"]["snr"])
    actual = detail["physical_candidate_fit"]
    return {
        "oversample": oversample,
        "period": period,
        "duration": float(result.duration[0]),
        "transit_time": float(result.transit_time[0]),
        "fast_snr": snr,
        "independent_max_snr": bound,
        "fast_minus_bound": snr - bound,
        "fast_within_bound": snr <= bound + policy["independent_upper_slack"],
        "trace_absolute_snr_error": error,
        "trace_passed": error <= policy["trace_absolute_snr_goal"],
        "physical_refit_within_bound": actual is None
        or actual["snr"] <= bound + policy["independent_upper_slack"],
        "trace": detail,
        "warnings": [str(w.message) for w in caught],
    }


def run():
    policy = json.loads((ROOT / POLICY).read_text())
    search_policy, fixture = load_inputs()
    source = Path(methods.__file__).with_name("bls.c")
    if (
        importlib.metadata.version("astropy") != policy["upstream_version"]
        or sha(source) != policy["upstream_c_sha256"]
    ):
        raise ValueError("Unreviewed upstream implementation: requalify source trace")
    baseline = json.loads((ROOT / BASELINE).read_text())
    cases = {c["id"]: c for c in fixture["cases"]}
    selected = [
        r
        for r in baseline["results"]
        if r["algorithm"] == "bls"
        and (
            not r["passed"]
            or (
                r["stage"] != "sigma_clipped"
                and r["kind"] in ["sine", "box", "published_transit"]
                and r["regime"] in ["uniform", "archive"]
            )
        )
    ]
    rows = []
    for row in selected:
        c = processed(cases[row["id"]], row["stage"], search_policy)
        t, y, e = ([getattr(x, k) for x in c.points] for k in ["time", "value", "uncertainty"])
        measurements = [
            measure(
                t,
                y,
                e,
                row["best_candidate"]["period"],
                search_policy["bls_durations_days"],
                s,
                policy,
            )
            for s in policy["oversamples"]
        ]
        rows.append(
            {
                "id": row["id"],
                "stage": row["stage"],
                "mission56_failed": not row["passed"],
                "original_fast_snr": row["best_candidate"]["depth_snr"],
                "measurements": measurements,
            }
        )
    w = policy["witness"]
    witness = measure(
        w["times"], w["values"], w["errors"], w["period"], w["durations"], w["oversample"], policy
    )
    witness["analytic_bound_passed"] = (
        abs(witness["independent_max_snr"] ** 2 - w["independent_max_snr_squared"]) < 1e-10
    )
    witness["legacy_analytic_passed"] = (
        abs(witness["fast_snr"] ** 2 - w["legacy_snr_squared"]) < 1e-10
    )
    checks = [
        m["trace_passed"] and m["physical_refit_within_bound"]
        for row in rows
        for m in row["measurements"]
    ]
    retained = [
        next(m for m in row["measurements"] if m["oversample"] == 10)
        for row in rows
        if row["mission56_failed"]
    ]
    reproduced = all(not m["fast_within_bound"] for m in retained) and len(retained) == 9
    return {
        "mission": 57,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "policy": policy,
        "selected_trial_count": len(rows),
        "measurement_count": sum(len(r["measurements"]) for r in rows),
        "retained_nine_failures_reproduced": reproduced,
        "mechanism_checks_passed": all(checks)
        and reproduced
        and witness["analytic_bound_passed"]
        and witness["legacy_analytic_passed"],
        "production_scientific_failures_resolved": False,
        "physical_arrival_qualification_changed": False,
        "rows": rows,
        "witness": witness,
        "fast_bound_violations": sum(
            not m["fast_within_bound"] for r in rows for m in r["measurements"]
        ),
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "versions": {k: importlib.metadata.version(k) for k in ["astropy", "numpy", "scipy"]},
            "machine": platform.machine(),
            "requested_openblas_coretype": os.getenv("OPENBLAS_CORETYPE"),
            "upstream_c_sha256": sha(source),
            "network_required": False,
            "source_sha256": {
                k: sha(ROOT / k)
                for k in [
                    "validation/bls_discrepancy.py",
                    "validation/light_curve_references.py",
                    "validation/light_curve_campaign.py",
                    "src/astroscope/light_curve_transit_search.py",
                    "src/astroscope/light_curve_processing.py",
                ]
            },
            "input_sha256": {
                k: sha(ROOT / k)
                for k in [POLICY, BASELINE, "validation/manifests/light_curve_campaign_v1.json"]
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "measurement_count",
                    "mechanism_checks_passed",
                    "fast_bound_violations",
                    "production_scientific_failures_resolved",
                ]
            }
        )
    )
    return 0 if result["mechanism_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
