"""Offline M67 first-exposure lineage, complete scientific results and preserved history."""

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from validation.schedule_baseline_checks import check_result  # noqa: E402
from validation.schedule_candidate_checks import check_candidate  # noqa: E402
from validation.schedule_evaluation_checks import verify_journal  # noqa: E402


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads((ROOT / path).read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(d):
    require(d["baseline_commit"] == "7f9f4d0276fc998224f9ba1d0e03ce24f0551b20", "baseline")
    require(d["baseline_accepted"] and d["review_status"] == "pending_merge", "review")
    require(d["reserved_candidate_outputs_before_freeze"] == 0, "premature exposure")
    require(
        d["case_count"] == 448
        and d["reserved_case_count"] == 216
        and d["method_case_count"] == 1344,
        "coverage",
    )
    require(
        d["finite_model_candidate_acceptance"] is True and d["optimizer_acceptance"] is None,
        "acceptance",
    )
    require(not d["physical_qualification"] and not d["phase_3_exit_approved"], "qualification")
    require(
        d["first_access_label"] == "first_frozen_evaluation"
        and d["replay_label"] == "exposed_regression_replay",
        "access labels",
    )
    old = read("docs/research/evidence/schedule_candidate_v1.json")
    for key in ["inherited_physical_status", "excluded_claims", "transit_production_counts", "x01"]:
        require(d[key] == old[key], f"restriction {key}")
    receipt = read("docs/research/evidence/mission66_merge_ci_v1.json")
    require(
        receipt["merge_commit"] == d["baseline_commit"] and receipt["conclusion"] == "success",
        "merge CI",
    )
    require(
        receipt["artifact_count"]
        == receipt["archives_downloaded"]
        == len(receipt["receipts"])
        == 31,
        "archive inventory",
    )
    require(
        receipt["tests"] == dict(passed=9670, historical_expected_failures=26), "baseline tests"
    )
    for r in receipt["receipts"]:
        require(
            r["head"] == d["baseline_commit"] and r["implementation_identity_verified"],
            "receipt identity",
        )
    for path, digest in d["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"current hash {path}")
    for path, digest in d["preserved_baseline_sha256"].items():
        require(
            sha(git("show", f"{d['baseline_commit']}:{path}")) == digest, f"baseline hash {path}"
        )
        require(sha((ROOT / path).read_bytes()) == digest, f"historical bytes changed {path}")
    freeze = read("validation/manifests/schedule_evaluation_freeze_v1.json")
    require(
        freeze["source_commit"] == d["source_commit"]
        and freeze["reserved_candidate_outputs_before_freeze"] == 0,
        "source identity/exposure",
    )
    require(
        git("show", "-s", "--format=%P", d["source_commit"]).decode().strip()
        == d["baseline_commit"],
        "source order",
    )
    require(
        git("show", "-s", "--format=%P", d["freeze_commit"]).decode().strip() == d["source_commit"],
        "freeze order",
    )
    for path, digest in freeze["file_sha256"].items():
        require(
            sha(git("show", f"{d['source_commit']}:{path}")) == digest, f"source checkpoint {path}"
        )
        require(sha((ROOT / path).read_bytes()) == digest, f"frozen file {path}")
    run = read("validation/results/schedule_evaluation_reference_run.json")
    require(
        run["overall_passed"]
        and run["complete_inventory_executed"]
        and not run["environment"]["git_dirty"],
        "canonical completeness",
    )
    require(run["environment"]["implementation_commit"] == d["freeze_commit"], "canonical revision")
    require(
        run["source_freeze_commit"] == d["source_commit"]
        and run["access_label"] == d["first_access_label"],
        "canonical source/label",
    )
    require(
        run["method_invocations"] == run["successful_method_invocations"] == 8064, "all invocations"
    )
    require(
        run["reserved_method_invocations"] == run["successful_reserved_method_invocations"] == 3888,
        "reserved invocations",
    )
    require(
        run["case_count"] == 448
        and run["method_case_count"] == 1344
        and run["reserved_method_case_count"] == 648,
        "run inventory",
    )
    require(
        run["finite_model_candidate_acceptance"]
        and run["optimizer_acceptance"] is None
        and not run["physical_qualification"]
        and not run["phase_3_exit_approved"],
        "run claims",
    )
    for name in ["numpy", "astropy"]:
        require(
            run["environment"]["versions"][name] == run["environment"]["imported_versions"][name],
            "imported versions",
        )
    corpus = read("validation/fixtures/schedule_corpus_v1.json")
    cases = [c for c in corpus["primary_cases"] if c["split"] == "development"] + corpus["controls"]
    cases += [c for c in corpus["primary_cases"] if c["split"] == "evaluation_reserved"]
    require(
        [r["case_id"] for r in run["results"]] == [c["case_id"] for c in cases],
        "exact ordered inventory",
    )
    reference = {
        r["case_id"]: r for r in read("validation/fixtures/schedule_exhaustive_v1.json")["results"]
    }
    development = {
        r["case_id"]: r
        for r in read("validation/results/schedule_candidate_reference_run.json")["results"]
    }
    for row, case in zip(run["results"], cases, strict=True):
        require(
            row["passed"]
            and row["split"] == case["split"]
            and set(row["methods"]) == {"B0", "B1", "B2"},
            "row identity/completion",
        )
        for method in ["B0", "B1", "B2"]:
            result = row["methods"][method]
            metrics = (
                check_candidate(case, result["output"], reference[case["case_id"]])
                if method == "B2"
                else check_result(case, result["output"], method, reference[case["case_id"]])
            )
            require(result["passed"] and metrics == result["metrics"], "independent metrics")
            require(
                result["calls"] == dict(warmup=1, measured=5)
                and len(result["runtime_ns"]["samples"]) == 5,
                "repetition completeness",
            )
            if case["split"] != "evaluation_reserved":
                for key in ["output", "metrics", "operation_counts"]:
                    require(
                        result[key] == development[case["case_id"]]["methods"][method][key],
                        "development drift",
                    )
    path = ROOT / "validation/results/schedule_evaluation_first_access.jsonl"
    require(sha(path.read_bytes()) == run["access_journal_sha256"], "raw journal hash")
    journal = [json.loads(line) for line in path.read_text().splitlines()]
    require(
        verify_journal(journal, run) == run["access_journal_verification"], "journal reconciliation"
    )
    require(len(journal) == run["access_journal_events"] == 16133, "journal event count")
    first = next(
        e for e in journal if e["event"] == "method_start" and e["split"] == "evaluation_reserved"
    )
    require(first["invocation"] == 4177, "development precedes reserved")
    access = read("docs/research/evidence/schedule_evaluation_access_v1.json")
    require(
        access["first_reserved_method_start"] == first
        and access["reserved_candidate_outputs_before_freeze"] == 0,
        "access history",
    )
    require(
        access["blind"] is False and access["events"][2]["access_label"] == d["replay_label"],
        "exposure disclosure",
    )
    old_artifacts = sum(
        (ROOT / p).read_text().count("uses: actions/upload-artifact@v4")
        for p in [
            ".github/workflows/quality-gate.yml",
            ".github/workflows/schedule-candidate-validation.yml",
        ]
    )
    workflow = (ROOT / ".github/workflows/schedule-evaluation-validation.yml").read_text()
    require(
        old_artifacts == 31 and workflow.count("uses: actions/upload-artifact@v4") == 1,
        "artifact count",
    )
    require(
        "--access-label exposed_regression_replay" in workflow
        and ".access.jsonl" in workflow
        and "timeout-minutes: 10" in workflow,
        "CI replay/journal/cap",
    )


def main():
    d = read("docs/research/evidence/schedule_evaluation_v1.json")
    validate(d)
    mutations = [
        ("reserved_candidate_outputs_before_freeze", 1),
        ("case_count", 447),
        ("reserved_case_count", 215),
        ("method_case_count", 1343),
        ("finite_model_candidate_acceptance", False),
        ("optimizer_acceptance", True),
        ("physical_qualification", True),
        ("phase_3_exit_approved", True),
        ("replay_label", "first_frozen_evaluation"),
        ("excluded_claims", []),
        ("review_status", "approved"),
    ]
    for key, value in mutations:
        changed = copy.deepcopy(d)
        changed[key] = value
        try:
            validate(changed)
        except ValueError:
            pass
        else:
            raise ValueError(f"undetected documentary mutation {key}")
    links = 0
    for path in [
        "docs/research/roadmap_status.md",
        "docs/research/validation/frozen_scheduler_evaluation.md",
        "docs/research/protocols/schedule_evaluation_execution_v1.md",
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" not in target and not target.startswith("#"):
                require(((ROOT / path).parent / target.split("#")[0]).exists(), f"link {target}")
                links += 1
    print(
        json.dumps(
            dict(
                passed=True,
                cases=448,
                method_cases=1344,
                reserved_cases=216,
                preserved_baseline_files=len(d["preserved_baseline_sha256"]),
                frozen_hashes=len(d["file_sha256"]),
                relative_links=links,
                journal_events=16133,
                documentary_mutants_rejected=len(mutations),
            )
        )
    )


if __name__ == "__main__":
    main()
