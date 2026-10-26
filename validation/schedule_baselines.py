"""Validation-only B0 adapter and B1 immediate policy; development access only."""

from datetime import UTC, datetime
from unittest.mock import patch

from astroscope import planner, schedule
from validation.schedule_corpus import canonicalize, protocol, require, slot_grid

_SPEC = protocol()
_DEVELOPMENT = {c["id"] for c in _SPEC["primary_corpus"]["cases"] if c["split"] == "development"}
_CONTROLS = {c["id"] for c in _SPEC["controls"]}
_ENDPOINT = {c["id"]: c["endpoint_override"] for c in _SPEC["controls"] if "endpoint_override" in c}


def development_case(case):
    c = canonicalize(case)
    allowed = (
        c["split"] == "development"
        and c["case_id"] in _DEVELOPMENT
        or c["split"] == "development_control"
        and c["case_id"] in _CONTROLS
    )
    require(allowed, "Mission 65 forbids evaluation-reserved or unregistered candidate execution")
    return c


def b1(case):
    """Choose maximum immediate net reward, including idle; retain history on idle."""
    c = development_case(case)
    last, path, examined = None, [], 0
    for scores, mask in zip(c["scores"], c["eligibility"], strict=True):
        choices = []
        for j, target in enumerate(c["target_ids"]):
            if mask[j] is True and scores[j] is not None:
                charge = c["switch_cost"] if last is not None and last != target else 0
                choices.append((scores[j] - charge, target))
        choices.append((0, "IDLE"))
        examined += len(choices)
        action = max(choices, key=lambda x: x[0])[1]
        path.append(action)
        if action != "IDLE":
            last = action
    return dict(path=path, action_values_examined=examined)


def decode_blocks(case, result):
    """Reject malformed blocks before decoding exact half-open slots and idle gaps."""
    c = development_case(case)
    grid = slot_grid(c)
    boundaries = [a for a, _ in grid] + [grid[-1][1]]
    path = ["IDLE"] * c["slots"]
    previous_end, previous_target = None, None
    for block in result.schedule_blocks:
        start, end = block.start_utc, block.end_utc
        for instant in (start, end, block.start_local, block.end_local, block.peak_local):
            require(
                isinstance(instant, datetime)
                and instant.tzinfo is not None
                and instant.utcoffset().total_seconds() == 0,
                "block must use aware UTC",
            )
        require(start in boundaries and end in boundaries and start < end, "block grid/range")
        require(block.object_key in c["target_ids"] and block.category == "catalog", "block target")
        require(previous_end is None or previous_end <= start, "overlap/order")
        require(
            not (previous_end == start and previous_target == block.object_key),
            "adjacent identical blocks were not merged",
        )
        require(block.start_local == start and block.end_local == end, "local/UTC block mismatch")
        require(block.duration_minutes == (end - start).total_seconds() / 60, "block duration")
        slots = [t for t, (a, b) in enumerate(grid) if start <= a and b <= end]
        require(bool(slots), "empty block")
        j = c["target_ids"].index(block.object_key)
        require(
            all(c["eligibility"][t][j] is True and c["scores"][t][j] is not None for t in slots),
            "block crosses unusable slot",
        )
        peak = max(slots, key=lambda t: c["scores"][t][j])
        require(
            block.peak_score == c["scores"][peak][j] and block.peak_local == grid[peak][0],
            "block peak/earliest tie",
        )
        require(
            block.peak_altitude_degrees == 45 and block.peak_moon_separation_degrees == 90,
            "synthetic block geometry",
        )
        for t in slots:
            require(path[t] == "IDLE", "overlapping decoded slot")
            path[t] = block.object_key
        previous_end, previous_target = end, block.object_key
    require(result.scheduled_minutes == 60 * sum(a != "IDLE" for a in path), "scheduled duration")
    require(
        result.sample_count == c["slots"] + 1 and result.evaluated_target_count == c["targets"],
        "sample/target count",
    )
    require(
        datetime.fromisoformat(result.start_local_iso) == grid[0][0]
        and datetime.fromisoformat(result.end_local_iso) == grid[-1][1],
        "result interval",
    )
    top = max(result.schedule_blocks, key=lambda b: b.peak_score, default=None)
    require(result.top_target_key == (top.object_key if top else None), "top-target metadata")
    return path


