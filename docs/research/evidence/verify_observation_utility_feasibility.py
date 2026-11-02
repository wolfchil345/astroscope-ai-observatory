"""M69 offline documentary checks; no observational acquisition or science run."""

import copy
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "38c0b5e44a2fee647653574d75c995ea0abd27dd"
HEAD68 = "aa5c4e3015cdc9f76e680ea67469e05215051308"
LEDGER = "docs/research/evidence/observation_utility_feasibility_v1.json"
SPEC = "docs/research/protocols/observation_utility_acquisition_v1.json"
SOURCES = "docs/research/evidence/observation_utility_feasibility_sources_v1.json"
CI = "docs/research/evidence/mission68_merge_ci_v1.json"
PRIOR = "docs/research/evidence/observation_utility_design_v1.json"
PROTOCOL = "docs/research/protocols/observation_utility_v1.json"
ROADMAP = "docs/research/roadmap_status.md"


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def validate(p, s, d, ci):
    require(
        p["specification_id"] == "P3-UTILITY-ACQUISITION-001-v1"
        and p["parent_protocol"] == "P3-UTILITY-001-v1"
        and p["mission"] == 69,
        "specification identity",
    )
    require(
        p["decision"] == "no_go_current_evidence"
        and p["scope"] == "documentation_source_feasibility_only"
        and p["review_status"] == "pending_review_merge"
        and p["execution_ready"] is False
        and p["acquisition_authorized"] is False,
        "acquisition promotion",
    )
    for key in [
        "selected_source",
        "selected_programme",
        "selected_site",
        "selected_instrument",
        "source_owner",
        "forecast_model",
        "forecast_version",
        "scientific_acceptance",
    ]:
        require(p[key] is None, "invented selection")
    require(
        p["current_execution"]
        == dict(
            observational_rows_acquired=0,
            labels_generated=0,
            models_fitted=0,
            scientific_evaluations=0,
            hardware_control=False,
            production_changes=False,
        ),
        "unsupported execution",
    )
    require(
        all(
            type(v) is int
            for k, v in p["current_execution"].items()
            if k not in {"hardware_control", "production_changes"}
        ),
        "execution count type",
    )
    require(
        p["phase_3_exit_approved"] is False
        and p["phase_4_started"] is False
        and p["physical_qualification"] is False,
        "phase promotion",
    )
    expected_routes = {
        "LCO": ("conditional_not_qualified", list(range(1, 8))),
        "ESO": ("conditional_not_qualified", list(range(8, 13))),
        "OM_HISTORY": ("excluded_primary_predictor", [13, 16]),
        "OM_RUN": ("insufficient_without_contemporaneous_receipts", [14, 15, 16]),
        "OM_PROSPECTIVE": ("conditional_not_started", [14, 15, 16]),
    }
    require([r["id"] for r in p["routes"]] == list(expected_routes), "route inventory")
    for r in p["routes"]:
        status, ids = expected_routes[r["id"]]
        require(
            r["status"] == status
            and r["source_ids"] == [f"S{i:02}" for i in ids]
            and len(r["blockers"]) > 0,
            "route disposition",
        )
        require(
            all(
                r[k] is False
                for k in [
                    "complete_roster_verified",
                    "independent_outcomes_qualified",
                    "rights_qualified",
                    "primary_predictor_admissible",
                ]
            ),
            "source qualification promotion",
        )
    require(
        p["licence_discrepancy"]
        == dict(
            source_ids=["S06", "S07"],
            reported_versions=["CC BY-NC 4.0", "CC BY-NC 2.0"],
            applicable_version=None,
            resolved=False,
        ),
        "rights conflict erased",
    )
    require(
        p["coverage"]
        == dict(
            actual_rows=None,
            actual_nights=None,
            class_balance=None,
            missingness=None,
            forecast_qualified_fraction=None,
            provider_claims_are_cohort_coverage=False,
        ),
        "invented cohort coverage",
    )
    rules = {
        "complete_predecision_roster_required": True,
        "include_cancellations": True,
        "one_opportunity_per_planned_exposure": True,
        "actual_time_as_planned_time_allowed": False,
        "unknown_as_zero": False,
        "score_derived_outcomes_allowed": False,
        "raw_capture_by_decision_required": True,
        "initialization_proves_capture": False,
        "stitched_or_reanalysis_substitution": False,
        "seven_field_lineage_required": True,
        "unqualified_forecast": "retain_opportunity_U1_equals_U0_D0_null",
        "historical_public_as_sealed_evaluation": False,
        "restricted_raw_claimed_public_offline": False,
        "study_predictions_control_acquisition": False,
    }
    for key, value in rules.items():
        require(
            type(p["preserved_rules"][key]) is type(value) and p["preserved_rules"][key] == value,
            "rule: " + key,
        )
    require(set(p["preserved_rules"]) == set(rules), "rule inventory")
    require(
        p["pilot"]
        == dict(
            status="proposed_not_executed",
            requires_separate_scope=True,
            requires_owner_packet=True,
            max_sites=1,
            max_setups=1,
            max_programmes=1,
            max_consecutive_nights=7,
            max_opportunities=100,
            max_objects=500,
            max_bytes=2147483648,
            max_concurrent_requests=1,
            max_requests_per_second=1,
            cap_is_scientific_sample_size=False,
            incomplete_roster_disposition="failed_feasibility_not_accepted_cohort",
            all_inspected_outcomes="development_exposed",
        ),
        "pilot scope",
    )
    expected = [
        dict(
            id=r["id"],
            field=r["field"],
            gate=r["gate"],
            status="unresolved",
            value=None,
            person_assigned=None,
            required_evidence=r["required_evidence"],
        )
        for r in read(PROTOCOL)["readiness"]["unresolved"]
    ]
    require(p["prerequisites"] == expected, "prerequisite promotion")
    require(
        p["next_mission"]
        == dict(
            number=70,
            title="Source-owner Evidence Intake and Go/No-go Review",
            status="conditional_not_started",
            condition="named_source_owner_programme_and_evidence_packet",
            without_condition="pause_workstream",
            bulk_acquisition=False,
            model_fitting=False,
            outcome_evaluation=False,
            hardware_control=False,
        ),
        "next mission expansion",
    )
    require(
        s["mission"] == 69
        and s["data_acquired"] is False
        and s["offline_runtime_downloads"] is False
        and s["source_bytes_vendored"] is False,
        "source review scope",
    )
    require(
        [r["id"] for r in s["sources"]] == [f"S{i:02}" for i in range(1, 17)], "source inventory"
    )
    for r in s["sources"]:
        require(
            r["status"] == "documentation_read_not_dataset_qualified"
            and r["reviewed_date_utc"] == "2026-11-02"
            and r["locator"]
            and r["support"]
            and r["limitation"]
            and r["url"].startswith("https://"),
            "source evidence",
        )
    require(
        len(s["failed_retrievals"]) == 1
        and s["failed_retrievals"][0]["result"] == "not_accessible_via_tool",
        "failed retrieval erased",
    )
    prior = read(PRIOR)
    require(
        d["mission"] == 69
        and d["baseline_commit"] == BASE
        and d["predecessor_head"] == HEAD68
        and d["baseline_accepted"] is True,
        "baseline identity",
    )
    for key in [
        "excluded_claims",
        "inherited_physical_status",
        "transit_production_counts",
        "ci",
        "phase_gates",
    ]:
        require(d[key] == prior[key], "inherited restriction: " + key)
    require(
        d["review_status"] == "pending_review_merge"
        and d["execution_ready"] is False
        and d["scientific_acceptance"] is None
        and d["physical_qualification"] is False
        and d["phase_3_exit_approved"] is False
        and d["production_changes"] is False
        and d["new_scientific_results"] == d["new_scientific_tests"] == d["new_ci_artifacts"] == 0,
        "ledger promotion",
    )
    require(
        ci["mission"] == 68
        and ci["merge_commit"] == BASE
        and ci["pr_head"] == HEAD68
        and ci["conclusion"] == "success",
        "merge receipt identity",
    )
    require(
        [ci[k] for k in ["run_id", "candidate_run_id", "evaluation_run_id"]]
        == [41425793437, 41425793656, 41425793368],
        "post-merge workflows",
    )
    require(ci["tests"] == dict(passed=10201, historical_expected_failures=26), "CI tests")
    require(
        ci["artifact_count"] == ci["archives_downloaded"] == len(ci["receipts"]) == 32,
        "archive completeness",
    )
    old_ci = read("docs/research/evidence/mission67_merge_ci_v1.json")
    require(
        {r["id"]: r["artifact_name"] for r in ci["receipts"]}
        == {r["id"]: r["artifact_name"] for r in old_ci["receipts"]},
        "archive inventory",
    )
    for r in ci["receipts"]:
        require(
            r["head"] == BASE
            and r["implementation_identity_verified"] is True
            and r["expired"] is False,
            "artifact implementation",
        )
        require(
            all(re.fullmatch("[0-9a-f]{64}", r[k]) for k in ["archive_sha256", "record_sha256"]),
            "artifact digest",
        )
    require(
        ci["documentary_checks"]["passed"] is True
        and ci["documentary_checks"]["documentary_mutants_rejected"] == 23,
        "M68 documentary check",
    )


