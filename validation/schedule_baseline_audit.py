"""Mission 65 development-only B0/B1 acceptance and diagnostic measurements."""

import argparse
import importlib.metadata
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from time import perf_counter_ns
from unittest.mock import patch

from astroscope import planner
from validation.schedule_baseline_checks import check_result
from validation.schedule_baselines import b0, b1
from validation.schedule_corpus import CORPUS, REFERENCE, ROOT, read_json, require, serialize, sha

CONFIG = "validation/manifests/schedule_baselines_v1.json"
FREEZE = "validation/manifests/schedule_baselines_freeze_v1.json"
SOURCES = [
    "validation/schedule_baselines.py",
    "validation/schedule_baseline_checks.py",
    "validation/schedule_baseline_audit.py",
    "validation/schedule_corpus.py",
    "src/astroscope/schedule.py",
    "src/astroscope/planner.py",
    "src/astroscope/observer.py",
]


@contextmanager
def offline_adapter():
    """Deny sockets and live planner computation while allowing production imports."""

    def deny(*args, **kwargs):
        raise RuntimeError("live astronomy/network forbidden in controlled schedule experiment")

    with ExitStack() as stack:
        for obj, name in [
            (socket, "socket"),
            (socket, "create_connection"),
            (socket, "getaddrinfo"),
            (subprocess, "Popen"),
            (os, "system"),
            (planner, "calculate_observation_plan"),
            (planner, "get_body"),
            (planner, "calculate_horizontal_coordinates"),
            (planner, "calculate_solar_system_body"),
        ]:
            stack.enter_context(patch.object(obj, name, deny))
        # Neither baseline may consult the exhaustive solver while choosing actions.
        stack.enter_context(
            patch.dict(sys.modules, {"validation.reference_generation.schedule_exhaustive": None})
        )
        yield


def load_inputs():
    config = read_json(ROOT / CONFIG)
    require(
        config["methods"] == ["B0", "B1"]
        and config["evaluation_reserved_executions"] == 0
        and not config["B2_implemented"],
        "scope changed",
    )
    require(
        config["runtime"]
        == dict(
            warmups=1, repetitions=5, clock="perf_counter_ns", acceptance_threshold_seconds=None
        ),
        "timing policy changed",
    )
    for path, digest in config["input_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"frozen input changed {path}")
    corpus = read_json(ROOT / CORPUS)
    cases = [c for c in corpus["primary_cases"] if c["split"] == "development"] + corpus["controls"]
    require(
        len(cases) == 232 and len({c["case_id"] for c in cases}) == 232, "development inventory"
    )
    selected = {c["case_id"] for c in cases}
    reference = {
        r["case_id"]: r for r in read_json(ROOT / REFERENCE)["results"] if r["case_id"] in selected
    }
    require(set(reference) == selected, "reference coverage")
    return config, cases, reference


def measure(case, method, function, reference):
    function(case)  # Exactly one warmup; output is not used as a reference.
    times, outputs = [], []
    for _ in range(5):
        start = perf_counter_ns()
        output = function(case)
        times.append(perf_counter_ns() - start)
        outputs.append(output)
    require(all(o == outputs[0] for o in outputs), f"nondeterministic {method}")
    metrics = check_result(case, outputs[0], method, reference)
    return dict(
        passed=True,
        output=outputs[0],
        metrics=metrics,
        runtime_ns=dict(
            samples=times, median=statistics.median(times), minimum=min(times), maximum=max(times)
        ),
        calls=dict(warmup=1, measured=5),
        operation_counts=(
            dict(planner_snapshots=outputs[0]["snapshot_count"], decoded_slots=case["slots"])
            if method == "B0"
            else dict(action_values_examined=outputs[0]["action_values_examined"])
        ),
    )


def aggregate(rows):
    groups = []
    keys = sorted({(r["family"], r["split"], r["switch_cost"]) for r in rows})
    for family, split, cost in keys:
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
        passed = [r for r in selected if r["passed"]]
        for method in ("B0", "B1"):
            regrets = [r["methods"][method]["metrics"]["regret"] for r in passed]
            summary["methods"][method] = dict(
                evaluated=len(regrets),
                mean_regret=statistics.mean(regrets) if regrets else None,
                median_regret=statistics.median(regrets) if regrets else None,
                max_regret=max(regrets) if regrets else None,
            )
        deltas = [
            r["methods"]["B1"]["metrics"]["net_objective"]
            - r["methods"]["B0"]["metrics"]["net_objective"]
            for r in passed
        ]
        summary["B1_vs_B0"] = dict(
            win=sum(x > 0 for x in deltas), tie=deltas.count(0), loss=sum(x < 0 for x in deltas)
        )
        groups.append(summary)
    return groups


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_benchmark():
    config, cases, references = load_inputs()
    freeze = read_json(ROOT / FREEZE)
    for path, digest in freeze["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"source/configuration freeze {path}")
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
        versions={
            d.metadata["Name"]: d.version
            for d in importlib.metadata.distributions()
            if d.metadata["Name"]
        },
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in SOURCES},
        input_sha256={p: sha((ROOT / p).read_bytes()) for p in [CONFIG, FREEZE, CORPUS, REFERENCE]},
        timezone="UTC; no local-zone transition in this synthetic study",
        geometry="synthetic fixed placeholders, not qualified",
        ephemeris="not used",
        eop="not used",
        network_required=False,
        command="python -m validation.schedule_baseline_audit --output <path>",
    )
    rows = []
    with offline_adapter():
        for case in cases:
            row = dict(
                case_id=case["case_id"],
                split=case["split"],
                family=case["family"],
                switch_cost=case["switch_cost"],
                methods={},
            )
            for method, function in (("B0", b0), ("B1", b1)):
                try:
                    row["methods"][method] = measure(
                        case, method, function, references[case["case_id"]]
                    )
                except Exception as exc:
                    row["methods"][method] = dict(
                        passed=False, error=f"{type(exc).__name__}: {exc}"
                    )
            row["passed"] = all(m["passed"] for m in row["methods"].values())
            rows.append(row)
    failures = [r["case_id"] for r in rows if not r["passed"]]
    return dict(
        mission=65,
        overall_passed=not failures,
        failed_cases=len(failures),
        failed_case_ids=failures,
        execution_target=(
            "unchanged production scheduler through controlled B0 adapter; B1 validation policy"
        ),
        primary_case_count=216,
        control_count=16,
        case_count=232,
        method_case_count=464,
        source_freeze_commit=freeze["source_commit"],
        environment=environment,
        config=config,
        results=rows,
        aggregates=aggregate(rows),
        evaluation_reserved_executions=0,
        B2_implemented=False,
        B2_evaluations=0,
        optimizer_acceptance=None,
        physical_qualification=False,
        phase_3_exit_approved=False,
        sockets_blocked=True,
        live_planner_blocked=True,
        oracle_import_blocked=True,
        acceptance="development policy faithfulness and adapter semantics only",
        performance_scope=(
            "B0 includes strict API/injection/decoding; B1 includes schema/guard; "
            "no algorithm-speedup claim"
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
            mission=65,
            overall_passed=False,
            status="failed_or_incomplete",
            error=f"{type(exc).__name__}: {exc}",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(serialize(result))
    print(
        json.dumps(
            {
                k: result[k]
                for k in ["overall_passed", "case_count", "failed_cases", "error"]
                if k in result
            }
        )
    )
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
