"""Mission 66 finite-horizon candidate; registered development inputs only."""

from validation.schedule_corpus import canonicalize, protocol, require

_SPEC = protocol()
_DEVELOPMENT = {c["id"] for c in _SPEC["primary_corpus"]["cases"] if c["split"] == "development"}
_CONTROLS = {c["id"] for c in _SPEC["controls"]}


def development_case(case):
    c = canonicalize(case)
    require(
        c["split"] == "development"
        and c["case_id"] in _DEVELOPMENT
        or c["split"] == "development_control"
        and c["case_id"] in _CONTROLS,
        "Mission 66 forbids evaluation-reserved or unregistered candidate execution",
    )
    return c


def b2(case):
    """Validate access before allocating or executing the backward recurrence."""
    return _solve(development_case(case))


def _solve(c):
    """Maximize nominal reward with last-non-idle state and canonical action ties."""
    n, m = c["slots"], c["targets"]
    # Index m denotes no previous target in state space, and IDLE in action space.
    values = [[0] * (m + 1) for _ in range(n + 1)]
    policy = [[m] * (m + 1) for _ in range(n)]
    examined = 0
    for t in range(n - 1, -1, -1):
        actions = [
            j for j in range(m) if c["eligibility"][t][j] is True and c["scores"][t][j] is not None
        ] + [m]
        for last in range(m + 1):
            best = None
            for action in actions:
                if action == m:
                    reward, successor = 0, last
                else:
                    charge = c["switch_cost"] if last != m and last != action else 0
                    reward, successor = c["scores"][t][action] - charge, action
                value = reward + values[t + 1][successor]
                examined += 1
                if best is None or value > best:
                    best = value
                    policy[t][last] = action
            values[t][last] = best
    path, last = [], m
    for t in range(n):
        action = policy[t][last]
        path.append("IDLE" if action == m else c["target_ids"][action])
        if action != m:
            last = action
    return dict(
        path=path,
        net_objective=values[0][m],
        operation_counts=dict(
            state_updates=n * (m + 1),
            action_values_examined=examined,
            value_cells=(n + 1) * (m + 1),
            policy_cells=n * (m + 1),
        ),
    )
