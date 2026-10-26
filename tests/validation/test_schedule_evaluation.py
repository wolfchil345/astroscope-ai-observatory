"""M67 adapter preflight: development computations only; reserved inputs used for guards."""

import copy
import json
from datetime import UTC, datetime

import pytest

from astroscope import schedule
from validation import schedule_baselines, schedule_candidate, schedule_evaluation
from validation.schedule_baseline_audit import offline_adapter
from validation.schedule_baseline_checks import check_result
from validation.schedule_candidate_checks import check_candidate
from validation.schedule_corpus import ROOT, read_json, serialize, sha
from validation.schedule_corpus_checks import invalid_cases
from validation.schedule_evaluation import (
    CONFIG,
    FREEZE,
    FROZEN_REQUIRED,
    INPUT_PATHS,
    bind_method,
    check_config,
    evaluation_session,
    frozen_case,
    run_method,
    verify_freeze,
)
from validation.schedule_evaluation_audit import aggregate, evaluate_cases, inputs, measure
from validation.schedule_evaluation_checks import verify_journal

CASES, REFERENCES, OLD = inputs()
DEVELOPMENT = [c for c in CASES if c["split"] != "evaluation_reserved"]
RESERVED = [c for c in CASES if c["split"] == "evaluation_reserved"]
CONTROL = next(c for c in DEVELOPMENT if c["case_id"] == "P3-C06")


@pytest.mark.parametrize("case", DEVELOPMENT, ids=lambda c: c["case_id"])
def test_adapter_preserves_every_development_output_and_metric(case):
    before = copy.deepcopy(case)
    with offline_adapter():
        for method in ["B0", "B1", "B2"]:
            output = run_method(method, case)
            assert output == OLD[case["case_id"]][method]["output"]
            metrics = (
                check_candidate(case, output, REFERENCES[case["case_id"]])
                if method == "B2"
                else check_result(case, output, method, REFERENCES[case["case_id"]])
            )
            assert metrics == OLD[case["case_id"]][method]["metrics"]
    assert case == before


@pytest.mark.parametrize("case", RESERVED, ids=lambda c: c["case_id"])
def test_reserved_rejected_without_session_and_with_relabelling(case):
    for method in ["B0", "B1", "B2"]:
        with pytest.raises(ValueError, match="active verified session"):
            bind_method(method, case)
        changed = copy.deepcopy(case)
        changed.update(split="development", replicate=0)
        with pytest.raises(ValueError, match="frozen corpus"):
            bind_method(method, changed)


@pytest.mark.parametrize("identity,case", list(invalid_cases(CONTROL)))
def test_malformed_cases_rejected_before_binding(identity, case):
    for method in ["B0", "B1", "B2"]:
        with pytest.raises(ValueError):
            bind_method(method, case)


@pytest.mark.parametrize(
    "field", ["scores", "eligibility", "start_utc", "switch_cost", "provenance", "case_id"]
)
def test_valid_but_changed_frozen_cases_rejected(field):
    c = copy.deepcopy(CONTROL)
    if field == "scores":
        c[field][0][0] -= 1
    elif field == "eligibility":
        c[field][0][0] = None
    elif field == "start_utc":
        c[field] = "2024-03-21T00:00:00Z"
    elif field == "switch_cost":
        c[field] += 1
    elif field == "provenance":
        c[field]["transformations"].append("unregistered")
    else:
        c[field] = "P3-unregistered"
    with pytest.raises(ValueError, match="frozen corpus"):
        bind_method("B2", c)


def test_private_globals_reuse_code_without_modifying_original_guards():
    for method, original in [
        ("B0", schedule_baselines.b0),
        ("B1", schedule_baselines.b1),
        ("B2", schedule_candidate.b2),
    ]:
        guard = original.__globals__["development_case"]
        bound = bind_method(method, CONTROL)
        assert bound.__code__ is original.__code__ and bound.__globals__ is not original.__globals__
        assert original.__globals__["development_case"] is guard
        if method == "B0":
            assert (
                bound.__globals__["decode_blocks"].__code__
                is schedule_baselines.decode_blocks.__code__
            )
        other = next(c for c in DEVELOPMENT if c["case_id"] == "P3-C07")
        with pytest.raises(ValueError, match="another case"):
            bound(other)


