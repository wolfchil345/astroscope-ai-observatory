"""Night timeline and observation-schedule generation."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from astroscope.observer import get_timezone, resolve_local_datetime
from astroscope.planner import (
    PlannerCategory,
    PlannerRating,
    calculate_observation_plan,
)
from astroscope.visibility import VisibilityStatus

_LEGACY_VISUAL_NAMES = frozenset(
    {
        "ScheduleChartLabels",
        "create_schedule_figure",
    }
)


def __getattr__(name: str) -> object:
    """Resolve the two legacy visualization imports without eager Plotly loading."""

    if name in _LEGACY_VISUAL_NAMES:
        from astroscope import schedule_visuals

        return getattr(schedule_visuals, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(frozen=True, slots=True)
class TimelinePoint:
    """One target evaluation at one observation time."""

    object_key: str
    category: PlannerCategory
    local_datetime_iso: str
    utc_datetime_iso: str
    altitude_degrees: float
    azimuth_degrees: float
    moon_separation_degrees: float
    total_score: float
    rating: PlannerRating
    status: VisibilityStatus
    recommended: bool
    sun_altitude_degrees: float


@dataclass(frozen=True, slots=True)
class ScheduleBlock:
    """One continuous observation block."""

    object_key: str
    category: PlannerCategory
    start_local: datetime
    end_local: datetime
    peak_local: datetime
    start_utc: datetime
    end_utc: datetime
    duration_minutes: float
    peak_score: float
    peak_altitude_degrees: float
    peak_moon_separation_degrees: float
    rating: PlannerRating


@dataclass(frozen=True, slots=True)
class ObservationScheduleResult:
    """Complete timeline and chronological observing schedule."""

    timeline_points: tuple[TimelinePoint, ...]
    schedule_blocks: tuple[ScheduleBlock, ...]
    start_local_iso: str
    end_local_iso: str
    sample_count: int
    evaluated_target_count: int
    scheduled_minutes: float
    top_target_key: str | None


@dataclass(frozen=True, slots=True)
class ScheduleCivilEndpoint:
    """One explicitly dated civil endpoint for a strict schedule interval."""

    local_date: date
    local_time: time
    fold: int | None = None


@dataclass(frozen=True, slots=True)
class ScheduleIntervalRequest:
    """The two independently resolved civil endpoints of a schedule."""

    timezone_name: str
    start: ScheduleCivilEndpoint
    end: ScheduleCivilEndpoint


@dataclass(frozen=True, slots=True)
class ResolvedScheduleInterval:
    """A physically ordered schedule interval resolved to UTC."""

    request: ScheduleIntervalRequest
    start_utc: datetime
    end_utc: datetime
    elapsed: timedelta


def _format_schedule_datetime(
    value: datetime,
    *,
    include_seconds: bool = False,
) -> str:
    """Format an aware schedule datetime without discarding supplied precision."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Schedule datetimes must be timezone-aware.")

    if value.microsecond:
        timespec = "microseconds"
    elif value.second or include_seconds:
        timespec = "seconds"
    else:
        timespec = "minutes"

    return value.isoformat(timespec=timespec)


def resolve_schedule_interval(
    request: ScheduleIntervalRequest,
) -> ResolvedScheduleInterval:
    """Resolve strict schedule endpoints without implicit fold or gap policy."""

    start_utc = resolve_local_datetime(
        local_date=request.start.local_date,
        local_time=request.start.local_time,
        timezone_name=request.timezone_name,
        fold=request.start.fold,
    )
    end_utc = resolve_local_datetime(
        local_date=request.end.local_date,
        local_time=request.end.local_time,
        timezone_name=request.timezone_name,
        fold=request.end.fold,
    )
    elapsed = end_utc - start_utc

    if elapsed <= timedelta(0):
        raise ValueError("Schedule duration must be greater than zero.")

    if elapsed > timedelta(hours=18):
        raise ValueError("Schedule duration cannot exceed 18 hours.")

    return ResolvedScheduleInterval(
        request=request,
        start_utc=start_utc,
        end_utc=end_utc,
        elapsed=elapsed,
    )


