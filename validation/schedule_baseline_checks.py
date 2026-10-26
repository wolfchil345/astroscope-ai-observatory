"""Independent per-slot policy and output checks; no baseline implementation imports."""

from validation.schedule_corpus import canonicalize, require, verify_path


def check_policy(case, path, method):
    c = canonicalize(case)
    metrics = verify_path(c, path)
    require(method in {"B0", "B1"}, "unknown method")
    observed = []
    for t, action in enumerate(path):
        candidates = []
        for rank, target in enumerate(c["target_ids"]):
            score = c["scores"][t][rank]
            if score is None or c["eligibility"][t][rank] is not True:
                continue
            if method == "B1" and observed and observed[-1] != target:
                score -= c["switch_cost"]
            candidates.append((target, score, rank))
        if method == "B1" or not candidates:
            candidates.append(("IDLE", 0, c["targets"]))
        selected = next((x for x in candidates if x[0] == action), None)
        require(selected is not None, f"{method}: chosen action not allowed at {t}")
        require(
            all(
                value < selected[1] or value == selected[1] and rank >= selected[2]
                for _, value, rank in candidates
            ),
            f"{method}: greedy policy mismatch at {t}",
        )
        if action != "IDLE":
            observed.append(action)
    return metrics


def check_result(case, result, method, reference):
    metrics = check_policy(case, result["path"], method)
    require(reference["case_id"] == case["case_id"], "reference ID")
    regret = reference["net_objective"] - metrics["net_objective"]
    require(regret >= 0, "baseline exceeds exhaustive bound")
    return dict(
        **metrics,
        oracle_objective=reference["net_objective"],
        regret=regret,
        regret_over_100N=regret / (100 * case["slots"]),
        exact_path_match=result["path"] == reference["path"],
        feasibility_violations=0,
    )
