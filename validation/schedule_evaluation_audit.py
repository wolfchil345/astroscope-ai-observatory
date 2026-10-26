"""Complete frozen scheduler comparison with durable, explicitly labelled access journals."""

import argparse
import json
import os
import platform
import statistics
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns

import astropy
import numpy

from validation.schedule_baseline_audit import dependency_versions, git, offline_adapter
from validation.schedule_baseline_checks import check_result
from validation.schedule_candidate_audit import aggregate
from validation.schedule_candidate_checks import check_candidate
from validation.schedule_corpus import CORPUS, REFERENCE, ROOT, read_json, require, serialize, sha
from validation.schedule_evaluation import (
    CONFIG,
    FREEZE,
    LABELS,
    evaluation_session,
    run_method,
    verify_freeze,
)
from validation.schedule_evaluation_checks import verify_journal

DEVELOPMENT_RECORD = "validation/results/schedule_candidate_reference_run.json"
FIRST_RECORD = "validation/results/schedule_evaluation_reference_run.json"
SOURCES = [
    "validation/schedule_evaluation.py",
    "validation/schedule_evaluation_audit.py",
    "validation/schedule_evaluation_checks.py",
    "validation/schedule_baselines.py",
    "validation/schedule_baseline_checks.py",
    "validation/schedule_baseline_audit.py",
    "validation/schedule_candidate.py",
    "validation/schedule_candidate_checks.py",
    "validation/schedule_candidate_audit.py",
    "validation/schedule_corpus.py",
    "src/astroscope/schedule.py",
    "src/astroscope/planner.py",
    "src/astroscope/observer.py",
]


def inputs():
    corpus = read_json(ROOT / CORPUS)
    development = [c for c in corpus["primary_cases"] if c["split"] == "development"]
    reserved = [c for c in corpus["primary_cases"] if c["split"] == "evaluation_reserved"]
    cases = development + corpus["controls"] + reserved
    require(
        [len(development), len(corpus["controls"]), len(reserved)] == [216, 16, 216], "inventory"
    )
    references = {r["case_id"]: r for r in read_json(ROOT / REFERENCE)["results"]}
    require({c["case_id"] for c in cases} == set(references) and len(cases) == 448, "E0 coverage")
    old = {r["case_id"]: r["methods"] for r in read_json(ROOT / DEVELOPMENT_RECORD)["results"]}
    require(
        set(old) == {c["case_id"] for c in development + corpus["controls"]}, "development coverage"
    )
    return cases, references, old


def measure(case, method, reference, old, session=None):
    result = dict(passed=False, calls=dict(warmup=0, measured=0), completed_outputs=[])
    samples = []
    try:
        warmup = run_method(method, case, session, "warmup", 0)
        result["calls"]["warmup"] = 1
        result["warmup_output_sha256"] = sha(serialize(warmup))
        for repetition in range(5):
            start = perf_counter_ns()
            output = run_method(method, case, session, "measured", repetition)
            samples.append(perf_counter_ns() - start)
            result["completed_outputs"].append(output)
            result["calls"]["measured"] += 1
        output = result["completed_outputs"][0]
        result["output"] = output
        require(
            all(o == output for o in result["completed_outputs"]) and warmup == output,
            "nondeterministic method output",
        )
        metrics = (
            check_candidate(case, output, reference)
            if method == "B2"
            else check_result(case, output, method, reference)
        )
        result["metrics"] = metrics
        result["operation_counts"] = (
            output["operation_counts"]
            if method == "B2"
            else dict(planner_snapshots=output["snapshot_count"], decoded_slots=case["slots"])
            if method == "B0"
            else dict(action_values_examined=output["action_values_examined"])
        )
        if old is not None:
            for key in ["output", "metrics", "operation_counts"]:
                require(
                    result[key] == old[method][key], f"development adapter mismatch: {method}/{key}"
                )
        result["passed"] = True
        # All six equal outputs are represented by the result plus the access-journal digests.
        del result["completed_outputs"]
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["runtime_ns"] = dict(
        samples=samples,
        median=statistics.median(samples) if samples else None,
        minimum=min(samples) if samples else None,
        maximum=max(samples) if samples else None,
    )
    return result


def evaluate_cases(cases, references, old, session=None):
    rows, development_ok = [], True
    for case in cases:
        row = {k: case[k] for k in ["case_id", "family", "split", "switch_cost"]}
        row["methods"] = {}
        if case["split"] == "evaluation_reserved" and not development_ok:
            row["methods"] = {
                m: dict(passed=False, error="not_executed: development preflight failed")
                for m in ["B0", "B1", "B2"]
            }
        else:
            for method in ["B0", "B1", "B2"]:
                row["methods"][method] = measure(
                    case, method, references[case["case_id"]], old.get(case["case_id"]), session
                )
        row["passed"] = all(m["passed"] for m in row["methods"].values())
        if case["split"] != "evaluation_reserved":
            development_ok &= row["passed"]
        rows.append(row)
    return rows


