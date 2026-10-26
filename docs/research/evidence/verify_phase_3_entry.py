"""Offline Mission 63 documentary checks; no scheduler, oracle or corpus evaluation."""

import copy
import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = "docs/research/evidence/phase_3_entry_v1.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def validate_protocol(p):
    require(p["protocol_id"] == "P3-SCHEDULE-001-v1", "protocol identity")
    require(p["status"] == "frozen_for_review_not_evaluated", "protocol status")
    require(
        p["current_execution"]
        == {
            "generated_primary_cases": 0,
            "scientific_evaluations": 0,
            "optimizer_implemented": False,
            "reference_oracle_implemented": False,
            "scientific_acceptance": None,
        },
        "unsupported execution claim",
    )
    m = p["model"]
    require(m["idle_preserves_last_target"] is True, "idle history lost")
    require(m["idle_always_allowed"] is True, "idle removed")
    require(
        m["first_acquisition_cost"] == m["terminal_reward"] == m["idle_reward"] == 0,
        "boundary cost changed",
    )
    require(m["physical_cost_model"] is False, "physical cost claim")
    require(m["slot_minutes"] == 60 and m["resource_count"] == 1, "model domain")
    require(m["usable_rule"] == "eligibility is true AND score is not null", "missing policy")
    require({x["id"] for x in p["methods"]} == {"B0", "B1", "B2", "E0"}, "method coverage")
    c = p["primary_corpus"]
    require([x["id"] for x in c["families"]] == [f"F{i}" for i in range(1, 7)], "families")
    require(c["slot_counts"] == [3, 6, 9] and c["target_counts"] == [2, 3], "dimensions")
    require(c["replicates"] == [0, 1, 2, 3] and c["switch_costs"] == [0, 5, 20], "profiles")
    expected = []
    for f, n, m, r, cost in itertools.product(
        c["families"], c["slot_counts"], c["target_counts"], c["replicates"], c["switch_costs"]
    ):
        core = f"P3-{f['id']}-N{n:02}-M{m:02}-R{r:02}"
        expected.append(
            {
                "id": f"{core}-C{cost:02}",
                "core_id": core,
                "family": f["id"],
                "slots": n,
                "targets": m,
                "replicate": r,
                "switch_cost": cost,
                "split": "development" if r < 2 else "evaluation_reserved",
                "status": "planned_not_generated",
            }
        )
    require(c["cases"] == expected, "case inventory or split changed")
    require(c["core_count"] == len({x["core_id"] for x in expected}) == 144, "core count")
    require(c["profile_case_count"] == len(expected) == 432, "case count")
    for split, key in [
        ("development", "development_count"),
        ("evaluation_reserved", "evaluation_reserved_count"),
    ]:
        require(sum(x["split"] == split for x in expected) == c[key] == 216, "split count")
    require(
        c["max_enumerated_paths_per_case"]
        == (max(c["target_counts"]) + 1) ** max(c["slot_counts"])
        == 262144,
        "enumeration bound",
    )
    require(
        p["splits"]["development_replicates"] == [0, 1]
        and p["splits"]["evaluation_reserved_replicates"] == [2, 3],
        "split policy",
    )
    require(
        p["splits"]["blind"] is False and p["splits"]["trained_model"] is False,
        "unsupported holdout claim",
    )
    require(
        [x["id"] for x in p["controls"]] == [f"P3-C{i:02}" for i in range(1, 17)],
        "control inventory",
    )
    require(
        [x["id"] for x in p["invalid_input_classes"]] == [f"P3-I{i:02}" for i in range(1, 17)],
        "invalid-class inventory",
    )
    for control in p["controls"]:
        require(control["status"] == "specified_not_executed", "control execution claim")
        n, m = control["slots"], control["targets"]
        require(1 <= n <= 9 and 0 <= m <= 3, "control dimensions")
        for key in ["scores", "eligibility"]:
            rows = control[key]
            require(len(rows) == n and all(len(row) == m for row in rows), "control shape")
        for row in control["scores"]:
            require(
                all(x is None or type(x) is int and 0 <= x <= 100 for x in row),
                "control score type",
            )
        for row in control["eligibility"]:
            require(all(x is None or type(x) is bool for x in row), "control eligibility type")
    old = read("validation/fixtures/heuristic_characterisation_v1.json")
    reference = next(x for x in old["schedules"] if x["id"] == "alternating-cost20")
    retained = next(x for x in p["controls"] if x["id"] == "P3-C07")
    require(
        retained["scores"] == reference["scores"]
        and retained["switch_cost"] == reference["switch_penalty"],
        "M55 input reuse",
    )
    a = p["acceptance"]
    require(
        a["integer_objective_tolerance"]
        == a["required_B2_regret"]
        == a["required_feasibility_violations"]
        == 0,
        "acceptance weakened",
    )
    require(a["required_B2_canonical_path_match"] is True, "canonical path requirement")
    require(a["required_B1_improvement_over_B0"] is None, "assumed baseline improvement")
    require(
        a["allow_case_dropping"] is False and a["require_all_cases"] is True,
        "case omission allowed",
    )
    require(p["adapter"]["production_changes"] is False, "production promotion")
    require(
        p["next_mission"]["number"] == 64 and p["next_mission"]["status"] == "proposed_not_started",
        "next mission state",
    )
    return len(expected)


