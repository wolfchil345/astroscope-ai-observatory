"""Independent candidate acceptance using raw path arithmetic and frozen exhaustive E0."""

from validation.schedule_corpus import canonicalize, require, verify_path


def check_candidate(case, result, reference):
    c = canonicalize(case)
    require(reference["case_id"] == c["case_id"], "reference ID")
    metrics = verify_path(c, result["path"])
    require(type(result["net_objective"]) is int, "candidate objective must be integer")
    require(result["net_objective"] == metrics["net_objective"], "candidate objective arithmetic")
    require(metrics["net_objective"] == reference["net_objective"], "nonzero exact regret")
    require(result["path"] == reference["path"], "canonical optimal path mismatch")
    counts = result["operation_counts"]
    require(all(type(x) is int and x >= 0 for x in counts.values()), "operation count type")
    n, m = c["slots"], c["targets"]
    feasible_actions = sum(
        1 + sum(e is True and q is not None for e, q in zip(mask, scores, strict=True))
        for mask, scores in zip(c["eligibility"], c["scores"], strict=True)
    )
    require(
        counts
        == dict(
            state_updates=n * (m + 1),
            action_values_examined=(m + 1) * feasible_actions,
            value_cells=(n + 1) * (m + 1),
            policy_cells=n * (m + 1),
        ),
        "operation accounting",
    )
    return dict(
        **metrics,
        oracle_objective=reference["net_objective"],
        regret=0,
        regret_over_100N=0.0,
        exact_path_match=True,
        feasibility_violations=0,
    )
