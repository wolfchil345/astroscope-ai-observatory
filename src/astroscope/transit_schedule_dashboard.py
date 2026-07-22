"""Streamlit dashboard for ranked exoplanet transit schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Final

import streamlit as st
from astropy.time import Time

from astroscope.transit_schedule import (
    TransitScheduleRequest,
    TransitScheduleResult,
    TransitScheduleTarget,
    generate_transit_schedule,
)
from astroscope.transit_schedule_exports import (
    transit_schedule_to_csv,
    transit_schedule_to_ics,
    transit_schedule_to_json,
)
from astroscope.transit_schedule_visuals import (
    create_schedule_timeline_figure,
    create_transit_altitude_figure,
    create_transit_score_figure,
    julian_date_to_utc_datetime,
)
from astroscope.transit_scheduler import TransitEphemeris
from astroscope.transit_visibility import (
    ObserverSite,
    TransitTarget,
)

_RESULT_SESSION_KEY: Final[str] = "mission15_transit_schedule_result"
_DEFAULT_OSAKA_LATITUDE: Final[float] = 34.6937
_DEFAULT_OSAKA_LONGITUDE: Final[float] = 135.5023
_DEFAULT_OSAKA_ELEVATION: Final[float] = 15.0


@dataclass(frozen=True, slots=True)
class TransitDashboardTargetInput:
    """User-entered ephemeris and host-star information."""

    planet_name: str
    host_star_name: str
    right_ascension_degrees: float
    declination_degrees: float
    orbital_period_days: float
    reference_mid_transit_jd: float
    transit_duration_hours: float
    period_uncertainty_days: float
    reference_epoch_uncertainty_days: float
    transit_depth_ppm: float | None
    host_magnitude: float | None


@dataclass(frozen=True, slots=True)
class TransitDashboardExportBundle:
    """Downloadable representations of one transit schedule."""

    csv_data: str
    json_data: str
    calendar_data: str
    csv_filename: str
    json_filename: str
    calendar_filename: str


def utc_datetime_to_julian_date(
    value: datetime,
) -> float:
    """Convert a timezone-aware datetime to a UTC Julian date."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must include timezone information.")

    utc_value = value.astimezone(UTC)

    return float(
        Time(
            utc_value,
            scale="utc",
        ).jd
    )


def build_schedule_request(
    start_date: date,
    end_date: date,
    *,
    baseline_before_hours: float,
    baseline_after_hours: float,
    uncertainty_sigma_multiplier: float,
    visibility_sample_count: int,
    minimum_altitude_degrees: float,
    darkness_sun_altitude_degrees: float,
) -> TransitScheduleRequest:
    """Build a complete UTC schedule request from calendar dates."""

    if end_date < start_date:
        raise ValueError("End date must not be earlier than start date.")

    start_datetime = datetime.combine(
        start_date,
        time.min,
        tzinfo=UTC,
    )
    end_datetime = datetime.combine(
        end_date,
        time.max,
        tzinfo=UTC,
    )

    return TransitScheduleRequest(
        start_jd=utc_datetime_to_julian_date(start_datetime),
        end_jd=utc_datetime_to_julian_date(end_datetime),
        baseline_before_hours=baseline_before_hours,
        baseline_after_hours=baseline_after_hours,
        uncertainty_sigma_multiplier=(uncertainty_sigma_multiplier),
        visibility_sample_count=visibility_sample_count,
        minimum_altitude_degrees=(minimum_altitude_degrees),
        darkness_sun_altitude_degrees=(darkness_sun_altitude_degrees),
    )


