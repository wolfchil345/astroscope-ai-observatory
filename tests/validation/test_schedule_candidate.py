"""Development-only exact DP acceptance, isolation, fault sensitivity and failure retention."""

import copy
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from validation import schedule_candidate
from validation.schedule_baseline_audit import load_inputs, offline_adapter
from validation.schedule_candidate import _solve, b2, development_case
from validation.schedule_candidate_audit import (
    BASELINE,
    aggregate,
    candidate_without_files,
    evaluate_cases,
    measure,
)
from validation.schedule_candidate_checks import check_candidate
from validation.schedule_corpus import CORPUS, ROOT, canonicalize, read_json, verify_path
from validation.schedule_corpus_checks import invalid_cases

_, CASES, REFERENCES = load_inputs()
CONTROLS = {c["case_id"]: c for c in CASES if c["split"] == "development_control"}
RESERVED = [
    c for c in read_json(ROOT / CORPUS)["primary_cases"] if c["split"] == "evaluation_reserved"
]
BASELINES = {r["case_id"]: r["methods"] for r in read_json(ROOT / BASELINE)["results"]}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_exact_development_objective_and_canonical_path(case):
    before = copy.deepcopy(case)
    with offline_adapter(), candidate_without_files():
        output = b2(case)
    metrics = check_candidate(case, output, REFERENCES[case["case_id"]])
    assert metrics["regret"] == 0 and metrics["exact_path_match"]
    assert case == before


@pytest.mark.parametrize("case", RESERVED, ids=lambda c: c["case_id"])
def test_all_reserved_ids_rejected_before_recurrence(case, monkeypatch):
    def forbidden(*args):
        pytest.fail("reserved input reached recurrence")

    monkeypatch.setattr(schedule_candidate, "_solve", forbidden)
    for relabel in [False, True]:
        changed = copy.deepcopy(case)
        if relabel:
            changed.update(split="development", replicate=0)
        with pytest.raises(ValueError, match="forbids"):
            b2(changed)


@pytest.mark.parametrize("identity,case", list(invalid_cases(CONTROLS["P3-C06"])))
def test_malformed_inputs_rejected_before_recurrence(identity, case, monkeypatch):
    def forbidden(*args):
        pytest.fail("invalid input reached recurrence")

    monkeypatch.setattr(schedule_candidate, "_solve", forbidden)
    with pytest.raises(ValueError):
        b2(case)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_target_storage_permutation_does_not_change_canonical_solution(case):
    changed = copy.deepcopy(case)
    changed["target_ids"].reverse()
    for key in ["scores", "eligibility"]:
        changed[key] = [row[::-1] for row in changed[key]]
    assert b2(changed) == b2(case)


@pytest.mark.parametrize(
    "transform", ["UTC_translation", "append_idle", "remove_unusable", "scale"]
)
def test_preregistered_metamorphic_relations(transform):
    case = CONTROLS["P3-C03" if transform == "remove_unusable" else "P3-C08"]
    changed = copy.deepcopy(case)
    original = b2(case)
    path, factor = original["path"], 1
    if transform == "UTC_translation":
        changed["start_utc"] = "2024-03-27T23:00:00Z"
    elif transform == "append_idle":
        changed["slots"] += 1
        changed["scores"].append([None] * changed["targets"])
        changed["eligibility"].append([False] * changed["targets"])
        path = path + ["IDLE"]
    elif transform == "remove_unusable":
        changed.update(
            targets=0, target_ids=[], scores=[[] for _ in path], eligibility=[[] for _ in path]
        )
    else:
        factor = 2
        changed["scores"] = [[q * factor for q in row] for row in changed["scores"]]
        changed["switch_cost"] *= factor
    changed["provenance"]["transformations"].append(transform)
    output = b2(changed)
    assert output["path"] == path
    assert output["net_objective"] == factor * original["net_objective"]
    assert verify_path(changed, path)["net_objective"] == output["net_objective"]


@pytest.mark.parametrize(
    "identity,path,value",
    [
        ("P3-C01", ["IDLE"], 0),
        ("P3-C02", ["target_00"], 0),
        ("P3-C07", ["target_00"] * 3, 269),
        ("P3-C08", ["target_00", "IDLE", "target_01"], 80),
        ("P3-C09", ["target_00", "IDLE", "target_00"], 100),
        ("P3-C10", ["target_00"], 1),
        ("P3-C12", ["target_00", "IDLE", "target_00"], 200),
        ("P3-C13", ["target_00"], 10),
        ("P3-C15", ["target_01", "target_00", "target_01"], 170),
        ("P3-C16", ["target_01", "target_00", "target_00"], 195),
    ],
)
def test_analytic_controls_without_oracle(identity, path, value):
    actual = b2(CONTROLS[identity])
    assert actual["path"] == path and actual["net_objective"] == value


MUTATIONS = {
    "erase_idle_history": ("reward, successor = 0, last", "reward, successor = 0, m"),
    "omit_cost": ('c["switch_cost"]', "0"),
    "double_cost": ('c["switch_cost"]', '(2 * c["switch_cost"])'),
    "charge_first_acquisition": ("last != m and last != action", "last != action"),
    "admit_unknown": ('c["eligibility"][t][j] is True', 'c["eligibility"][t][j] is not False'),
    "missing_as_zero": ('and c["scores"][t][j] is not None', ""),
    "reverse_ties": ("value > best", "value >= best"),
    "nonzero_terminal": ("[[0] * (m + 1)", "[[1] * (m + 1)"),
    "skip_first_slot": ("range(n - 1, -1, -1)", "range(n - 1, 0, -1)"),
    "discard_future": ("reward + values[t + 1][successor]", "reward"),
    "reset_reconstruction_on_idle": ("if action != m:\n            last = action", "last = action"),
}


