"""Offline documentary, freeze-order and preserved-baseline checks for Mission 64."""

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = "docs/research/evidence/schedule_corpus_release_v1.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def validate(d):
    baseline, source, release = (
        d[k] for k in ("baseline_commit", "source_commit", "release_commit")
    )
    require(baseline == "c489863badae5d28e6ae05e3b5d2f65565a0b1aa", "baseline identity")
    require(
        d["protocol_approved"] is True and d["release_review"] == "pending_merge", "review scope"
    )
    require(
        d["candidate_evaluations"] == 0 and d["optimizer_acceptance"] is None,
        "unsupported candidate acceptance",
    )
    require(
        d["phase_3_exit_approved"] is False and d["physical_qualification"] is False,
        "unsupported promotion",
    )
    old = read("docs/research/evidence/phase_3_entry_v1.json")
    for key in ["inherited_physical_status", "excluded_claims", "transit_production_counts", "x01"]:
        require(d[key] == old[key], f"preserved restriction {key}")
    receipt = read(d["baseline_receipt"])
    require(receipt["merge_commit"] == baseline and receipt["conclusion"] == "success", "merge CI")
    require(
        receipt["artifact_count"]
        == receipt["archives_downloaded"]
        == len(receipt["receipts"])
        == 28,
        "predecessor archive completeness",
    )
    require(
        receipt["tests"] == {"passed": 8356, "historical_expected_failures": 26}, "baseline tests"
    )
    for path, digest in d["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"file hash {path}")
    for path, digest in d["preserved_baseline_sha256"].items():
        require(sha(git("show", f"{baseline}:{path}")) == digest, f"baseline hash {path}")
        require(sha((ROOT / path).read_bytes()) == digest, f"old file modified {path}")
    require(git("show", "-s", "--format=%P", source).decode().strip() == baseline, "source order")
    require(git("show", "-s", "--format=%P", release).decode().strip() == source, "release order")
    manifest = read("validation/manifests/schedule_corpus_v1.json")
    require(manifest["source_commit"] == source, "release source identity")
    for path, digest in manifest["source_sha256"].items():
        require(sha(git("show", f"{source}:{path}")) == digest, f"source freeze {path}")
    for path in d["source_configuration_paths"]:
        require(
            git("show", f"{source}:{path}") == (ROOT / path).read_bytes(),
            f"source configuration changed {path}",
        )
    for path in d["release_paths"]:
        require(
            git("show", f"{release}:{path}") == (ROOT / path).read_bytes(),
            f"release changed {path}",
        )
    canonical = read("validation/results/schedule_corpus_reference_run.json")
    require(
        canonical["overall_passed"] and canonical["environment"]["git_dirty"] is False,
        "canonical execution",
    )
    require(canonical["environment"]["implementation_commit"] == release, "canonical identity")
    require(canonical["counts"] == manifest["expected_counts"] == d["counts"], "denominators")
    require(canonical["enumerated_paths"] == 20645809, "path coverage")
    access = read("docs/research/evidence/schedule_corpus_access_v1.json")
    require(
        access["blind"] is False and access["candidate_outputs_inspected"] == 0,
        "exposure misrepresentation",
    )
    require(
        access["source_commit"] == source and access["release_commit"] == release,
        "exposure freeze identity",
    )
    # All pre-existing workflow steps are retained byte-for-byte. Only checkout
    # history depth and the new, appended M64 step/artifact are different.
    workflow = ".github/workflows/quality-gate.yml"
    before = git("show", f"{baseline}:{workflow}").decode()
    expected = before.replace(
        "        uses: actions/checkout@v4\n",
        "        uses: actions/checkout@v4\n        with:\n          fetch-depth: 0\n",
    )
    current = (ROOT / workflow).read_text()
    require(current.startswith(expected.rstrip() + "\n"), "historical workflow changed")
    require(current.count("uses: actions/upload-artifact@v4") == 29, "artifact count")
    return d["counts"]


def main():
    d = read(LEDGER)
    counts = validate(d)
    mutants = []
    for key, value in [
        ("candidate_evaluations", 1),
        ("optimizer_acceptance", True),
        ("physical_qualification", True),
        ("phase_3_exit_approved", True),
        ("protocol_approved", False),
    ]:
        changed = copy.deepcopy(d)
        changed[key] = value
        mutants.append(changed)
    changed = copy.deepcopy(d)
    changed["counts"]["evaluation_reserved"] = 215
    mutants.append(changed)
    changed = copy.deepcopy(d)
    changed["excluded_claims"] = []
    mutants.append(changed)
    for index, changed in enumerate(mutants):
        try:
            validate(changed)
        except ValueError:
            pass
        else:
            raise ValueError(f"documentary mutant survived: {index}")
    links = 0
    for path in [
        "docs/research/roadmap_status.md",
        "docs/research/validation/controlled_schedule_corpus.md",
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" in target or target.startswith("#"):
                continue
            require(((ROOT / path).parent / target.split("#")[0]).exists(), f"broken link {target}")
            links += 1
    print(
        json.dumps(
            dict(
                passed=True,
                counts=counts,
                relative_links=links,
                frozen_hashes=len(d["file_sha256"]),
                preserved_baseline_files=len(d["preserved_baseline_sha256"]),
                documentary_mutants_rejected=len(mutants),
            )
        )
    )


if __name__ == "__main__":
    main()
