"""Offline Mission 64 input/reference release and complete replay; no B0/B1/B2 runs."""

import argparse
import ast
import importlib.abc
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from validation.reference_generation.schedule_exhaustive import solve
from validation.schedule_corpus import (
    CORPUS,
    MANIFEST,
    ORACLE,
    PROTOCOL,
    PROTOCOL_SHA256,
    REFERENCE,
    ROOT,
    SOURCE,
    build_corpus,
    canonicalize,
    protocol,
    read_json,
    require,
    serialize,
    sha,
    slot_grid,
)
from validation.schedule_corpus_checks import (
    check_metamorphic,
    check_mutations,
    check_reference_row,
    check_rejections,
    independent_matrix_check,
)

SOURCE_PATHS = [
    SOURCE,
    ORACLE,
    "validation/schedule_corpus_checks.py",
    "validation/schedule_corpus_audit.py",
]
BASELINE = "c489863badae5d28e6ae05e3b5d2f65565a0b1aa"
BLOCKED_IMPORTS = {
    "astroscope",
    "astropy",
    "numpy",
    "scipy",
    "pandas",
    "plotly",
    "streamlit",
    "erfa",
    "requests",
    "urllib.request",
    "http.client",
}


class DenyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in BLOCKED_IMPORTS):
            raise ImportError(f"forbidden in synthetic reference replay: {fullname}")
        return None


@contextmanager
def offline_computation():
    def deny(*args, **kwargs):
        raise RuntimeError("network/subprocess forbidden during reference computation")

    finder = DenyImports()
    # Also prevent retrieval of already imported numerical/production modules.
    with (
        patch.dict(sys.modules, dict.fromkeys(BLOCKED_IMPORTS)),
        patch.object(socket, "socket", deny),
        patch.object(socket, "create_connection", deny),
        patch.object(socket, "getaddrinfo", deny),
        patch.object(subprocess, "Popen", deny),
        patch.object(os, "system", deny),
    ):
        sys.meta_path.insert(0, finder)
        try:
            yield
        finally:
            sys.meta_path.remove(finder)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check_oracle_imports():
    tree = ast.parse((ROOT / ORACLE).read_text())
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    require(
        len(imports) == 1
        and isinstance(imports[0], ast.ImportFrom)
        and imports[0].module == "itertools"
        and [x.name for x in imports[0].names] == ["product"],
        "oracle import independence",
    )


def reference_release(corpus, source_commit):
    rows = []
    for case in corpus["primary_cases"] + corpus["controls"]:
        require(canonicalize(case) == case, "noncanonical release input")
        result = solve(case)
        check_reference_row(case, result)
        rows.append(result)
    return dict(
        schema_version=1,
        release_id="P3-SCHEDULE-E0-v1",
        protocol_id="P3-SCHEDULE-001-v1",
        protocol_sha256=PROTOCOL_SHA256,
        input_sha256=sha(serialize(corpus)),
        oracle_commit=source_commit,
        oracle_sha256=sha((ROOT / ORACLE).read_bytes()),
        method="E0 Cartesian product, direct traversal, integer arithmetic",
        candidate_evaluations=0,
        primary_case_count=432,
        control_count=16,
        results=rows,
    )