def build_schedule_target(
    target_input: TransitDashboardTargetInput,
) -> TransitScheduleTarget:
    """Convert dashboard target input into schedule-domain objects."""

    ephemeris = TransitEphemeris(
        planet_name=target_input.planet_name,
        orbital_period_days=(target_input.orbital_period_days),
        reference_mid_transit_jd=(target_input.reference_mid_transit_jd),
        transit_duration_hours=(target_input.transit_duration_hours),
        period_uncertainty_days=(target_input.period_uncertainty_days),
        reference_epoch_uncertainty_days=(target_input.reference_epoch_uncertainty_days),
    )

    target = TransitTarget(
        name=target_input.host_star_name,
        right_ascension_degrees=(target_input.right_ascension_degrees),
        declination_degrees=(target_input.declination_degrees),
    )

    return TransitScheduleTarget(
        ephemeris=ephemeris,
        target=target,
        transit_depth_ppm=(target_input.transit_depth_ppm),
        host_magnitude=target_input.host_magnitude,
    )


def ranked_schedule_rows(
    result: TransitScheduleResult,
) -> tuple[dict[str, object], ...]:
    """Create display-table rows from a ranked schedule."""

    rows: list[dict[str, object]] = []

    for ranked in result.ranked_transits:
        event = ranked.candidate.event
        visibility = ranked.candidate.visibility

        midpoint = julian_date_to_utc_datetime(event.mid_transit_jd)

        rows.append(
            {
                "Rank": ranked.rank,
                "Planet": event.planet_name,
                "Score": round(
                    ranked.score.total_score,
                    1,
                ),
                "Mid-transit UTC": midpoint.strftime("%Y-%m-%d %H:%M"),
                "Observable fraction": round(
                    visibility.observable_sample_fraction,
                    3,
                ),
                "Full window visible": (visibility.full_observation_window_visible),
                "Midpoint altitude (deg)": round(
                    visibility.midpoint_sample.target_altitude_degrees,
                    1,
                ),
                "Moon separation (deg)": round(
                    visibility.minimum_moon_separation_degrees,
                    1,
                ),
                "Timing uncertainty (h)": round(
                    event.timing_uncertainty_hours,
                    3,
                ),
            }
        )

    return tuple(rows)


def _safe_filename_component(
    value: str,
) -> str:
    """Convert text into a compact filename component."""

    normalized = "".join(
        character.casefold() if character.isalnum() else "-" for character in value.strip()
    )

    compact = "-".join(component for component in normalized.split("-") if component)

    return compact or "observatory"


def build_dashboard_exports(
    result: TransitScheduleResult,
) -> TransitDashboardExportBundle:
    """Build downloadable schedule data and deterministic filenames."""

    site_component = _safe_filename_component(result.site.name)

    start_component = julian_date_to_utc_datetime(result.request.start_jd).strftime("%Y%m%d")

    end_component = julian_date_to_utc_datetime(result.request.end_jd).strftime("%Y%m%d")

    filename_stem = f"astroscope-transits-{site_component}-{start_component}-{end_component}"

    return TransitDashboardExportBundle(
        csv_data=transit_schedule_to_csv(result),
        json_data=transit_schedule_to_json(result),
        calendar_data=transit_schedule_to_ics(result),
        csv_filename=f"{filename_stem}.csv",
        json_filename=f"{filename_stem}.json",
        calendar_filename=f"{filename_stem}.ics",
    )


