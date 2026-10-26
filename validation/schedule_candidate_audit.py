"""Mission 66 development-only B2 acceptance with frozen B0/B1 comparisons."""

import argparse
import builtins
import io
import os
import platform
import statistics
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter_ns
from unittest.mock import patch

import astropy
import numpy

from validation.schedule_baseline_audit import (
    dependency_versions,
    git,
    load_inputs,
    offline_adapter,
)
from validation.schedule_baseline_checks import check_result
from validation.schedule_baselines import b0, b1
from validation.schedule_candidate import b2
from validation.schedule_candidate_checks import check_candidate
from validation.schedule_corpus import ROOT, read_json, require, serialize, sha

CONFIG = "validation/manifests/schedule_candidate_v1.json"
FREEZE = "validation/manifests/schedule_candidate_freeze_v1.json"
BASELINE = "validation/results/schedule_baselines_reference_run.json"
SOURCES = [
    "validation/schedule_candidate.py",
    "validation/schedule_candidate_checks.py",
    "validation/schedule_candidate_audit.py",
    "validation/schedule_baselines.py",
    "validation/schedule_baseline_checks.py",
    "validation/schedule_baseline_audit.py",
    "validation/schedule_corpus.py",
    "src/astroscope/schedule.py",
    "src/astroscope/planner.py",
    "src/astroscope/observer.py",
]


@contextmanager
def candidate_without_files():
    """The candidate receives case data only; disallow file reads while it executes."""

    def deny(*args, **kwargs):
        raise RuntimeError("candidate file access forbidden")

    with patch.object(builtins, "open", deny), patch.object(io, "open", deny):
        yield