def run_benchmark(access_label, journal):
    config, freeze = verify_freeze()
    require(access_label in LABELS, "access label")
    if access_label == "first_frozen_evaluation":
        require(
            not (ROOT / FIRST_RECORD).exists(),
            "first record already exists; use exposed regression label",
        )
    cases, references, old = inputs()
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
        geometry="synthetic placeholders; unqualified",
        ephemeris="not used",
        eop="not used",
        network_required=False,
        command=(
            "python -m validation.schedule_evaluation_audit "
            f"--access-label {access_label} --output <new-path>"
        ),
    )
    require(not environment["git_dirty"], "reserved evaluation requires clean checkout")
    journal(
        dict(
            event="run_verified",
            environment=environment,
            source_commit=freeze["source_commit"],
            access_label=access_label,
        )
    )
    with evaluation_session(access_label, journal) as session, offline_adapter():
        rows = evaluate_cases(cases, references, old, session)
    failures = [r["case_id"] for r in rows if not r["passed"]]
    complete = (
        session.attempts == session.successes == 8064
        and session.reserved_attempts == session.reserved_successes == 3888
    )
    passed = not failures and complete
    return dict(
        mission=67,
        overall_passed=passed,
        status="passed" if passed else "failed_or_incomplete",
        failed_cases=len(failures),
        failed_case_ids=failures,
        complete_inventory_executed=complete,
        execution_target="Unchanged B0/B1/B2 code objects through private frozen-input guards",
        primary_case_count=432,
        development_case_count=216,
        evaluation_reserved_case_count=216,
        control_count=16,
        case_count=448,
        method_case_count=1344,
        reserved_method_case_count=648,
        method_invocations=session.attempts,
        successful_method_invocations=session.successes,
        reserved_method_invocations=session.reserved_attempts,
        successful_reserved_method_invocations=session.reserved_successes,
        source_freeze_commit=freeze["source_commit"],
        access_label=access_label,
        blind=False,
        trained_model=False,
        environment=environment,
        config=config,
        results=rows,
        aggregates=aggregate(rows),
        finite_model_candidate_acceptance=passed,
        optimizer_acceptance=None,
        physical_qualification=False,
        phase_3_exit_approved=False,
        production_changed=False,
        sockets_blocked=True,
        live_planner_blocked=True,
        oracle_import_blocked=True,
        B2_file_access_blocked=True,
        original_development_guards_preserved=True,
        acceptance="Frozen finite-corpus exact candidate and baseline policy acceptance only",
        performance_scope=(
            "Adapter/case hashing, journaling, guard and differing method overheads "
            "included; no algorithm-speedup claim"
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--access-label", choices=sorted(LABELS), required=True)
    args = parser.parse_args()
    journal_path = args.output.with_suffix(".access.jsonl")
    require(
        not args.output.exists() and not journal_path.exists(),
        "refuse to overwrite previous evidence",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(
            serialize(
                dict(
                    mission=67,
                    overall_passed=False,
                    status="incomplete",
                    access_label=args.access_label,
                )
            )
        )
    with journal_path.open("x", encoding="utf-8") as stream:
        sequence = 0

        def journal(event):
            nonlocal sequence
            sequence += 1
            row = dict(sequence=sequence, timestamp_utc=datetime.now(UTC).isoformat(), **event)
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()

        journal(dict(event="run_start", access_label=args.access_label))
        try:
            result = run_benchmark(args.access_label, journal)
        except Exception as exc:
            result = dict(
                mission=67,
                overall_passed=False,
                status="failed_or_incomplete",
                access_label=args.access_label,
                error=f"{type(exc).__name__}: {exc}",
            )
        journal(
            dict(
                event="run_complete",
                overall_passed=result["overall_passed"],
                status=result["status"],
            )
        )
    if result["overall_passed"]:
        try:
            result["access_journal_verification"] = verify_journal(
                [json.loads(line) for line in journal_path.read_text().splitlines()], result
            )
        except Exception as exc:
            result.update(
                overall_passed=False,
                status="failed_or_incomplete",
                error=f"journal verification: {type(exc).__name__}: {exc}",
            )
    result["access_journal_sha256"] = sha(journal_path.read_bytes())
    result["access_journal_events"] = sequence
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
