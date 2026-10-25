"""Offline arithmetic and controlled heuristic characterization; no observing-utility claim."""

import argparse
import importlib.metadata
import json
import math
import os
import platform
import subprocess
from collections import Counter
from dataclasses import asdict, fields
from datetime import UTC, date, datetime, time
from pathlib import Path
from unittest.mock import patch

from astroscope import planner as p
from astroscope import schedule as s
from astroscope import transit_ranking as r
from astroscope import weather as w
from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import TransitVisibilitySample, TransitVisibilitySummary
from validation.celestial_coordinates import sha

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "validation/fixtures/heuristic_characterisation_v1.json"
POLICY = "validation/manifests/heuristic_characterisation_policy_v1.json"
MANIFEST = "validation/manifests/heuristic_characterisation_v1.json"


def load_inputs():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for path, digest in manifest["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"Checksum mismatch: {path}")
    return json.loads((ROOT / POLICY).read_text()), json.loads((ROOT / FIXTURE).read_text())


def evaluate(case, policy):
    family, args = case["family"], case["inputs"]
    functions = {
        "planner_altitude": p.calculate_altitude_score,
        "planner_airmass": p.calculate_airmass_score,
        "planner_darkness": p.calculate_darkness_score,
        "rank_altitude": r.score_midpoint_altitude,
        "rank_moon": r.score_moon_separation,
        "rank_depth": r.score_transit_depth,
        "rank_timing": r.score_timing_confidence,
        "rank_brightness": r.score_host_brightness,
        "planner_rating": p.classify_planner_rating,
        "dew": w.classify_dew_risk,
    }
    if family == "planner_moon":
        actual = p.calculate_moon_separation_score(args[0], args[1], target_is_moon=args[2])
    elif family == "weather":
        actual = w.calculate_weather_score(**args)
    elif family == "weather_rating":
        actual = w.classify_weather_rating(args[0], precipitation_mm=0, wind_gusts_kmh=0)
    elif family == "plan_entry":
        entry = p.create_plan_entry(
            object_key="moon" if args["moon"] else "synthetic",
            category="catalog",
            altitude_degrees=45,
            azimuth_degrees=90,
            cardinal_direction="east",
            airmass=None if args["missing_airmass"] else 2,
            moon_separation_degrees=60,
            sun_altitude_degrees=-9,
            status=args["status"],
            minimum_altitude_degrees=20,
            minimum_moon_separation_degrees=30,
            minimum_score=args["threshold"],
        )
        actual = {"total": str(entry.total_score), "recommended": entry.recommended}
    else:
        actual = functions[family](*args)
    expected = case["expected"]
    if isinstance(actual, (int, float)):
        error = abs(actual - float(expected))
        passed = math.isfinite(actual) and error <= policy["absolute_score_tolerance"]
    elif family == "plan_entry":
        error = abs(float(actual["total"]) - float(expected["total"]))
        passed = error <= policy["absolute_score_tolerance"] and (
            actual["recommended"] == expected["recommended"]
        )
    else:
        error = None
        passed = actual == expected
    return {
        "id": case["id"],
        "family": family,
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "passed": passed,
    }


def candidate(case):
    name = case["name"]
    event = TransitEvent(name, 0, 2460389.5, 2460389.4, 2460389.6, 2460389.3, 2460389.7, 2 / 24)
    sample = TransitVisibilitySample(2460389.5, 45, 90, 1.4, -30, 0, 45, 0.5, True, True)
    # Deliberately controlled summary fields, not claimed physically realized observations.
    visibility = TransitVisibilitySummary(
        name,
        "synthetic",
        "synthetic",
        (sample,),
        sample,
        45,
        45,
        1.4,
        45,
        0.5,
        1,
        0.5,
        case["full"],
    )
    return r.TransitObservationCandidate(
        event,
        visibility,
        None if case["missing"] else 10000 if case["high"] else 0,
        None if case["missing"] else 5 if case["high"] else 16,
    )


def weights(case):
    return r.RankingWeights(
        **{f.name: float(v) for f, v in zip(fields(r.RankingWeights), case["weights"], strict=True)}
    )


def evaluate_ranking(case, policy):
    score = r.score_transit_candidate(candidate(case), weights=weights(case))
    actual = [getattr(score, f.name + "_score") for f in fields(r.RankingWeights)]
    errors = [abs(x - float(y)) for x, y in zip(actual, case["components"], strict=True)]
    error = abs(score.total_score - float(case["expected_total"]))
    missing = ["transit_depth_ppm", "host_magnitude"] if case["missing"] else []
    return {
        "id": case["id"],
        "profile": case["profile"],
        "score": asdict(score),
        "component_errors": errors,
        "total_error": error,
        "passed": all(
            math.isfinite(x) and x <= policy["weighted_total_tolerance"] for x in [*errors, error]
        )
        and list(score.missing_fields) == missing,
    }


def schedule_entry(name, score):
    return p.ObservationPlanEntry(
        name, "catalog", 45, 90, "east", 1.4, 90, "observable", 0, 0, 0, 0, score, "good", True
    )


def controlled_schedule(scores, *, reverse=False, interval=60):
    def plan(**kwargs):
        minute = kwargs["local_time"].hour * 60 + kwargs["local_time"].minute
        row = scores[min(minute // 60, len(scores) - 1)]
        entries = tuple(
            schedule_entry(name, score) for name, score in zip(["alpha", "beta"], row, strict=True)
        )
        if reverse:
            entries = entries[::-1]
        return p.ObservationPlanResult(entries, -30, 2, 2, "2024-03-20T00:00:00+00:00")

    with patch.object(s, "calculate_observation_plan", side_effect=plan):
        return s.calculate_observation_schedule(
            0, 0, 0, "UTC", date(2024, 3, 20), time(0), time(3), interval_minutes=interval
        )


def evaluate_schedule(case):
    result = controlled_schedule(case["scores"])
    path = []
    for hour in range(3):
        instant = datetime(2024, 3, 20, hour, tzinfo=UTC)
        block = next(b for b in result.schedule_blocks if b.start_utc <= instant < b.end_utc)
        path.append(["alpha", "beta"].index(block.object_key))
    gross = sum(case["scores"][i][k] for i, k in enumerate(path))
    switches = sum(a != b for a, b in zip(path[:-1], path[1:], strict=True))
    utility = gross - case["switch_penalty"] * switches
    # Per-slot upper envelope is independently obvious for this uncoupled objective.
    expected_gross = sum(max(row) for row in case["scores"])
    regret = case["optimal_utility"] - utility
    return {
        "id": case["id"],
        "selected_path": path,
        "gross_score": gross,
        "switches": switches,
        "net_utility": utility,
        "exhaustive_optimal_utility": case["optimal_utility"],
        "regret": regret,
        "optimal_paths": case["optimal_paths"],
        "passed": gross == expected_gross
        and regret >= 0
        and (case["switch_penalty"] != 0 or regret == 0),
        "production_optimizes_switch_cost": False,
    }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    policy, fixture = load_inputs()
    rows = [evaluate(c, policy) for c in fixture["cases"]]
    ranks = [evaluate_ranking(c, policy) for c in fixture["rankings"]]
    schedules = [evaluate_schedule(c) for c in fixture["schedules"]]
    sources = [
        "src/astroscope/" + x + ".py"
        for x in ["planner", "weather", "schedule", "transit_ranking", "transit_timing"]
    ]
    sources += ["validation/heuristic_characterisation.py", "validation/celestial_coordinates.py"]
    all_rows = rows + ranks + schedules
    return {
        "mission": 55,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "case_count": len(all_rows),
        "failed_cases": sum(not x["passed"] for x in all_rows),
        "overall_passed": all(x["passed"] for x in all_rows),
        "family_counts": dict(Counter(x["family"] for x in rows)),
        "ranking_case_count": len(ranks),
        "schedule_case_count": len(schedules),
        "maximum_schedule_regret": max(x["regret"] for x in schedules),
        "policy": policy,
        "physical_arrival_qualification_changed": False,
        "observational_calibration_established": False,
        "environment": {
            "implementation_commit": os.getenv(
                "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
            ),
            "checkout_commit": os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
            "git_dirty": bool(git("status", "--porcelain")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {x: importlib.metadata.version(x) for x in ["numpy", "astropy"]},
            "source_sha256": {x: sha(ROOT / x) for x in sources},
            "input_sha256": {x: sha(ROOT / x) for x in [FIXTURE, POLICY, MANIFEST]},
            "network_required": False,
            "randomness": "none",
        },
        "score_results": rows,
        "ranking_results": ranks,
        "schedule_results": schedules,
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