def measure(case, method, function, reference, baseline):
    def invoke():
        if method == "B2":
            with candidate_without_files():
                return function(case)
        return function(case)

    invoke()
    times, outputs = [], []
    for _ in range(5):
        start = perf_counter_ns()
        output = invoke()
        times.append(perf_counter_ns() - start)
        outputs.append(output)
    result = dict(
        passed=False,
        output=outputs[0],
        runtime_ns=dict(
            samples=times, median=statistics.median(times), minimum=min(times), maximum=max(times)
        ),
        calls=dict(warmup=1, measured=5),
    )
    try:
        require(all(o == outputs[0] for o in outputs), f"nondeterministic {method}")
        if method == "B2":
            result["metrics"] = check_candidate(case, outputs[0], reference)
            result["operation_counts"] = outputs[0]["operation_counts"]
        else:
            result["metrics"] = check_result(case, outputs[0], method, reference)
            result["operation_counts"] = (
                dict(planner_snapshots=outputs[0]["snapshot_count"], decoded_slots=case["slots"])
                if method == "B0"
                else dict(action_values_examined=outputs[0]["action_values_examined"])
            )
            for key in ["output", "metrics", "operation_counts"]:
                require(result[key] == baseline[method][key], f"frozen {method} changed: {key}")
        result["passed"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        if any(o != outputs[0] for o in outputs):
            result["nondeterministic_outputs"] = outputs
    return result


def aggregate(rows):
    groups = []
    for family, split, cost in sorted({(r["family"], r["split"], r["switch_cost"]) for r in rows}):
        selected = [
            r for r in rows if (r["family"], r["split"], r["switch_cost"]) == (family, split, cost)
        ]
        summary = dict(
            family=family,
            split=split,
            switch_cost=cost,
            denominator=len(selected),
            failed_cases=sum(not r["passed"] for r in selected),
            methods={},
        )
        for method in ["B0", "B1", "B2"]:
            passed = [r["methods"][method] for r in selected if r["methods"][method]["passed"]]
            regrets = [m["metrics"]["regret"] for m in passed]
            summary["methods"][method] = dict(
                evaluated=len(passed),
                failed=len(selected) - len(passed),
                mean_regret=statistics.mean(regrets) if regrets else None,
                median_regret=statistics.median(regrets) if regrets else None,
                max_regret=max(regrets) if regrets else None,
            )
        for left, right in [("B1", "B0"), ("B2", "B0"), ("B2", "B1")]:
            deltas = [
                r["methods"][left]["metrics"]["net_objective"]
                - r["methods"][right]["metrics"]["net_objective"]
                for r in selected
                if r["methods"][left]["passed"] and r["methods"][right]["passed"]
            ]
            summary[f"{left}_vs_{right}"] = dict(
                paired=len(deltas),
                incomplete=len(selected) - len(deltas),
                win=sum(x > 0 for x in deltas),
                tie=deltas.count(0),
                loss=sum(x < 0 for x in deltas),
            )
        groups.append(summary)
    return groups


def evaluate_cases(cases, references, baselines, methods=None):
    methods = methods if methods is not None else [("B0", b0), ("B1", b1), ("B2", b2)]
    rows = []
    with offline_adapter():
        for case in cases:
            row = {k: case[k] for k in ["case_id", "split", "family", "switch_cost"]}
            row["methods"] = {}
            for method, function in methods:
                try:
                    result = measure(
                        case,
                        method,
                        function,
                        references[case["case_id"]],
                        baselines[case["case_id"]],
                    )
                except Exception as exc:
                    result = dict(passed=False, error=f"{type(exc).__name__}: {exc}")
                row["methods"][method] = result
            row["passed"] = all(m["passed"] for m in row["methods"].values())
            rows.append(row)
    return rows


def run_benchmark():
    _, cases, references = load_inputs()
    config, freeze = read_json(ROOT / CONFIG), read_json(ROOT / FREEZE)
    require(
        config["methods"] == ["B0", "B1", "B2"] and config["evaluation_reserved_executions"] == 0,
        "scope",
    )
    for path, digest in config["input_sha256"].items() | freeze["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"source/input freeze {path}")
    old_freeze = read_json(ROOT / "validation/manifests/schedule_baselines_freeze_v2.json")
    for path, digest in old_freeze["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"M65 frozen file changed {path}")
    baselines = {r["case_id"]: r["methods"] for r in read_json(ROOT / BASELINE)["results"]}
    environment = dict(
        implementation_commit=os.getenv(
            "ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD")
        ),
        checkout_commit=os.getenv("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
        parent_commits=git("show", "-s", "--format=%P", "HEAD").split(),
        git_dirty=bool(git("status", "--porcelain")),
        python=platform.python_version(),
        platform=platform.platform(),
        machine=platform.machine(),
        versions=dependency_versions(),
        imported_versions=dict(astropy=astropy.__version__, numpy=numpy.__version__),
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in SOURCES},
        input_sha256={
            p: sha((ROOT / p).read_bytes()) for p in [CONFIG, FREEZE, *config["input_sha256"]]
        },
        timezone="UTC; synthetic half-open slots",
        geometry="synthetic fixed placeholders, not qualified",
        ephemeris="not used",
        eop="not used",
        network_required=False,
        command="python -m validation.schedule_candidate_audit --output <path>",
    )
    rows = evaluate_cases(cases, references, baselines)
    failures = [r["case_id"] for r in rows if not r["passed"]]
    return dict(
        mission=66,
        overall_passed=not failures,
        failed_cases=len(failures),
        failed_case_ids=failures,
        execution_target="validation-only B2; unchanged B0/B1 for development comparison",
        primary_case_count=216,
        control_count=16,
        case_count=232,
        method_case_count=696,
        source_freeze_commit=freeze["source_commit"],
        environment=environment,
        config=config,
        results=rows,
        aggregates=aggregate(rows),
        evaluation_reserved_executions=0,
        B2_implemented=True,
        B2_case_evaluations=len(rows),
        development_candidate_acceptance=not failures,
        optimizer_acceptance=None,
        physical_qualification=False,
        phase_3_exit_approved=False,
        sockets_blocked=True,
        live_planner_blocked=True,
        oracle_import_blocked=True,
        candidate_file_access_blocked=True,
        acceptance="exact objective and canonical path on frozen development inputs only",
        performance_scope=(
            "Same process/machine; differing adapter/guard overheads; no algorithm-speedup claim"
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_benchmark()
    except Exception as exc:
        result = dict(
            mission=66,
            overall_passed=False,
            status="failed_or_incomplete",
            error=f"{type(exc).__name__}: {exc}",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(serialize(result))
    print(
        {
            k: result.get(k)
            for k in ["overall_passed", "case_count", "failed_cases", "status", "error"]
        }
    )
    raise SystemExit(0 if result["overall_passed"] else 1)


if __name__ == "__main__":
    main()