def freeze_release(source_commit):
    """Run only after a separate source/configuration commit, before candidate evaluation."""
    require(git("rev-parse", "HEAD") == source_commit, "freeze at committed source HEAD")
    require(not git("status", "--porcelain"), "freeze requires a clean source checkout")
    for path in (CORPUS, REFERENCE, MANIFEST):
        require(not (ROOT / path).exists(), "versioned release already exists; never overwrite")
    check_oracle_imports()
    with offline_computation():
        corpus = build_corpus(source_commit)
        reference = reference_release(corpus, source_commit)
        invalid = check_rejections(corpus["controls"])
        metamorphic = check_metamorphic(corpus["controls"])
        mutations = check_mutations(corpus["controls"])
    manifest = dict(
        schema_version=1,
        release_id="P3-SCHEDULE-RELEASE-v1",
        protocol_id="P3-SCHEDULE-001-v1",
        baseline_commit=BASELINE,
        source_commit=source_commit,
        protocol_sha256=PROTOCOL_SHA256,
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in SOURCE_PATHS},
        file_sha256={
            CORPUS: sha(serialize(corpus)),
            REFERENCE: sha(serialize(reference)),
            PROTOCOL: PROTOCOL_SHA256,
        },
        expected_counts=dict(
            primary=432,
            development=216,
            evaluation_reserved=216,
            cores=144,
            controls=16,
            invalid_classes=16,
            invalid_variants=len(invalid),
            metamorphic=len(metamorphic),
            mutations=len(mutations),
        ),
        scope="Inputs and independent oracle only; no candidate implementation or evaluation",
        license="MIT; project-generated synthetic values; primary method sources linked only",
        randomness="none; exact public SHA256 counter, no distributional sampling claim",
        execution_cap=dict(
            max_slots=9,
            max_targets=3,
            max_paths_per_case=262144,
            early_stop=False,
            ci_step_timeout_minutes=10,
            timeout_result="incomplete, never accepted",
        ),
        performance=dict(
            comparative_timing_performed=False,
            policy="M63 warmup/five-repeat timing reserved for method comparison",
        ),
        endpoint_control_scope=(
            "C13 oracle covers N=1; real scheduler sentinel test remains pending"
        ),
        reserved_access=dict(
            public_inputs=True,
            blind=False,
            candidate_outputs_inspected=0,
            oracle_results_generated=True,
            later_candidate_access_requires_separate_frozen_source_and_config=True,
        ),
        scientific_acceptance="bounded synthetic corpus and exhaustive reference only",
        optimizer_acceptance=None,
        physical_qualification=False,
        phase_3_exit_approved=False,
    )
    for path, value in ((CORPUS, corpus), (REFERENCE, reference), (MANIFEST, manifest)):
        (ROOT / path).write_bytes(serialize(value))
    return manifest


