"""Analytic, malformed-input and fault-sensitive checks of the M64 reference release."""

import copy
import hashlib
import math
from datetime import timedelta

from validation.reference_generation.schedule_exhaustive import solve
from validation.schedule_corpus import (
    ORACLE,
    ROOT,
    canonicalize,
    require,
    slot_grid,
    verify_path,
)

# Hand-derived control values and canonical paths, specified before E0 generation.
# A/B mean target_00/target_01 and I means IDLE; these are not copied from E0.
ANALYTIC = {
    "P3-C01": (0, "I"),
    "P3-C02": (0, "A"),
    "P3-C03": (0, "III"),
    "P3-C04": (0, "III"),
    "P3-C05": (0, "III"),
    "P3-C06": (210, "AAA"),
    "P3-C07": (269, "AAA"),
    "P3-C08": (80, "AIB"),
    "P3-C09": (100, "AIA"),
    "P3-C10": (1, "A"),
    "P3-C11": (270, "ABA"),
    "P3-C12": (200, "AIA"),
    "P3-C13": (10, "A"),
    "P3-C14": (100, "AIA"),
    "P3-C15": (170, "BAB"),
    "P3-C16": (195, "BAA"),
}


def analytic_matches(case, result):
    value, letters = ANALYTIC[case["case_id"]]
    path = [{"A": "target_00", "B": "target_01", "I": "IDLE"}[x] for x in letters]
    return result["net_objective"] == value and result["path"] == path


def independent_matrix_check(case):
    """Separate formula transcription using the hexadecimal digest representation."""
    f, n, m, r = (case[k] for k in ("family", "slots", "targets", "replicate"))

    def h(t, j, channel, modulus):
        fields = ("astroscope-p3-v1", f, n, m, r, t, j, channel)
        digest = hashlib.sha256("|".join(map(str, fields)).encode("ascii")).hexdigest()
        return int(digest[:16], 16) % modulus

    for t in range(n):
        for j in range(m):
            q, e = h(t, j, "score", 101), True
            if f == "F1":
                q = h(0, j, "score", 101)
            if f == "F2":
                q = 40 + h(0, 0, "base", 41)
                q += (1 + h(0, 0, "gap", 5)) * int((t + r) % m == j)
            if f == "F3":
                q = h(0, j, "base", 101) + t * (h(0, j, "slope", 21) - 10)
                q = 0 if q < 0 else 100 if q > 100 else q
            if f == "F4":
                e = h(t, j, "eligibility", 4) == 0
            if f == "F5":
                e = t != n // 2
            if f == "F6":
                q = None if h(t, j, "score_missing", 4) == 0 else q
                code = h(t, j, "eligibility", 3)
                e = True if code == 0 else False if code == 1 else None
            require(case["scores"][t][j] == q, f"independent score: {case['case_id']}")
            require(case["eligibility"][t][j] is e, f"independent mask: {case['case_id']}")


def invalid_cases(base):
    """Concrete variants grouped by the sixteen preregistered rejection classes."""
    variants = {
        "P3-I01": [("slots", 0), ("slots", True), ("slots", 1.0)],
        "P3-I02": [("targets", -1), ("targets", True), ("targets", 4)],
        "P3-I03": [("target_ids", ["target_00", "target_00"])],
        "P3-I04": [
            ("target_ids", ["target_００", "target_01"]),
            ("target_ids", ["A", "B"]),
            ("target_ids", [0, 1]),
        ],
        "P3-I05": [("scores", []), ("scores", [[1]]), ("scores", "matrix")],
        "P3-I06": [("eligibility", []), ("eligibility", [[True]])],
        "P3-I07": [("score_cell", -1)],
        "P3-I08": [("score_cell", 101)],
        "P3-I09": [("score_cell", True), ("score_cell", False)],
        "P3-I10": [("score_cell", x) for x in [1.0, 1.5, math.nan, math.inf, -math.inf, "1"]],
        "P3-I11": [("eligibility_cell", x) for x in [0, 1, "true", [], {}]],
        "P3-I12": [("switch_cost", -1)],
        "P3-I13": [("switch_cost", x) for x in [True, 1.0, 1.5, None]],
        "P3-I14": [
            ("start_utc", x)
            for x in [
                "2024-03-20T00:00:00",
                "2024-03-20T00:00:00+00:00",
                "2024-03-20T09:00:00+09:00",
                "2024-02-30T00:00:00Z",
                "2024-03-20T00:00:60Z",
                "2024-3-20T00:00:00Z",
                "9999-12-31T23:00:00Z",
                None,
            ]
        ]
        + [("slot_minutes", x) for x in [30, 60.0, True]],
        "P3-I15": [("slots", 10)],
        "P3-I16": [("unknown", 1)],
    }
    for group, specs in variants.items():
        for index, (key, value) in enumerate(specs):
            case = copy.deepcopy(base)
            if key == "score_cell":
                case["scores"][0][0] = value
            elif key == "eligibility_cell":
                case["eligibility"][0][0] = value
            else:
                case[key] = value
            yield f"{group}-{index:02}", case


def check_rejections(controls):
    results = []
    for identity, case in invalid_cases(controls[5]):
        try:
            canonicalize(case)
        except ValueError:
            results.append(dict(id=identity, rejected=True))
        else:
            raise ValueError(f"invalid input accepted: {identity}")
    return results