def create_resolved_schedule_time_grid(
    interval: ResolvedScheduleInterval,
    interval_minutes: int,
) -> tuple[datetime, ...]:
    """Create a local-display grid from fixed elapsed UTC increments."""

    if not 15 <= interval_minutes <= 180:
        raise ValueError("Sampling interval must be between 15 and 180 minutes.")

    timezone_info = get_timezone(interval.request.timezone_name)
    step = timedelta(minutes=interval_minutes)
    grid: list[datetime] = []
    current_utc = interval.start_utc

    while current_utc < interval.end_utc:
        grid.append(current_utc.astimezone(timezone_info))
        current_utc += step

    grid.append(interval.end_utc.astimezone(timezone_info))

    return tuple(grid)


def _legacy_schedule_interval_request(
    local_date: date,
    start_time: time,
    end_time: time,
    timezone_name: str,
) -> ScheduleIntervalRequest:
    """Build the historical inferred-date request for compatibility wrappers."""

    if start_time == end_time:
        raise ValueError("Schedule start and end times must be different.")

    end_date = local_date if end_time > start_time else local_date + timedelta(days=1)

    return ScheduleIntervalRequest(
        timezone_name=timezone_name,
        start=ScheduleCivilEndpoint(local_date=local_date, local_time=start_time),
        end=ScheduleCivilEndpoint(local_date=end_date, local_time=end_time),
    )


def create_local_time_grid(
    local_date: date,
    start_time: time,
    end_time: time,
    timezone_name: str,
    interval_minutes: int,
) -> tuple[datetime, ...]:
    """Create the historical inferred-date grid with strict endpoint safety."""

    return create_resolved_schedule_time_grid(
        interval=resolve_schedule_interval(
            _legacy_schedule_interval_request(
                local_date=local_date,
                start_time=start_time,
                end_time=end_time,
                timezone_name=timezone_name,
            )
        ),
        interval_minutes=interval_minutes,
    )


def calculate_observation_schedule(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    start_time: time,
    end_time: time,
    interval_minutes: int = 60,
    minimum_altitude_degrees: float = 20.0,
    minimum_moon_separation_degrees: float = 30.0,
    minimum_score: float = 40.0,
    include_catalog_targets: bool = True,
    include_solar_system_targets: bool = True,
) -> ObservationScheduleResult:
    """Compatibility wrapper using historical overnight-date inference."""

    interval = resolve_schedule_interval(
        _legacy_schedule_interval_request(
            local_date=local_date,
            start_time=start_time,
            end_time=end_time,
            timezone_name=timezone_name,
        )
    )

    return calculate_observation_schedule_strict(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
        interval=interval,
        interval_minutes=interval_minutes,
        minimum_altitude_degrees=minimum_altitude_degrees,
        minimum_moon_separation_degrees=minimum_moon_separation_degrees,
        minimum_score=minimum_score,
        include_catalog_targets=include_catalog_targets,
        include_solar_system_targets=include_solar_system_targets,
    )