def _render_target_inputs(
    target_count: int,
    default_reference_jd: float,
) -> tuple[TransitDashboardTargetInput, ...]:
    """Render manual target widgets inside the schedule form."""

    target_inputs: list[TransitDashboardTargetInput] = []

    for index in range(target_count):
        target_number = index + 1

        with st.expander(
            f"Target {target_number}",
            expanded=target_number == 1,
        ):
            name_columns = st.columns(2)

            planet_name = name_columns[0].text_input(
                "Planet name",
                value=f"Example-{target_number} b",
                key=f"transit_planet_name_{index}",
            )
            host_star_name = name_columns[1].text_input(
                "Host-star name",
                value=f"Example Star {target_number}",
                key=f"transit_host_name_{index}",
            )

            coordinate_columns = st.columns(2)

            right_ascension_degrees = coordinate_columns[0].number_input(
                "Right ascension (degrees)",
                min_value=0.0,
                max_value=359.999999,
                value=120.0 + index * 10.0,
                step=0.1,
                format="%.6f",
                key=f"transit_ra_{index}",
            )
            declination_degrees = coordinate_columns[1].number_input(
                "Declination (degrees)",
                min_value=-90.0,
                max_value=90.0,
                value=20.0,
                step=0.1,
                format="%.6f",
                key=f"transit_dec_{index}",
            )

            ephemeris_columns = st.columns(3)

            orbital_period_days = ephemeris_columns[0].number_input(
                "Orbital period (days)",
                min_value=0.000001,
                value=3.0 + index,
                step=0.1,
                format="%.8f",
                key=f"transit_period_{index}",
            )
            reference_mid_transit_jd = ephemeris_columns[1].number_input(
                "Reference midpoint (JD)",
                min_value=0.0,
                value=(default_reference_jd + index * 0.25),
                step=0.01,
                format="%.8f",
                key=f"transit_epoch_{index}",
            )
            transit_duration_hours = ephemeris_columns[2].number_input(
                "Transit duration (hours)",
                min_value=0.000001,
                value=2.5,
                step=0.1,
                format="%.4f",
                key=f"transit_duration_{index}",
            )

            uncertainty_columns = st.columns(2)

            period_uncertainty_days = uncertainty_columns[0].number_input(
                "Period uncertainty (days)",
                min_value=0.0,
                value=0.0001,
                step=0.0001,
                format="%.8f",
                key=f"transit_period_uncertainty_{index}",
            )
            reference_epoch_uncertainty_days = uncertainty_columns[1].number_input(
                "Epoch uncertainty (days)",
                min_value=0.0,
                value=0.001,
                step=0.0001,
                format="%.8f",
                key=f"transit_epoch_uncertainty_{index}",
            )

            ranking_columns = st.columns(2)

            transit_depth_ppm = ranking_columns[0].number_input(
                "Transit depth (ppm)",
                min_value=0.0,
                value=2_000.0,
                step=100.0,
                format="%.1f",
                key=f"transit_depth_{index}",
            )
            host_magnitude = ranking_columns[1].number_input(
                "Host apparent magnitude",
                min_value=-30.0,
                max_value=30.0,
                value=10.0,
                step=0.1,
                format="%.2f",
                key=f"transit_magnitude_{index}",
            )

        target_inputs.append(
            TransitDashboardTargetInput(
                planet_name=planet_name,
                host_star_name=host_star_name,
                right_ascension_degrees=float(right_ascension_degrees),
                declination_degrees=float(declination_degrees),
                orbital_period_days=float(orbital_period_days),
                reference_mid_transit_jd=float(reference_mid_transit_jd),
                transit_duration_hours=float(transit_duration_hours),
                period_uncertainty_days=float(period_uncertainty_days),
                reference_epoch_uncertainty_days=float(reference_epoch_uncertainty_days),
                transit_depth_ppm=float(transit_depth_ppm),
                host_magnitude=float(host_magnitude),
            )
        )

    return tuple(target_inputs)


def _render_schedule_downloads(
    result: TransitScheduleResult,
) -> None:
    """Render CSV, JSON, and iCalendar download controls."""

    exports = build_dashboard_exports(result)

    st.subheader("Download schedule")
    st.caption(
        "Export the ranked observation plan for analysis, automation, or calendar scheduling."
    )

    download_columns = st.columns(3)

    download_columns[0].download_button(
        label="Download CSV",
        data=exports.csv_data,
        file_name=exports.csv_filename,
        mime="text/csv",
        key="transit_schedule_download_csv",
    )

    download_columns[1].download_button(
        label="Download JSON",
        data=exports.json_data,
        file_name=exports.json_filename,
        mime="application/json",
        key="transit_schedule_download_json",
    )

    download_columns[2].download_button(
        label="Download calendar",
        data=exports.calendar_data,
        file_name=exports.calendar_filename,
        mime="text/calendar",
        key="transit_schedule_download_ics",
    )


