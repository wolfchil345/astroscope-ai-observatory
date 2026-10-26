"""Offline Mission 65 provenance, development-only scope and preserved-history audit."""

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
    require(d["baseline_commit"] == "0577e5461797491ce3578b03ed94cbcc331b22a6", "baseline")
    require(
        d["input_reference_approved"] is True and d["review_status"] == "pending_merge", "review"
    )
    require(
        d["evaluation_reserved_executions"] == 0 and d["B2_implemented"] is False,
        "unapproved candidate execution",
    )
    require(
        d["optimizer_acceptance"] is None
        and d["phase_3_exit_approved"] is False
        and d["physical_qualification"] is False,
        "unsupported qualification",
    )
    old = read("docs/research/evidence/schedule_corpus_release_v1.json")
    for key in ["inherited_physical_status", "excluded_claims", "transit_production_counts", "x01"]:
        require(d[key] == old[key], f"restriction {key}")
    receipt = read("docs/research/evidence/mission64_merge_ci_v1.json")
    require(
        receipt["merge_commit"] == d["baseline_commit"] and receipt["conclusion"] == "success",
        "merge CI",
    )
    require(
        receipt["artifact_count"]
        == receipt["archives_downloaded"]
        == len(receipt["receipts"])
        == 29,
        "archive coverage",
    )
    require(
        receipt["tests"] == {"passed": 8377, "historical_expected_failures": 26}, "test baseline"
    )
    for path, digest in d["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"current hash {path}")
    for path, digest in d["preserved_baseline_sha256"].items():
        require(
            sha(git("show", f"{d['baseline_commit']}:{path}")) == digest, f"baseline hash {path}"
        )
        require(sha((ROOT / path).read_bytes()) == digest, f"historical bytes changed {path}")
    freeze = read("validation/manifests/schedule_baselines_freeze_v1.json")
    require(freeze["source_commit"] == d["source_commit"], "source identity")
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
        require(sha(git("show", f"{d['source_commit']}:{path}")) == digest, f"frozen source {path}")
        require(sha((ROOT / path).read_bytes()) == digest, f"source changed {path}")
    run = read("validation/results/schedule_baselines_reference_run.json")
    require(run["overall_passed"] and not run["environment"]["git_dirty"], "canonical execution")
    require(run["environment"]["implementation_commit"] == d["freeze_commit"], "canonical revision")
    require(
        run["case_count"] == d["case_count"] == 232 and run["method_case_count"] == 464,
        "case coverage",
    )
    corpus = read("validation/fixtures/schedule_corpus_v1.json")
    expected = [c["case_id"] for c in corpus["primary_cases"] if c["split"] == "development"]
    expected += [c["case_id"] for c in corpus["controls"]]
    require([r["case_id"] for r in run["results"]] == expected, "development-only exact inventory")
    require(
        all(r["passed"] and set(r["methods"]) == {"B0", "B1"} for r in run["results"]),
        "method acceptance",
    )
    require(
        run["evaluation_reserved_executions"] == 0 and run["B2_evaluations"] == 0,
        "evaluation scope",
    )
    access = read("docs/research/evidence/schedule_baselines_access_v1.json")
    require(
        access["reserved_candidate_outputs_inspected"] == 0 and access["blind"] is False,
        "exposure claim",
    )
    old_workflow = git(
        "show", f"{d['baseline_commit']}:.github/workflows/quality-gate.yml"
    ).decode()
    workflow = (ROOT / ".github/workflows/quality-gate.yml").read_text()
    require(workflow.startswith(old_workflow.rstrip() + "\n"), "old CI steps changed")
    require(workflow.count("uses: actions/upload-artifact@v4") == 30, "CI artifact count")


def main():
    d = read("docs/research/evidence/schedule_baselines_v1.json")
    validate(d)
    mutations = [
        ("evaluation_reserved_executions", 1),
        ("B2_implemented", True),
        ("optimizer_acceptance", True),
        ("physical_qualification", True),
        ("phase_3_exit_approved", True),
        ("case_count", 231),
        ("excluded_claims", []),
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
        "docs/research/validation/controlled_scheduler_baselines.md",
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" in target or target.startswith("#"):
                continue
            require(((ROOT / path).parent / target.split("#")[0]).exists(), f"link {target}")
            links += 1
    print(
        json.dumps(
            dict(
                passed=True,
                cases=232,
                method_cases=464,
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