def test_b0_calls_actual_scheduler_and_restores_planner_on_error(monkeypatch):
    original = schedule.calculate_observation_schedule_strict
    planner_before = schedule.calculate_observation_plan
    seen = []

    def capture(*args, **kwargs):
        seen.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(schedule, "calculate_observation_schedule_strict", capture)
    run_method("B0", CONTROL)
    assert seen == [1] and schedule.calculate_observation_plan is planner_before

    def fail(*args, **kwargs):
        raise RuntimeError("controlled scheduler failure")

    monkeypatch.setattr(schedule, "calculate_observation_schedule_strict", fail)
    with pytest.raises(RuntimeError, match="controlled scheduler failure"):
        run_method("B0", CONTROL)
    assert schedule.calculate_observation_plan is planner_before


def fake_freeze_tree(tmp_path, monkeypatch):
    config = read_json(ROOT / CONFIG)
    for path in INPUT_PATHS | FROZEN_REQUIRED:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"unit fixture; never used to compute a reserved result")
    receipt = dict(
        merge_commit="7f9f4d0276fc998224f9ba1d0e03ce24f0551b20",
        conclusion="success",
        archives_downloaded=31,
        receipts=[{}] * 31,
    )
    (tmp_path / "docs/research/evidence/mission66_merge_ci_v1.json").write_bytes(serialize(receipt))
    config["input_sha256"] = {p: sha((tmp_path / p).read_bytes()) for p in INPUT_PATHS}
    (tmp_path / CONFIG).write_bytes(serialize(config))
    freeze = dict(
        baseline_commit=receipt["merge_commit"],
        source_commit="0" * 40,
        reserved_candidate_outputs_before_freeze=0,
        file_sha256={p: sha((tmp_path / p).read_bytes()) for p in FROZEN_REQUIRED},
    )
    (tmp_path / FREEZE).write_bytes(serialize(freeze))
    monkeypatch.setattr(schedule_evaluation, "ROOT", tmp_path)
    return freeze


@pytest.mark.parametrize(
    "fault",
    [
        "missing_manifest",
        "changed_source",
        "changed_input",
        "missing_source_hash",
        "prior_exposure",
    ],
)
def test_freeze_gate_rejects_incomplete_or_changed_evidence(tmp_path, monkeypatch, fault):
    freeze = fake_freeze_tree(tmp_path, monkeypatch)
    if fault == "missing_manifest":
        (tmp_path / FREEZE).unlink()
    elif fault == "changed_source":
        (tmp_path / "validation/schedule_candidate.py").write_bytes(b"changed")
    elif fault == "changed_input":
        (tmp_path / "validation/fixtures/schedule_exhaustive_v1.json").write_bytes(b"changed")
    elif fault == "missing_source_hash":
        del freeze["file_sha256"][CONFIG]
        (tmp_path / FREEZE).write_bytes(serialize(freeze))
    else:
        freeze["reserved_candidate_outputs_before_freeze"] = 1
        (tmp_path / FREEZE).write_bytes(serialize(freeze))
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_freeze()


def test_session_lifetime_input_gate_and_original_entrypoints(tmp_path, monkeypatch):
    fake_freeze_tree(tmp_path, monkeypatch)
    events = []
    with evaluation_session("exposed_regression_replay", events.append) as session:
        # Public input admission only: no reserved method execution in any unit test.
        assert frozen_case(RESERVED[0], session) == RESERVED[0]
        for function in [schedule_baselines.b0, schedule_baselines.b1, schedule_candidate.b2]:
            with pytest.raises(ValueError, match="forbids"):
                function(RESERVED[0])
        with pytest.raises(ValueError, match="nested"):
            with evaluation_session("exposed_regression_replay", events.append):
                pass
        run_method("B2", CONTROL, session, "warmup", 0)
        bound = bind_method("B2", CONTROL, session)
    with pytest.raises(ValueError, match="expired"):
        bound(CONTROL)
    with pytest.raises(ValueError, match="active verified session"):
        frozen_case(RESERVED[0], session)
    assert session.reserved_attempts == 0 and events[-1]["event"] == "session_close"


