"""Mission 61 current-production acceptance, distinct from retained Mission 60 replay."""

import argparse
import json
from collections import Counter
from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from astroscope import exoplanet_catalog as exo
from astroscope import gaia_catalog as gaia
from astroscope.exoplanet_visuals import calculate_trapezoid_transit_flux
from astroscope.gaia_visuals import calculate_local_offsets_deg
from validation import catalogue_quantities as historical
from validation.catalogue_quantities import ROOT, csv_text, decode, sha

FIXTURE = "validation/fixtures/catalogue_correction_v1.json"
POLICY = "validation/manifests/catalogue_correction_policy_v1.json"
MANIFEST = "validation/manifests/catalogue_correction_v1.json"
SOURCE_PATHS = [
    "src/astroscope/" + x + ".py"
    for x in [
        "_catalogue_numerics",
        "gaia_catalog",
        "gaia_visuals",
        "gaia_dashboard",
        "gaia_messages",
        "exoplanet_catalog",
        "exoplanet_visuals",
        "exoplanet_dashboard",
        "exoplanet_export",
        "exoplanet_messages",
    ]
] + ["validation/catalogue_correction.py", "validation/catalogue_quantities.py"]


def load_inputs():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    return json.loads((ROOT / POLICY).read_text()), json.loads((ROOT / FIXTURE).read_text())


def source_at(ra, dec):
    values = dict.fromkeys(f.name for f in fields(gaia.GaiaSource))
    values.update(
        source_id=1, designation="synthetic", ra_deg=ra, dec_deg=dec, angular_distance_deg=0
    )
    return gaia.GaiaSource(**values)


def call_production(case):
    family, inputs = case["family"], case["inputs"]
    scalar_functions = {
        "distance": gaia.estimate_naive_distance_parsecs,
        "absolute_g": gaia.calculate_absolute_g_magnitude,
        "density": exo.calculate_planet_density_g_cm3,
        "depth": exo.calculate_transit_depth_ppm,
        "probability": exo.calculate_transit_probability_percent,
        "screen": exo.classify_temperate_candidate,
    }
    if family in scalar_functions:
        return scalar_functions[family](*map(decode, inputs))
    if family == "gaia_row":
        row = dict(source_id="1", ra="0", dec="60", angular_distance_deg="0", **inputs)
        obj = gaia.parse_gaia_csv(csv_text(row))[0]
        return {k: getattr(obj, k) for k in case["expected"]}
    if family == "exoplanet_row":
        row = dict(
            pl_name="synthetic b",
            hostname="synthetic",
            discoverymethod="synthetic",
            tran_flag="0",
            **inputs,
        )
        obj = exo.parse_exoplanet_csv(csv_text(row))[0]
        return {k: getattr(obj, k) for k in case["expected"]}
    if family == "offsets":
        ra, dec, cra, cdec = map(decode, inputs)
        return list(
            calculate_local_offsets_deg(source_at(ra, dec), center_ra_deg=cra, center_dec_deg=cdec)
        )
    if family == "trapezoid":
        return list(
            calculate_trapezoid_transit_flux(
                list(map(decode, inputs["times"])),
                depth_ppm=decode(inputs["depth"]),
                duration_hours=decode(inputs["duration"]),
                ingress_fraction=decode(inputs["ingress"]),
            )
        )
    if family == "constant":
        return getattr(exo, inputs[0])
    if family == "radius_coherence":
        # Compare implied SI radii from the two separate production conversions.
        depth_radius = Decimal(str(exo.EARTH_RADIUS_IN_SOLAR_RADII)) * Decimal("695700000")
        probability_radius = Decimal(str(exo.EARTH_RADIUS_IN_AU)) * Decimal("149597870700")
        return float(depth_radius - probability_radius)
    raise ValueError(f"Unknown family: {family}")


def evaluate(case, policy):
    row = historical.evaluate(case, policy, evaluator=call_production)
    if case["family"] in {"density", "depth", "probability"} and case["expected"] is not None:
        # Absolute comparison allowance must not turn a positive result into zero.
        row["passed"] = (
            row["passed"] and isinstance(row["actual"], (float, int)) and row["actual"] > 0
        )
    return row


def run_benchmark():
    policy, fixture = load_inputs()
    rows = [evaluate(c, policy) for c in fixture["cases"]]
    # Metadata only; no historical evaluations enter current acceptance.
    import importlib.metadata
    import os
    import platform

    from validation.catalogue_quantities import git

    return {
        "mission": 61,
        "execution_target": "current production",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(rows),
        "original_case_count": 911,
        "failed_cases": sum(not r["passed"] for r in rows),
        "failed_case_ids": [r["id"] for r in rows if not r["passed"]],
        "overall_passed": all(r["passed"] for r in rows),
        "family_counts": dict(Counter(r["family"] for r in rows)),
        "requirement_counts": dict(Counter(r["requirement"] for r in rows)),
        "projection_accepted_cases": sum(
            r["family"] == "offsets" and r["requirement"] == "value" for r in rows
        ),
        "projection_rejected_cases": sum(
            r["family"] == "offsets" and r["requirement"] == "reject" for r in rows
        ),
        "maximum_sampled_accepted_projection_error_arcsec": max(
            r["projection_diagnostic"]["error_arcsec"]
            for r in rows
            if "projection_diagnostic" in r
            and r["projection_diagnostic"]["error_arcsec"] is not None
        ),
        "analytic_projection_bound_arcsec": fixture["analytic_projection_bound_arcsec"],
        "projection_goal_arcsec": fixture["projection_goal_arcsec"],
        "calculation_convention": exo.CALCULATION_CONVENTION,
        "physical_arrival_qualification_changed": False,
        "observational_calibration_established": False,
        "phase_2_exit_approved": False,
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {x: importlib.metadata.version(x) for x in ["astropy", "numpy", "plotly"]},
            "source_sha256": {p: sha(ROOT / p) for p in SOURCE_PATHS},
            "input_sha256": {p: sha(ROOT / p) for p in [FIXTURE, POLICY, MANIFEST]},
            "network_required": False,
            "randomness": "none",
        },
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ["case_count", "failed_cases", "overall_passed"]}))
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
