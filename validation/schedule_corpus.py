"""Mission 64 deterministic synthetic inputs and strict, non-production contract."""

import copy
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/research/protocols/observation_optimisation_v1.json"
PROTOCOL_SHA256 = "fc379a617fecf29400fb9cc999c009067a13154efb2b20e51529e0a6a57408ff"
CORPUS = "validation/fixtures/schedule_corpus_v1.json"
REFERENCE = "validation/fixtures/schedule_exhaustive_v1.json"
MANIFEST = "validation/manifests/schedule_corpus_v1.json"
SOURCE = "validation/schedule_corpus.py"
ORACLE = "validation/reference_generation/schedule_exhaustive.py"
KEYS = {
    "case_id",
    "core_id",
    "family",
    "split",
    "replicate",
    "slots",
    "targets",
    "start_utc",
    "slot_minutes",
    "target_ids",
    "scores",
    "eligibility",
    "switch_cost",
    "provenance",
}
PROVENANCE_KEYS = {
    "source_kind",
    "protocol_id",
    "protocol_sha256",
    "generator_commit",
    "generator_sha256",
    "construction",
    "transformations",
    "license",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def read_json(path):
    """Reject duplicate keys and non-JSON numeric extensions before schema checks."""

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"non-JSON constant: {value}")

    return json.loads(
        Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )


def protocol():
    raw = (ROOT / PROTOCOL).read_bytes()
    require(sha(raw) == PROTOCOL_SHA256, "reviewed protocol bytes changed")
    return json.loads(raw)


