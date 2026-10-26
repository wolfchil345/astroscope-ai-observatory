"""Frozen-corpus adapter with explicit reserved-access sessions; original guards unchanged."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import FunctionType

from validation import schedule_baselines, schedule_candidate
from validation.schedule_candidate_audit import candidate_without_files
from validation.schedule_corpus import (
    CORPUS,
    ROOT,
    canonicalize,
    read_json,
    require,
    serialize,
    sha,
)

CONFIG = "validation/manifests/schedule_evaluation_v1.json"
FREEZE = "validation/manifests/schedule_evaluation_freeze_v1.json"
CORPUS_SHA = "c658972b68f445b335b9f3dfe6058faea999db98b5c26dfd40c603d0423f5825"
raw = (ROOT / CORPUS).read_bytes()
require(sha(raw) == CORPUS_SHA, "frozen corpus changed")
_corpus = read_json(ROOT / CORPUS)
_CASE_HASHES = {
    c["case_id"]: sha(serialize(c)) for c in _corpus["primary_cases"] + _corpus["controls"]
}
_ACTIVE = ContextVar("schedule_evaluation_session", default=None)
LABELS = {"first_frozen_evaluation", "exposed_regression_replay"}
INPUT_PATHS = {
    "docs/research/protocols/observation_optimisation_v1.json",
    "validation/fixtures/schedule_corpus_v1.json",
    "validation/fixtures/schedule_exhaustive_v1.json",
    "validation/results/schedule_candidate_reference_run.json",
    "validation/manifests/schedule_baselines_freeze_v2.json",
    "validation/manifests/schedule_candidate_freeze_v1.json",
}
FROZEN_REQUIRED = set(
    read_json(ROOT / "validation/manifests/schedule_candidate_freeze_v1.json")["file_sha256"]
) | {
    CONFIG,
    "validation/schedule_evaluation.py",
    "validation/schedule_evaluation_audit.py",
    "validation/schedule_evaluation_checks.py",
    "tests/validation/test_schedule_evaluation.py",
    ".github/workflows/schedule-evaluation-validation.yml",
    "docs/research/evidence/mission66_merge_ci_v1.json",
    "docs/research/protocols/schedule_evaluation_execution_v1.md",
}


def check_config(config):
    require(config["methods"] == ["B0", "B1", "B2"], "methods")
    require(
        config["counts"] == dict(development=216, controls=16, evaluation_reserved=216, total=448),
        "counts",
    )
    require(
        type(config["objective_tolerance"]) is int
        and config["objective_tolerance"] == 0
        and config["require_canonical_candidate_path"] is True,
        "exact acceptance",
    )
    require(
        config["development_preflight_required"] is True and not config["allow_case_dropping"],
        "preflight/denominator",
    )
    require(config["case_order"] == "development_then_controls_then_reserved", "case order")
    require(
        config["runtime"]
        == dict(
            warmups=1, repetitions=5, clock="perf_counter_ns", acceptance_threshold_seconds=None
        ),
        "runtime",
    )
    require(
        not config["physical_qualification"]
        and not config["phase_3_exit_approved"]
        and not config["production_changes"],
        "scope",
    )


def verify_freeze():
    config, freeze = read_json(ROOT / CONFIG), read_json(ROOT / FREEZE)
    check_config(config)
    require(set(config["input_sha256"]) == INPUT_PATHS, "input hash coverage")
    require(FROZEN_REQUIRED <= set(freeze["file_sha256"]), "source hash coverage")
    require(freeze["reserved_candidate_outputs_before_freeze"] == 0, "prior exposure")
    require(freeze["baseline_commit"] == "7f9f4d0276fc998224f9ba1d0e03ce24f0551b20", "baseline")
    for path, digest in config["input_sha256"].items() | freeze["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == digest, f"frozen bytes changed: {path}")
    receipt = read_json(ROOT / "docs/research/evidence/mission66_merge_ci_v1.json")
    require(
        receipt["merge_commit"] == freeze["baseline_commit"] and receipt["conclusion"] == "success",
        "baseline CI",
    )
    require(receipt["archives_downloaded"] == len(receipt["receipts"]) == 31, "baseline archives")
    return config, freeze


@dataclass
class EvaluationSession:
    label: str
    journal: object
    source_commit: str
    attempts: int = 0
    successes: int = 0
    reserved_attempts: int = 0
    reserved_successes: int = 0


@contextmanager
def evaluation_session(label, journal):
    require(label in LABELS and callable(journal), "explicit access label/journal required")
    require(_ACTIVE.get() is None, "nested evaluation session forbidden")
    _, freeze = verify_freeze()
    session = EvaluationSession(label, journal, freeze["source_commit"])
    token = _ACTIVE.set(session)
    try:
        journal(dict(event="session_open", access_label=label, source_commit=session.source_commit))
        yield session
    finally:
        _ACTIVE.reset(token)
        journal(
            dict(
                event="session_close",
                attempts=session.attempts,
                successes=session.successes,
                reserved_attempts=session.reserved_attempts,
                reserved_successes=session.reserved_successes,
            )
        )


def frozen_case(case, session=None):
    c = canonicalize(case)
    require(
        _CASE_HASHES.get(c["case_id"]) == sha(serialize(case)), "case differs from frozen corpus"
    )
    if c["split"] == "evaluation_reserved":
        require(
            session is not None and _ACTIVE.get() is session,
            "reserved access requires active verified session",
        )
    elif session is not None:
        require(_ACTIVE.get() is session, "expired evaluation session")
    return c


def bind_method(method, case, session=None):
    """Reuse the identical code objects with private guard globals; never patch module guards."""
    require(method in {"B0", "B1", "B2"}, "unknown method")
    c = frozen_case(case, session)
    identity = c["case_id"]

    def guard(value):
        checked = frozen_case(value, session)
        require(checked["case_id"] == identity, "adapter bound to another case")
        return checked

    module = schedule_candidate if method == "B2" else schedule_baselines
    original = getattr(module, method.lower())
    namespace = original.__globals__.copy()
    namespace["development_case"] = guard
    if method == "B0":
        decoder = schedule_baselines.decode_blocks
        namespace["decode_blocks"] = FunctionType(decoder.__code__, namespace, decoder.__name__)
    return FunctionType(original.__code__, namespace, original.__name__)


def run_method(method, case, session=None, phase="preflight", repetition=0):
    function = bind_method(method, case, session)
    event = dict(
        case_id=case["case_id"],
        split=case["split"],
        method=method,
        phase=phase,
        repetition=repetition,
    )
    reserved = case["split"] == "evaluation_reserved"
    if session is not None:
        session.attempts += 1
        session.reserved_attempts += reserved
        event["invocation"] = session.attempts
        session.journal(dict(event="method_start", **event))
    try:
        if method == "B2":
            with candidate_without_files():
                output = function(case)
        else:
            output = function(case)
    except Exception as exc:
        if session is not None:
            session.journal(
                dict(event="method_error", error=f"{type(exc).__name__}: {exc}", **event)
            )
        raise
    if session is not None:
        session.successes += 1
        session.reserved_successes += reserved
        session.journal(
            dict(event="method_complete", output_sha256=sha(serialize(output)), **event)
        )
    return output
