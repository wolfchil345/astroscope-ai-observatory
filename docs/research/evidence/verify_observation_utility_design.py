"""M68 offline documentary validation; no observations, fitting or scientific execution."""

import copy
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "3fd937baca1e78c24d3d6a3a637b19a963251d6e"
LEDGER = "docs/research/evidence/observation_utility_design_v1.json"
PROTOCOL = "docs/research/protocols/observation_utility_v1.json"
SOURCES = "docs/research/evidence/observation_utility_sources_v1.json"
CI = "docs/research/evidence/mission67_merge_ci_v1.json"
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


def validate_protocol(p):
    require(p["protocol_id"] == "P3-UTILITY-001-v1", "protocol identity")
    require(p["status"] == "design_for_review_not_execution_ready", "design status")
    require(
        p["current_execution"]
        == {
            "observational_rows_acquired": 0,
            "labels_generated": 0,
            "models_fitted": 0,
            "scientific_evaluations": 0,
            "scientific_acceptance": None,
            "production_changes": False,
            "hardware_control": False,
        },
        "unsupported execution",
    )
    require(p["readiness"]["ready"] is False, "readiness promotion")
    unresolved = p["readiness"]["unresolved"]
    require(
        [r["id"] for r in unresolved] == [f"U68-R{i:02}" for i in range(1, 14)],
        "prerequisite inventory",
    )
    require(len({r["field"] for r in unresolved}) == 13, "duplicate prerequisite")
    for r in unresolved:
        require(r["value"] is None and r["status"] == "unresolved", "invented prerequisite")
        require(r["required_evidence"] and r["responsible_role"], "missing closure evidence")
        require(r["person_assigned"] is None, "invented reviewer")
        require(r["gate"] in {f"U68-G{i:02}" for i in range(1, 7)}, "unknown readiness gate")
    s = p["scope"]
    require(s["sites"] == s["instrument_configurations"] == 1, "scope expansion")
    require(s["primary_predictors"] == ["unchanged_weather_score"], "predictor scope")
    require(
        s["transit"] == "excluded_X01" and s["scheduler_policy_effect"] == "not_identified",
        "physical or causal scope",
    )
    require(
        s["phase_4_started"] is False
        and s["phase_3_exit_approved"] is False
        and s["physical_qualification"] is False,
        "phase promotion",
    )
    c = p["cohort"]
    require(c["source"] == "complete_roster_before_forecast_inspection", "selected roster")
    require(
        c["include_cancellations"] is True and c["include_instrument_failures"] is True,
        "dropped adverse outcomes",
    )
    require(
        c["allow_outcome_based_dropping"] is False
        and c["allow_score_based_roster_selection"] is False,
        "selection leakage",
    )
    require(
        c["primary_weighting"] == "equal_night_then_equal_opportunity_within_night",
        "estimand weighting",
    )
    require(c["study_predictions_control_acquisition"] is False, "self-fulfilling outcome")
    o = p["outcome"]
    require(o["values"] == [0, 1, None] and o["unknown_as_zero"] is False, "unknown outcome")
    require(
        o["independent_of_scores"] is True and o["reference_candidate_imports_allowed"] is False,
        "circular reference",
    )
    require(o["adjudicator_prediction_masking_required"] is True, "unmasked adjudication")
    require(
        all(o[k] is None for k in ["snr_min", "fwhm_max_arcsec", "acquisition_tolerance_seconds"]),
        "invented measurement threshold",
    )
    f = p["forecast"]
    require(f["decision_lead_hours"] == 24, "forecast horizon")
    require(
        f["ordering"] == "initialization<=availability<=capture<=decision<planned_start",
        "forecast ordering",
    )
    require(
        f["availability_evidence_required"] is True
        and f["raw_capture_by_decision_required"] is True
        and f["initialization_alone_sufficient"] is False,
        "late forecast leakage",
    )
    require(
        f["stitched_history_as_prospective"] is False and f["reanalysis_as_predictor"] is False,
        "retrospective substitution",
    )
    require(
        f["unknown_input_imputation"] is False
        and f["missing_policy"] == "U1_equals_U0_with_reason",
        "predictor missingness",
    )
    methods = p["methods"]
    require([m["id"] for m in methods] == ["U0", "U1", "D0"], "method inventory")
    require(
        methods[0]["formula"] == "(k+1)/(n+2)" and methods[1]["formula"] == "(k_b+1)/(n_b+2)",
        "method formula",
    )
    require(all(m["fit_split"] == "training_only" for m in methods[:2]), "test label fitting")
    require(
        methods[1]["edges"] == [0, 20, 40, 60, 80, 100]
        and methods[1]["minimum_resolved_training_bin_nights"] == 20
        and methods[1]["low_support_or_missing"] == "U0",
        "bin or fallback change",
    )
    require(
        methods[2]["calibrated_claim"] is False and methods[2]["kind"] == "diagnostic_only",
        "raw probability promotion",
    )
    require(
        methods[0]["training_weighting"]
        == "each_resolved_row_weight_1_over_resolved_rows_in_its_night"
        and methods[1]["training_weighting"] == "same_U0_row_weights_restricted_to_bin",
        "training weighting",
    )
    split = p["splits"]
    require(
        split["order"] == ["training", "development", "sealed_evaluation"]
        and split["chronological"] is True
        and split["random_row_shuffle"] is False,
        "temporal leakage",
    )
    require(
        split["training_only_fit"] is True and split["refit_on_development"] is False,
        "refit leakage",
    )
    require(split["exact_dates"] is None and split["purge_gap"] is None, "invented split")
    require(
        split["public_archive_is_blind"] is False
        and split["evaluation_access_logged"]
        and split["post_repair_label"] == "exposed_regression",
        "exposure claim",
    )
    m = p["metrics"]
    require(
        m["primary"] == "night_balanced_mean_paired_Brier_U1_minus_U0" and m["loss"] == "(p-y)^2",
        "primary metric",
    )
    require(
        m["unknown_outcome_policy"] == "full_roster_binary_extremal_bounds"
        and m["bound_labels"] == [0, 1]
        and m["complete_case_primary"] is False,
        "missing outcome deletion",
    )
    require(
        m["reliability_edges"] == [0, 0.2, 0.4, 0.6, 0.8, 1] and m["empty_bins_retained"] is True,
        "selective reliability",
    )
    u = p["uncertainty"]
    require(
        u["method"] == "paired_moving_block_bootstrap_calendar_nights"
        and u["paired"] is True
        and u["resample_rows_independently"] is False,
        "unpaired or IID inference",
    )
    require(
        u["qualified"] is False
        and u["development_coverage_checks_required"] is True
        and u["unqualified_action"] == "descriptive_only",
        "unqualified inference",
    )
    require(
        u["retain_empty_calendar_nights"]
        and not u["bridge_campaign_gaps"]
        and not u["wrap_end_to_start"]
        and u["condition_on_training_fit"],
        "resampling scope",
    )
    require(
        all(u[k] is None for k in ["block_length", "replicates", "rng", "quantile_rule"]),
        "invented inference configuration",
    )
    a = p["acceptance"]
    require(
        a["design_review"] == "pending_merge" and a["evaluation_ready"] is False,
        "approval or readiness claim",
    )
    require(
        a["skill_rule"]
        == ("qualified_upper95_worst_case_paired_difference_below_negative_delta_and_precision_met")
        and a["all_readiness_gates_required"] is True,
        "skill acceptance weakened",
    )
    require(
        all(
            a[k] is None
            for k in [
                "delta",
                "max_interval_width",
                "min_nights",
                "min_class_support",
                "predictor_coverage_min",
                "outcome_coverage_min",
                "reliability_tolerance",
                "scientific_acceptance",
            ]
        ),
        "invented acceptance result or threshold",
    )
    require(
        a["production_promotion"] is False
        and a["phase_3_exit"] is False
        and a["optional_stopping"] is False,
        "promotion or optional stopping",
    )
    require(
        [c["id"] for c in p["controls"]] == [f"U68-C{i:02}" for i in range(1, 19)],
        "future control inventory",
    )
    require(
        all(c["status"] == "specified_not_executed" for c in p["controls"]),
        "unexecuted control claim",
    )
    off = p["offline"]
    require(
        off["raw_hashes_required"]
        and off["source_and_environment_required"]
        and not off["network_during_analysis"]
        and off["independent_references_required"]
        and off["restricted_raw_data_limitation_required"]
        and off["archive_access_journal_required"],
        "offline claim",
    )
    nxt = p["next_mission"]
    require(
        nxt["number"] == 69
        and nxt["status"] == "proposed_not_started"
        and not any(
            nxt[k]
            for k in ["bulk_acquisition", "outcome_evaluation", "model_fitting", "hardware_control"]
        ),
        "next mission expansion",
    )