def check_reference_row(case, row):
    require(
        set(row)
        == {
            "case_id",
            "path",
            "net_objective",
            "gross_score",
            "switch_count",
            "switch_charge",
            "enumerated_paths",
            "feasible_paths",
            "maximizing_paths",
        },
        "reference keys",
    )
    require(row["case_id"] == case["case_id"], "reference ID")
    metrics = verify_path(case, row["path"])
    for key in ("gross_score", "switch_count", "switch_charge", "net_objective"):
        require(type(row[key]) is int and row[key] == metrics[key], f"independent {key}")
    expected_feasible = 1
    for q, e in zip(case["scores"], case["eligibility"], strict=True):
        expected_feasible *= 1 + sum(
            mask is True and score is not None for score, mask in zip(q, e, strict=True)
        )
    require(
        type(row["enumerated_paths"]) is int
        and row["enumerated_paths"] == (case["targets"] + 1) ** case["slots"],
        "path coverage",
    )
    require(
        type(row["feasible_paths"]) is int and row["feasible_paths"] == expected_feasible,
        "feasible path coverage",
    )
    require(
        type(row["maximizing_paths"]) is int and 1 <= row["maximizing_paths"] <= expected_feasible,
        "maximizer count",
    )
    require(row["net_objective"] >= 0, "all-idle lower bound")
    if case["family"] == "control":
        require(analytic_matches(case, row), f"analytic control {case['case_id']}")
    return metrics


def check_metamorphic(controls):
    results = []
    for case in controls:
        original = solve(case)
        variants = []
        permuted = copy.deepcopy(case)
        for key in ("target_ids",):
            permuted[key].reverse()
        for key in ("scores", "eligibility"):
            permuted[key] = [row[::-1] for row in permuted[key]]
        variants.append(("permutation", permuted, 1, original["path"]))
        shifted = copy.deepcopy(case)
        shifted["start_utc"] = (slot_grid(case)[0][0] + timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        variants.append(("UTC_translation", shifted, 1, original["path"]))
        keep = [
            j
            for j in range(case["targets"])
            if any(
                row[j] is True and score[j] is not None
                for row, score in zip(case["eligibility"], case["scores"], strict=True)
            )
        ]
        if len(keep) < case["targets"]:
            removed = copy.deepcopy(case)
            removed["target_ids"] = [case["target_ids"][j] for j in keep]
            removed["targets"] = len(keep)
            for key in ("scores", "eligibility"):
                removed[key] = [[row[j] for j in keep] for row in case[key]]
            variants.append(("remove_unusable", removed, 1, original["path"]))
        if case["slots"] < 9:
            appended = copy.deepcopy(case)
            appended["slots"] += 1
            appended["scores"].append([None] * case["targets"])
            appended["eligibility"].append([False] * case["targets"])
            variants.append(("append_idle", appended, 1, original["path"] + ["IDLE"]))
        if all(q is None or q <= 50 for row in case["scores"] for q in row):
            scaled = copy.deepcopy(case)
            scaled["scores"] = [
                [None if q is None else 2 * q for q in row] for row in case["scores"]
            ]
            scaled["switch_cost"] *= 2
            variants.append(("positive_scaling", scaled, 2, original["path"]))
        for name, variant, factor, expected_path in variants:
            variant["provenance"]["transformations"].append(name)
            answer = solve(canonicalize(variant))
            require(
                answer["net_objective"] == factor * original["net_objective"]
                and answer["path"] == expected_path,
                f"metamorphic {name}",
            )
            results.append(dict(case_id=case["case_id"], transformation=name, passed=True))
    return results


def check_mutations(controls):
    source = (ROOT / ORACLE).read_text()
    by_id = {x["case_id"]: x for x in controls}
    mutations = [
        (
            "erase_last_target_on_idle",
            "P3-C08",
            "if action == m:\n                continue",
            "if action == m:\n                last = None\n                continue",
        ),
        ("omit_switch_cost", "P3-C08", "value = gross - cost * changes", "value = gross"),
        (
            "double_switch_cost",
            "P3-C08",
            "value = gross - cost * changes",
            "value = gross - 2 * cost * changes",
        ),
        (
            "charge_first_acquisition",
            "P3-C10",
            "if last is not None and action != last:",
            "if action != last:",
        ),
        (
            "admit_unknown_eligibility",
            "P3-C05",
            "eligibility[t][action] is not True",
            "eligibility[t][action] is False",
        ),
        (
            "treat_missing_score_as_known_zero",
            "P3-C03",
            "if eligibility[t][action] is not True or scores[t][action] is None:",
            "if eligibility[t][action] is not True:",
        ),
        ("wrong_canonical_tie", "P3-C02", "value > best:", "value >= best:"),
    ]
    results = []
    for name, case_id, before, after in mutations:
        require(source.count(before) == 1, f"mutation site changed: {name}")
        mutated = source.replace(before, after)
        if name == "treat_missing_score_as_known_zero":
            mutated = mutated.replace(
                "gross += scores[t][action]", "gross += (scores[t][action] or 0)"
            )
        namespace = {}
        exec(compile(mutated, f"<controlled-mutation:{name}>", "exec"), namespace)
        result = namespace["solve"](by_id[case_id])
        require(not analytic_matches(by_id[case_id], result), f"undetected mutation: {name}")
        results.append(
            dict(
                id=name,
                case_id=case_id,
                detected=True,
                mechanism="mutated independent oracle rejected by analytic control",
            )
        )
    for name, path in (
        ("select_terminal_snapshot", ["target_00", "target_01"]),
        ("off_by_one_time_membership", []),
    ):
        try:
            verify_path(by_id["P3-C13"], path)
        except ValueError:
            results.append(
                dict(
                    id=name,
                    case_id="P3-C13",
                    detected=True,
                    mechanism="malformed returned path rejected; adapter not exercised",
                )
            )
        else:
            raise ValueError(f"undetected boundary mutation: {name}")
    return results
