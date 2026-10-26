"""E0: direct exhaustive paths, independent of all project computation helpers.

Only itertools is imported. Callers validate the full documentary input contract;
this module independently checks the numeric problem and canonical ID order.
Every Cartesian path is visited, including infeasible paths. No DP, pruning,
candidate objective helper, cached solution or production import is used.
"""

from itertools import product


def solve(case):
    n, m = case["slots"], case["targets"]
    ids, scores, eligibility = case["target_ids"], case["scores"], case["eligibility"]
    cost = case["switch_cost"]
    if type(n) is not int or not 1 <= n <= 9 or type(m) is not int or not 0 <= m <= 3:
        raise ValueError("E0 dimensions")
    if (
        type(ids) is not list
        or len(ids) != m
        or any(
            type(x) is not str
            or len(x) != 9
            or x[:7] != "target_"
            or any(c not in "0123456789" for c in x[7:])
            for x in ids
        )
        or len(set(ids)) != m
        or ids != sorted(ids)
    ):
        raise ValueError("E0 canonical IDs")
    for matrix in (scores, eligibility):
        if (
            type(matrix) is not list
            or len(matrix) != n
            or any(type(row) is not list or len(row) != m for row in matrix)
        ):
            raise ValueError("E0 matrix shape")
    if any(
        q is not None and (type(q) is not int or not 0 <= q <= 100) for row in scores for q in row
    ):
        raise ValueError("E0 score domain")
    if any(e is not None and type(e) is not bool for row in eligibility for e in row):
        raise ValueError("E0 eligibility domain")
    if type(cost) is not int or cost < 0:
        raise ValueError("E0 cost")
    best, best_path, best_gross, best_changes = None, None, None, None
    visited, feasible, maximizers = 0, 0, 0
    for path in product(range(m + 1), repeat=n):
        visited += 1
        last, gross, changes = None, 0, 0
        for t, action in enumerate(path):
            if action == m:
                continue
            if eligibility[t][action] is not True or scores[t][action] is None:
                break
            gross += scores[t][action]
            if last is not None and action != last:
                changes += 1
            last = action
        else:
            feasible += 1
            value = gross - cost * changes
            if best is None or value > best:
                best, best_path, best_gross, best_changes = value, path, gross, changes
                maximizers = 1
            elif value == best:
                maximizers += 1
    return dict(
        case_id=case["case_id"],
        path=["IDLE" if j == m else ids[j] for j in best_path],
        net_objective=best,
        gross_score=best_gross,
        switch_count=best_changes,
        switch_charge=cost * best_changes,
        enumerated_paths=visited,
        feasible_paths=feasible,
        maximizing_paths=maximizers,
    )