def validate_evidence(d, ci, sources):
    require(d["mission"] == 68 and d["baseline_commit"] == BASE, "baseline identity")
    require(
        d["design_approval"] == "pending_review_merge"
        and d["scientific_acceptance"] is None
        and not d["execution_ready"],
        "ledger promotion",
    )
    require(
        d["new_scientific_results"] == d["new_scientific_tests"] == d["new_ci_artifacts"] == 0
        and d["production_changes"] is False,
        "ledger scope",
    )
    require(
        d["phase_3_exit_approved"] is False and d["physical_qualification"] is False,
        "ledger physical promotion",
    )
    prior = read("docs/research/evidence/schedule_evaluation_v1.json")
    for key in ["excluded_claims", "inherited_physical_status", "transit_production_counts"]:
        require(d[key] == prior[key], "inherited restriction: " + key)
    require(
        d["phase_gates"]
        == {
            "P3-E01": "accepted_M63",
            "P3-E02": "accepted_M64",
            "P3-E03": "accepted_finite_study_M67",
            "P3-E04": "accepted_finite_study_M67",
            "P3-E05": "open_design_only_execution_blocked",
            "P3-E06": "open_not_approved",
        },
        "phase gates",
    )
    require(
        ci["merge_commit"] == BASE and ci["pr_head"] == d["predecessor_head"],
        "merge receipt identity",
    )
    require(
        ci["conclusion"] == "success"
        and [ci[k] for k in ["run_id", "candidate_run_id", "evaluation_run_id"]]
        == [40339372041, 40339372101, 40339372093],
        "post-merge workflows",
    )
    require(ci["tests"] == {"passed": 10201, "historical_expected_failures": 26}, "CI tests")
    require(
        ci["artifact_count"] == ci["archives_downloaded"] == len(ci["receipts"]) == 32,
        "archive completeness",
    )
    expected = {
        r["id"]: r["artifact_name"]
        for r in read("docs/research/evidence/phase_2_exit_readiness_v1.json")["experiments"]
    }
    expected.update(
        {
            "M64": "schedule-corpus-validation-record",
            "M65": "schedule-baselines-validation-record",
            "M66": "schedule-candidate-validation-record",
            "M67": "schedule-evaluation-validation-record",
        }
    )
    require({r["id"]: r["artifact_name"] for r in ci["receipts"]} == expected, "archive inventory")
    for r in ci["receipts"]:
        require(
            r["head"] == BASE and r["implementation_identity_verified"] and r["expired"] is False,
            "artifact implementation",
        )
        require(
            all(re.fullmatch("[0-9a-f]{64}", r[k]) for k in ["archive_sha256", "record_sha256"]),
            "artifact digest",
        )
    require(
        sources["data_acquired"] is False and sources["offline_runtime_downloads"] is False,
        "source review scope",
    )
    require(
        [r["id"] for r in sources["sources"]] == [f"R{i}" for i in range(1, 7)],
        "primary source inventory",
    )
    for r in sources["sources"]:
        require(
            r["status"] == "read_not_dataset_qualified"
            and r["limitation"]
            and r["locator"]
            and r["url"].startswith("https://"),
            "source applicability",
        )


