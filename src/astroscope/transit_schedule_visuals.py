"""Plotly visualizations for ranked exoplanet transit schedules."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Final

import plotly.graph_objects as go
from astropy.time import Time

from astroscope.transit_ranking import RankedTransit
from astroscope.transit_schedule import TransitScheduleResult

MILLISECONDS_PER_DAY: Final[float] = 86_400_000.0


class TransitScheduleVisualError(ValueError):
    """Raised when schedule visualization inputs are invalid."""


def julian_date_to_utc_datetime(
    julian_date: float,
) -> datetime:
    """Convert one Julian date to a timezone-aware UTC datetime."""

    if not math.isfinite(julian_date):
        raise TransitScheduleVisualError("Julian date must be finite.")

    return Time(
        julian_date,
        format="jd",
        scale="utc",
    ).to_datetime(timezone=UTC)


def create_schedule_timeline_figure(
    result: TransitScheduleResult,
) -> go.Figure:
    """Create an observing-window timeline ordered by rank."""

    figure = go.Figure()

    if not result.ranked_transits:
        figure.add_annotation(
            text="No predicted transit events in this schedule.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figure.update_layout(
            title="Transit observation timeline",
            xaxis_title="UTC time",
            yaxis_title="Planet",
        )
        return figure

    for ranked in result.ranked_transits:
        event = ranked.candidate.event
        visibility = ranked.candidate.visibility

        observation_start = julian_date_to_utc_datetime(event.observation_start_jd)
        observation_duration_ms = (
            event.observation_end_jd - event.observation_start_jd
        ) * MILLISECONDS_PER_DAY

        transit_start = julian_date_to_utc_datetime(event.ingress_jd)
        transit_duration_ms = (event.egress_jd - event.ingress_jd) * MILLISECONDS_PER_DAY

        label = f"#{ranked.rank} {event.planet_name} (score {ranked.score.total_score:.1f})"

        figure.add_trace(
            go.Bar(
                name="Observation window",
                y=[label],
                x=[observation_duration_ms],
                base=[observation_start],
                orientation="h",
                customdata=[
                    [
                        ranked.score.total_score,
                        visibility.observable_sample_fraction,
                        visibility.midpoint_sample.target_altitude_degrees,
                    ]
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Start: %{base|%Y-%m-%d %H:%M UTC}<br>"
                    "Duration: %{x:.0f} ms<br>"
                    "Priority score: %{customdata[0]:.1f}<br>"
                    "Observable fraction: "
                    "%{customdata[1]:.0%}<br>"
                    "Midpoint altitude: "
                    "%{customdata[2]:.1f}°"
                    "<extra></extra>"
                ),
                legendgroup="observation-window",
                showlegend=ranked.rank == 1,
            )
        )

        figure.add_trace(
            go.Bar(
                name="Transit",
                y=[label],
                x=[transit_duration_ms],
                base=[transit_start],
                orientation="h",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Ingress: %{base|%Y-%m-%d %H:%M UTC}<br>"
                    "Transit duration: %{x:.0f} ms"
                    "<extra></extra>"
                ),
                legendgroup="transit",
                showlegend=ranked.rank == 1,
            )
        )

    figure.update_layout(
        title=(f"Ranked transit observation timeline at {result.site.name}"),
        xaxis_title="UTC time",
        yaxis_title="Ranked target",
        barmode="overlay",
        hovermode="closest",
        legend_title="Window type",
        margin={
            "l": 40,
            "r": 20,
            "t": 70,
            "b": 40,
        },
    )

    figure.update_yaxes(autorange="reversed")

    return figure


def create_transit_altitude_figure(
    ranked_transit: RankedTransit,
) -> go.Figure:
    """Create target, Sun, and Moon altitude curves."""

    samples = ranked_transit.candidate.visibility.samples

    figure = go.Figure()

    if not samples:
        figure.add_annotation(
            text="No visibility samples are available.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return figure

    times = [julian_date_to_utc_datetime(sample.julian_date) for sample in samples]

    figure.add_trace(
        go.Scatter(
            name="Target altitude",
            x=times,
            y=[sample.target_altitude_degrees for sample in samples],
            mode="lines+markers",
            hovertemplate=("%{x|%Y-%m-%d %H:%M UTC}<br>Target altitude: %{y:.1f}°<extra></extra>"),
        )
    )

    figure.add_trace(
        go.Scatter(
            name="Sun altitude",
            x=times,
            y=[sample.sun_altitude_degrees for sample in samples],
            mode="lines",
            hovertemplate=("%{x|%Y-%m-%d %H:%M UTC}<br>Sun altitude: %{y:.1f}°<extra></extra>"),
        )
    )

    figure.add_trace(
        go.Scatter(
            name="Moon altitude",
            x=times,
            y=[sample.moon_altitude_degrees for sample in samples],
            mode="lines",
            hovertemplate=("%{x|%Y-%m-%d %H:%M UTC}<br>Moon altitude: %{y:.1f}°<extra></extra>"),
        )
    )

    figure.add_hline(
        y=0.0,
        line_dash="dot",
        annotation_text="Horizon",
    )

    event = ranked_transit.candidate.event

    figure.add_vline(
        x=julian_date_to_utc_datetime(event.ingress_jd).timestamp() * 1_000.0,
        line_dash="dot",
        annotation_text="Ingress",
    )

    figure.add_vline(
        x=julian_date_to_utc_datetime(event.mid_transit_jd).timestamp() * 1_000.0,
        line_dash="dash",
        annotation_text="Mid-transit",
    )

    figure.add_vline(
        x=julian_date_to_utc_datetime(event.egress_jd).timestamp() * 1_000.0,
        line_dash="dot",
        annotation_text="Egress",
    )

    figure.update_layout(
        title=(f"{event.planet_name} altitude and sky conditions"),
        xaxis_title="UTC time",
        yaxis_title="Altitude (degrees)",
        hovermode="x unified",
        margin={
            "l": 40,
            "r": 20,
            "t": 70,
            "b": 40,
        },
    )

    figure.update_yaxes(range=[-90.0, 90.0])

    return figure


def create_transit_score_figure(
    ranked_transit: RankedTransit,
) -> go.Figure:
    """Create a component-score breakdown chart."""

    score = ranked_transit.score

    labels = [
        "Observable fraction",
        "Midpoint altitude",
        "Darkness",
        "Moon separation",
        "Transit depth",
        "Timing confidence",
        "Host brightness",
        "Full-window visibility",
    ]

    values = [
        score.observable_fraction_score * 100.0,
        score.midpoint_altitude_score * 100.0,
        score.darkness_fraction_score * 100.0,
        score.moon_separation_score * 100.0,
        score.transit_depth_score * 100.0,
        score.timing_confidence_score * 100.0,
        score.host_brightness_score * 100.0,
        score.full_window_visibility_score * 100.0,
    ]

    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            text=[f"{value:.1f}" for value in values],
            textposition="auto",
            hovertemplate=("%{y}<br>Component score: %{x:.1f}/100<extra></extra>"),
        )
    )

    figure.update_layout(
        title=(
            f"{ranked_transit.candidate.event.planet_name} "
            f"score breakdown "
            f"({score.total_score:.1f}/100)"
        ),
        xaxis_title="Normalized component score",
        yaxis_title="",
        margin={
            "l": 40,
            "r": 20,
            "t": 70,
            "b": 40,
        },
    )

    figure.update_xaxes(range=[0.0, 100.0])
    figure.update_yaxes(autorange="reversed")

    return figure