def b0(case):
    """Run the unchanged strict scheduler, patching only its planner-call boundary."""
    c = development_case(case)
    grid = slot_grid(c)
    instants = [a for a, _ in grid] + [grid[-1][1]]
    snapshots = []
    for t in range(c["slots"]):
        snapshots.append((c["scores"][t], c["eligibility"][t]))
    endpoint = _ENDPOINT.get(
        c["case_id"], {"scores": [0] * c["targets"], "eligibility": [False] * c["targets"]}
    )
    snapshots.append((endpoint["scores"], endpoint["eligibility"]))
    calls = []

    def controlled_plan(**kwargs):
        instant = datetime.combine(kwargs["local_date"], kwargs["local_time"], tzinfo=UTC)
        require(len(calls) < len(instants) and instant == instants[len(calls)], "planner call grid")
        require(
            kwargs["timezone_name"] == "UTC"
            and kwargs["latitude_deg"] == 0
            and kwargs["longitude_deg"] == 0
            and kwargs["elevation_m"] == 0,
            "synthetic site contract",
        )
        q, e = snapshots[len(calls)]
        calls.append(instant.isoformat())
        entries = tuple(
            planner.ObservationPlanEntry(
                object_key=target,
                category="catalog",
                altitude_degrees=45,
                azimuth_degrees=90,
                cardinal_direction="east",
                airmass=1.4,
                moon_separation_degrees=90,
                status="observable",
                altitude_score=0,
                airmass_score=0,
                moon_separation_score=0,
                darkness_score=0,
                total_score=0 if q[j] is None else q[j],
                rating="good",
                recommended=e[j] is True and q[j] is not None,
            )
            for j, target in enumerate(c["target_ids"])
        )
        return planner.ObservationPlanResult(
            entries, -30, sum(x.recommended for x in entries), c["targets"], instant.isoformat()
        )

    interval = schedule.resolve_schedule_interval(
        schedule.ScheduleIntervalRequest(
            "UTC",
            schedule.ScheduleCivilEndpoint(instants[0].date(), instants[0].time()),
            schedule.ScheduleCivilEndpoint(instants[-1].date(), instants[-1].time()),
        )
    )
    with patch.object(schedule, "calculate_observation_plan", side_effect=controlled_plan):
        result = schedule.calculate_observation_schedule_strict(
            0,
            0,
            0,
            interval,
            interval_minutes=60,
            minimum_score=0,
            include_catalog_targets=True,
            include_solar_system_targets=False,
        )
    require(calls == [x.isoformat() for x in instants], "N+1 snapshots required")
    require(len(result.timeline_points) == len(instants) * c["targets"], "timeline count")
    for t, (q, e) in enumerate(snapshots):
        for j, target in enumerate(c["target_ids"]):
            point = result.timeline_points[t * c["targets"] + j]
            require(
                point.object_key == target
                and point.category == "catalog"
                and datetime.fromisoformat(point.utc_datetime_iso) == instants[t]
                and datetime.fromisoformat(point.local_datetime_iso) == instants[t],
                "timeline identity/time",
            )
            require(
                point.total_score == (0 if q[j] is None else q[j])
                and point.recommended is (e[j] is True and q[j] is not None),
                "timeline mask",
            )
    return dict(
        path=decode_blocks(c, result),
        planner_calls=calls,
        snapshot_count=len(calls),
        endpoint_override=c["case_id"] in _ENDPOINT,
        missing_score_mask=[[q is None for q in row] for row in c["scores"]],
        unknown_eligibility_mask=[[e is None for e in row] for row in c["eligibility"]],
        block_count=len(result.schedule_blocks),
        blocks=[
            dict(
                target=b.object_key,
                start_utc=b.start_utc.isoformat(),
                end_utc=b.end_utc.isoformat(),
                duration_minutes=b.duration_minutes,
                peak_score=b.peak_score,
            )
            for b in result.schedule_blocks
        ],
    )