def _render_schedule_result(
    result: TransitScheduleResult,
) -> None:
    """Render schedule metrics, charts, table, and event inspector."""

    st.subheader("Schedule results")

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Predicted events",
        result.predicted_event_count,
    )
    metric_columns[1].metric(
        "Observable events",
        result.observable_transit_count,
    )
    metric_columns[2].metric(
        "Fully visible",
        result.fully_visible_count,
    )
    metric_columns[3].metric(
        "Targets searched",
        result.target_count,
    )

    if result.targets_without_events:
        st.info(
            "No transit midpoint occurred in the selected range for: "
            + ", ".join(result.targets_without_events)
        )

    if not result.ranked_transits:
        st.warning("No transit events were predicted in the selected date range.")
        return

    st.plotly_chart(
        create_schedule_timeline_figure(result),
        use_container_width=True,
        key="transit_schedule_timeline",
    )

    rows = ranked_schedule_rows(result)

    st.dataframe(
        list(rows),
        use_container_width=True,
        hide_index=True,
    )

    _render_schedule_downloads(result)

    selected_index = st.selectbox(
        "Inspect a ranked event",
        options=list(range(len(result.ranked_transits))),
        format_func=lambda index: (
            f"#{result.ranked_transits[index].rank} "
            f"{result.ranked_transits[index].candidate.event.planet_name} "
            f"({result.ranked_transits[index].score.total_score:.1f}/100)"
        ),
        key="transit_schedule_selected_event",
    )

    selected = result.ranked_transits[int(selected_index)]
    event = selected.candidate.event
    visibility = selected.candidate.visibility

    detail_columns = st.columns(4)

    detail_columns[0].metric(
        "Priority score",
        f"{selected.score.total_score:.1f}/100",
    )
    detail_columns[1].metric(
        "Midpoint altitude",
        (f"{visibility.midpoint_sample.target_altitude_degrees:.1f}°"),
    )
    detail_columns[2].metric(
        "Observable fraction",
        f"{visibility.observable_sample_fraction:.0%}",
    )
    detail_columns[3].metric(
        "Timing uncertainty",
        f"{event.timing_uncertainty_hours:.3f} h",
    )

    midpoint_utc = julian_date_to_utc_datetime(event.mid_transit_jd)
    ingress_utc = julian_date_to_utc_datetime(event.ingress_jd)
    egress_utc = julian_date_to_utc_datetime(event.egress_jd)

    st.caption(
        "Ingress: "
        f"{ingress_utc:%Y-%m-%d %H:%M UTC} | "
        "Midpoint: "
        f"{midpoint_utc:%Y-%m-%d %H:%M UTC} | "
        "Egress: "
        f"{egress_utc:%Y-%m-%d %H:%M UTC}"
    )

    chart_columns = st.columns(2)

    with chart_columns[0]:
        st.plotly_chart(
            create_transit_altitude_figure(selected),
            use_container_width=True,
            key="transit_altitude_chart",
        )

    with chart_columns[1]:
        st.plotly_chart(
            create_transit_score_figure(selected),
            use_container_width=True,
            key="transit_score_chart",
        )

    if selected.score.missing_fields:
        st.info(
            "Neutral scores were used for missing fields: "
            + ", ".join(selected.score.missing_fields)
        )


