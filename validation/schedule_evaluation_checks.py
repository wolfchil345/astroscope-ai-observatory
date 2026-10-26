"""Independent access-journal reconciliation; imports no scheduling methods."""

from datetime import datetime

from validation.schedule_corpus import require, serialize, sha


def verify_journal(events, record):
    require(record["overall_passed"] is True, "journal acceptance requires complete passing record")
    require([e["sequence"] for e in events] == list(range(1, len(events) + 1)), "journal sequence")
    for event in events:
        instant = datetime.fromisoformat(event["timestamp_utc"])
        require(
            instant.tzinfo is not None and instant.utcoffset().total_seconds() == 0, "journal UTC"
        )
    require(
        [e["event"] for e in events[:3]] == ["run_start", "run_verified", "session_open"],
        "opening events",
    )
    require(
        [e["event"] for e in events[-2:]] == ["session_close", "run_complete"], "closing events"
    )
    require(
        all(e["access_label"] == record["access_label"] for e in events[:3]), "journal access label"
    )
    require(events[1]["environment"] == record["environment"], "journal implementation environment")
    require(events[2]["source_commit"] == record["source_freeze_commit"], "journal frozen source")
    calls = []
    for row in record["results"]:
        for method in ["B0", "B1", "B2"]:
            require(
                row["methods"][method]["calls"] == dict(warmup=1, measured=5), "method repetitions"
            )
            for phase, repetition in [("warmup", 0)] + [("measured", r) for r in range(5)]:
                calls.append(
                    dict(
                        case_id=row["case_id"],
                        split=row["split"],
                        method=method,
                        phase=phase,
                        repetition=repetition,
                        output_sha256=sha(serialize(row["methods"][method]["output"])),
                    )
                )
    access = events[3:-2]
    require(len(access) == 2 * len(calls), "journal complete call coverage")
    for invocation, expected in enumerate(calls, 1):
        start, complete = access[2 * invocation - 2 : 2 * invocation]
        require(
            start["event"] == "method_start" and complete["event"] == "method_complete",
            "call event order",
        )
        require(start["invocation"] == complete["invocation"] == invocation, "invocation identity")
        for key, value in expected.items():
            require(complete[key] == value, f"completed call {key}")
            if key != "output_sha256":
                require(start[key] == value, f"started call {key}")
    reserved = sum(c["split"] == "evaluation_reserved" for c in calls)
    require(events[-2]["attempts"] == events[-2]["successes"] == len(calls), "session call counts")
    require(
        events[-2]["reserved_attempts"] == events[-2]["reserved_successes"] == reserved,
        "session reserved counts",
    )
    require(
        events[-1]["overall_passed"] is True and events[-1]["status"] == "passed", "run completion"
    )
    return dict(
        passed=True,
        method_invocations=len(calls),
        reserved_method_invocations=reserved,
        events=len(events),
    )
