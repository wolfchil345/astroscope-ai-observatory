"""B0/B1 development acceptance, live scheduler boundaries and reserved-output guards."""

import copy
import importlib
import inspect
import socket
from dataclasses import replace
from datetime import timedelta

import pytest

from astroscope import planner, schedule
from validation.schedule_baseline_audit import load_inputs, offline_adapter
from validation.schedule_baseline_checks import check_policy, check_result
from validation.schedule_baselines import b0, b1, decode_blocks, development_case
from validation.schedule_corpus import CORPUS, ROOT, read_json
from validation.schedule_corpus_checks import invalid_cases

_, CASES, REFERENCES = load_inputs()
CONTROLS = {c["case_id"]: c for c in CASES if c["split"] == "development_control"}
RESERVED = [
    c for c in read_json(ROOT / CORPUS)["primary_cases"] if c["split"] == "evaluation_reserved"
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_development_policy_and_independent_reference_bound(case):
    original = copy.deepcopy(case)
    with offline_adapter():
        for method, function in [("B0", b0), ("B1", b1)]:
            result = function(case)
            metrics = check_result(case, result, method, REFERENCES[case["case_id"]])
            assert metrics["feasibility_violations"] == 0
            if method == "B0":
                assert result["block_count"] == metrics["block_count"]
    assert case == original


@pytest.mark.parametrize("case", RESERVED, ids=lambda c: c["case_id"])
def test_reserved_candidate_execution_is_blocked_before_scheduler_call(case, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail("reserved case reached scheduler")

    monkeypatch.setattr(schedule, "calculate_observation_schedule_strict", forbidden)
    for function in [b0, b1]:
        with pytest.raises(ValueError, match="forbids"):
            function(case)
        relabelled = copy.deepcopy(case)
        relabelled.update(split="development", replicate=0)
        with pytest.raises(ValueError, match="forbids"):
            function(relabelled)


@pytest.mark.parametrize(
    "identity,case",
    list(invalid_cases(CONTROLS["P3-C06"])),
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_invalid_inputs_rejected_by_both_methods(identity, case):
    for function in [b0, b1]:
        with pytest.raises(ValueError):
            function(case)


def test_real_scheduler_called_and_scoped_patch_restored(monkeypatch):
    real = schedule.calculate_observation_schedule_strict
    original_planner = schedule.calculate_observation_plan
    calls = []

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(schedule, "calculate_observation_schedule_strict", wrapper)
    result = b0(CONTROLS["P3-C13"])
    assert len(calls) == 1 and result["snapshot_count"] == 2
    assert result["endpoint_override"] and result["path"] == ["target_00"]
    assert schedule.calculate_observation_plan is original_planner


def test_exception_restores_planner_patch(monkeypatch):
    original = schedule.calculate_observation_plan

    def fail(*a, **k):
        raise RuntimeError("controlled failure")

    monkeypatch.setattr(schedule, "calculate_observation_schedule_strict", fail)
    with pytest.raises(RuntimeError, match="controlled failure"):
        b0(CONTROLS["P3-C13"])
    assert schedule.calculate_observation_plan is original


def capture_result(case, monkeypatch):
    real = schedule.calculate_observation_schedule_strict
    captured = []

    def wrapper(*a, **kw):
        result = real(*a, **kw)
        captured.append(result)
        return result

    with monkeypatch.context() as patcher:
        patcher.setattr(schedule, "calculate_observation_schedule_strict", wrapper)
        b0(case)
    return captured[0]


@pytest.mark.parametrize(
    "fault",
    [
        "terminal",
        "off_grid",
        "overlap",
        "reverse",
        "duration",
        "peak",
        "bridge_gap",
        "unknown_target",
        "naive",
        "split_adjacent",
    ],
)
def test_actual_scheduler_block_mutations_are_rejected(fault, monkeypatch):
    case = CONTROLS["P3-C09"]
    result = capture_result(case, monkeypatch)
    blocks = list(result.schedule_blocks)
    a, b = blocks
    if fault == "terminal":
        blocks.append(replace(b, start_utc=b.end_utc, end_utc=b.end_utc + timedelta(hours=1)))
    elif fault == "off_grid":
        blocks[0] = replace(a, start_utc=a.start_utc + timedelta(microseconds=1))
    elif fault == "overlap":
        blocks.insert(1, a)
    elif fault == "reverse":
        blocks.reverse()
    elif fault == "duration":
        blocks[0] = replace(a, duration_minutes=59)
    elif fault == "peak":
        blocks[0] = replace(a, peak_score=100)
    elif fault == "bridge_gap":
        blocks = [replace(a, end_utc=b.end_utc, end_local=b.end_local, duration_minutes=180)]
    elif fault == "unknown_target":
        blocks[0] = replace(a, object_key="target_99")
    elif fault == "naive":
        blocks[0] = replace(a, start_utc=a.start_utc.replace(tzinfo=None))
    else:
        case = CONTROLS["P3-C06"]
        result = capture_result(case, monkeypatch)
        a = result.schedule_blocks[0]
        boundary = a.start_utc + timedelta(hours=1)
        blocks = [
            replace(a, end_utc=boundary, end_local=boundary, duration_minutes=60),
            replace(
                a,
                start_utc=boundary,
                start_local=boundary,
                peak_local=boundary,
                duration_minutes=120,
            ),
        ]
    with pytest.raises(ValueError):
        decode_blocks(case, replace(result, schedule_blocks=tuple(blocks)))


@pytest.mark.parametrize("method", ["B0", "B1"])
def test_wrong_tie_and_unknown_missing_selection_rejected(method):
    for identity, path in [
        ("P3-C06", ["target_01"] * 3),
        ("P3-C03", ["target_00"] * 3),
        ("P3-C05", ["target_00"] * 3),
    ]:
        with pytest.raises(ValueError):
            check_policy(CONTROLS[identity], path, method)


def test_m55_and_optional_idle_adverse_results_retained():
    for identity, expected in [("P3-C07", (230, 269)), ("P3-C12", (161, 200))]:
        c = CONTROLS[identity]
        actual = tuple(
            check_policy(c, f(c)["path"], m)["net_objective"] for m, f in [("B0", b0), ("B1", b1)]
        )
        assert actual == expected


def test_known_zero_missing_masks_and_midnight():
    assert b0(CONTROLS["P3-C02"])["path"] == ["target_00"]
    assert all(all(row) for row in b0(CONTROLS["P3-C03"])["missing_score_mask"])
    assert all(all(row) for row in b0(CONTROLS["P3-C05"])["unknown_eligibility_mask"])
    result = b0(CONTROLS["P3-C15"])
    assert result["planner_calls"][-1] == "2024-03-21T02:00:00+00:00"


def test_permutation_metamorphism_on_all_development_inputs():
    for case in CASES:
        changed = copy.deepcopy(case)
        changed["target_ids"].reverse()
        for key in ["scores", "eligibility"]:
            changed[key] = [row[::-1] for row in changed[key]]
        for function in [b0, b1]:
            assert function(changed)["path"] == function(case)["path"]


def test_both_methods_survive_blocked_live_planner_and_oracle():
    with offline_adapter():
        with pytest.raises(RuntimeError):
            socket.socket()
        with pytest.raises(RuntimeError):
            planner.calculate_observation_plan()
        with pytest.raises(ImportError):
            importlib.import_module("validation.reference_generation.schedule_exhaustive")
        assert b0(CONTROLS["P3-C13"])["path"] == b1(CONTROLS["P3-C13"])["path"]


@pytest.mark.parametrize("method,function", [("B0", b0), ("B1", b1)])
@pytest.mark.parametrize(
    "transform", ["UTC_translation", "append_idle", "remove_unusable", "scale"]
)
def test_remaining_preregistered_metamorphic_relations(method, function, transform):
    case = CONTROLS["P3-C03" if transform == "remove_unusable" else "P3-C08"]
    changed = copy.deepcopy(case)
    expected = function(case)["path"]
    factor = 1
    if transform == "UTC_translation":
        changed["start_utc"] = "2024-03-27T23:00:00Z"
    elif transform == "append_idle":
        changed["slots"] += 1
        changed["scores"].append([None] * changed["targets"])
        changed["eligibility"].append([False] * changed["targets"])
        expected = expected + ["IDLE"]
    elif transform == "remove_unusable":
        changed.update(
            targets=0,
            target_ids=[],
            scores=[[] for _ in range(case["slots"])],
            eligibility=[[] for _ in range(case["slots"])],
        )
    else:
        factor = 2
        changed["scores"] = [[q * 2 for q in row] for row in changed["scores"]]
        changed["switch_cost"] *= 2
    changed["provenance"]["transformations"].append(transform)
    result = function(changed)
    assert result["path"] == expected
    assert (
        check_policy(changed, result["path"], method)["net_objective"]
        == factor * check_policy(case, function(case)["path"], method)["net_objective"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "erase_idle_history",
        "omit_cost",
        "double_cost",
        "first_cost",
        "admit_unknown",
        "missing_zero",
        "wrong_tie",
    ],
)
def test_b1_code_mutants_detected_on_development_only(fault):
    source = inspect.getsource(b1)
    before, after = {
        "erase_idle_history": (
            'if action != "IDLE":\n            last = action',
            'last = action if action != "IDLE" else None',
        ),
        "omit_cost": ('c["switch_cost"]', "0"),
        "double_cost": ('c["switch_cost"]', '(2 * c["switch_cost"])'),
        "first_cost": ("last is not None and last != target", "last != target"),
        "admit_unknown": ("mask[j] is True", "mask[j] is not False"),
        "missing_zero": ("mask[j] is True and scores[j] is not None", "mask[j] is True"),
        "wrong_tie": ("max(choices, key=", "max(choices[::-1], key="),
    }[fault]
    assert source.count(before) == 1
    source = source.replace(before, after)
    if fault == "missing_zero":
        source = source.replace("scores[j] - charge", "(scores[j] or 0) - charge")
    namespace = dict(development_case=development_case)
    exec(compile(source, "<B1-test-mutant>", "exec"), namespace)
    detected = []
    for case in CASES:
        path = namespace["b1"](case)["path"]
        try:
            check_policy(case, path, "B1")
        except ValueError:
            detected.append(case["case_id"])
    assert detected, fault