def validate_files(d):
    # Read the immutable baseline in one Git operation; no network or science imports.
    archive = tarfile.open(fileobj=io.BytesIO(git("archive", BASE)), mode="r:")
    baseline = {
        m.name: sha(archive.extractfile(m).read())
        for m in archive.getmembers()
        if m.isfile() and m.name != ROADMAP
    }
    require(baseline == d["preserved_baseline_sha256"], "baseline hash inventory")
    for path, digest in baseline.items():
        require(sha((ROOT / path).read_bytes()) == digest, "changed baseline: " + path)
    for path, digest in d["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, "changed mission file: " + path)
    current = set(
        git("ls-files", "--cached", "--others", "--exclude-standard").decode().splitlines()
    )
    require(
        current == set(baseline) | {ROADMAP, LEDGER} | set(d["file_sha256"]),
        "unexpected new or removed file",
    )
    require(
        git("rev-parse", BASE + "^{tree}") == git("rev-parse", d["predecessor_head"] + "^{tree}"),
        "M67 merge tree differs",
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


def negative_controls(p, d, ci, sources):
    # Each mutation must trigger its intended semantic guard, not merely a hash mismatch.
    mutations = [
        ("p", ["cohort", "study_predictions_control_acquisition"], True, "self-fulfilling outcome"),
        ("p", ["current_execution", "models_fitted"], 1, "unsupported execution"),
        ("p", ["readiness", "ready"], True, "readiness promotion"),
        ("p", ["readiness", "unresolved", 0, "value"], "invented", "invented prerequisite"),
        ("p", ["cohort", "include_cancellations"], False, "dropped adverse outcomes"),
        ("p", ["outcome", "unknown_as_zero"], True, "unknown outcome"),
        ("p", ["outcome", "independent_of_scores"], False, "circular reference"),
        ("p", ["forecast", "raw_capture_by_decision_required"], False, "late forecast leakage"),
        ("p", ["forecast", "reanalysis_as_predictor"], True, "retrospective substitution"),
        ("p", ["methods", 1, "fit_split"], "evaluation", "test label fitting"),
        ("p", ["methods", 2, "calibrated_claim"], True, "raw probability promotion"),
        ("p", ["splits", "random_row_shuffle"], True, "temporal leakage"),
        ("p", ["metrics", "complete_case_primary"], True, "missing outcome deletion"),
        ("p", ["uncertainty", "resample_rows_independently"], True, "unpaired or IID inference"),
        ("p", ["uncertainty", "qualified"], True, "unqualified inference"),
        ("p", ["acceptance", "delta"], 0, "invented acceptance result or threshold"),
        ("p", ["scope", "phase_4_started"], True, "phase promotion"),
        ("p", ["next_mission", "bulk_acquisition"], True, "next mission expansion"),
        (
            "d",
            ["inherited_physical_status", "physical_arrival_bound_seconds"],
            0,
            "inherited restriction: inherited_physical_status",
        ),
        ("ci", ["archives_downloaded"], 31, "archive completeness"),
        ("ci", ["receipts", 0, "head"], "wrong", "artifact implementation"),
        ("ci", ["evaluation_run_id"], 40322726657, "post-merge workflows"),
        ("s", ["data_acquired"], True, "source review scope"),
    ]
    for kind, path, value, expected in mutations:
        items = copy.deepcopy(dict(p=p, d=d, ci=ci, s=sources))
        target = items[kind]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            validate_protocol(items["p"])
            validate_evidence(items["d"], items["ci"], items["s"])
        except ValueError as error:
            require(str(error) == expected, "mutation failed for unrelated reason: " + str(error))
        else:
            raise ValueError("missed documentary mutation: " + expected)
    return len(mutations)


def main():
    p, d, ci, sources = read(PROTOCOL), read(LEDGER), read(CI), read(SOURCES)
    validate_protocol(p)
    validate_evidence(d, ci, sources)
    files, links = validate_files(d)
    rejected = negative_controls(p, d, ci, sources)
    print(
        json.dumps(
            dict(
                passed=True,
                mission=68,
                preserved_baseline_files=files,
                checked_mission_hashes=len(d["file_sha256"]),
                relative_links=links,
                primary_sources=6,
                unresolved_execution_prerequisites=13,
                future_controls_specified_not_executed=18,
                documentary_mutants_rejected=rejected,
                observational_rows_acquired=0,
                models_fitted=0,
                scientific_evaluations=0,
                execution_ready=False,
                meaning="Documentary integrity only; design review pending",
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
