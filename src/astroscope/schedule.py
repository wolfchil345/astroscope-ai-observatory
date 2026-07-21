"""Night timeline and observation-schedule generation."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import plotly.graph_objects as go

from astroscope.observer import get_timezone
from astroscope.planner import (
    PlannerCategory,
    PlannerRating,
    calculate_observation_plan,
)
from astroscope.visibility import VisibilityStatus


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
class ScheduleChartLabels:
    """Translated labels for the score timeline."""

    title: str
    time_axis: str
    score_axis: str
    altitude: str
    moon_separation: str
    rating: str
    recommended: str
    yes: str
    no: str


def create_local_time_grid(
    local_date: date,
    start_time: time,
    end_time: time,
    timezone_name: str,
    interval_minutes: int,
) -> tuple[datetime, ...]:
    """Create a timezone-aware grid that may cross midnight."""

    if not 15 <= interval_minutes <= 180:
        raise ValueError("Sampling interval must be between 15 and 180 minutes.")

    if start_time == end_time:
        raise ValueError("Schedule start and end times must be different.")

    timezone_info = get_timezone(timezone_name)

    start_local = datetime.combine(
        local_date,
        start_time.replace(tzinfo=None),
        tzinfo=timezone_info,
    )

    end_date = local_date if end_time > start_time else local_date + timedelta(days=1)

    end_local = datetime.combine(
        end_date,
        end_time.replace(tzinfo=None),
        tzinfo=timezone_info,
    )

    start_utc = start_local.astimezone(UTC)
    end_utc = end_local.astimezone(UTC)
    duration = end_utc - start_utc

    if duration <= timedelta(0):
        raise ValueError("Schedule duration must be greater than zero.")

    if duration > timedelta(hours=18):
        raise ValueError("Schedule duration cannot exceed 18 hours.")

    interval = timedelta(minutes=interval_minutes)
    grid: list[datetime] = []
    current_utc = start_utc

    while current_utc < end_utc:
        grid.append(current_utc.astimezone(timezone_info))
        current_utc += interval

    grid.append(end_utc.astimezone(timezone_info))

    return tuple(grid)


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
    """Evaluate and schedule targets throughout an observing night."""

    time_grid = create_local_time_grid(
        local_date=local_date,
        start_time=start_time,
        end_time=end_time,
        timezone_name=timezone_name,
        interval_minutes=interval_minutes,
    )

    if not (include_catalog_targets or include_solar_system_targets):
        return ObservationScheduleResult(
            timeline_points=(),
            schedule_blocks=(),
            start_local_iso=time_grid[0].isoformat(timespec="minutes"),
            end_local_iso=time_grid[-1].isoformat(timespec="minutes"),
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
                    local_datetime_iso=(local_datetime.isoformat(timespec="minutes")),
                    utc_datetime_iso=(plan.utc_datetime_iso),
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
            and previous_block.end_local == slot_start
        )

        if can_merge and previous_block is not None:
            peak_is_new = selected_entry.total_score > previous_block.peak_score

            schedule_blocks[-1] = ScheduleBlock(
                object_key=previous_block.object_key,
                category=previous_block.category,
                start_local=previous_block.start_local,
                end_local=slot_end,
                peak_local=(slot_start if peak_is_new else previous_block.peak_local),
                duration_minutes=(slot_end - previous_block.start_local).total_seconds() / 60.0,
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
                    duration_minutes=(slot_end - slot_start).total_seconds() / 60.0,
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
        start_local_iso=time_grid[0].isoformat(timespec="minutes"),
        end_local_iso=time_grid[-1].isoformat(timespec="minutes"),
        sample_count=len(time_grid),
        evaluated_target_count=(evaluated_target_count),
        scheduled_minutes=scheduled_minutes,
        top_target_key=top_target_key,
    )


def create_schedule_figure(
    points: tuple[TimelinePoint, ...],
    display_names: Mapping[str, str],
    rating_names: Mapping[str, str],
    labels: ScheduleChartLabels,
) -> go.Figure:
    """Create an interactive score timeline."""

    figure = go.Figure()

    object_keys = sorted(
        {point.object_key for point in points},
        key=lambda key: display_names.get(key, key),
    )

    for object_key in object_keys:
        object_points = sorted(
            (point for point in points if point.object_key == object_key),
            key=lambda point: point.local_datetime_iso,
        )

        figure.add_trace(
            go.Scatter(
                x=[point.local_datetime_iso for point in object_points],
                y=[point.total_score for point in object_points],
                mode="lines+markers",
                name=display_names.get(
                    object_key,
                    object_key,
                ),
                customdata=[
                    [
                        point.altitude_degrees,
                        point.moon_separation_degrees,
                        rating_names.get(
                            point.rating,
                            point.rating,
                        ),
                        (labels.yes if point.recommended else labels.no),
                    ]
                    for point in object_points
                ],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{x}<br>"
                    f"{labels.score_axis}: "
                    "%{y:.1f}<br>"
                    f"{labels.altitude}: "
                    "%{customdata[0]:.2f}°<br>"
                    f"{labels.moon_separation}: "
                    "%{customdata[1]:.2f}°<br>"
                    f"{labels.rating}: "
                    "%{customdata[2]}<br>"
                    f"{labels.recommended}: "
                    "%{customdata[3]}"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        title=labels.title,
        height=620,
        hovermode="x unified",
        xaxis={
            "title": labels.time_axis,
            "type": "date",
        },
        yaxis={
            "title": labels.score_axis,
            "range": [0, 100],
        },
        margin={
            "l": 40,
            "r": 40,
            "t": 70,
            "b": 40,
        },
    )

    return figure