def validate_files(d):
    with tarfile.open(fileobj=io.BytesIO(git("archive", BASE)), mode="r:") as archive:
        baseline = {
            m.name: sha(archive.extractfile(m).read())
            for m in archive.getmembers()
            if m.isfile() and m.name != ROADMAP
        }
    require(baseline == d["preserved_baseline_sha256"], "baseline hash inventory")
    for path, digest in (baseline | d["file_sha256"]).items():
        require(sha((ROOT / path).read_bytes()) == digest, "changed file: " + path)
    current = set(
        git("ls-files", "--cached", "--others", "--exclude-standard").decode().splitlines()
    )
    require(
        current == set(baseline) | {ROADMAP, LEDGER} | set(d["file_sha256"]),
        "unexpected new or removed file",
    )
    require(
        git("rev-parse", BASE + "^{tree}") == git("rev-parse", HEAD68 + "^{tree}"),
        "M68 merge tree differs",
    )
    links = 0
    for path in d["markdown_paths"]:
        for target in re.findall(r"\]\(([^)]+)\)", (ROOT / path).read_text()):
            if "://" in target or target.startswith("#"):
                continue
            require(
                ((ROOT / path).parent / target.split("#")[0]).resolve().exists(),
                "broken link: " + target,
            )
            links += 1
    return len(baseline), links