def run_benchmark():
    implementation = os.environ.get("ASTROSCOPE_IMPLEMENTATION_COMMIT", git("rev-parse", "HEAD"))
    environment = dict(
        implementation_commit=implementation,
        checkout_commit=os.environ.get("ASTROSCOPE_CHECKOUT_COMMIT", git("rev-parse", "HEAD")),
        parent_commits=git("show", "-s", "--format=%P", "HEAD").split(),
        git_dirty=bool(git("status", "--porcelain")),
        python=platform.python_version(),
        python_implementation=platform.python_implementation(),
        platform=platform.platform(),
        machine=platform.machine(),
        runtime_dependencies="Python standard library only",
        installed_packages={
            d.metadata["Name"]: d.version
            for d in importlib.metadata.distributions()
            if d.metadata["Name"]
        },
        timezone="UTC, fixed aware datetime; no civil zone lookup",
        ephemeris="not applicable: synthetic supplied scores",
        eop="not applicable",
        geometry="not applicable",
        network_required=False,
        command="python -m validation.schedule_corpus_audit --output <path>",
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in SOURCE_PATHS},
        input_sha256={
            p: sha((ROOT / p).read_bytes()) for p in [PROTOCOL, CORPUS, REFERENCE, MANIFEST]
        },
    )
    manifest = read_json(ROOT / MANIFEST)
    source_commit = manifest["source_commit"]
    require(manifest["baseline_commit"] == BASELINE, "merge baseline")
    for path in SOURCE_PATHS:
        require(
            environment["source_sha256"][path] == manifest["source_sha256"][path],
            f"frozen source changed: {path}",
        )
    for path, expected in manifest["file_sha256"].items():
        require(sha((ROOT / path).read_bytes()) == expected, f"frozen bytes: {path}")
    require(
        manifest["execution_cap"]
        == dict(
            max_slots=9,
            max_targets=3,
            max_paths_per_case=262144,
            early_stop=False,
            ci_step_timeout_minutes=10,
            timeout_result="incomplete, never accepted",
        ),
        "execution policy changed",
    )
    check_oracle_imports()
    with offline_computation():
        corpus = build_corpus(source_commit)
        require(serialize(corpus) == (ROOT / CORPUS).read_bytes(), "input regeneration bytes")
        p = protocol()
        cases = corpus["primary_cases"]
        require(
            [c["case_id"] for c in cases] == [c["id"] for c in p["primary_corpus"]["cases"]],
            "primary inventory",
        )
        require(len({c["core_id"] for c in cases}) == 144, "core count")
        for case in cases:
            independent_matrix_check(case)
        reference = reference_release(corpus, source_commit)
        require(
            serialize(reference) == (ROOT / REFERENCE).read_bytes(), "reference regeneration bytes"
        )
        invalid = check_rejections(corpus["controls"])
        metamorphic = check_metamorphic(corpus["controls"])
        mutations = check_mutations(corpus["controls"])
        rows = []
        for case, answer in zip(cases + corpus["controls"], reference["results"], strict=True):
            metrics = check_reference_row(case, answer)
            grid = slot_grid(case)
            require(
                len(grid) == case["slots"]
                and all((b - a).total_seconds() == 3600 for a, b in grid),
                "UTC slots",
            )
            rows.append(
                dict(
                    case_id=case["case_id"],
                    split=case["split"],
                    family=case["family"],
                    switch_cost=case["switch_cost"],
                    passed=True,
                    enumerated_paths=answer["enumerated_paths"],
                    feasible_paths=answer["feasible_paths"],
                    metrics=metrics,
                )
            )
    counts = dict(
        primary=len(cases),
        development=sum(c["split"] == "development" for c in cases),
        evaluation_reserved=sum(c["split"] == "evaluation_reserved" for c in cases),
        cores=len({c["core_id"] for c in cases}),
        controls=len(corpus["controls"]),
        invalid_classes=len({x["id"][:6] for x in invalid}),
        invalid_variants=len(invalid),
        metamorphic=len(metamorphic),
        mutations=len(mutations),
    )
    require(counts == manifest["expected_counts"], "frozen denominators")
    return dict(
        mission=64,
        experiment_id="P3-SCHEDULE-001-v1",
        overall_passed=True,
        execution_target="independent synthetic corpus/reference; no production methods",
        counts=counts,
        failed_cases=0,
        results=rows,
        rejections=invalid,
        metamorphic=metamorphic,
        negative_controls=mutations,
        enumerated_paths=sum(r["enumerated_paths"] for r in rows),
        input_regenerated_byte_identical=True,
        reference_regenerated_byte_identical=True,
        independent_formula_checks=432,
        analytic_controls=16,
        sockets_and_subprocesses_blocked_during_computation=True,
        external_science_and_production_imports_blocked=True,
        source_commit=source_commit,
        environment=environment,
        evaluation_reserved_access="E0 reference replay only; recorded in this artifact",
        candidate_evaluations=0,
        optimizer_acceptance=None,
        physical_qualification=False,
        phase_3_exit_approved=False,
        limits=[
            "Synthetic nominal objective, not astronomical accuracy or scientific yield",
            "Shared written model and author; independent algorithm, not independent human review",
            "C13 sentinel and schedule block decoding await actual B0 adapter",
            "Current replay cannot reconstruct historical Phase 2 environments",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-source-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.freeze_source_commit:
        require(args.output is None, "freeze and audit are separate commands")
        result = freeze_release(args.freeze_source_commit)
        print(json.dumps(result["expected_counts"]))
        return 0
    require(args.output is not None, "--output required for audit")
    try:
        result = run_benchmark()
    except Exception as exc:
        result = dict(
            mission=64,
            overall_passed=False,
            status="failed_or_incomplete",
            error=f"{type(exc).__name__}: {exc}",
            candidate_evaluations=0,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(serialize(result))
    print(
        json.dumps(
            {key: result[key] for key in ("overall_passed", "counts", "error") if key in result}
        )
    )
    return 0 if result["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
