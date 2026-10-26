"""Offline Mission 62 documentary integrity checks; no scientific qualification."""

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = "docs/research/evidence/phase_2_exit_readiness_v1.json"
REPORT = "docs/research/phase_2_exit_readiness.md"
EXPECTED_MISSIONS = [25, 27, 32, 33, 34, 35, *range(38, 51), *range(52, 59), 60, 61]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def load(path):
    return json.loads((ROOT / path).read_text())


def pointer(obj, path):
    for key in path.strip("/").split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        obj = obj[int(key)] if isinstance(obj, list) else obj[key]
    return obj


def validate(ledger, ci, history, *, historical_objects=False):
    require(ledger["decision"] == "LIMITED_SCOPE_EXIT_PROPOSED", "decision changed")
    require(ledger["phase_2_exit_approved"] is False, "unauthorized exit flag")
    require(ledger["phase_3_started"] is False, "unauthorized Phase 3 start")
    require(ledger["phase_2_status"] == "active_pending_owner_review", "phase status changed")
    for field in ["new_numerical_experiments", "new_scientific_tests", "new_ci_artifacts"]:
        require(ledger[field] == 0, field)
    require(ledger["production_changes"] is False, "production change")
    base = ledger["baseline_commit"]
    require(ci["baseline_commit"] == base == history["baseline_commit"], "baseline identity")
    require(ci["conclusion"] == "success", "baseline CI failed")
    require(
        ci["postmerge_tests"] == {"passed": 8356, "historical_expected_failures": 26},
        "baseline test result",
    )
    require(
        ci["artifact_count"] == ci["archives_downloaded"] == len(ci["receipts"]) == 28,
        "artifact count",
    )
    require(
        [e["mission"] for e in ledger["experiments"]] == EXPECTED_MISSIONS, "experiment inventory"
    )
    require(
        {r["id"] for r in history["records"]} == {f"M{i}" for i in EXPECTED_MISSIONS},
        "historical inventory",
    )
    require(
        {r["id"] for r in ledger["coverage"]} == {f"P2-{i:02}" for i in range(1, 9)},
        "coverage inventory",
    )
    require(
        {r["id"] for r in ledger["catalogue_and_visualisation"]}
        == {f"C{i:02}" for i in range(1, 9)},
        "catalogue inventory",
    )
    require(
        {r["id"] for r in ledger["exit_gates"]} == {f"E{i:02}" for i in range(1, 9)},
        "gate inventory",
    )
    require(
        next(g for g in ledger["exit_gates"] if g["id"] == "E08")["status"] == "review_pending",
        "review gate",
    )
    require(
        {r["id"] for r in ledger["excluded_claims"]} == {f"L62-{i:02}" for i in range(1, 6)},
        "exclusion inventory",
    )
    old = load("docs/research/evidence/phase_2_reconciliation_v1.json")
    require(ledger["transit_scenarios"] == old["transit_scenarios"], "transit scenario changed")
    require(
        ledger["transit_production_counts"] == old["transit_production_counts"],
        "transit coverage counts",
    )
    require(
        ledger["inherited_physical_status"] == old["inherited_physical_status"],
        "physical unknown or restriction changed",
    )
    require(ledger["x01"] == "blocked; not closed or automatically deferred", "X01 changed")
    for row in ledger["transit_scenarios"]:
        require(row["observing_enabled"] is False, "strict observing enabled")
        for selector in row["test_selectors"]:
            path, name = selector.split("::", 1)
            require(f"def {name}(" in (ROOT / path).read_text(), f"missing test: {selector}")
    for path, value in ledger["baseline_file_sha256"].items():
        require(digest(git("show", f"{base}:{path}")) == value, f"baseline hash: {path}")
    for path, value in ledger["preserved_tree_oids"].items():
        require(git("rev-parse", f"HEAD:{path}").decode().strip() == value, f"changed tree: {path}")
        require(not git("diff", base, "--", path).strip(), f"worktree change: {path}")
        require(
            not git("ls-files", "--others", "--exclude-standard", path).strip(),
            f"untracked protected file: {path}",
        )
    by_history = {row["id"]: row for row in history["records"]}
    by_ci = {row["id"]: row for row in ci["receipts"]}
    require(len(by_ci) == 28, "duplicate archive mapping")
    checked = 0
    for exp in ledger["experiments"]:
        require(exp["id"] in by_ci, "missing archive receipt")
        receipt = by_ci[exp["id"]]
        require(receipt["artifact_name"] == exp["artifact_name"], "artifact name")
        require(receipt["head"] == base and not receipt["expired"], "artifact identity/expiry")
        require(receipt["implementation_identity_verified"] is True, "payload identity")
        for field in ["archive_sha256", "record_sha256"]:
            require(re.fullmatch(r"[0-9a-f]{64}", receipt[field]) is not None, "digest syntax")
        require(Path(exp["canonical_record"]).name in receipt["archive_members"], "archive member")
        canonical = load(exp["canonical_record"])
        origin = exp["provenance"]["implementation_commit"]
        h = by_history[exp["id"]]
        require(
            pointer(canonical, origin["pointer"]) == origin["value"] == h["commit"],
            "canonical implementation identity",
        )
        require(h["commit_object_present"] is True, "historical source not recovered")
        for check in h["recorded_hash_checks"]:
            require(
                check["matched"] is True and check["expected_sha256"] == check["actual_sha256"],
                "recorded historical hash mismatch",
            )
            require(
                pointer(canonical, check["pointer"]) == check["expected_sha256"],
                "recorded hash pointer",
            )
            if historical_objects:
                require(
                    digest(git("show", f"{h['commit']}:{check['path']}"))
                    == check["expected_sha256"],
                    "historical object bytes",
                )
            checked += 1
        require(
            digest((ROOT / exp["runner"]).read_bytes()) == h["current_runner_sha256"],
            "current runner hash",
        )
        if historical_objects:
            require(
                git("rev-parse", h["commit"] + "^{tree}").decode().strip() == h["commit_tree"],
                "historical tree",
            )
            for path, value in h["import_closure_sha256"].items():
                require(digest(git("show", f"{h['commit']}:{path}")) == value, "import source hash")
    require(checked == history["recorded_file_hash_checks"] == 185, "history check count")
    require(history["recorded_file_hash_mismatches"] == 0, "history failures")
    require(by_ci["M60"]["scientific_status"]["failed_cases"] == 17, "historical M60 failures lost")
    require(by_ci["M56"]["scientific_status"]["failed_trials"] == 9, "historical M56 failures lost")
    require(
        by_ci["M61"]["scientific_status"]["overall_passed"] is True
        and by_ci["M61"]["scientific_status"]["failed_cases"] == 0,
        "current catalogue acceptance",
    )
    require(
        by_ci["M58"]["scientific_status"]["overall_passed"] is True
        and by_ci["M58"]["scientific_status"]["failed_trials"] == 0,
        "current BLS acceptance",
    )
    return {
        "baseline_hashes": len(ledger["baseline_file_sha256"]),
        "experiments": 28,
        "historical_hash_checks": checked,
        "historical_objects_rechecked": historical_objects,
        "protected_trees": len(ledger["preserved_tree_oids"]),
    }