def render_transit_schedule_dashboard() -> None:
    """Render the complete manual transit scheduler dashboard."""

    st.header("Exoplanet Transit Observation Scheduler")
    st.write(
        "Predict and rank transit observing windows using ephemerides, "
        "observer geometry, darkness, Moon separation, timing confidence, "
        "transit depth, and host-star brightness."
    )
    st.caption("All schedule dates and displayed event times use UTC.")

    today = datetime.now(UTC).date()

    target_count = int(
        st.number_input(
            "Number of targets",
            min_value=1,
            max_value=5,
            value=1,
            step=1,
            key="transit_schedule_target_count",
        )
    )

    with st.form(
        "transit_schedule_form",
    ):
        st.subheader("Observer site")

        site_name = st.text_input(
            "Site name",
            value="Osaka",
        )

        site_columns = st.columns(3)

        latitude_degrees = site_columns[0].number_input(
            "Latitude (degrees)",
            min_value=-90.0,
            max_value=90.0,
            value=_DEFAULT_OSAKA_LATITUDE,
            step=0.0001,
            format="%.6f",
        )
        longitude_degrees = site_columns[1].number_input(
            "Longitude (degrees)",
            min_value=-180.0,
            max_value=180.0,
            value=_DEFAULT_OSAKA_LONGITUDE,
            step=0.0001,
            format="%.6f",
        )
        elevation_meters = site_columns[2].number_input(
            "Elevation (meters)",
            value=_DEFAULT_OSAKA_ELEVATION,
            step=1.0,
            format="%.1f",
        )

        st.subheader("Schedule range")

        range_columns = st.columns(2)

        start_date = range_columns[0].date_input(
            "Start date",
            value=today,
        )
        end_date = range_columns[1].date_input(
            "End date",
            value=today + timedelta(days=7),
        )

        st.subheader("Observation settings")

        baseline_columns = st.columns(3)

        baseline_before_hours = baseline_columns[0].number_input(
            "Baseline before transit (hours)",
            min_value=0.0,
            value=1.0,
            step=0.25,
            format="%.2f",
        )
        baseline_after_hours = baseline_columns[1].number_input(
            "Baseline after transit (hours)",
            min_value=0.0,
            value=1.0,
            step=0.25,
            format="%.2f",
        )
        uncertainty_sigma_multiplier = baseline_columns[2].number_input(
            "Timing uncertainty multiplier",
            min_value=0.0,
            value=1.0,
            step=0.5,
            format="%.2f",
        )

        visibility_columns = st.columns(3)

        minimum_altitude_degrees = visibility_columns[0].number_input(
            "Minimum altitude (degrees)",
            min_value=-90.0,
            max_value=90.0,
            value=20.0,
            step=1.0,
            format="%.1f",
        )
        darkness_sun_altitude_degrees = visibility_columns[1].number_input(
            "Maximum Sun altitude (degrees)",
            min_value=-90.0,
            max_value=90.0,
            value=-18.0,
            step=1.0,
            format="%.1f",
        )
        visibility_sample_count = int(
            visibility_columns[2].number_input(
                "Visibility samples",
                min_value=3,
                max_value=501,
                value=25,
                step=2,
            )
        )

        st.subheader("Transit targets")

        default_reference_jd = utc_datetime_to_julian_date(
            datetime.combine(
                today,
                time.min,
                tzinfo=UTC,
            )
        )

        target_inputs = _render_target_inputs(
            target_count,
            default_reference_jd,
        )

        submitted = st.form_submit_button(
            "Generate ranked schedule",
            type="primary",
        )

    if submitted:
        try:
            site = ObserverSite(
                name=site_name,
                latitude_degrees=float(latitude_degrees),
                longitude_degrees=float(longitude_degrees),
                elevation_meters=float(elevation_meters),
            )

            request = build_schedule_request(
                start_date,
                end_date,
                baseline_before_hours=float(baseline_before_hours),
                baseline_after_hours=float(baseline_after_hours),
                uncertainty_sigma_multiplier=float(uncertainty_sigma_multiplier),
                visibility_sample_count=(visibility_sample_count),
                minimum_altitude_degrees=float(minimum_altitude_degrees),
                darkness_sun_altitude_degrees=float(darkness_sun_altitude_degrees),
            )

            targets = tuple(build_schedule_target(target_input) for target_input in target_inputs)

            with st.spinner("Predicting and ranking transit events..."):
                result = generate_transit_schedule(
                    targets,
                    site,
                    request,
                )

            st.session_state[_RESULT_SESSION_KEY] = result

        except ValueError as error:
            st.error(f"Unable to generate schedule: {error}")
            return

    stored_result = st.session_state.get(_RESULT_SESSION_KEY)

    if isinstance(
        stored_result,
        TransitScheduleResult,
    ):
        _render_schedule_result(stored_result)
