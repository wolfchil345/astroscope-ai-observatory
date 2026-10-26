"""M64 mathematical/contract tests; historical scientific tests remain unchanged."""

import copy
import importlib
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from validation.reference_generation.schedule_exhaustive import solve
from validation.schedule_corpus import (
    CORPUS,
    MANIFEST,
    ORACLE,
    REFERENCE,
    ROOT,
    build_corpus,
    canonicalize,
    protocol,
    read_json,
    serialize,
    sha,
    slot_grid,
    verify_path,
)
from validation.schedule_corpus_audit import check_oracle_imports, offline_computation
from validation.schedule_corpus_checks import (
    ANALYTIC,
    check_metamorphic,
    check_mutations,
    check_reference_row,
    independent_matrix_check,
    invalid_cases,
)


class ScheduleCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = read_json(ROOT / CORPUS)
        cls.reference = read_json(ROOT / REFERENCE)
        cls.manifest = read_json(ROOT / MANIFEST)
        cls.controls = {c["case_id"]: c for c in cls.corpus["controls"]}

    def test_frozen_inventory_and_splits(self):
        cases = self.corpus["primary_cases"]
        self.assertEqual(
            [c["case_id"] for c in cases], [c["id"] for c in protocol()["primary_corpus"]["cases"]]
        )
        self.assertEqual(len(cases), 432)
        self.assertEqual(len({c["case_id"] for c in cases}), 432)
        self.assertEqual(len({c["core_id"] for c in cases}), 144)
        self.assertEqual(
            Counter(c["split"] for c in cases), {"development": 216, "evaluation_reserved": 216}
        )
        self.assertEqual(Counter(c["family"] for c in cases), {f"F{i}": 72 for i in range(1, 7)})

    def test_independent_counter_formula_every_primary_cell(self):
        for case in self.corpus["primary_cases"]:
            with self.subTest(case=case["case_id"]):
                independent_matrix_check(case)

    def test_input_regeneration_is_byte_identical(self):
        actual = build_corpus(self.manifest["source_commit"])
        self.assertEqual(serialize(actual), (ROOT / CORPUS).read_bytes())

    def test_cost_profiles_share_their_original_matrices(self):
        groups = {}
        for c in self.corpus["primary_cases"]:
            value = (c["scores"], c["eligibility"], c["split"])
            if c["core_id"] in groups:
                self.assertEqual(groups[c["core_id"]], value)
            groups[c["core_id"]] = value

    def test_controls_match_reviewed_explicit_inputs(self):
        for spec in protocol()["controls"]:
            actual = self.controls[spec["id"]]
            for key in ("scores", "eligibility", "slots", "targets", "switch_cost"):
                self.assertEqual(actual[key], spec[key])
        self.assertEqual(
            self.corpus["future_adapter_endpoint_overrides"],
            {"P3-C13": {"scores": [0, 100], "eligibility": [True, True]}},
        )

    def test_hand_derived_optima_and_canonical_ties(self):
        self.assertEqual(set(ANALYTIC), set(self.controls))
        for case in self.controls.values():
            with self.subTest(case=case["case_id"]):
                check_reference_row(case, solve(case))

    def test_independent_scoring_every_frozen_reference(self):
        for case, row in zip(
            self.corpus["primary_cases"] + self.corpus["controls"],
            self.reference["results"],
            strict=True,
        ):
            with self.subTest(case=case["case_id"]):
                check_reference_row(case, row)

    def test_all_sixteen_invalid_classes_are_rejected(self):
        variants = list(invalid_cases(self.controls["P3-C06"]))
        self.assertEqual(len(variants), 48)
        self.assertEqual(len({name[:6] for name, _ in variants}), 16)
        for name, case in variants:
            with self.subTest(variant=name), self.assertRaises(ValueError):
                canonicalize(case)

    def test_missing_keys_and_documentary_provenance_rejected(self):
        for key in self.controls["P3-C06"]:
            case = copy.deepcopy(self.controls["P3-C06"])
            del case[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                canonicalize(case)
        for key, value in [
            ("generator_commit", "bad"),
            ("source_kind", "observed"),
            ("protocol_sha256", "0" * 64),
            ("transformations", "hidden"),
        ]:
            case = copy.deepcopy(self.controls["P3-C06"])
            case["provenance"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                canonicalize(case)

    def test_literal_missing_and_zero_remain_distinct(self):
        self.assertEqual(solve(self.controls["P3-C02"])["path"], ["target_00"])
        for identity in ("P3-C03", "P3-C04", "P3-C05"):
            self.assertEqual(solve(self.controls[identity])["path"], ["IDLE"] * 3)

    def test_idle_history_and_negative_path_score(self):
        c = copy.deepcopy(self.controls["P3-C08"])
        c["switch_cost"] = 200
        metrics = verify_path(c, ["target_00", "IDLE", "target_01"])
        self.assertEqual(metrics["switch_count"], 1)
        self.assertEqual(metrics["net_objective"], -100)
        self.assertEqual(metrics["block_count"], 2)
        self.assertEqual(solve(c)["net_objective"], 50)

    def test_permutation_canonicalizes_both_matrices_without_mutating(self):
        case = copy.deepcopy(self.controls["P3-C11"])
        case["target_ids"].reverse()
        for key in ("scores", "eligibility"):
            case[key] = [row[::-1] for row in case[key]]
        original = copy.deepcopy(case)
        self.assertEqual(canonicalize(case), self.controls["P3-C11"])
        self.assertEqual(case, original)
        with self.assertRaises(ValueError):
            solve(case)  # E0 itself requires canonical order.

    def test_reference_is_read_only_and_stdlib_independent(self):
        check_oracle_imports()
        c = copy.deepcopy(self.controls["P3-C16"])
        before = copy.deepcopy(c)
        solve(c)
        self.assertEqual(c, before)
        self.assertEqual(self.manifest["source_sha256"][ORACLE], sha((ROOT / ORACLE).read_bytes()))

    def test_oracle_itself_rejects_malformed_numeric_problems(self):
        for name, case in invalid_cases(self.controls["P3-C06"]):
            if name[:6] in {"P3-I14", "P3-I16"}:
                continue  # UTC/provenance are the harness contract, not E0's numeric problem.
            with self.subTest(variant=name), self.assertRaises(ValueError):
                solve(case)

    def test_metamorphic_relations(self):
        checks = check_metamorphic(self.corpus["controls"])
        self.assertEqual(len(checks), 59)
        self.assertEqual(len({c["transformation"] for c in checks}), 5)

    def test_all_predeclared_fault_classes_are_detected_with_scope_labels(self):
        checks = check_mutations(self.corpus["controls"])
        self.assertEqual(
            {x["id"] for x in checks}, set(protocol()["acceptance"]["negative_controls"])
        )
        self.assertTrue(all(x["detected"] for x in checks))
        self.assertIn("adapter not exercised", checks[-1]["mechanism"])

    def test_wrong_objective_path_counts_and_boolean_results_rejected(self):
        c = self.controls["P3-C08"]
        for key, value in [
            ("net_objective", 100),
            ("switch_count", 0),
            ("enumerated_paths", 26),
            ("feasible_paths", 0),
            ("maximizing_paths", True),
            ("path", ["target_00"] * 3),
        ]:
            row = solve(c)
            row[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_reference_row(c, row)

    def test_utc_midnight_and_half_open_grid(self):
        grid = slot_grid(self.controls["P3-C15"])
        self.assertEqual(grid[0][0].isoformat(), "2024-03-20T23:00:00+00:00")
        self.assertEqual(grid[-1][1].isoformat(), "2024-03-21T02:00:00+00:00")
        for index, (_, boundary) in enumerate(grid):
            membership = [i for i, (start, end) in enumerate(grid) if start <= boundary < end]
            self.assertEqual(membership, [index + 1] if index < 2 else [])

    def test_strict_json_rejects_duplicates_nonfinite_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for raw in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}']:
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    read_json(path)
        self.assertEqual(serialize({"z": None, "a": True}), b'{\n  "a": true,\n  "z": null\n}\n')

    def test_offline_guards_actually_reject_network_imports_and_subprocess(self):
        with offline_computation():
            for operation in [
                lambda: socket.socket(),
                lambda: socket.create_connection(("x", 1)),
                lambda: socket.getaddrinfo("x", 1),
                lambda: subprocess.run(["true"]),
            ]:
                with self.assertRaises(RuntimeError):
                    operation()
            for name in ("astroscope", "astropy", "numpy", "scipy", "requests"):
                with self.assertRaises(ImportError):
                    importlib.import_module(name)

    def test_fresh_interpreter_full_offline_byte_replay(self):
        # -I -S proves no installed scientific package is needed. No candidate is imported.
        code = """
import sys
sys.path.insert(0, sys.argv[1])
from validation.schedule_corpus_audit import main
sys.argv = ['schedule_corpus_audit', '--output', sys.argv[2]]
raise SystemExit(main())
"""
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "audit.json"
            subprocess.run(
                [sys.executable, "-I", "-S", "-c", code, str(ROOT), str(output)],
                cwd=ROOT,
                check=True,
                timeout=600,
                capture_output=True,
                text=True,
            )
            record = json.loads(output.read_text())
            self.assertTrue(record["overall_passed"])
            self.assertTrue(record["reference_regenerated_byte_identical"])
            self.assertEqual(record["counts"], self.manifest["expected_counts"])
            self.assertEqual(record["candidate_evaluations"], 0)
            self.assertFalse(record["physical_qualification"])
            self.assertEqual(record["environment"]["installed_packages"], {})


if __name__ == "__main__":
    unittest.main()