@pytest.mark.parametrize("fault", MUTATIONS)
def test_mutated_candidate_detected_on_development_only(fault):
    source = inspect.getsource(_solve)
    before, after = MUTATIONS[fault]
    assert source.count(before) == 1
    source = source.replace(before, after)
    if fault == "missing_as_zero":
        source = source.replace(
            'c["scores"][t][action] - charge', '(c["scores"][t][action] or 0) - charge'
        )
    namespace = {}
    exec(compile(source, f"<M66-{fault}>", "exec"), namespace)
    detected = []
    for case in CASES:
        output = namespace["_solve"](development_case(case))
        try:
            check_candidate(case, output, REFERENCES[case["case_id"]])
        except ValueError as exc:
            # Reject a substantive solution defect, not just an accounting discrepancy.
            if "operation" not in str(exc):
                detected.append(case["case_id"])
    assert detected, fault


@pytest.mark.parametrize("fault", ["objective", "boolean_objective", "tie", "operation_count"])
def test_falsified_outputs_rejected(fault):
    case = CONTROLS["P3-C06"]
    output = b2(case)
    if fault == "objective":
        output["net_objective"] += 1
    elif fault == "boolean_objective":
        output["net_objective"] = True
    elif fault == "tie":
        output["path"] = ["target_01"] * 3
    else:
        output["operation_counts"]["state_updates"] = True
    with pytest.raises(ValueError):
        check_candidate(case, output, REFERENCES[case["case_id"]])


def test_candidate_file_reads_forbidden():
    with candidate_without_files(), pytest.raises(RuntimeError, match="file access forbidden"):
        Path(ROOT / "validation/fixtures/schedule_exhaustive_v1.json").read_bytes()


def test_candidate_imports_and_executes_without_science_packages_or_oracle():
    code = """
import sys, json, importlib.abc
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
class Forbidden(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  forbidden = ['schedule_exhaustive','schedule_baseline','schedule_candidate_checks']
  if (fullname.split('.')[0] in {'astroscope','astropy','numpy','scipy'}
      or any(x in fullname for x in forbidden)):
   raise ImportError('forbidden dependency: '+fullname)
sys.meta_path.insert(0, Forbidden())
from validation.schedule_candidate import b2
case = json.loads(Path('validation/fixtures/schedule_corpus_v1.json').read_text())['controls'][11]
assert case['case_id'] == 'P3-C12'
assert b2(case)['net_objective'] == 200
print('stdlib-only B2 pass')
"""
    completed = subprocess.run(
        [sys.executable, "-S", "-c", code], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert "stdlib-only B2 pass" in completed.stdout


def test_incorrect_solution_retained_in_measurement():
    case = CONTROLS["P3-C06"]

    def wrong(c):
        output = b2(c)
        output["path"] = ["target_01"] * 3
        return output

    result = measure(case, "B2", wrong, REFERENCES[case["case_id"]], BASELINES[case["case_id"]])
    assert not result["passed"] and result["output"]["path"] == ["target_01"] * 3
    assert len(result["runtime_ns"]["samples"]) == 5
    assert "canonical optimal path" in result["error"]


def test_nondeterministic_outputs_retained():
    case = CONTROLS["P3-C06"]
    calls = []

    def unstable(c):
        result = b2(c)
        calls.append(1)
        result["net_objective"] += len(calls)
        return result

    result = measure(case, "B2", unstable, REFERENCES[case["case_id"]], BASELINES[case["case_id"]])
    assert not result["passed"] and len(result["nondeterministic_outputs"]) == 5


def test_exception_or_timeout_keeps_remaining_cases_and_denominators():
    cases = [CONTROLS["P3-C06"], CONTROLS["P3-C07"]]

    def sometimes_fails(case):
        if case["case_id"] == "P3-C06":
            raise TimeoutError("controlled timeout, incomplete")
        return b2(case)

    from validation.schedule_baselines import b0, b1

    rows = evaluate_cases(
        cases, REFERENCES, BASELINES, [("B0", b0), ("B1", b1), ("B2", sometimes_fails)]
    )
    assert len(rows) == 2 and not rows[0]["passed"] and rows[1]["passed"]
    assert "TimeoutError" in rows[0]["methods"]["B2"]["error"]
    groups = aggregate(rows)
    assert sum(g["denominator"] for g in groups) == 2
    assert sum(g["methods"]["B2"]["failed"] for g in groups) == 1
    assert sum(g["B2_vs_B0"]["incomplete"] for g in groups) == 1


def test_unregistered_id_and_reference_mismatch_rejected():
    case = copy.deepcopy(CONTROLS["P3-C06"])
    case["case_id"] = "unregistered"
    with pytest.raises(ValueError, match="forbids"):
        b2(case)
    case = CONTROLS["P3-C06"]
    with pytest.raises(ValueError, match="reference ID"):
        check_candidate(case, b2(case), REFERENCES["P3-C07"])
    assert canonicalize(case) == case