def test_session_closes_after_exception(tmp_path, monkeypatch):
    fake_freeze_tree(tmp_path, monkeypatch)
    events = []
    with pytest.raises(RuntimeError):
        with evaluation_session("exposed_regression_replay", events.append):
            raise RuntimeError("test")
    assert events[-1]["event"] == "session_close" and schedule_evaluation._ACTIVE.get() is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("objective_tolerance", 1),
        ("objective_tolerance", False),
        ("require_canonical_candidate_path", False),
        ("allow_case_dropping", True),
        ("development_preflight_required", False),
        ("case_order", "reserved_first"),
        ("methods", ["B2"]),
        ("physical_qualification", True),
        ("phase_3_exit_approved", True),
    ],
)
def test_configuration_claim_changes_rejected(key, value):
    config = read_json(ROOT / CONFIG)
    config[key] = value
    with pytest.raises(ValueError):
        check_config(config)


def test_failed_development_preflight_retains_unexecuted_reserved_denominator(monkeypatch):
    import validation.schedule_evaluation_audit as audit

    calls = []

    def fail(method, case, *args):
        assert case["split"] != "evaluation_reserved"
        calls.append(method)
        raise TimeoutError("development failure")

    monkeypatch.setattr(audit, "run_method", fail)
    rows = evaluate_cases([CONTROL, RESERVED[0]], REFERENCES, OLD)
    assert calls == ["B0", "B1", "B2"] and len(rows) == 2
    assert all(not row["passed"] for row in rows)
    assert all("not_executed" in m["error"] for m in rows[1]["methods"].values())
    assert sum(g["denominator"] for g in aggregate(rows)) == 2


def test_partial_outputs_survive_timeout(monkeypatch):
    import validation.schedule_evaluation_audit as audit

    original = audit.run_method

    def fail(method, case, session, phase, repetition):
        if phase == "measured" and repetition == 2:
            raise TimeoutError("controlled timeout")
        return original(method, case, session, phase, repetition)

    monkeypatch.setattr(audit, "run_method", fail)
    result = measure(CONTROL, "B2", REFERENCES[CONTROL["case_id"]], OLD[CONTROL["case_id"]])
    assert not result["passed"] and result["calls"] == dict(warmup=1, measured=2)
    assert len(result["completed_outputs"]) == len(result["runtime_ns"]["samples"]) == 2


@pytest.fixture
def journal_record(tmp_path, monkeypatch):
    fake_freeze_tree(tmp_path, monkeypatch)
    events = []

    def journal(event):
        events.append(
            dict(sequence=len(events) + 1, timestamp_utc=datetime.now(UTC).isoformat(), **event)
        )

    label = "exposed_regression_replay"
    journal(dict(event="run_start", access_label=label))
    journal(dict(event="run_verified", access_label=label, environment={}))
    with evaluation_session(label, journal) as session, offline_adapter():
        rows = evaluate_cases([CONTROL], REFERENCES, OLD, session)
    journal(dict(event="run_complete", overall_passed=True, status="passed"))
    record = dict(
        overall_passed=True,
        access_label=label,
        environment={},
        source_freeze_commit="0" * 40,
        results=rows,
    )
    assert verify_journal(events, record)["method_invocations"] == 18
    return events, record


@pytest.mark.parametrize(
    "fault", ["missing", "reordered", "output", "case_id", "label", "counts", "timestamp"]
)
def test_journal_faults_rejected(journal_record, fault):
    events, record = copy.deepcopy(journal_record)
    if fault == "missing":
        del events[3]
    elif fault == "reordered":
        events[3], events[4] = events[4], events[3]
    elif fault == "output":
        events[4]["output_sha256"] = "0" * 64
    elif fault == "case_id":
        events[3]["case_id"] = "P3-C07"
    elif fault == "label":
        events[0]["access_label"] = "first_frozen_evaluation"
    elif fault == "counts":
        events[-2]["successes"] -= 1
    else:
        events[0]["timestamp_utc"] = "2024-03-20T00:00:00"
    with pytest.raises(ValueError):
        verify_journal(events, record)


def test_unknown_method_and_access_label_rejected():
    with pytest.raises(ValueError, match="unknown method"):
        bind_method("B3", CONTROL)
    with pytest.raises(ValueError, match="explicit access"):
        with evaluation_session("unseen_again", lambda event: None):
            pass


def test_source_tests_never_compute_reserved_results():
    assert len(DEVELOPMENT) == 232 and len(RESERVED) == 216
    assert json.loads(serialize(CONTROL)) == CONTROL
