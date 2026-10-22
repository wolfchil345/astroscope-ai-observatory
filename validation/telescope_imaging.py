"""Mission 52 offline comparison with a frozen independent optical reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from astroscope import imaging, telescope

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "validation/fixtures/telescope_imaging_v1.json"
MANIFEST = "validation/manifests/telescope_imaging_v1.json"
EXPECTED_MANIFEST_SHA256 = "5e27a79431022355680925300fadea5a2419ba90aa2e84861bb87653294573f6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(root=ROOT):
    if sha(root / MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Manifest checksum mismatch")
    manifest = json.loads((root / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(root / path) != digest:
            raise ValueError(f"Input checksum mismatch: {path}")
    fixture = json.loads((root / FIXTURE).read_text())
    ids = [c["id"] for c in fixture["cases"]]
    if (
        len(ids) != len(set(ids))
        or dict(Counter(c["kind"] for c in fixture["cases"])) != manifest["counts"]
    ):
        raise ValueError("Invalid reference inventory")
    return manifest, fixture


def evaluate(case):
    p = case["inputs"]
    kind = case["kind"]
    if kind in ("optical", "imaging"):
        scope = telescope.TelescopeSpec(float(p["aperture"]), float(p["focal"]))
        accessories = {"barlow_factor": float(p["barlow"]), "reducer_factor": float(p["reducer"])}
        if kind == "optical":
            return telescope.calculate_optical_simulation(
                scope, telescope.EyepieceSpec(float(p["eye"]), float(p["apparent"])), **accessories
            )
        return imaging.calculate_astrophotography_setup(
            scope,
            imaging.CameraSensorSpec(p["width"], p["height"], float(p["pixel"])),
            **accessories,
        )
    if kind == "field":
        return SimpleNamespace(
            field_degrees=imaging.calculate_sensor_field_degrees(
                float(p["size"]), float(p["focal"])
            )
        )
    if kind == "mosaic":
        return imaging.calculate_target_framing(
            field_width_degrees=float(p["width"]),
            field_height_degrees=float(p["height"]),
            overlap_percent=float(p["overlap"]),
            target=imaging.ImagingTargetSpec(
                "reference", float(p["target_width"]), float(p["target_height"])
            ),
        )
    raise ValueError(f"Unknown case kind: {kind}")


def compare_case(case, policy):
    result = evaluate(case)
    metrics = {}
    for name, expected in case["expected"].items():
        actual = getattr(result, name)
        digits = case["digits"][name]
        bound = (
            policy["unrounded_absolute_degrees"]
            if digits is None
            else 0
            if digits == 0
            else 0.5 * 10 ** (-digits) + policy["rounding_slack"]
        )
        error = actual - float(expected)
        metrics[name] = {
            "actual": actual if math.isfinite(actual) else None,
            "reference": expected,
            "absolute_error": abs(error) if math.isfinite(error) else None,
            "bound": bound,
            "passed": math.isfinite(error) and abs(error) <= bound,
        }
    return {
        "id": case["id"],
        "kind": case["kind"],
        "metrics": metrics,
        "passed": all(m["passed"] for m in metrics.values()),
    }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    manifest, fixture = load_inputs()
    rows = [compare_case(c, manifest["policy"]) for c in fixture["cases"]]
    paths = [
        MANIFEST,
        FIXTURE,
        "validation/telescope_imaging.py",
        "src/astroscope/telescope.py",
        "src/astroscope/imaging.py",
    ]
    failures = [
        {"id": r["id"], "field": k, **v}
        for r in rows
        for k, v in r["metrics"].items()
        if not v["passed"]
    ]
    return {
        "schema_version": "1.0",
        "mission": 52,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "implementation_commit": os.environ.get(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.environ.get(
                "ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")
            ),
            "git_dirty": bool(git("status", "--porcelain")),
            "source_sha256": {p: sha(ROOT / p) for p in paths},
            "network_required": False,
            "randomness": "none",
            "dependencies": "Python stdlib only; no astronomy, time or ephemeris data used",
        },
        "policy": manifest["policy"],
        "counts": dict(Counter(c["kind"] for c in rows)),
        "case_count": len(rows),
        "passed_cases": sum(c["passed"] for c in rows),
        "failed_cases": sum(not c["passed"] for c in rows),
        "failure_metrics": failures,
        "overall_passed": not failures,
        "scientific_status": "bounded ideal geometry and declared numerical conventions only",
        "physical_optical_performance_validated": False,
        "heuristics_calibrated": False,
        "plate_scale_constant_relative_error": abs(
            206.265 / float(fixture["exact_plate_scale_constant"]) - 1
        ),
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ("case_count", "passed_cases", "failed_cases", "overall_passed")}
        )
    )
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
