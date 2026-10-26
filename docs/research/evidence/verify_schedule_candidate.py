"""Offline M66 source lineage, exact development claims and preserved-history checks."""

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


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
    require(d["baseline_commit"] == "b4e6cd13282ab2b87715aa659d74446f1ccab5a4", "baseline")
    require(d["review_status"] == "pending_merge" and d["baseline_accepted"], "review")
    require(d["evaluation_reserved_executions"] == 0, "reserved execution")
    require(d["case_count"] == 232 and d["primary_case_count"] == 216, "coverage")
    require(d["development_candidate_acceptance"] is True, "development acceptance")
    require(
        d["optimizer_acceptance"] is None
        and not d["physical_qualification"]
        and not d["phase_3_exit_approved"],
        "unsupported qualification",
    )
    old = read("docs/research/evidence/schedule_baselines_v1.json")
    for key in ["inherited_physical_status", "excluded_claims", "transit_production_counts", "x01"]:
        require(d[key] == old[key], f"restriction {key}")
    receipt = read("docs/research/evidence/mission65_merge_ci_v1.json")
    require(
        receipt["merge_commit"] == d["baseline_commit"] and receipt["conclusion"] == "success",
        "merge CI",
    )
    require(
        receipt["artifact_count"]
        == receipt["archives_downloaded"]
        == len(receipt["receipts"])
        == 30,
        "archive inventory",
    )
    require(
        receipt["tests"] == dict(passed=8907, historical_expected_failures=26), "baseline tests"
    )
    for r in receipt["receipts"]:
        require(
            r["head"] == d["baseline_commit"] and r["implementation_identity_verified"],
            "receipt identity",
        )
        for key in ["archive_sha256", "record_sha256"]:
            require(re.fullmatch("[0-9a-f]{64}", r[key]), "receipt digest")
    for path, digest in d["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"current hash {path}")
    for path, digest in d["preserved_baseline_sha256"].items():
        require(
            sha(git("show", f"{d['baseline_commit']}:{path}")) == digest, f"baseline hash {path}"
        )
        require(sha((ROOT / path).read_bytes()) == digest, f"preserved bytes changed {path}")
    freeze = read("validation/manifests/schedule_candidate_freeze_v1.json")
    require(freeze["source_commit"] == d["source_commit"], "source identity")
    require(
        git("show", "-s", "--format=%P", d["source_commit"]).decode().strip()
        == d["baseline_commit"],
        "source parent",
    )
    require(
        git("show", "-s", "--format=%P", d["freeze_commit"]).decode().strip() == d["source_commit"],
        "freeze order",
    )
    for path, digest in freeze["file_sha256"].items():
        require(sha(git("show", f"{d['source_commit']}:{path}")) == digest, f"frozen source {path}")
        require(sha((ROOT / path).read_bytes()) == digest, f"source changed {path}")
    run = read("validation/results/schedule_candidate_reference_run.json")
    require(run["overall_passed"] and not run["environment"]["git_dirty"], "clean canonical run")
    require(run["environment"]["implementation_commit"] == d["freeze_commit"], "canonical revision")
    require(run["case_count"] == 232 and run["method_case_count"] == 696, "canonical coverage")
    require(
        run["evaluation_reserved_executions"] == 0 and run["B2_case_evaluations"] == 232,
        "run scope",
    )
    require(
        run["development_candidate_acceptance"] and run["optimizer_acceptance"] is None,
        "run acceptance",
    )
    require(
        not run["physical_qualification"] and not run["phase_3_exit_approved"], "run qualification"
    )
    for name in ["astropy", "numpy"]:
        require(
            run["environment"]["versions"][name] == run["environment"]["imported_versions"][name],
            "imported version",
        )
    corpus = read("validation/fixtures/schedule_corpus_v1.json")
    cases = [c for c in corpus["primary_cases"] if c["split"] == "development"] + corpus["controls"]
    require(
        [r["case_id"] for r in run["results"]] == [c["case_id"] for c in cases], "exact case IDs"
    )
    references = {
        r["case_id"]: r for r in read("validation/fixtures/schedule_exhaustive_v1.json")["results"]
    }
    baselines = {
        r["case_id"]: r
        for r in read("validation/results/schedule_baselines_reference_run.json")["results"]
    }
    for row, case in zip(run["results"], cases, strict=True):
        require(row["passed"] and set(row["methods"]) == {"B0", "B1", "B2"}, "method inventory")
        require(row["split"] == case["split"], "split")
        for method in ["B0", "B1", "B2"]:
            result = row["methods"][method]
            require(
                result["passed"] and result["calls"] == dict(warmup=1, measured=5),
                "method completion",
            )
            require(len(result["runtime_ns"]["samples"]) == 5, "timing samples")
            if method != "B2":
                for key in ["output", "metrics", "operation_counts"]:
                    require(
                        result[key] == baselines[row["case_id"]]["methods"][method][key],
                        "baseline drift",
                    )
            else:
                reference = references[row["case_id"]]
                require(result["output"]["path"] == reference["path"], "canonical path")
                require(
                    result["metrics"]["net_objective"]
                    == result["output"]["net_objective"]
                    == reference["net_objective"],
                    "exact objective",
                )
                require(
                    result["metrics"]["regret"] == 0 and result["metrics"]["exact_path_match"],
                    "regret",
                )
    access = read("docs/research/evidence/schedule_candidate_access_v1.json")
    require(
        access["reserved_candidate_outputs_inspected"] == 0 and access["blind"] is False, "access"
    )
    require(all(e["reserved_candidate_outputs"] == 0 for e in access["events"]), "access event")
    old_workflow = (ROOT / ".github/workflows/quality-gate.yml").read_text()
    workflow = (ROOT / ".github/workflows/schedule-candidate-validation.yml").read_text()
    require(old_workflow.count("uses: actions/upload-artifact@v4") == 30, "old artifacts")
    require(workflow.count("uses: actions/upload-artifact@v4") == 1, "new artifact")
    require(
        "timeout-minutes: 10" in workflow and "schedule-candidate-validation-record" in workflow,
        "new CI",
    )


def main():
    d = read("docs/research/evidence/schedule_candidate_v1.json")
    validate(d)
    mutations = [
        ("evaluation_reserved_executions", 1),
        ("optimizer_acceptance", True),
        ("physical_qualification", True),
        ("phase_3_exit_approved", True),
        ("case_count", 231),
        ("primary_case_count", 215),
        ("excluded_claims", []),
        ("development_candidate_acceptance", False),
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
        "docs/research/validation/finite_horizon_candidate_validation.md",
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" not in target and not target.startswith("#"):
                require(((ROOT / path).parent / target.split("#")[0]).exists(), f"link {target}")
                links += 1
    print(
        json.dumps(
            dict(
                passed=True,
                cases=232,
                method_cases=696,
                reserved_executions=0,
                preserved_baseline_files=len(d["preserved_baseline_sha256"]),
                frozen_hashes=len(d["file_sha256"]),
                relative_links=links,
                documentary_mutants_rejected=len(mutations),
            )
        )
    )


if __name__ == "__main__":
    main()