def markdown_targets(paths):
    count = 0
    for path in paths:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            require(((ROOT / path).parent / target).resolve().exists(), f"broken link: {target}")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history", action="store_true", help="Also inspect pre-fetched Git objects"
    )
    args = parser.parse_args()
    ledger = load(LEDGER)
    for field in ["baseline_ci_evidence", "historical_provenance"]:
        require(
            digest((ROOT / ledger[field]).read_bytes()) == ledger[field + "_sha256"],
            f"receipt digest: {field}",
        )
    ci, history = load(ledger["baseline_ci_evidence"]), load(ledger["historical_provenance"])
    result = validate(ledger, ci, history, historical_objects=args.history)
    result["markdown_targets"] = markdown_targets([REPORT, "docs/research/roadmap_status.md"])
    for mutation in ["hash", "scenario", "archive", "physical_zero", "exit", "phase3"]:
        altered, altered_ci = copy.deepcopy(ledger), copy.deepcopy(ci)
        if mutation == "hash":
            key = next(iter(altered["baseline_file_sha256"]))
            altered["baseline_file_sha256"][key] = "0" * 64
        elif mutation == "scenario":
            altered["transit_scenarios"].pop()
        elif mutation == "archive":
            altered_ci["receipts"].pop()
        elif mutation == "physical_zero":
            altered["inherited_physical_status"]["physical_arrival_bound_seconds"] = 0
        elif mutation == "exit":
            altered["phase_2_exit_approved"] = True
        else:
            altered["phase_3_started"] = True
        try:
            validate(altered, altered_ci, history)
        except ValueError:
            continue
        raise ValueError(f"Undetected documentary mutation: {mutation}")
    result["negative_controls_rejected"] = 6
    result["meaning"] = "Documentary integrity only; proposed scope still requires owner review"
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