def canonicalize(case):
    """Validate without coercion; sort IDs and remap both matrices on a copy."""
    require(type(case) is dict and set(case) == KEYS, "case keys")
    n, m = case["slots"], case["targets"]
    require(type(n) is int and 1 <= n <= 9, "slots must be integer 1..9")
    require(type(m) is int and 0 <= m <= 3, "targets must be integer 0..3")
    for key in ("case_id", "core_id", "family"):
        require(type(case[key]) is str and re.fullmatch(r"[A-Za-z0-9_-]+", case[key]), key)
    require(case["family"] in {"F1", "F2", "F3", "F4", "F5", "F6", "control"}, "family")
    require(case["split"] in {"development", "evaluation_reserved", "development_control"}, "split")
    require(type(case["replicate"]) is int and 0 <= case["replicate"] <= 3, "replicate")
    if case["family"] == "control":
        require(case["split"] == "development_control", "control split")
    else:
        require(
            case["split"] == ("development" if case["replicate"] < 2 else "evaluation_reserved"),
            "replicate split",
        )
    ids = case["target_ids"]
    require(type(ids) is list and len(ids) == m, "target IDs shape")
    require(
        all(type(x) is str and re.fullmatch(r"target_[0-9]{2}", x) for x in ids), "ASCII target IDs"
    )
    require(len(set(ids)) == m, "duplicate target ID")
    for key in ("scores", "eligibility"):
        matrix = case[key]
        require(type(matrix) is list and len(matrix) == n, f"{key} rows")
        require(all(type(row) is list and len(row) == m for row in matrix), f"{key} columns")
    require(
        all(x is None or type(x) is int and 0 <= x <= 100 for row in case["scores"] for x in row),
        "score domain",
    )
    require(
        all(x is None or type(x) is bool for row in case["eligibility"] for x in row),
        "eligibility domain",
    )
    require(type(case["switch_cost"]) is int and case["switch_cost"] >= 0, "switch cost")
    require(type(case["slot_minutes"]) is int and case["slot_minutes"] == 60, "cadence")
    start = case["start_utc"]
    require(
        type(start) is str
        and re.fullmatch(r"[0-9]{4}(-[0-9]{2}){2}T[0-9]{2}(:[0-9]{2}){2}Z", start),
        "canonical UTC",
    )
    try:
        instant = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        instant + timedelta(hours=n)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid UTC grid") from exc
    p = case["provenance"]
    require(type(p) is dict and set(p) == PROVENANCE_KEYS, "provenance keys")
    require(
        p["source_kind"] == "synthetic_project_definition" and p["license"] == "MIT",
        "source kind/license",
    )
    require(
        p["protocol_id"] == "P3-SCHEDULE-001-v1" and p["protocol_sha256"] == PROTOCOL_SHA256,
        "protocol provenance",
    )
    for key, length in (("generator_commit", 40), ("generator_sha256", 64)):
        require(type(p[key]) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", p[key]), key)
    require(type(p["construction"]) is str and bool(p["construction"]), "construction")
    require(
        type(p["transformations"]) is list
        and all(type(x) is str and bool(x) for x in p["transformations"]),
        "transforms",
    )
    order = sorted(range(m), key=ids.__getitem__)
    result = copy.deepcopy(case)
    result["target_ids"] = [ids[j] for j in order]
    for key in ("scores", "eligibility"):
        result[key] = [[row[j] for j in order] for row in case[key]]
    return result


def counter(family, n, m, replicate, t, j, channel, modulus):
    text = f"astroscope-p3-v1|{family}|{n}|{m}|{replicate}|{t}|{j}|{channel}"
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big") % modulus


def matrices(family, n, m, replicate):
    def h(t, j, channel, modulus):
        return counter(family, n, m, replicate, t, j, channel, modulus)

    scores, eligibility = [], []
    for t in range(n):
        q, e = [], []
        for j in range(m):
            known = True
            if family == "F1":
                score = h(0, j, "score", 101)
            elif family == "F2":
                score = 40 + h(0, 0, "base", 41)
                if j == (t + replicate) % m:
                    score += 1 + h(0, 0, "gap", 5)
            elif family == "F3":
                score = min(100, max(0, h(0, j, "base", 101) + t * (h(0, j, "slope", 21) - 10)))
            elif family in {"F4", "F5", "F6"}:
                score = h(t, j, "score", 101)
                if family == "F4":
                    known = h(t, j, "eligibility", 4) == 0
                elif family == "F5":
                    known = t != n // 2
                else:
                    if h(t, j, "score_missing", 4) == 0:
                        score = None
                    known = [True, False, None][h(t, j, "eligibility", 3)]
            else:
                raise ValueError("unknown family")
            q.append(score)
            e.append(known)
        scores.append(q)
        eligibility.append(e)
    return scores, eligibility


def build_corpus(source_commit):
    p = protocol()
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit), "source commit")
    provenance = dict(
        source_kind="synthetic_project_definition",
        protocol_id=p["protocol_id"],
        protocol_sha256=PROTOCOL_SHA256,
        generator_commit=source_commit,
        generator_sha256=sha((ROOT / SOURCE).read_bytes()),
        construction="M63 SHA256 counter and family formula v1",
        transformations=[],
        license="MIT",
    )
    cases = []
    for spec in p["primary_corpus"]["cases"]:
        q, e = matrices(spec["family"], spec["slots"], spec["targets"], spec["replicate"])
        cases.append(
            canonicalize(
                dict(
                    case_id=spec["id"],
                    core_id=spec["core_id"],
                    family=spec["family"],
                    split=spec["split"],
                    replicate=spec["replicate"],
                    slots=spec["slots"],
                    targets=spec["targets"],
                    start_utc=p["model"]["start_utc"],
                    slot_minutes=60,
                    target_ids=[f"target_{j:02}" for j in range(spec["targets"])],
                    scores=q,
                    eligibility=e,
                    switch_cost=spec["switch_cost"],
                    provenance=provenance,
                )
            )
        )
    controls, adapter_metadata = [], {}
    for spec in p["controls"]:
        prov = {**provenance, "construction": f"M63 explicit control {spec['id']}"}
        if "original_reference" in spec:
            prov["transformations"] = ["M55 retained published example; development reuse"]
        controls.append(
            canonicalize(
                dict(
                    case_id=spec["id"],
                    core_id=spec["id"],
                    family="control",
                    split="development_control",
                    replicate=0,
                    slots=spec["slots"],
                    targets=spec["targets"],
                    start_utc=spec.get("start_utc", p["model"]["start_utc"]),
                    slot_minutes=60,
                    target_ids=[f"target_{j:02}" for j in range(spec["targets"])],
                    scores=spec["scores"],
                    eligibility=spec["eligibility"],
                    switch_cost=spec["switch_cost"],
                    provenance=prov,
                )
            )
        )
        if "endpoint_override" in spec:
            adapter_metadata[spec["id"]] = spec["endpoint_override"]
    return dict(
        schema_version=1,
        release_id="P3-SCHEDULE-INPUT-v1",
        protocol_id=p["protocol_id"],
        primary_cases=cases,
        controls=controls,
        future_adapter_endpoint_overrides=adapter_metadata,
        scope="Synthetic nominal scores; no calibrated astronomy or production change",
    )


def slot_grid(case):
    c = canonicalize(case)
    start = datetime.strptime(c["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return [(start + timedelta(hours=t), start + timedelta(hours=t + 1)) for t in range(c["slots"])]


def verify_path(case, path):
    """Independent scoring: filter observations then compare adjacent retained IDs."""
    c = canonicalize(case)
    require(type(path) is list and len(path) == c["slots"], "path length")
    selected, gross = [], 0
    for t, action in enumerate(path):
        require(type(action) is str, "action type")
        if action == "IDLE":
            continue
        require(action in c["target_ids"], "unknown action")
        j = c["target_ids"].index(action)
        require(
            c["eligibility"][t][j] is True and c["scores"][t][j] is not None,
            "infeasible observation",
        )
        selected.append(action)
        gross += c["scores"][t][j]
    changes = sum(a != b for a, b in zip(selected, selected[1:], strict=False))
    blocks = sum(a != "IDLE" and (t == 0 or path[t - 1] != a) for t, a in enumerate(path))
    return dict(
        gross_score=gross,
        switch_count=changes,
        switch_charge=c["switch_cost"] * changes,
        net_objective=gross - c["switch_cost"] * changes,
        observed_minutes=60 * len(selected),
        idle_minutes=60 * (c["slots"] - len(selected)),
        block_count=blocks,
    )