def validate_transition(d, ci):
    require(d["phase_2_exit_approved"] is True, "accepted transition missing")
    require(
        d["phase_2_exit_scope"] == "limited_to_M62_documented_claims_and_exclusions",
        "unrestricted exit",
    )
    require(
        d["phase_3_started"] is True and d["phase_3_status"] == "active_entry_protocol_only",
        "entry status",
    )
    require(d["protocol_approval"] == "pending_review_merge", "unapproved protocol")
    require(d["phase_3_exit_approved"] is False, "premature Phase 3 exit")
    require(
        d["new_scientific_results"] == d["new_scientific_tests"] == d["new_ci_artifacts"] == 0
        and d["production_changes"] is False,
        "unsupported mission scope",
    )
    old = read("docs/research/evidence/phase_2_exit_readiness_v1.json")
    require(
        old["phase_2_exit_approved"] is False and old["phase_3_started"] is False,
        "historical pre-approval ledger rewritten",
    )
    for key in ["inherited_physical_status", "excluded_claims", "transit_production_counts", "x01"]:
        require(d[key] == old[key], f"inherited restriction: {key}")
    require(
        {g["id"] for g in d["gates"]} == {f"P3-E{i:02}" for i in range(1, 7)}, "entry gate coverage"
    )
    base = d["baseline_commit"]
    require(base == d["predecessor"]["merged_commit"] == ci["baseline_commit"], "merge identity")
    require(ci["conclusion"] == "success" and ci["run_id"] == 40271565621, "baseline CI")
    require(ci["tests"] == {"passed": 8356, "historical_expected_failures": 26}, "CI totals")
    require(
        ci["artifact_count"] == ci["archives_downloaded"] == len(ci["receipts"]) == 28,
        "receipt completeness",
    )
    expected = {x["id"]: x["artifact_name"] for x in old["experiments"]}
    require({x["id"]: x["artifact_name"] for x in ci["receipts"]} == expected, "artifact mapping")
    for r in ci["receipts"]:
        require(
            r["head"] == base and r["implementation_identity_verified"] and r["expired"] is False,
            "artifact identity",
        )
        require(
            all(re.fullmatch(r"[0-9a-f]{64}", r[k]) for k in ["archive_sha256", "record_sha256"]),
            "digest syntax",
        )
    for path, value in d["baseline_file_sha256"].items():
        require(sha(git("show", f"{base}:{path}")) == value, f"baseline hash: {path}")
    for path, value in d["preserved_tree_oids"].items():
        require(git("rev-parse", f"HEAD:{path}").decode().strip() == value, f"tree: {path}")
        require(not git("diff", base, "--", path).strip(), f"source changed: {path}")
        require(
            not git("ls-files", "--others", "--exclude-standard", path).strip(),
            f"new protected file: {path}",
        )
    require(
        git("rev-parse", base + "^{tree}")
        == git("rev-parse", d["predecessor"]["head_commit"] + "^{tree}"),
        "merge tree",
    )


def markdown_links(paths):
    count = 0
    for path in paths:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" in target or target.startswith("#"):
                continue
            require(
                ((ROOT / path).parent / target.split("#", 1)[0]).resolve().exists(),
                f"broken link: {path}: {target}",
            )
            count += 1
    return count


def main():
    d = read(LEDGER)
    for key in ["baseline_ci_evidence", "protocol", "report"]:
        require(sha((ROOT / d[key]).read_bytes()) == d[key + "_sha256"], f"file digest: {key}")
    p, ci = read(d["protocol"]), read(d["baseline_ci_evidence"])
    cases = validate_protocol(p)
    validate_transition(d, ci)
    for mutation in [
        "split",
        "blind",
        "history",
        "tolerance",
        "result",
        "scope",
        "physical",
        "archive",
    ]:
        pd, dd, cd = copy.deepcopy(p), copy.deepcopy(d), copy.deepcopy(ci)
        if mutation == "split":
            pd["primary_corpus"]["cases"][0]["split"] = "evaluation_reserved"
        elif mutation == "blind":
            pd["splits"]["blind"] = True
        elif mutation == "history":
            pd["model"]["idle_preserves_last_target"] = False
        elif mutation == "tolerance":
            pd["acceptance"]["integer_objective_tolerance"] = 1
        elif mutation == "result":
            pd["current_execution"]["scientific_evaluations"] = 1
        elif mutation == "scope":
            dd["phase_2_exit_scope"] = "unrestricted"
        elif mutation == "physical":
            dd["inherited_physical_status"]["physical_arrival_bound_seconds"] = 0
        else:
            cd["receipts"].pop()
        try:
            validate_protocol(pd)
            validate_transition(dd, cd)
        except ValueError:
            continue
        raise ValueError(f"Missed documentary mutation: {mutation}")
    print(
        json.dumps(
            {
                "planned_profile_ids": cases,
                "specified_controls": len(p["controls"]),
                "specified_invalid_classes": len(p["invalid_input_classes"]),
                "baseline_hashes": len(d["baseline_file_sha256"]),
                "archives": len(ci["receipts"]),
                "protected_entries": len(d["preserved_tree_oids"]),
                "negative_controls_rejected": 8,
                "relative_links": markdown_links(
                    [
                        d["report"],
                        "docs/research/roadmap_status.md",
                        "docs/research/phase_2_exit_readiness.md",
                    ]
                ),
                "scientific_evaluations": 0,
                "meaning": "Documentary checks only; protocol review pending",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