def calculate_observation_schedule_strict(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    interval: ResolvedScheduleInterval,
    interval_minutes: int = 60,
    minimum_altitude_degrees: float = 20.0,
    minimum_moon_separation_degrees: float = 30.0,
    minimum_score: float = 40.0,
    include_catalog_targets: bool = True,
    include_solar_system_targets: bool = True,
) -> ObservationScheduleResult:
    """Evaluate targets over an explicitly resolved physical schedule interval."""

    time_grid = create_resolved_schedule_time_grid(
        interval=interval,
        interval_minutes=interval_minutes,
    )
    timezone_name = interval.request.timezone_name

    if not (include_catalog_targets or include_solar_system_targets):
        return ObservationScheduleResult(
            timeline_points=(),
            schedule_blocks=(),
            start_local_iso=_format_schedule_datetime(time_grid[0]),
            end_local_iso=_format_schedule_datetime(time_grid[-1]),
            sample_count=len(time_grid),
            evaluated_target_count=0,
            scheduled_minutes=0.0,
            top_target_key=None,
        )

    plans = []
    timeline_points: list[TimelinePoint] = []

    for local_datetime in time_grid:
        plan = calculate_observation_plan(
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            elevation_m=elevation_m,
            timezone_name=timezone_name,
            local_date=local_datetime.date(),
            local_time=local_datetime.time().replace(tzinfo=None),
            minimum_altitude_degrees=(minimum_altitude_degrees),
            minimum_moon_separation_degrees=(minimum_moon_separation_degrees),
            minimum_score=minimum_score,
            include_catalog_targets=(include_catalog_targets),
            include_solar_system_targets=(include_solar_system_targets),
        )

        plans.append(plan)

        for entry in plan.entries:
            timeline_points.append(
                TimelinePoint(
                    object_key=entry.object_key,
                    category=entry.category,
                    local_datetime_iso=_format_schedule_datetime(local_datetime),
                    utc_datetime_iso=_format_schedule_datetime(
                        local_datetime.astimezone(UTC),
                        include_seconds=True,
                    ),
                    altitude_degrees=(entry.altitude_degrees),
                    azimuth_degrees=(entry.azimuth_degrees),
                    moon_separation_degrees=(entry.moon_separation_degrees),
                    total_score=entry.total_score,
                    rating=entry.rating,
                    status=entry.status,
                    recommended=entry.recommended,
                    sun_altitude_degrees=(plan.sun_altitude_degrees),
                )
            )

    schedule_blocks: list[ScheduleBlock] = []

    for slot_start, slot_end, plan in zip(
        time_grid[:-1],
        time_grid[1:],
        plans[:-1],
        strict=True,
    ):
        slot_start_utc = slot_start.astimezone(UTC)
        slot_end_utc = slot_end.astimezone(UTC)
        recommended_entries = tuple(entry for entry in plan.entries if entry.recommended)

        if not recommended_entries:
            continue

        selected_entry = max(
            recommended_entries,
            key=lambda entry: (
                entry.total_score,
                entry.altitude_degrees,
            ),
        )

        previous_block = schedule_blocks[-1] if schedule_blocks else None

        can_merge = (
            previous_block is not None
            and previous_block.object_key == selected_entry.object_key
            and previous_block.category == selected_entry.category
            and previous_block.end_utc == slot_start_utc
        )

        if can_merge and previous_block is not None:
            peak_is_new = selected_entry.total_score > previous_block.peak_score

            schedule_blocks[-1] = ScheduleBlock(
                object_key=previous_block.object_key,
                category=previous_block.category,
                start_local=previous_block.start_local,
                end_local=slot_end,
                peak_local=(slot_start if peak_is_new else previous_block.peak_local),
                start_utc=previous_block.start_utc,
                end_utc=slot_end_utc,
                duration_minutes=(
                    slot_end_utc - previous_block.start_utc
                ).total_seconds()
                / 60.0,
                peak_score=(
                    selected_entry.total_score if peak_is_new else previous_block.peak_score
                ),
                peak_altitude_degrees=(
                    selected_entry.altitude_degrees
                    if peak_is_new
                    else previous_block.peak_altitude_degrees
                ),
                peak_moon_separation_degrees=(
                    selected_entry.moon_separation_degrees
                    if peak_is_new
                    else (previous_block.peak_moon_separation_degrees)
                ),
                rating=(selected_entry.rating if peak_is_new else previous_block.rating),
            )
        else:
            schedule_blocks.append(
                ScheduleBlock(
                    object_key=selected_entry.object_key,
                    category=selected_entry.category,
                    start_local=slot_start,
                    end_local=slot_end,
                    peak_local=slot_start,
                    start_utc=slot_start_utc,
                    end_utc=slot_end_utc,
                    duration_minutes=(slot_end_utc - slot_start_utc).total_seconds() / 60.0,
                    peak_score=selected_entry.total_score,
                    peak_altitude_degrees=(selected_entry.altitude_degrees),
                    peak_moon_separation_degrees=(selected_entry.moon_separation_degrees),
                    rating=selected_entry.rating,
                )
            )

    scheduled_minutes = sum(block.duration_minutes for block in schedule_blocks)

    top_target_key = None

    if schedule_blocks:
        top_target_key = max(
            schedule_blocks,
            key=lambda block: block.peak_score,
        ).object_key

    evaluated_target_count = plans[0].total_target_count if plans else 0

    return ObservationScheduleResult(
        timeline_points=tuple(timeline_points),
        schedule_blocks=tuple(schedule_blocks),
        start_local_iso=_format_schedule_datetime(time_grid[0]),
        end_local_iso=_format_schedule_datetime(time_grid[-1]),
        sample_count=len(time_grid),
        evaluated_target_count=(evaluated_target_count),
        scheduled_minutes=scheduled_minutes,
        top_target_key=top_target_key,
    )