def negative_controls(p, s, d, ci):
    # Each corrupt claim must fail semantically, not merely through a file hash.
    mutations = [
        ("p", ["acquisition_authorized"], True, "acquisition promotion"),
        ("p", ["selected_site"], "invented", "invented selection"),
        ("p", ["current_execution", "models_fitted"], 1, "unsupported execution"),
        ("p", ["phase_4_started"], True, "phase promotion"),
        ("p", ["routes", 0, "complete_roster_verified"], True, "source qualification promotion"),
        ("p", ["routes", 2, "status"], "qualified", "route disposition"),
        ("p", ["licence_discrepancy", "resolved"], True, "rights conflict erased"),
        ("p", ["coverage", "actual_nights"], 100, "invented cohort coverage"),
        ("p", ["pilot", "cap_is_scientific_sample_size"], True, "pilot scope"),
        ("p", ["prerequisites", 0, "value"], "closed", "prerequisite promotion"),
        ("p", ["next_mission", "bulk_acquisition"], True, "next mission expansion"),
        ("s", ["source_bytes_vendored"], True, "source review scope"),
        ("s", ["failed_retrievals"], [], "failed retrieval erased"),
        (
            "d",
            ["inherited_physical_status", "physical_arrival_bound_seconds"],
            0,
            "inherited restriction: inherited_physical_status",
        ),
        ("ci", ["archives_downloaded"], 31, "archive completeness"),
        ("ci", ["receipts", 0, "head"], "wrong", "artifact implementation"),
        ("ci", ["evaluation_run_id"], 0, "post-merge workflows"),
    ]
    for key, value in p["preserved_rules"].items():
        mutations.append(
            (
                "p",
                ["preserved_rules", key],
                not value if type(value) is bool else "drop_row",
                "rule: " + key,
            )
        )
    for kind, path, value, expected in mutations:
        items = copy.deepcopy(dict(p=p, s=s, d=d, ci=ci))
        target = items[kind]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            validate(**items)
        except ValueError as error:
            require(str(error) == expected, "unrelated mutation failure: " + str(error))
        else:
            raise ValueError("missed documentary mutation: " + expected)
    return len(mutations)


def main():
    p, s, d, ci = read(SPEC), read(SOURCES), read(LEDGER), read(CI)
    validate(p, s, d, ci)
    files, links = validate_files(d)
    rejected = negative_controls(p, s, d, ci)
    print(
        json.dumps(
            dict(
                passed=True,
                mission=69,
                preserved_baseline_files=files,
                checked_mission_hashes=len(d["file_sha256"]),
                relative_links=links,
                primary_sources=16,
                routes_reviewed=5,
                qualified_combinations=0,
                unresolved_execution_prerequisites=13,
                future_controls_specified_not_executed=18,
                documentary_mutants_rejected=rejected,
                observational_rows_acquired=0,
                models_fitted=0,
                scientific_evaluations=0,
                execution_ready=False,
                meaning="Documentary integrity only; current no-go and conditional specification",
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
