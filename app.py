"""Main Streamlit entry point for AstroScope AI."""

import datetime as dt
from datetime import datetime, time
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st

from astroscope.coordinates import (
    CELESTIAL_PRESETS,
    calculate_coordinate_details,
)
from astroscope.exoplanet_dashboard import render_exoplanet_dashboard
from astroscope.gaia_dashboard import render_gaia_dashboard
from astroscope.i18n import SUPPORTED_LANGUAGES, translate
from astroscope.imaging import (
    CAMERA_PRESETS,
    IMAGING_TARGET_PRESETS,
    CameraSensorSpec,
    calculate_astrophotography_setup,
    calculate_target_framing,
    compare_camera_sensors,
)
from astroscope.imaging_visuals import (
    ImagingFrameLabels,
    create_imaging_frame_figure,
)
from astroscope.observation_log import (
    EquipmentSnapshot,
    ObservationLogError,
    ObservationSession,
    TargetObservation,
    calculate_session_summary,
    session_from_json,
    session_observations_to_csv,
    session_to_json,
)
from astroscope.observation_report import (
    ObservationReportLabels,
    create_markdown_report,
)
from astroscope.observer import (
    OBSERVER_PRESETS,
    calculate_astronomical_time,
)
from astroscope.observer import (
    get_timezone as get_observation_log_timezone,
)
from astroscope.planner import calculate_observation_plan
from astroscope.schedule import (
    ScheduleChartLabels,
    calculate_observation_schedule,
    create_schedule_figure,
)
from astroscope.sky_map import (
    SkyMapLabels,
    calculate_sky_map_points,
    create_sky_map_figure,
)
from astroscope.solar_system import (
    SOLAR_SYSTEM_BODIES,
    calculate_solar_system_body,
)
from astroscope.telescope import (
    EYEPIECE_PRESETS,
    TELESCOPE_PRESETS,
    EyepieceSpec,
    TelescopeSpec,
    calculate_optical_simulation,
    compare_eyepieces,
)
from astroscope.telescope_visuals import (
    ANGULAR_SIZE_PRESETS,
    FieldOfViewLabels,
    classify_target_fit,
    create_field_of_view_figure,
)
from astroscope.transit_schedule_dashboard import render_transit_schedule_dashboard
from astroscope.visibility import calculate_horizontal_coordinates
from astroscope.weather import (
    WeatherServiceError,
    fetch_observing_weather,
)
from astroscope.weather_charts import (
    WeatherChartLabels,
    create_weather_conditions_figure,
    create_weather_score_figure,
)

TIMEZONE_OPTIONS = [
    "Asia/Tokyo",
    "Asia/Bangkok",
    "Asia/Seoul",
    "UTC",
]

st.set_page_config(
    page_title="AstroScope AI Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

language_name = st.sidebar.selectbox(
    "Language / 言語 / 언어 / ภาษา",
    options=list(SUPPORTED_LANGUAGES),
)

language = SUPPORTED_LANGUAGES[language_name]

st.title(f"🔭 {translate('app_title', language)}")
st.subheader(translate("app_subtitle", language))

st.success(translate("foundation_message", language))
st.write(translate("welcome", language))

st.divider()

st.header(f"🌍 {translate('observer_section', language)}")
st.info(translate("observer_explanation", language))

observer_preset_key = st.selectbox(
    translate("observer_preset", language),
    options=list(OBSERVER_PRESETS),
    format_func=lambda key: translate(
        f"preset_{key}",
        language,
    ),
)

observer_preset = OBSERVER_PRESETS[observer_preset_key]

location_column, time_column = st.columns(2)

with location_column:
    latitude = st.number_input(
        translate("latitude", language),
        min_value=-90.0,
        max_value=90.0,
        value=float(observer_preset.latitude_deg),
        step=0.0001,
        format="%.4f",
        key=f"latitude_{observer_preset_key}",
    )

    longitude = st.number_input(
        translate("longitude", language),
        min_value=-180.0,
        max_value=180.0,
        value=float(observer_preset.longitude_deg),
        step=0.0001,
        format="%.4f",
        help=translate("coordinate_help", language),
        key=f"longitude_{observer_preset_key}",
    )

    elevation = st.number_input(
        translate("elevation", language),
        min_value=-500.0,
        max_value=10_000.0,
        value=float(observer_preset.elevation_m),
        step=1.0,
        format="%.1f",
        key=f"elevation_{observer_preset_key}",
    )

with time_column:
    timezone_index = TIMEZONE_OPTIONS.index(observer_preset.timezone_name)

    timezone_name = st.selectbox(
        translate("timezone", language),
        options=TIMEZONE_OPTIONS,
        index=timezone_index,
        key=f"timezone_{observer_preset_key}",
    )

    default_date = datetime.now(ZoneInfo(observer_preset.timezone_name)).date()

    observation_date = st.date_input(
        translate("observation_date", language),
        value=default_date,
    )

    observation_time = st.time_input(
        translate("observation_time", language),
        value=time(21, 0),
    )

calculate_time_button = st.button(
    translate("calculate_time", language),
    type="primary",
    use_container_width=True,
)

if calculate_time_button:
    try:
        time_result = calculate_astronomical_time(
            latitude_deg=float(latitude),
            longitude_deg=float(longitude),
            elevation_m=float(elevation),
            timezone_name=timezone_name,
            local_date=observation_date,
            local_time=observation_time,
        )
    except ValueError as error:
        st.error(f"{translate('calculation_error', language)}: {error}")
    else:
        st.subheader(translate("results", language))

        time_first_row = st.columns(2)

        time_first_row[0].metric(
            translate("local_datetime", language),
            time_result.local_datetime_iso,
        )

        time_first_row[1].metric(
            translate("utc_datetime", language),
            time_result.utc_datetime_iso,
        )

        time_second_row = st.columns(3)

        time_second_row[0].metric(
            translate("julian_date", language),
            f"{time_result.julian_date:.5f}",
        )

        time_second_row[1].metric(
            translate("modified_julian_date", language),
            f"{time_result.modified_julian_date:.5f}",
        )

        time_second_row[2].metric(
            translate("local_sidereal_time", language),
            time_result.local_sidereal_time_hms,
        )

        st.caption(translate("result_note", language))

st.divider()

st.header(f"🌌 {translate('coordinate_section', language)}")
st.info(translate("coordinate_explanation", language))

celestial_preset_key = st.selectbox(
    translate("celestial_object", language),
    options=list(CELESTIAL_PRESETS),
    format_func=lambda key: translate(
        f"object_{key}",
        language,
    ),
)

celestial_preset = CELESTIAL_PRESETS[celestial_preset_key]

coordinate_input_columns = st.columns(2)

with coordinate_input_columns[0]:
    right_ascension = st.text_input(
        translate("right_ascension_input", language),
        value=celestial_preset.right_ascension,
        help=translate("ra_help", language),
        key=f"right_ascension_{celestial_preset_key}",
    )

with coordinate_input_columns[1]:
    declination = st.text_input(
        translate("declination_input", language),
        value=celestial_preset.declination,
        help=translate("dec_help", language),
        key=f"declination_{celestial_preset_key}",
    )

convert_button = st.button(
    translate("convert_coordinates", language),
    type="primary",
    use_container_width=True,
)

if convert_button:
    try:
        coordinate_result = calculate_coordinate_details(
            right_ascension=right_ascension,
            declination=declination,
        )
    except ValueError as error:
        st.error(f"{translate('coordinate_error', language)}: {error}")
    else:
        st.subheader(translate("coordinate_results", language))

        icrs_first_row = st.columns(4)

        icrs_first_row[0].metric(
            translate("right_ascension_hms", language),
            coordinate_result.right_ascension_hms,
        )

        icrs_first_row[1].metric(
            translate("right_ascension_degrees", language),
            f"{coordinate_result.right_ascension_degrees:.6f}°",
        )

        icrs_first_row[2].metric(
            translate("declination_dms", language),
            coordinate_result.declination_dms,
        )

        icrs_first_row[3].metric(
            translate("declination_degrees", language),
            f"{coordinate_result.declination_degrees:.6f}°",
        )

        galactic_columns = st.columns(2)

        galactic_columns[0].metric(
            translate("galactic_longitude", language),
            f"{coordinate_result.galactic_longitude_degrees:.6f}°",
        )

        galactic_columns[1].metric(
            translate("galactic_latitude", language),
            f"{coordinate_result.galactic_latitude_degrees:.6f}°",
        )

        st.markdown(f"#### {translate('cartesian_direction', language)}")

        st.code(
            (
                f"x = {coordinate_result.cartesian_x:.6f}\n"
                f"y = {coordinate_result.cartesian_y:.6f}\n"
                f"z = {coordinate_result.cartesian_z:.6f}"
            ),
            language="text",
        )

        st.caption(translate("coordinate_note", language))


st.divider()

st.header(f"🔭 {translate('visibility_section', language)}")
st.info(translate("visibility_explanation", language))

minimum_altitude = st.slider(
    translate("minimum_altitude", language),
    min_value=0.0,
    max_value=90.0,
    value=20.0,
    step=1.0,
    help=translate("minimum_altitude_help", language),
)

calculate_visibility_button = st.button(
    translate("calculate_visibility", language),
    type="primary",
    use_container_width=True,
    key="calculate_visibility_button",
)

if calculate_visibility_button:
    try:
        visibility_result = calculate_horizontal_coordinates(
            right_ascension=right_ascension,
            declination=declination,
            latitude_deg=float(latitude),
            longitude_deg=float(longitude),
            elevation_m=float(elevation),
            timezone_name=timezone_name,
            local_date=observation_date,
            local_time=observation_time,
            minimum_altitude_degrees=float(minimum_altitude),
        )
    except ValueError as error:
        st.error(f"{translate('visibility_error', language)}: {error}")
    else:
        st.subheader(translate("horizontal_results", language))

        horizontal_first_row = st.columns(4)

        horizontal_first_row[0].metric(
            translate("altitude", language),
            f"{visibility_result.altitude_degrees:.3f}°",
        )

        horizontal_first_row[1].metric(
            translate("azimuth", language),
            f"{visibility_result.azimuth_degrees:.3f}°",
        )

        horizontal_first_row[2].metric(
            translate("zenith_distance", language),
            f"{visibility_result.zenith_distance_degrees:.3f}°",
        )

        airmass_text = (
            f"{visibility_result.airmass:.3f}"
            if visibility_result.airmass is not None
            else translate("not_available", language)
        )

        horizontal_first_row[3].metric(
            translate("airmass", language),
            airmass_text,
        )

        horizontal_second_row = st.columns(2)

        direction_key = f"direction_{visibility_result.cardinal_direction}"

        horizontal_second_row[0].metric(
            translate("cardinal_direction", language),
            translate(direction_key, language),
        )

        above_horizon_text = translate(
            ("value_yes" if visibility_result.is_above_horizon else "value_no"),
            language,
        )

        horizontal_second_row[1].metric(
            translate("above_horizon", language),
            above_horizon_text,
        )

        status_text = translate(
            f"status_{visibility_result.status}",
            language,
        )

        st.markdown(f"#### {translate('observation_status', language)}")

        if visibility_result.status == "observable":
            st.success(status_text)
        elif visibility_result.status == "low_altitude":
            st.warning(status_text)
        else:
            st.error(status_text)

        st.caption(translate("visibility_note", language))


st.divider()

st.divider()

st.header(f"🪐 {translate('solar_system_section', language)}")
st.info(translate("solar_system_explanation", language))

solar_system_body = st.selectbox(
    translate("solar_system_body", language),
    options=list(SOLAR_SYSTEM_BODIES),
    format_func=lambda body: translate(
        f"body_{body}",
        language,
    ),
)

calculate_solar_system_button = st.button(
    translate("calculate_solar_system", language),
    type="primary",
    use_container_width=True,
    key="calculate_solar_system_button",
)

if calculate_solar_system_button:
    try:
        solar_system_result = calculate_solar_system_body(
            body=solar_system_body,
            latitude_deg=float(latitude),
            longitude_deg=float(longitude),
            elevation_m=float(elevation),
            timezone_name=timezone_name,
            local_date=observation_date,
            local_time=observation_time,
            minimum_altitude_degrees=float(minimum_altitude),
        )
    except ValueError as error:
        st.error(f"{translate('solar_system_error', language)}: {error}")
    else:
        st.subheader(translate("solar_system_results", language))

        solar_coordinate_row = st.columns(4)

        solar_coordinate_row[0].metric(
            translate("apparent_ra", language),
            solar_system_result.right_ascension_hms,
        )

        solar_coordinate_row[1].metric(
            translate("apparent_dec", language),
            solar_system_result.declination_dms,
        )

        solar_coordinate_row[2].metric(
            translate("distance_au", language),
            f"{solar_system_result.distance_au:.6f}",
        )

        solar_coordinate_row[3].metric(
            translate("distance_km", language),
            f"{solar_system_result.distance_km:,.0f}",
        )

        solar_local_row = st.columns(4)

        solar_local_row[0].metric(
            translate("altitude", language),
            f"{solar_system_result.altitude_degrees:.3f}°",
        )

        solar_local_row[1].metric(
            translate("azimuth", language),
            f"{solar_system_result.azimuth_degrees:.3f}°",
        )

        solar_direction_key = f"direction_{solar_system_result.cardinal_direction}"

        solar_local_row[2].metric(
            translate("cardinal_direction", language),
            translate(solar_direction_key, language),
        )

        solar_above_horizon = translate(
            ("value_yes" if solar_system_result.is_above_horizon else "value_no"),
            language,
        )

        solar_local_row[3].metric(
            translate("above_horizon", language),
            solar_above_horizon,
        )

        solar_separation_row = st.columns(3)

        solar_separation_row[0].metric(
            translate("solar_elongation", language),
            f"{solar_system_result.solar_elongation_degrees:.3f}°",
        )

        solar_separation_row[1].metric(
            translate("moon_separation", language),
            f"{solar_system_result.moon_separation_degrees:.3f}°",
        )

        moon_illumination_percent = solar_system_result.moon_illumination_fraction * 100.0

        solar_separation_row[2].metric(
            translate("moon_illumination", language),
            f"{moon_illumination_percent:.1f}%",
        )

        solar_status_text = translate(
            f"status_{solar_system_result.status}",
            language,
        )

        st.markdown(f"#### {translate('observation_status', language)}")

        if solar_system_result.status == "observable":
            st.success(solar_status_text)
        elif solar_system_result.status == "low_altitude":
            st.warning(solar_status_text)
        else:
            st.error(solar_status_text)

        st.write(
            f"**{translate('ephemeris', language)}:** {translate('builtin_ephemeris', language)}"
        )

        st.caption(translate("solar_system_note", language))


st.divider()

st.header(f"🌌 {translate('sky_map_section', language)}")
st.info(translate("sky_map_explanation", language))

sky_map_control_columns = st.columns(2)

with sky_map_control_columns[0]:
    include_catalog_objects = st.checkbox(
        translate("include_catalog_objects", language),
        value=True,
    )

with sky_map_control_columns[1]:
    include_solar_system_objects = st.checkbox(
        translate(
            "include_solar_system_objects",
            language,
        ),
        value=True,
    )

generate_sky_map_button = st.button(
    translate("generate_sky_map", language),
    type="primary",
    width="stretch",
    key="generate_sky_map_button",
)

if generate_sky_map_button:
    if not (include_catalog_objects or include_solar_system_objects):
        st.warning(translate("no_sky_map_category", language))
    else:
        try:
            sky_map_points = calculate_sky_map_points(
                latitude_deg=float(latitude),
                longitude_deg=float(longitude),
                elevation_m=float(elevation),
                timezone_name=timezone_name,
                local_date=observation_date,
                local_time=observation_time,
                minimum_altitude_degrees=float(minimum_altitude),
                include_catalog_objects=(include_catalog_objects),
                include_solar_system_objects=(include_solar_system_objects),
            )
        except ValueError as error:
            st.error(f"{translate('sky_map_error', language)}: {error}")
        else:
            visible_sky_points = tuple(point for point in sky_map_points if point.is_above_horizon)

            below_horizon_points = tuple(
                point for point in sky_map_points if not point.is_above_horizon
            )

            count_columns = st.columns(2)

            count_columns[0].metric(
                translate(
                    "visible_object_count",
                    language,
                ),
                len(visible_sky_points),
            )

            count_columns[1].metric(
                translate(
                    "below_horizon_count",
                    language,
                ),
                len(below_horizon_points),
            )

            if not visible_sky_points:
                st.info(
                    translate(
                        "no_visible_sky_objects",
                        language,
                    )
                )
            else:
                object_display_names = {
                    object_key: translate(
                        f"object_{object_key}",
                        language,
                    )
                    for object_key in CELESTIAL_PRESETS
                }

                object_display_names.update(
                    {
                        body_key: translate(
                            f"body_{body_key}",
                            language,
                        )
                        for body_key in SOLAR_SYSTEM_BODIES
                    }
                )

                direction_keys = (
                    "north",
                    "northeast",
                    "east",
                    "southeast",
                    "south",
                    "southwest",
                    "west",
                    "northwest",
                )

                direction_display_names = {
                    direction_key: translate(
                        f"direction_{direction_key}",
                        language,
                    )
                    for direction_key in direction_keys
                }

                status_keys = (
                    "observable",
                    "low_altitude",
                    "below_horizon",
                )

                status_display_names = {
                    status_key: translate(
                        f"status_{status_key}",
                        language,
                    )
                    for status_key in status_keys
                }

                sky_map_labels = SkyMapLabels(
                    title=translate(
                        "sky_map_title",
                        language,
                    ),
                    catalog_trace=translate(
                        "catalog_trace",
                        language,
                    ),
                    solar_system_trace=translate(
                        "solar_system_trace",
                        language,
                    ),
                    altitude=translate(
                        "sky_map_altitude",
                        language,
                    ),
                    azimuth=translate(
                        "sky_map_azimuth",
                        language,
                    ),
                    direction=translate(
                        "sky_map_direction",
                        language,
                    ),
                    status=translate(
                        "sky_map_status",
                        language,
                    ),
                    zenith=translate(
                        "sky_map_zenith",
                        language,
                    ),
                    horizon=translate(
                        "sky_map_horizon",
                        language,
                    ),
                )

                sky_map_figure = create_sky_map_figure(
                    points=sky_map_points,
                    display_names=object_display_names,
                    direction_names=(direction_display_names),
                    status_names=(status_display_names),
                    labels=sky_map_labels,
                )

                st.plotly_chart(
                    sky_map_figure,
                    width="stretch",
                    key="interactive_local_sky_map",
                )

                st.caption(translate("sky_map_note", language))


st.divider()

st.header(f"🧠 {translate('planner_section', language)}")
st.info(translate("planner_explanation", language))

planner_category_columns = st.columns(2)

with planner_category_columns[0]:
    include_catalog_targets = st.checkbox(
        translate("include_catalog_targets", language),
        value=True,
        key="planner_include_catalog",
    )

with planner_category_columns[1]:
    include_solar_system_targets = st.checkbox(
        translate(
            "include_solar_system_targets",
            language,
        ),
        value=True,
        key="planner_include_solar_system",
    )

planner_filter_columns = st.columns(2)

with planner_filter_columns[0]:
    minimum_moon_separation = st.slider(
        translate(
            "minimum_moon_separation",
            language,
        ),
        min_value=0.0,
        max_value=180.0,
        value=30.0,
        step=5.0,
    )

with planner_filter_columns[1]:
    minimum_planner_score = st.slider(
        translate(
            "minimum_planner_score",
            language,
        ),
        min_value=0.0,
        max_value=100.0,
        value=40.0,
        step=5.0,
    )

planner_display_columns = st.columns(2)

with planner_display_columns[0]:
    maximum_targets = st.slider(
        translate("maximum_targets", language),
        min_value=1,
        max_value=13,
        value=8,
        step=1,
    )

with planner_display_columns[1]:
    recommended_only = st.checkbox(
        translate("recommended_only", language),
        value=True,
    )

create_plan_button = st.button(
    translate("create_observation_plan", language),
    type="primary",
    width="stretch",
    key="create_observation_plan_button",
)

if create_plan_button:
    if not (include_catalog_targets or include_solar_system_targets):
        st.warning(translate("no_planner_categories", language))
    else:
        try:
            plan_result = calculate_observation_plan(
                latitude_deg=float(latitude),
                longitude_deg=float(longitude),
                elevation_m=float(elevation),
                timezone_name=timezone_name,
                local_date=observation_date,
                local_time=observation_time,
                minimum_altitude_degrees=float(minimum_altitude),
                minimum_moon_separation_degrees=float(minimum_moon_separation),
                minimum_score=float(minimum_planner_score),
                include_catalog_targets=(include_catalog_targets),
                include_solar_system_targets=(include_solar_system_targets),
            )
        except ValueError as error:
            st.error(f"{translate('planner_error', language)}: {error}")
        else:
            st.subheader(translate("planner_results", language))

            recommended_entries = tuple(entry for entry in plan_result.entries if entry.recommended)

            if recommended_only:
                displayed_entries = recommended_entries
            else:
                displayed_entries = plan_result.entries

            if not displayed_entries:
                st.info(
                    translate(
                        "no_recommended_targets",
                        language,
                    )
                )

                displayed_entries = plan_result.entries

            displayed_entries = displayed_entries[:maximum_targets]

            planner_metrics = st.columns(4)

            planner_metrics[0].metric(
                translate(
                    "recommended_target_count",
                    language,
                ),
                plan_result.recommended_count,
            )

            planner_metrics[1].metric(
                translate(
                    "planner_total_targets",
                    language,
                ),
                plan_result.total_target_count,
            )

            planner_metrics[2].metric(
                translate("sun_altitude", language),
                f"{plan_result.sun_altitude_degrees:.2f}°",
            )

            if plan_result.entries:
                highest_ranked_entry = plan_result.entries[0]

                if highest_ranked_entry.category == "catalog":
                    highest_ranked_name = translate(
                        (f"object_{highest_ranked_entry.object_key}"),
                        language,
                    )
                else:
                    highest_ranked_name = translate(
                        (f"body_{highest_ranked_entry.object_key}"),
                        language,
                    )

                planner_metrics[3].metric(
                    translate("best_target", language),
                    highest_ranked_name,
                )

            planner_rows = []

            for rank, entry in enumerate(
                displayed_entries,
                start=1,
            ):
                if entry.category == "catalog":
                    target_name = translate(
                        f"object_{entry.object_key}",
                        language,
                    )
                else:
                    target_name = translate(
                        f"body_{entry.object_key}",
                        language,
                    )

                category_name = translate(
                    f"category_{entry.category}",
                    language,
                )

                direction_name = translate(
                    (f"direction_{entry.cardinal_direction}"),
                    language,
                )

                status_name = translate(
                    f"status_{entry.status}",
                    language,
                )

                rating_name = translate(
                    f"rating_{entry.rating}",
                    language,
                )

                recommended_name = translate(
                    ("value_yes" if entry.recommended else "value_no"),
                    language,
                )

                planner_rows.append(
                    {
                        "rank": rank,
                        "target": target_name,
                        "category": category_name,
                        "score": entry.total_score,
                        "rating": rating_name,
                        "altitude": (entry.altitude_degrees),
                        "azimuth": (entry.azimuth_degrees),
                        "direction": direction_name,
                        "airmass": entry.airmass,
                        "moon_separation": (entry.moon_separation_degrees),
                        "status": status_name,
                        "recommended": (recommended_name),
                    }
                )

            st.dataframe(
                planner_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "rank": st.column_config.NumberColumn(
                        translate(
                            "planner_rank",
                            language,
                        ),
                        format="%d",
                    ),
                    "target": translate(
                        "planner_target",
                        language,
                    ),
                    "category": translate(
                        "planner_category",
                        language,
                    ),
                    "score": (
                        st.column_config.ProgressColumn(
                            translate(
                                "planner_score",
                                language,
                            ),
                            min_value=0.0,
                            max_value=100.0,
                            format="%.1f",
                        )
                    ),
                    "rating": translate(
                        "planner_rating",
                        language,
                    ),
                    "altitude": (
                        st.column_config.NumberColumn(
                            translate(
                                "planner_altitude",
                                language,
                            ),
                            format="%.2f°",
                        )
                    ),
                    "azimuth": (
                        st.column_config.NumberColumn(
                            translate(
                                "azimuth",
                                language,
                            ),
                            format="%.2f°",
                        )
                    ),
                    "direction": translate(
                        "cardinal_direction",
                        language,
                    ),
                    "airmass": (
                        st.column_config.NumberColumn(
                            translate(
                                "planner_airmass",
                                language,
                            ),
                            format="%.2f",
                        )
                    ),
                    "moon_separation": (
                        st.column_config.NumberColumn(
                            translate(
                                "planner_moon_separation",
                                language,
                            ),
                            format="%.2f°",
                        )
                    ),
                    "status": translate(
                        "observation_status",
                        language,
                    ),
                    "recommended": translate(
                        "planner_recommended",
                        language,
                    ),
                },
            )

            chart_entries = tuple(reversed(displayed_entries))

            chart_names = []

            for entry in chart_entries:
                if entry.category == "catalog":
                    chart_names.append(
                        translate(
                            f"object_{entry.object_key}",
                            language,
                        )
                    )
                else:
                    chart_names.append(
                        translate(
                            f"body_{entry.object_key}",
                            language,
                        )
                    )

            ranking_figure = go.Figure(
                go.Bar(
                    x=[entry.total_score for entry in chart_entries],
                    y=chart_names,
                    orientation="h",
                    customdata=[
                        [
                            entry.altitude_degrees,
                            entry.moon_separation_degrees,
                            translate(
                                f"rating_{entry.rating}",
                                language,
                            ),
                        ]
                        for entry in chart_entries
                    ],
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        f"{translate('planner_score', language)}: "
                        "%{x:.1f}<br>"
                        f"{translate('planner_altitude', language)}: "
                        "%{customdata[0]:.2f}°<br>"
                        f"{translate('planner_moon_separation', language)}: "
                        "%{customdata[1]:.2f}°<br>"
                        f"{translate('planner_rating', language)}: "
                        "%{customdata[2]}"
                        "<extra></extra>"
                    ),
                )
            )

            ranking_figure.update_layout(
                title=translate(
                    "ranking_chart",
                    language,
                ),
                xaxis={
                    "range": [0, 100],
                    "title": translate(
                        "planner_score",
                        language,
                    ),
                },
                yaxis={
                    "title": translate(
                        "planner_target",
                        language,
                    ),
                },
                height=max(
                    420,
                    70 * len(chart_entries),
                ),
                margin={
                    "l": 40,
                    "r": 40,
                    "t": 70,
                    "b": 40,
                },
            )

            st.plotly_chart(
                ranking_figure,
                width="stretch",
                key="observation_ranking_chart",
            )

            st.caption(translate("planner_note", language))


st.divider()

st.header(f"📅 {translate('schedule_section', language)}")
st.info(translate("schedule_explanation", language))

schedule_time_columns = st.columns(3)

with schedule_time_columns[0]:
    schedule_start_time = st.time_input(
        translate("schedule_start_time", language),
        value=observation_time,
        key="schedule_start_time_input",
    )

with schedule_time_columns[1]:
    schedule_end_time = st.time_input(
        translate("schedule_end_time", language),
        value=time(4, 0),
        key="schedule_end_time_input",
    )

with schedule_time_columns[2]:
    schedule_interval = st.selectbox(
        translate("sampling_interval", language),
        options=[30, 60, 90, 120],
        index=1,
        format_func=lambda minutes: f"{minutes} {translate('minutes_short', language)}",
    )

schedule_filter_columns = st.columns(2)

with schedule_filter_columns[0]:
    schedule_moon_separation = st.slider(
        translate(
            "schedule_minimum_moon_separation",
            language,
        ),
        min_value=0.0,
        max_value=180.0,
        value=30.0,
        step=5.0,
    )

with schedule_filter_columns[1]:
    schedule_minimum_score = st.slider(
        translate(
            "schedule_minimum_score",
            language,
        ),
        min_value=0.0,
        max_value=100.0,
        value=40.0,
        step=5.0,
    )

schedule_category_columns = st.columns(2)

with schedule_category_columns[0]:
    schedule_catalog_targets = st.checkbox(
        translate(
            "schedule_catalog_targets",
            language,
        ),
        value=True,
    )

with schedule_category_columns[1]:
    schedule_solar_targets = st.checkbox(
        translate(
            "schedule_solar_targets",
            language,
        ),
        value=True,
    )

generate_schedule_button = st.button(
    translate("generate_schedule", language),
    type="primary",
    width="stretch",
    key="generate_night_schedule_button",
)

if generate_schedule_button:
    try:
        schedule_result = calculate_observation_schedule(
            latitude_deg=float(latitude),
            longitude_deg=float(longitude),
            elevation_m=float(elevation),
            timezone_name=timezone_name,
            local_date=observation_date,
            start_time=schedule_start_time,
            end_time=schedule_end_time,
            interval_minutes=int(schedule_interval),
            minimum_altitude_degrees=float(minimum_altitude),
            minimum_moon_separation_degrees=float(schedule_moon_separation),
            minimum_score=float(schedule_minimum_score),
            include_catalog_targets=(schedule_catalog_targets),
            include_solar_system_targets=(schedule_solar_targets),
        )
    except ValueError as error:
        st.error(f"{translate('schedule_error', language)}: {error}")
    else:
        st.subheader(translate("schedule_results", language))

        schedule_display_names = {
            object_key: translate(
                f"object_{object_key}",
                language,
            )
            for object_key in CELESTIAL_PRESETS
        }

        schedule_display_names.update(
            {
                body_key: translate(
                    f"body_{body_key}",
                    language,
                )
                for body_key in SOLAR_SYSTEM_BODIES
            }
        )

        schedule_metrics = st.columns(4)

        schedule_metrics[0].metric(
            translate("schedule_block_count", language),
            len(schedule_result.schedule_blocks),
        )

        schedule_metrics[1].metric(
            translate("scheduled_minutes", language),
            f"{schedule_result.scheduled_minutes:.0f}",
        )

        schedule_metrics[2].metric(
            translate("timeline_samples", language),
            schedule_result.sample_count,
        )

        top_target_name = (
            schedule_display_names.get(
                schedule_result.top_target_key,
                schedule_result.top_target_key,
            )
            if schedule_result.top_target_key
            else translate("not_available", language)
        )

        schedule_metrics[3].metric(
            translate("schedule_top_target", language),
            top_target_name,
        )

        if not schedule_result.schedule_blocks:
            st.info(translate("no_schedule_blocks", language))
        else:
            schedule_rows = []

            for block in schedule_result.schedule_blocks:
                target_name = schedule_display_names.get(
                    block.object_key,
                    block.object_key,
                )

                category_name = translate(
                    f"category_{block.category}",
                    language,
                )

                schedule_rows.append(
                    {
                        "target": target_name,
                        "category": category_name,
                        "start": block.start_local.strftime("%Y-%m-%d %H:%M"),
                        "end": block.end_local.strftime("%Y-%m-%d %H:%M"),
                        "duration": block.duration_minutes,
                        "peak_time": (block.peak_local.strftime("%Y-%m-%d %H:%M")),
                        "peak_score": block.peak_score,
                        "peak_altitude": (block.peak_altitude_degrees),
                        "moon_separation": (block.peak_moon_separation_degrees),
                        "rating": translate(
                            f"rating_{block.rating}",
                            language,
                        ),
                    }
                )

            st.dataframe(
                schedule_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "target": translate(
                        "planner_target",
                        language,
                    ),
                    "category": translate(
                        "planner_category",
                        language,
                    ),
                    "start": translate(
                        "schedule_start",
                        language,
                    ),
                    "end": translate(
                        "schedule_end",
                        language,
                    ),
                    "duration": (
                        st.column_config.NumberColumn(
                            translate(
                                "schedule_duration",
                                language,
                            ),
                            format="%.0f min",
                        )
                    ),
                    "peak_time": translate(
                        "schedule_peak_time",
                        language,
                    ),
                    "peak_score": (
                        st.column_config.ProgressColumn(
                            translate(
                                "schedule_peak_score",
                                language,
                            ),
                            min_value=0.0,
                            max_value=100.0,
                            format="%.1f",
                        )
                    ),
                    "peak_altitude": (
                        st.column_config.NumberColumn(
                            translate(
                                "schedule_peak_altitude",
                                language,
                            ),
                            format="%.2f°",
                        )
                    ),
                    "moon_separation": (
                        st.column_config.NumberColumn(
                            translate(
                                "schedule_peak_moon_separation",
                                language,
                            ),
                            format="%.2f°",
                        )
                    ),
                    "rating": translate(
                        "planner_rating",
                        language,
                    ),
                },
            )

        if schedule_result.timeline_points:
            schedule_rating_names = {
                rating_key: translate(
                    f"rating_{rating_key}",
                    language,
                )
                for rating_key in (
                    "excellent",
                    "very_good",
                    "good",
                    "fair",
                    "poor",
                )
            }

            schedule_chart_labels = ScheduleChartLabels(
                title=translate(
                    "schedule_timeline_chart",
                    language,
                ),
                time_axis=translate(
                    "schedule_time_axis",
                    language,
                ),
                score_axis=translate(
                    "schedule_score_axis",
                    language,
                ),
                altitude=translate(
                    "planner_altitude",
                    language,
                ),
                moon_separation=translate(
                    "planner_moon_separation",
                    language,
                ),
                rating=translate(
                    "planner_rating",
                    language,
                ),
                recommended=translate(
                    "planner_recommended",
                    language,
                ),
                yes=translate("value_yes", language),
                no=translate("value_no", language),
            )

            schedule_figure = create_schedule_figure(
                points=schedule_result.timeline_points,
                display_names=schedule_display_names,
                rating_names=schedule_rating_names,
                labels=schedule_chart_labels,
            )

            st.plotly_chart(
                schedule_figure,
                width="stretch",
                key="night_schedule_timeline",
            )

        st.caption(translate("schedule_note", language))


st.divider()

st.header(f"🌦️ {translate('weather_section', language)}")
st.info(translate("weather_explanation", language))

weather_time_columns = st.columns(2)

with weather_time_columns[0]:
    weather_start_time = st.time_input(
        translate("weather_start_time", language),
        value=observation_time,
        key="weather_start_time_input",
    )

with weather_time_columns[1]:
    weather_end_time = st.time_input(
        translate("weather_end_time", language),
        value=time(4, 0),
        key="weather_end_time_input",
    )

retrieve_weather_button = st.button(
    translate("fetch_weather_forecast", language),
    type="primary",
    width="stretch",
    key="retrieve_observing_weather_button",
)

if retrieve_weather_button:
    try:
        weather_result = fetch_observing_weather(
            latitude_deg=float(latitude),
            longitude_deg=float(longitude),
            elevation_m=float(elevation),
            timezone_name=timezone_name,
            local_date=observation_date,
            start_time=weather_start_time,
            end_time=weather_end_time,
        )
    except (ValueError, WeatherServiceError) as error:
        st.error(f"{translate('weather_error', language)}: {error}")
    else:
        st.subheader(translate("weather_results", language))

        weather_rating_names = {
            rating_key: translate(
                f"weather_rating_{rating_key}",
                language,
            )
            for rating_key in (
                "excellent",
                "good",
                "fair",
                "poor",
                "unsuitable",
            )
        }

        dew_risk_names = {
            risk_key: translate(
                f"dew_risk_{risk_key}",
                language,
            )
            for risk_key in (
                "low",
                "moderate",
                "high",
                "critical",
            )
        }

        weather_metrics = st.columns(5)

        weather_metrics[0].metric(
            translate("best_weather_hour", language),
            weather_result.best_point.local_datetime.strftime("%m-%d %H:%M"),
        )

        weather_metrics[1].metric(
            translate("best_weather_score", language),
            f"{weather_result.best_point.observing_score:.1f}",
        )

        weather_metrics[2].metric(
            translate("average_weather_score", language),
            f"{weather_result.average_score:.1f}",
        )

        weather_metrics[3].metric(
            translate("maximum_cloud_cover", language),
            f"{weather_result.maximum_cloud_cover_percent:.0f}%",
        )

        weather_metrics[4].metric(
            translate("worst_dew_risk", language),
            dew_risk_names[weather_result.worst_dew_risk],
        )

        dew_warning_key = f"dew_warning_{weather_result.worst_dew_risk}"

        if weather_result.worst_dew_risk == "critical":
            st.error(translate(dew_warning_key, language))
        elif weather_result.worst_dew_risk in {
            "moderate",
            "high",
        }:
            st.warning(translate(dew_warning_key, language))
        else:
            st.success(translate(dew_warning_key, language))

        unsuitable_weather_points = tuple(
            point for point in weather_result.points if point.rating == "unsuitable"
        )

        if unsuitable_weather_points:
            st.warning(
                translate(
                    "unsafe_weather_warning",
                    language,
                )
            )

        weather_rows = []

        for point in weather_result.points:
            weather_rows.append(
                {
                    "time": (point.local_datetime.strftime("%Y-%m-%d %H:%M")),
                    "score": point.observing_score,
                    "rating": weather_rating_names[point.rating],
                    "temperature": point.temperature_c,
                    "dew_point": point.dew_point_c,
                    "dew_spread": (point.dew_point_spread_c),
                    "humidity": (point.relative_humidity_percent),
                    "cloud_cover": (point.cloud_cover_percent),
                    "precipitation_probability": (point.precipitation_probability_percent),
                    "precipitation": (point.precipitation_mm),
                    "visibility": (point.visibility_m / 1000.0),
                    "wind_speed": (point.wind_speed_kmh),
                    "wind_gusts": (point.wind_gusts_kmh),
                    "dew_risk": dew_risk_names[point.dew_risk],
                }
            )

        st.dataframe(
            weather_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "time": translate(
                    "weather_time",
                    language,
                ),
                "score": (
                    st.column_config.ProgressColumn(
                        translate(
                            "weather_score",
                            language,
                        ),
                        min_value=0.0,
                        max_value=100.0,
                        format="%.1f",
                    )
                ),
                "rating": translate(
                    "weather_rating",
                    language,
                ),
                "temperature": (
                    st.column_config.NumberColumn(
                        translate(
                            "temperature_c",
                            language,
                        ),
                        format="%.1f °C",
                    )
                ),
                "dew_point": (
                    st.column_config.NumberColumn(
                        translate(
                            "dew_point_c",
                            language,
                        ),
                        format="%.1f °C",
                    )
                ),
                "dew_spread": (
                    st.column_config.NumberColumn(
                        translate(
                            "dew_spread_c",
                            language,
                        ),
                        format="%.1f °C",
                    )
                ),
                "humidity": (
                    st.column_config.NumberColumn(
                        translate(
                            "relative_humidity",
                            language,
                        ),
                        format="%.0f%%",
                    )
                ),
                "cloud_cover": (
                    st.column_config.NumberColumn(
                        translate(
                            "cloud_cover",
                            language,
                        ),
                        format="%.0f%%",
                    )
                ),
                "precipitation_probability": (
                    st.column_config.NumberColumn(
                        translate(
                            "precipitation_probability",
                            language,
                        ),
                        format="%.0f%%",
                    )
                ),
                "precipitation": (
                    st.column_config.NumberColumn(
                        translate(
                            "precipitation_amount",
                            language,
                        ),
                        format="%.2f mm",
                    )
                ),
                "visibility": (
                    st.column_config.NumberColumn(
                        translate(
                            "visibility_km",
                            language,
                        ),
                        format="%.1f km",
                    )
                ),
                "wind_speed": (
                    st.column_config.NumberColumn(
                        translate(
                            "wind_speed",
                            language,
                        ),
                        format="%.1f km/h",
                    )
                ),
                "wind_gusts": (
                    st.column_config.NumberColumn(
                        translate(
                            "wind_gusts",
                            language,
                        ),
                        format="%.1f km/h",
                    )
                ),
                "dew_risk": translate(
                    "dew_risk",
                    language,
                ),
            },
        )

        weather_chart_labels = WeatherChartLabels(
            score_title=translate(
                "weather_score_chart",
                language,
            ),
            conditions_title=translate(
                "weather_conditions_chart",
                language,
            ),
            time_axis=translate(
                "weather_time_axis",
                language,
            ),
            score_axis=translate(
                "weather_score",
                language,
            ),
            cloud_cover=translate(
                "cloud_cover",
                language,
            ),
            precipitation_probability=translate(
                "precipitation_probability",
                language,
            ),
            precipitation_amount=translate(
                "precipitation_amount",
                language,
            ),
            humidity=translate(
                "relative_humidity",
                language,
            ),
            wind_speed=translate(
                "wind_speed",
                language,
            ),
            rating=translate(
                "weather_rating",
                language,
            ),
            dew_risk=translate(
                "dew_risk",
                language,
            ),
        )

        weather_score_figure = create_weather_score_figure(
            points=weather_result.points,
            labels=weather_chart_labels,
            rating_names=weather_rating_names,
            dew_risk_names=dew_risk_names,
        )

        st.plotly_chart(
            weather_score_figure,
            width="stretch",
            key="observing_weather_score_chart",
        )

        weather_conditions_figure = create_weather_conditions_figure(
            points=weather_result.points,
            labels=weather_chart_labels,
        )

        st.plotly_chart(
            weather_conditions_figure,
            width="stretch",
            key="observing_weather_conditions_chart",
        )

        st.write(f"**{translate('weather_source', language)}:** {weather_result.source_name}")

        st.markdown(translate("weather_attribution", language))

        st.caption(
            translate(
                "weather_forecast_note",
                language,
            )
        )


st.divider()

st.header(f"🔭 {translate('telescope_section', language)}")
st.info(translate("telescope_explanation", language))

telescope_mode_columns = st.columns(2)

with telescope_mode_columns[0]:
    telescope_input_mode = st.selectbox(
        translate("telescope_input_mode", language),
        options=("preset", "custom"),
        format_func=lambda mode: translate(
            f"telescope_mode_{mode}",
            language,
        ),
        key="telescope_input_mode",
    )

with telescope_mode_columns[1]:
    eyepiece_input_mode = st.selectbox(
        translate("telescope_input_mode", language),
        options=("preset", "custom"),
        format_func=lambda mode: translate(
            f"telescope_mode_{mode}",
            language,
        ),
        key="eyepiece_input_mode",
    )

if telescope_input_mode == "preset":
    selected_telescope_key = st.selectbox(
        translate("telescope_preset", language),
        options=tuple(TELESCOPE_PRESETS),
        format_func=lambda preset_key: translate(
            f"telescope_preset_{preset_key}",
            language,
        ),
    )

    telescope_spec = TELESCOPE_PRESETS[selected_telescope_key]
else:
    custom_telescope_columns = st.columns(2)

    with custom_telescope_columns[0]:
        custom_aperture = st.number_input(
            translate("telescope_aperture", language),
            min_value=10.0,
            max_value=2000.0,
            value=130.0,
            step=1.0,
            format="%.1f",
        )

    with custom_telescope_columns[1]:
        custom_telescope_focal_length = st.number_input(
            translate(
                "telescope_focal_length",
                language,
            ),
            min_value=50.0,
            max_value=20_000.0,
            value=650.0,
            step=10.0,
            format="%.1f",
        )

    telescope_spec = TelescopeSpec(
        aperture_mm=float(custom_aperture),
        focal_length_mm=float(custom_telescope_focal_length),
    )

if eyepiece_input_mode == "preset":
    selected_eyepiece_key = st.selectbox(
        translate("eyepiece_preset", language),
        options=tuple(EYEPIECE_PRESETS),
        format_func=lambda preset_key: translate(
            f"eyepiece_preset_{preset_key}",
            language,
        ),
    )

    eyepiece_spec = EYEPIECE_PRESETS[selected_eyepiece_key]
else:
    custom_eyepiece_columns = st.columns(2)

    with custom_eyepiece_columns[0]:
        custom_eyepiece_focal_length = st.number_input(
            translate(
                "eyepiece_focal_length",
                language,
            ),
            min_value=1.0,
            max_value=100.0,
            value=25.0,
            step=0.5,
            format="%.1f",
        )

    with custom_eyepiece_columns[1]:
        custom_apparent_field = st.number_input(
            translate("apparent_field", language),
            min_value=20.0,
            max_value=180.0,
            value=50.0,
            step=1.0,
            format="%.1f",
        )

    eyepiece_spec = EyepieceSpec(
        focal_length_mm=float(custom_eyepiece_focal_length),
        apparent_field_degrees=float(custom_apparent_field),
    )

optical_accessory_columns = st.columns(2)

with optical_accessory_columns[0]:
    selected_barlow_factor = st.selectbox(
        translate("barlow_factor", language),
        options=(1.0, 1.5, 2.0, 2.5, 3.0),
        index=0,
        format_func=lambda factor: f"{factor:.1f}×",
    )

with optical_accessory_columns[1]:
    selected_reducer_factor = st.selectbox(
        translate("reducer_factor", language),
        options=(1.0, 0.8, 0.63, 0.5),
        index=0,
        format_func=lambda factor: f"{factor:.2f}×",
    )

run_telescope_simulation = st.button(
    translate("run_optical_simulation", language),
    type="primary",
    width="stretch",
    key="run_telescope_simulation",
)

if run_telescope_simulation:
    try:
        optical_result = calculate_optical_simulation(
            telescope=telescope_spec,
            eyepiece=eyepiece_spec,
            barlow_factor=float(selected_barlow_factor),
            reducer_factor=float(selected_reducer_factor),
        )
    except ValueError as error:
        st.error(f"{translate('telescope_error', language)}: {error}")
    else:
        st.subheader(translate("optical_results", language))

        primary_metrics = st.columns(3)

        primary_metrics[0].metric(
            translate("magnification", language),
            f"{optical_result.magnification:.1f}×",
        )

        primary_metrics[1].metric(
            translate("exit_pupil", language),
            f"{optical_result.exit_pupil_mm:.2f} mm",
        )

        primary_metrics[2].metric(
            translate("true_field", language),
            f"{optical_result.true_field_degrees:.3f}°",
        )

        secondary_metrics = st.columns(3)

        secondary_metrics[0].metric(
            translate(
                "effective_focal_length",
                language,
            ),
            f"{optical_result.effective_focal_length_mm:.1f} mm",
        )

        secondary_metrics[1].metric(
            translate(
                "effective_focal_ratio",
                language,
            ),
            f"f/{optical_result.effective_focal_ratio:.2f}",
        )

        secondary_metrics[2].metric(
            translate(
                "maximum_useful_magnification",
                language,
            ),
            f"{optical_result.maximum_useful_magnification:.0f}×",
        )

        resolution_metrics = st.columns(3)

        resolution_metrics[0].metric(
            translate("native_focal_ratio", language),
            f"f/{optical_result.native_focal_ratio:.2f}",
        )

        resolution_metrics[1].metric(
            translate("dawes_resolution", language),
            f"{optical_result.dawes_resolution_arcseconds:.2f}″",
        )

        resolution_metrics[2].metric(
            translate(
                "rayleigh_resolution",
                language,
            ),
            f"{optical_result.rayleigh_resolution_arcseconds:.2f}″",
        )

        optical_status_message = translate(
            f"optical_status_{optical_result.status}",
            language,
        )

        if optical_result.status in {
            "excessive_exit_pupil",
            "excessive_magnification",
        }:
            st.warning(optical_status_message)
        elif optical_result.status == "high_power":
            st.info(optical_status_message)
        else:
            st.success(optical_status_message)

        st.subheader(translate("eyepiece_comparison", language))

        comparison_results = compare_eyepieces(
            telescope=telescope_spec,
            eyepieces=tuple(EYEPIECE_PRESETS.values()),
            barlow_factor=float(selected_barlow_factor),
            reducer_factor=float(selected_reducer_factor),
        )

        eyepiece_keys_by_spec = {
            specification: key for key, specification in EYEPIECE_PRESETS.items()
        }

        comparison_rows = []

        for comparison_result in comparison_results:
            eyepiece_key = eyepiece_keys_by_spec[comparison_result.eyepiece]

            comparison_rows.append(
                {
                    "eyepiece": translate(
                        f"eyepiece_preset_{eyepiece_key}",
                        language,
                    ),
                    "magnification": (comparison_result.magnification),
                    "exit_pupil": (comparison_result.exit_pupil_mm),
                    "true_field": (comparison_result.true_field_degrees),
                    "status": translate(
                        (f"optical_status_{comparison_result.status}"),
                        language,
                    ),
                }
            )

        st.dataframe(
            comparison_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "eyepiece": translate(
                    "eyepiece_preset",
                    language,
                ),
                "magnification": (
                    st.column_config.NumberColumn(
                        translate(
                            "magnification",
                            language,
                        ),
                        format="%.1f×",
                    )
                ),
                "exit_pupil": (
                    st.column_config.NumberColumn(
                        translate(
                            "exit_pupil",
                            language,
                        ),
                        format="%.2f mm",
                    )
                ),
                "true_field": (
                    st.column_config.NumberColumn(
                        translate(
                            "true_field",
                            language,
                        ),
                        format="%.3f°",
                    )
                ),
                "status": translate(
                    "optical_status",
                    language,
                ),
            },
        )

        st.subheader(translate("fov_visualizer", language))

        selected_angular_target_key = st.selectbox(
            translate("angular_target", language),
            options=tuple(ANGULAR_SIZE_PRESETS),
            format_func=lambda target_key: translate(
                f"target_{target_key}",
                language,
            ),
            key="telescope_angular_target",
        )

        angular_target = ANGULAR_SIZE_PRESETS[selected_angular_target_key]

        target_fit = classify_target_fit(
            true_field_degrees=(optical_result.true_field_degrees),
            target=angular_target,
        )

        target_fit_message = translate(
            f"field_fit_{target_fit}",
            language,
        )

        if target_fit == "comfortable":
            st.success(target_fit_message)
        elif target_fit == "tight":
            st.info(target_fit_message)
        else:
            st.warning(target_fit_message)

        target_display_name = translate(
            f"target_{selected_angular_target_key}",
            language,
        )

        field_labels = FieldOfViewLabels(
            title=translate(
                "fov_chart_title",
                language,
            ),
            angular_distance=translate(
                "angular_distance",
                language,
            ),
            field_of_view=translate(
                "true_field",
                language,
            ),
            target=translate(
                "angular_target",
                language,
            ),
            target_size=translate(
                "target_angular_size",
                language,
            ),
            fit=translate(
                "field_fit",
                language,
            ),
        )

        field_figure = create_field_of_view_figure(
            true_field_degrees=(optical_result.true_field_degrees),
            target=angular_target,
            target_name=target_display_name,
            fit_name=target_fit_message,
            labels=field_labels,
        )

        st.plotly_chart(
            field_figure,
            width="stretch",
            key="telescope_field_of_view_chart",
        )

        st.warning(
            translate(
                "telescope_solar_warning",
                language,
            )
        )

        st.caption(translate("telescope_note", language))


st.divider()

st.header(f"📷 {translate('imaging_section', language)}")
st.info(translate("imaging_explanation", language))

imaging_mode_columns = st.columns(2)

with imaging_mode_columns[0]:
    imaging_telescope_mode = st.selectbox(
        translate(
            "imaging_specification_mode",
            language,
        ),
        options=("preset", "custom"),
        format_func=lambda mode: translate(
            f"imaging_mode_{mode}",
            language,
        ),
        key="mission11_telescope_mode",
    )

with imaging_mode_columns[1]:
    imaging_camera_mode = st.selectbox(
        translate(
            "imaging_specification_mode",
            language,
        ),
        options=("preset", "custom"),
        format_func=lambda mode: translate(
            f"imaging_mode_{mode}",
            language,
        ),
        key="mission11_camera_mode",
    )

if imaging_telescope_mode == "preset":
    imaging_telescope_key = st.selectbox(
        translate("telescope_preset", language),
        options=tuple(TELESCOPE_PRESETS),
        format_func=lambda preset_key: translate(
            f"telescope_preset_{preset_key}",
            language,
        ),
        key="mission11_telescope_preset",
    )

    imaging_telescope = TELESCOPE_PRESETS[imaging_telescope_key]
else:
    imaging_telescope_columns = st.columns(2)

    with imaging_telescope_columns[0]:
        imaging_aperture_mm = st.number_input(
            translate("telescope_aperture", language),
            min_value=10.0,
            max_value=2000.0,
            value=130.0,
            step=1.0,
            format="%.1f",
            key="mission11_aperture",
        )

    with imaging_telescope_columns[1]:
        imaging_focal_length_mm = st.number_input(
            translate(
                "telescope_focal_length",
                language,
            ),
            min_value=50.0,
            max_value=20_000.0,
            value=650.0,
            step=10.0,
            format="%.1f",
            key="mission11_focal_length",
        )

    imaging_telescope = TelescopeSpec(
        aperture_mm=float(imaging_aperture_mm),
        focal_length_mm=float(imaging_focal_length_mm),
    )

if imaging_camera_mode == "preset":
    imaging_camera_key = st.selectbox(
        translate("camera_preset", language),
        options=tuple(CAMERA_PRESETS),
        format_func=lambda preset_key: translate(
            f"camera_preset_{preset_key}",
            language,
        ),
        key="mission11_camera_preset",
    )

    imaging_camera = CAMERA_PRESETS[imaging_camera_key]
else:
    custom_sensor_columns = st.columns(3)

    with custom_sensor_columns[0]:
        sensor_width_pixels = st.number_input(
            translate(
                "sensor_width_pixels",
                language,
            ),
            min_value=100,
            max_value=30_000,
            value=6248,
            step=100,
            key="mission11_sensor_width",
        )

    with custom_sensor_columns[1]:
        sensor_height_pixels = st.number_input(
            translate(
                "sensor_height_pixels",
                language,
            ),
            min_value=100,
            max_value=30_000,
            value=4176,
            step=100,
            key="mission11_sensor_height",
        )

    with custom_sensor_columns[2]:
        sensor_pixel_size_um = st.number_input(
            translate("pixel_size_um", language),
            min_value=0.5,
            max_value=30.0,
            value=3.76,
            step=0.01,
            format="%.2f",
            key="mission11_pixel_size",
        )

    imaging_camera = CameraSensorSpec(
        width_pixels=int(sensor_width_pixels),
        height_pixels=int(sensor_height_pixels),
        pixel_size_um=float(sensor_pixel_size_um),
    )

imaging_environment_columns = st.columns(3)

with imaging_environment_columns[0]:
    imaging_seeing = st.number_input(
        translate("seeing_arcseconds", language),
        min_value=0.3,
        max_value=10.0,
        value=2.0,
        step=0.1,
        format="%.1f",
        key="mission11_seeing",
    )

with imaging_environment_columns[1]:
    imaging_barlow = st.selectbox(
        translate("barlow_factor", language),
        options=(1.0, 1.5, 2.0, 2.5, 3.0),
        index=0,
        format_func=lambda factor: f"{factor:.1f}×",
        key="mission11_barlow",
    )

with imaging_environment_columns[2]:
    imaging_reducer = st.selectbox(
        translate("reducer_factor", language),
        options=(1.0, 0.8, 0.63, 0.5),
        index=0,
        format_func=lambda factor: f"{factor:.2f}×",
        key="mission11_reducer",
    )

run_imaging_button = st.button(
    translate("run_imaging_simulation", language),
    type="primary",
    width="stretch",
    key="mission11_run_imaging",
)

if run_imaging_button:
    try:
        calculated_imaging_result = calculate_astrophotography_setup(
            telescope=imaging_telescope,
            camera=imaging_camera,
            seeing_arcseconds=float(imaging_seeing),
            barlow_factor=float(imaging_barlow),
            reducer_factor=float(imaging_reducer),
        )
    except ValueError as error:
        st.session_state.pop(
            "mission11_imaging_payload",
            None,
        )

        st.error(f"{translate('imaging_error', language)}: {error}")
    else:
        st.session_state["mission11_imaging_payload"] = {
            "result": calculated_imaging_result,
            "telescope": imaging_telescope,
            "camera": imaging_camera,
            "seeing": float(imaging_seeing),
            "barlow": float(imaging_barlow),
            "reducer": float(imaging_reducer),
        }

imaging_payload = st.session_state.get("mission11_imaging_payload")

if imaging_payload is not None:
    imaging_result = imaging_payload["result"]

    st.subheader(translate("imaging_results", language))

    imaging_primary_metrics = st.columns(4)

    imaging_primary_metrics[0].metric(
        translate("image_scale", language),
        (f"{imaging_result.image_scale_arcsec_per_pixel:.3f} arcsec/px"),
    )

    imaging_primary_metrics[1].metric(
        translate("sensor_field", language),
        (f"{imaging_result.field_width_degrees:.3f}° × {imaging_result.field_height_degrees:.3f}°"),
    )

    imaging_primary_metrics[2].metric(
        translate("seeing_disk_pixels", language),
        f"{imaging_result.seeing_disk_pixels:.2f} px",
    )

    imaging_primary_metrics[3].metric(
        translate("sampling_status", language),
        imaging_result.sampling_status.replace(
            "_",
            " ",
        ).title(),
    )

    imaging_secondary_metrics = st.columns(4)

    imaging_secondary_metrics[0].metric(
        translate(
            "effective_focal_length",
            language,
        ),
        (f"{imaging_result.effective_focal_length_mm:.1f} mm"),
    )

    imaging_secondary_metrics[1].metric(
        translate(
            "effective_focal_ratio",
            language,
        ),
        (f"f/{imaging_result.effective_focal_ratio:.2f}"),
    )

    imaging_secondary_metrics[2].metric(
        translate("sensor_dimensions", language),
        (f"{imaging_result.sensor_width_mm:.2f} × {imaging_result.sensor_height_mm:.2f} mm"),
    )

    imaging_secondary_metrics[3].metric(
        translate("camera_megapixels", language),
        f"{imaging_result.megapixels:.1f} MP",
    )

    imaging_resolution_metrics = st.columns(3)

    imaging_resolution_metrics[0].metric(
        translate("field_diagonal", language),
        (f"{imaging_result.field_diagonal_degrees:.3f}°"),
    )

    imaging_resolution_metrics[1].metric(
        translate(
            "dawes_sampling_pixels",
            language,
        ),
        (f"{imaging_result.dawes_resolution_pixels:.2f} px"),
    )

    imaging_resolution_metrics[2].metric(
        translate("ideal_image_scale", language),
        (
            f"{imaging_result.ideal_scale_min_arcsec_per_pixel:.3f}"
            "–"
            f"{imaging_result.ideal_scale_max_arcsec_per_pixel:.3f} "
            "arcsec/px"
        ),
    )

    sampling_message = translate(
        (f"sampling_status_{imaging_result.sampling_status}"),
        language,
    )

    if imaging_result.sampling_status == ("well_sampled"):
        st.success(sampling_message)
    elif imaging_result.sampling_status in {
        "oversampled",
        "undersampled",
    }:
        st.info(sampling_message)
    else:
        st.warning(sampling_message)

    st.subheader(translate("camera_comparison", language))

    comparison_results = compare_camera_sensors(
        telescope=imaging_payload["telescope"],
        cameras=tuple(CAMERA_PRESETS.values()),
        seeing_arcseconds=imaging_payload["seeing"],
        barlow_factor=imaging_payload["barlow"],
        reducer_factor=imaging_payload["reducer"],
    )

    camera_keys_by_spec = {specification: key for key, specification in CAMERA_PRESETS.items()}

    camera_comparison_rows = []

    for comparison_result in comparison_results:
        camera_key = camera_keys_by_spec[comparison_result.camera]

        camera_comparison_rows.append(
            {
                "camera": translate(
                    f"camera_preset_{camera_key}",
                    language,
                ),
                "megapixels": (comparison_result.megapixels),
                "sensor_width": (comparison_result.sensor_width_mm),
                "sensor_height": (comparison_result.sensor_height_mm),
                "image_scale": (comparison_result.image_scale_arcsec_per_pixel),
                "field_width": (comparison_result.field_width_degrees),
                "field_height": (comparison_result.field_height_degrees),
                "sampling": translate(
                    (f"sampling_status_{comparison_result.sampling_status}"),
                    language,
                ),
            }
        )

    st.dataframe(
        camera_comparison_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "camera": translate(
                "camera_preset",
                language,
            ),
            "megapixels": (
                st.column_config.NumberColumn(
                    translate(
                        "camera_megapixels",
                        language,
                    ),
                    format="%.1f MP",
                )
            ),
            "sensor_width": (
                st.column_config.NumberColumn(
                    translate(
                        "field_width",
                        language,
                    ),
                    format="%.2f mm",
                )
            ),
            "sensor_height": (
                st.column_config.NumberColumn(
                    translate(
                        "field_height",
                        language,
                    ),
                    format="%.2f mm",
                )
            ),
            "image_scale": (
                st.column_config.NumberColumn(
                    translate(
                        "image_scale",
                        language,
                    ),
                    format="%.3f arcsec/px",
                )
            ),
            "field_width": (
                st.column_config.NumberColumn(
                    translate(
                        "field_width",
                        language,
                    ),
                    format="%.3f°",
                )
            ),
            "field_height": (
                st.column_config.NumberColumn(
                    translate(
                        "field_height",
                        language,
                    ),
                    format="%.3f°",
                )
            ),
            "sampling": translate(
                "sampling_status",
                language,
            ),
        },
    )

    st.subheader(translate("target_framing", language))

    framing_control_columns = st.columns(3)

    with framing_control_columns[0]:
        imaging_target_key = st.selectbox(
            translate("imaging_target", language),
            options=tuple(IMAGING_TARGET_PRESETS),
            format_func=lambda target_key: translate(
                f"target_{target_key}",
                language,
            ),
            key="mission11_target",
        )

    with framing_control_columns[1]:
        imaging_overlap = st.slider(
            translate("mosaic_overlap", language),
            min_value=0,
            max_value=50,
            value=15,
            step=5,
            format="%d%%",
            key="mission11_overlap",
        )

    with framing_control_columns[2]:
        imaging_rotation = st.slider(
            translate("sensor_rotation", language),
            min_value=0,
            max_value=175,
            value=0,
            step=5,
            format="%d°",
            key="mission11_rotation",
        )

    imaging_target = IMAGING_TARGET_PRESETS[imaging_target_key]

    framing_result = calculate_target_framing(
        field_width_degrees=(imaging_result.field_width_degrees),
        field_height_degrees=(imaging_result.field_height_degrees),
        target=imaging_target,
        overlap_percent=float(imaging_overlap),
    )

    framing_message = translate(
        f"framing_status_{framing_result.status}",
        language,
    )

    if framing_result.status == "comfortable":
        st.success(framing_message)
    elif framing_result.status == "tight":
        st.info(framing_message)
    else:
        st.warning(framing_message)

    framing_metrics = st.columns(5)

    framing_metrics[0].metric(
        translate("horizontal_panels", language),
        framing_result.panels_horizontal,
    )

    framing_metrics[1].metric(
        translate("vertical_panels", language),
        framing_result.panels_vertical,
    )

    framing_metrics[2].metric(
        translate("total_panels", language),
        framing_result.total_panels,
    )

    framing_metrics[3].metric(
        translate("width_fill", language),
        f"{framing_result.width_fill_percent:.1f}%",
    )

    framing_metrics[4].metric(
        translate("height_fill", language),
        f"{framing_result.height_fill_percent:.1f}%",
    )

    st.write(
        f"**{translate('covered_field', language)}:** "
        f"{framing_result.covered_width_degrees:.3f}°"
        " × "
        f"{framing_result.covered_height_degrees:.3f}°"
    )

    imaging_frame_labels = ImagingFrameLabels(
        title=translate(
            "imaging_frame_title",
            language,
        ),
        horizontal_axis=translate(
            "horizontal_angle",
            language,
        ),
        vertical_axis=translate(
            "vertical_angle",
            language,
        ),
        target=translate(
            "imaging_target",
            language,
        ),
        sensor_panel=translate(
            "sensor_panel",
            language,
        ),
        rotation=translate(
            "sensor_rotation",
            language,
        ),
        mosaic=translate(
            "mosaic_layout",
            language,
        ),
    )

    imaging_frame_figure = create_imaging_frame_figure(
        field_width_degrees=(imaging_result.field_width_degrees),
        field_height_degrees=(imaging_result.field_height_degrees),
        target=imaging_target,
        framing=framing_result,
        rotation_degrees=float(imaging_rotation),
        target_name=translate(
            f"target_{imaging_target_key}",
            language,
        ),
        labels=imaging_frame_labels,
    )

    st.plotly_chart(
        imaging_frame_figure,
        width="stretch",
        key="mission11_imaging_frame_chart",
    )

    st.caption(translate("imaging_note", language))


st.divider()

st.header(f"📝 {translate('log_section', language)}")
st.info(translate("log_explanation", language))

mission12_today = dt.date.today()

mission12_defaults = {
    "mission12_session_id": (f"session-{mission12_today.isoformat()}"),
    "mission12_session_title": "",
    "mission12_observer": "",
    "mission12_location": "Osaka",
    "mission12_latitude": 34.6937,
    "mission12_longitude": 135.5023,
    "mission12_elevation": 15.0,
    "mission12_timezone": "Asia/Tokyo",
    "mission12_start_date": mission12_today,
    "mission12_start_time": dt.time(20, 0),
    "mission12_end_date": (mission12_today + dt.timedelta(days=1)),
    "mission12_end_time": dt.time(0, 0),
    "mission12_mode": "mixed",
    "mission12_seeing": 2.0,
    "mission12_transparency": 4,
    "mission12_cloud_cover": 10.0,
    "mission12_general_notes": "",
    "mission12_telescope_name": "",
    "mission12_aperture": 0.0,
    "mission12_focal_length": 0.0,
    "mission12_eyepiece_name": "",
    "mission12_camera_name": "",
    "mission12_pixel_size": 0.0,
    "mission12_mount_name": "",
    "mission12_filters": "",
    "mission12_observations": [],
    "mission12_observation_counter": 0,
    "mission12_current_session": None,
}

for mission12_key, mission12_value in mission12_defaults.items():
    if mission12_key not in st.session_state:
        st.session_state[mission12_key] = mission12_value

with st.expander(translate("log_import_title", language)):
    mission12_uploaded_log = st.file_uploader(
        translate("log_import_file", language),
        type=("json",),
        key="mission12_uploaded_log",
        width="stretch",
    )

    mission12_import_button = st.button(
        translate("log_import_button", language),
        key="mission12_import_button",
        width="stretch",
    )

    if mission12_import_button:
        if mission12_uploaded_log is None:
            st.warning(
                translate(
                    "log_import_missing",
                    language,
                )
            )
        else:
            try:
                mission12_imported_session = session_from_json(
                    mission12_uploaded_log.getvalue().decode("utf-8-sig")
                )
            except (
                ObservationLogError,
                UnicodeDecodeError,
                ValueError,
            ) as error:
                st.error(f"{translate('log_validation_error', language)}: {error}")
            else:
                mission12_equipment = mission12_imported_session.equipment

                st.session_state["mission12_session_id"] = mission12_imported_session.session_id

                st.session_state["mission12_session_title"] = mission12_imported_session.title

                st.session_state["mission12_observer"] = mission12_imported_session.observer

                st.session_state["mission12_location"] = mission12_imported_session.location_name

                st.session_state["mission12_latitude"] = mission12_imported_session.latitude_degrees

                st.session_state["mission12_longitude"] = (
                    mission12_imported_session.longitude_degrees
                )

                st.session_state["mission12_elevation"] = mission12_imported_session.elevation_m

                st.session_state["mission12_timezone"] = mission12_imported_session.timezone_name

                st.session_state["mission12_start_date"] = (
                    mission12_imported_session.started_at_local.date()
                )

                st.session_state["mission12_start_time"] = (
                    mission12_imported_session.started_at_local.time().replace(tzinfo=None)
                )

                st.session_state["mission12_end_date"] = (
                    mission12_imported_session.ended_at_local.date()
                )

                st.session_state["mission12_end_time"] = (
                    mission12_imported_session.ended_at_local.time().replace(tzinfo=None)
                )

                st.session_state["mission12_mode"] = mission12_imported_session.mode

                st.session_state["mission12_seeing"] = (
                    mission12_imported_session.seeing_arcseconds or 2.0
                )

                st.session_state["mission12_transparency"] = (
                    mission12_imported_session.transparency_rating or 3
                )

                st.session_state["mission12_cloud_cover"] = (
                    mission12_imported_session.cloud_cover_percent or 0.0
                )

                st.session_state["mission12_general_notes"] = (
                    mission12_imported_session.general_notes
                )

                st.session_state["mission12_telescope_name"] = mission12_equipment.telescope_name

                st.session_state["mission12_aperture"] = mission12_equipment.aperture_mm or 0.0

                st.session_state["mission12_focal_length"] = (
                    mission12_equipment.focal_length_mm or 0.0
                )

                st.session_state["mission12_eyepiece_name"] = mission12_equipment.eyepiece_name

                st.session_state["mission12_camera_name"] = mission12_equipment.camera_name

                st.session_state["mission12_pixel_size"] = mission12_equipment.pixel_size_um or 0.0

                st.session_state["mission12_mount_name"] = mission12_equipment.mount_name

                st.session_state["mission12_filters"] = ", ".join(mission12_equipment.filters)

                st.session_state["mission12_observations"] = list(
                    mission12_imported_session.observations
                )

                st.session_state["mission12_observation_counter"] = len(
                    mission12_imported_session.observations
                )

                st.session_state["mission12_current_session"] = mission12_imported_session

                st.success(
                    translate(
                        "log_import_success",
                        language,
                    )
                )

with st.expander(
    translate("log_session_metadata", language),
    expanded=True,
):
    mission12_identity_columns = st.columns(3)

    with mission12_identity_columns[0]:
        mission12_session_id = st.text_input(
            translate("log_session_id", language),
            key="mission12_session_id",
        )

    with mission12_identity_columns[1]:
        mission12_session_title = st.text_input(
            translate(
                "log_session_title",
                language,
            ),
            key="mission12_session_title",
        )

    with mission12_identity_columns[2]:
        mission12_observer = st.text_input(
            translate("log_observer", language),
            key="mission12_observer",
        )

    mission12_location_columns = st.columns(4)

    with mission12_location_columns[0]:
        mission12_location = st.text_input(
            translate("log_location", language),
            key="mission12_location",
        )

    with mission12_location_columns[1]:
        mission12_latitude = st.number_input(
            translate("log_latitude", language),
            min_value=-90.0,
            max_value=90.0,
            step=0.0001,
            format="%.4f",
            key="mission12_latitude",
        )

    with mission12_location_columns[2]:
        mission12_longitude = st.number_input(
            translate("log_longitude", language),
            min_value=-180.0,
            max_value=180.0,
            step=0.0001,
            format="%.4f",
            key="mission12_longitude",
        )

    with mission12_location_columns[3]:
        mission12_elevation = st.number_input(
            translate("log_elevation", language),
            step=1.0,
            format="%.1f",
            key="mission12_elevation",
        )

    mission12_time_columns = st.columns(5)

    with mission12_time_columns[0]:
        mission12_timezone = st.text_input(
            translate("log_timezone", language),
            key="mission12_timezone",
        )

    with mission12_time_columns[1]:
        mission12_start_date = st.date_input(
            translate("log_start_date", language),
            key="mission12_start_date",
        )

    with mission12_time_columns[2]:
        mission12_start_time = st.time_input(
            translate("log_start_time", language),
            key="mission12_start_time",
        )

    with mission12_time_columns[3]:
        mission12_end_date = st.date_input(
            translate("log_end_date", language),
            key="mission12_end_date",
        )

    with mission12_time_columns[4]:
        mission12_end_time = st.time_input(
            translate("log_end_time", language),
            key="mission12_end_time",
        )

    mission12_mode = st.selectbox(
        translate("log_mode", language),
        options=("visual", "imaging", "mixed"),
        format_func=lambda mode_key: translate(
            f"log_mode_{mode_key}",
            language,
        ),
        key="mission12_mode",
    )

with st.expander(translate("log_conditions", language)):
    mission12_condition_columns = st.columns(3)

    with mission12_condition_columns[0]:
        mission12_seeing = st.number_input(
            translate(
                "seeing_arcseconds",
                language,
            ),
            min_value=0.1,
            max_value=20.0,
            step=0.1,
            format="%.1f",
            key="mission12_seeing",
        )

    with mission12_condition_columns[1]:
        mission12_transparency = st.slider(
            translate(
                "log_transparency",
                language,
            ),
            min_value=1,
            max_value=5,
            key="mission12_transparency",
        )

    with mission12_condition_columns[2]:
        mission12_cloud_cover = st.slider(
            translate("cloud_cover", language),
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            format="%.0f%%",
            key="mission12_cloud_cover",
        )

    mission12_general_notes = st.text_area(
        translate("log_general_notes", language),
        key="mission12_general_notes",
    )

with st.expander(translate("log_equipment", language)):
    mission12_equipment_name_columns = st.columns(4)

    with mission12_equipment_name_columns[0]:
        mission12_telescope_name = st.text_input(
            translate(
                "log_telescope_name",
                language,
            ),
            key="mission12_telescope_name",
        )

    with mission12_equipment_name_columns[1]:
        mission12_eyepiece_name = st.text_input(
            translate(
                "log_eyepiece_name",
                language,
            ),
            key="mission12_eyepiece_name",
        )

    with mission12_equipment_name_columns[2]:
        mission12_camera_name = st.text_input(
            translate(
                "log_camera_name",
                language,
            ),
            key="mission12_camera_name",
        )

    with mission12_equipment_name_columns[3]:
        mission12_mount_name = st.text_input(
            translate(
                "log_mount_name",
                language,
            ),
            key="mission12_mount_name",
        )

    mission12_equipment_value_columns = st.columns(3)

    with mission12_equipment_value_columns[0]:
        mission12_aperture = st.number_input(
            translate(
                "telescope_aperture",
                language,
            ),
            min_value=0.0,
            max_value=5000.0,
            step=1.0,
            format="%.1f",
            key="mission12_aperture",
        )

    with mission12_equipment_value_columns[1]:
        mission12_focal_length = st.number_input(
            translate(
                "telescope_focal_length",
                language,
            ),
            min_value=0.0,
            max_value=50_000.0,
            step=10.0,
            format="%.1f",
            key="mission12_focal_length",
        )

    with mission12_equipment_value_columns[2]:
        mission12_pixel_size = st.number_input(
            translate("pixel_size_um", language),
            min_value=0.0,
            max_value=100.0,
            step=0.01,
            format="%.2f",
            key="mission12_pixel_size",
        )

    mission12_filters = st.text_input(
        translate("log_filters", language),
        key="mission12_filters",
    )

st.subheader(translate("log_target_entries", language))

mission12_categories = (
    "galaxy",
    "nebula",
    "cluster",
    "star",
    "double_star",
    "solar_system",
    "moon",
    "deep_sky",
    "other",
)

with st.form(
    "mission12_add_observation_form",
    clear_on_submit=True,
):
    mission12_target_identity_columns = st.columns(3)

    with mission12_target_identity_columns[0]:
        mission12_object_key = st.text_input(translate("log_object_key", language))

    with mission12_target_identity_columns[1]:
        mission12_display_name = st.text_input(translate("log_display_name", language))

    with mission12_target_identity_columns[2]:
        mission12_category = st.selectbox(
            translate("log_category", language),
            options=mission12_categories,
            format_func=lambda category_key: translate(
                f"log_category_{category_key}",
                language,
            ),
        )

    mission12_target_time_columns = st.columns(3)

    with mission12_target_time_columns[0]:
        mission12_observation_date = st.date_input(
            translate(
                "log_observation_date",
                language,
            ),
            value=mission12_start_date,
        )

    with mission12_target_time_columns[1]:
        mission12_observation_start = st.time_input(
            translate(
                "log_observation_start",
                language,
            ),
            value=mission12_start_time,
        )

    with mission12_target_time_columns[2]:
        mission12_observation_end = st.time_input(
            translate(
                "log_observation_end",
                language,
            ),
            value=(
                dt.datetime.combine(
                    mission12_start_date,
                    mission12_start_time,
                )
                + dt.timedelta(minutes=30)
            ).time(),
        )

    mission12_target_result_columns = st.columns(4)

    with mission12_target_result_columns[0]:
        mission12_outcome = st.selectbox(
            translate("log_outcome", language),
            options=(
                "observed",
                "partial",
                "not_observed",
            ),
            format_func=lambda outcome_key: translate(
                f"log_outcome_{outcome_key}",
                language,
            ),
        )

    with mission12_target_result_columns[1]:
        mission12_quality = st.slider(
            translate("log_quality", language),
            min_value=1,
            max_value=5,
            value=3,
        )

    with mission12_target_result_columns[2]:
        mission12_altitude = st.number_input(
            translate("log_altitude", language),
            min_value=-90.0,
            max_value=90.0,
            value=45.0,
            step=1.0,
            format="%.1f",
        )

    with mission12_target_result_columns[3]:
        mission12_exposure = st.number_input(
            translate("log_exposure", language),
            min_value=0.0,
            max_value=86_400.0,
            value=0.0,
            step=1.0,
            format="%.1f",
        )

    mission12_frame_columns = st.columns(2)

    with mission12_frame_columns[0]:
        mission12_frames_captured = st.number_input(
            translate(
                "log_frames_captured",
                language,
            ),
            min_value=0,
            max_value=1_000_000,
            value=0,
            step=1,
        )

    with mission12_frame_columns[1]:
        mission12_frames_accepted = st.number_input(
            translate(
                "log_frames_accepted",
                language,
            ),
            min_value=0,
            max_value=1_000_000,
            value=0,
            step=1,
        )

    mission12_observation_notes = st.text_area(
        translate(
            "log_observation_notes",
            language,
        )
    )

    mission12_add_observation = st.form_submit_button(
        translate(
            "log_add_observation",
            language,
        )
    )

if mission12_add_observation:
    try:
        mission12_log_timezone = get_observation_log_timezone(mission12_timezone)

        mission12_target_start = dt.datetime.combine(
            mission12_observation_date,
            mission12_observation_start,
            tzinfo=mission12_log_timezone,
        )

        mission12_target_end = dt.datetime.combine(
            mission12_observation_date,
            mission12_observation_end,
            tzinfo=mission12_log_timezone,
        )

        if mission12_target_end <= mission12_target_start:
            mission12_target_end += dt.timedelta(days=1)

        mission12_counter = st.session_state["mission12_observation_counter"] + 1

        mission12_existing_ids = {
            observation.observation_id for observation in st.session_state["mission12_observations"]
        }

        mission12_observation_id = f"obs-{mission12_counter:03d}"

        while mission12_observation_id in mission12_existing_ids:
            mission12_counter += 1
            mission12_observation_id = f"obs-{mission12_counter:03d}"

        mission12_new_observation = TargetObservation(
            observation_id=(mission12_observation_id),
            object_key=mission12_object_key,
            display_name=(mission12_display_name),
            category=mission12_category,
            started_at_local=(mission12_target_start),
            ended_at_local=(mission12_target_end),
            outcome=mission12_outcome,
            quality_rating=int(mission12_quality),
            altitude_degrees=float(mission12_altitude),
            notes=mission12_observation_notes,
            exposure_seconds=float(mission12_exposure),
            frames_captured=int(mission12_frames_captured),
            frames_accepted=int(mission12_frames_accepted),
        )
    except ValueError as error:
        st.error(f"{translate('log_validation_error', language)}: {error}")
    else:
        st.session_state["mission12_observations"].append(mission12_new_observation)

        st.session_state["mission12_observation_counter"] = mission12_counter

        st.session_state["mission12_current_session"] = None

        st.success(
            translate(
                "log_observation_added",
                language,
            )
        )

mission12_observations = st.session_state["mission12_observations"]

if mission12_observations:
    mission12_remove_id = st.selectbox(
        translate(
            "log_remove_observation",
            language,
        ),
        options=tuple(observation.observation_id for observation in mission12_observations),
        format_func=lambda observation_id: next(
            (
                f"{observation.display_name} ({observation_id})"
                for observation in mission12_observations
                if (observation.observation_id == observation_id)
            ),
            observation_id,
        ),
        key="mission12_remove_id",
    )

    mission12_remove_columns = st.columns(2)

    with mission12_remove_columns[0]:
        mission12_remove_button = st.button(
            translate(
                "log_remove_observation",
                language,
            ),
            key="mission12_remove_button",
            width="stretch",
        )

    with mission12_remove_columns[1]:
        mission12_clear_button = st.button(
            translate(
                "log_clear_observations",
                language,
            ),
            key="mission12_clear_button",
            width="stretch",
        )

    if mission12_remove_button:
        st.session_state["mission12_observations"] = [
            observation
            for observation in mission12_observations
            if (observation.observation_id != mission12_remove_id)
        ]

        st.session_state["mission12_current_session"] = None

        st.success(
            translate(
                "log_observation_removed",
                language,
            )
        )

    if mission12_clear_button:
        st.session_state["mission12_observations"] = []

        st.session_state["mission12_current_session"] = None

        st.success(
            translate(
                "log_observations_cleared",
                language,
            )
        )

mission12_observations = st.session_state["mission12_observations"]

if mission12_observations:
    mission12_observation_rows = []

    for mission12_observation in mission12_observations:
        mission12_category_key = mission12_observation.category

        if mission12_category_key in mission12_categories:
            mission12_category_name = translate(
                (f"log_category_{mission12_category_key}"),
                language,
            )
        else:
            mission12_category_name = mission12_category_key

        mission12_observation_rows.append(
            {
                "object": (mission12_observation.display_name),
                "category": (mission12_category_name),
                "start": (mission12_observation.started_at_local.strftime("%Y-%m-%d %H:%M")),
                "end": (mission12_observation.ended_at_local.strftime("%Y-%m-%d %H:%M")),
                "outcome": translate(
                    (f"log_outcome_{mission12_observation.outcome}"),
                    language,
                ),
                "quality": (mission12_observation.quality_rating),
                "altitude": (mission12_observation.altitude_degrees),
                "exposure": (mission12_observation.exposure_seconds),
                "captured": (mission12_observation.frames_captured),
                "accepted": (mission12_observation.frames_accepted),
                "notes": (mission12_observation.notes),
            }
        )

    st.dataframe(
        mission12_observation_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "object": translate(
                "log_display_name",
                language,
            ),
            "category": translate(
                "log_category",
                language,
            ),
            "start": translate(
                "log_observation_start",
                language,
            ),
            "end": translate(
                "log_observation_end",
                language,
            ),
            "outcome": translate(
                "log_outcome",
                language,
            ),
            "quality": translate(
                "log_quality",
                language,
            ),
            "altitude": (
                st.column_config.NumberColumn(
                    translate(
                        "log_altitude",
                        language,
                    ),
                    format="%.1f°",
                )
            ),
            "exposure": (
                st.column_config.NumberColumn(
                    translate(
                        "log_exposure",
                        language,
                    ),
                    format="%.1f s",
                )
            ),
            "captured": translate(
                "log_frames_captured",
                language,
            ),
            "accepted": translate(
                "log_frames_accepted",
                language,
            ),
            "notes": translate(
                "log_observation_notes",
                language,
            ),
        },
    )
else:
    st.info(
        translate(
            "log_no_observations",
            language,
        )
    )


def build_mission12_session() -> ObservationSession:
    """Build the current logbook session."""

    mission12_log_timezone = get_observation_log_timezone(mission12_timezone)

    mission12_session_start = dt.datetime.combine(
        mission12_start_date,
        mission12_start_time,
        tzinfo=mission12_log_timezone,
    )

    mission12_session_end = dt.datetime.combine(
        mission12_end_date,
        mission12_end_time,
        tzinfo=mission12_log_timezone,
    )

    mission12_filter_values = tuple(
        filter_name.strip() for filter_name in mission12_filters.split(",") if filter_name.strip()
    )

    mission12_equipment_snapshot = EquipmentSnapshot(
        telescope_name=(mission12_telescope_name),
        aperture_mm=(None if mission12_aperture == 0.0 else float(mission12_aperture)),
        focal_length_mm=(None if mission12_focal_length == 0.0 else float(mission12_focal_length)),
        eyepiece_name=(mission12_eyepiece_name),
        camera_name=mission12_camera_name,
        pixel_size_um=(None if mission12_pixel_size == 0.0 else float(mission12_pixel_size)),
        mount_name=mission12_mount_name,
        filters=mission12_filter_values,
    )

    return ObservationSession(
        session_id=mission12_session_id,
        title=mission12_session_title,
        observer=mission12_observer,
        location_name=mission12_location,
        latitude_degrees=float(mission12_latitude),
        longitude_degrees=float(mission12_longitude),
        elevation_m=float(mission12_elevation),
        timezone_name=mission12_timezone,
        started_at_local=mission12_session_start,
        ended_at_local=mission12_session_end,
        mode=mission12_mode,
        equipment=mission12_equipment_snapshot,
        observations=tuple(st.session_state["mission12_observations"]),
        seeing_arcseconds=float(mission12_seeing),
        transparency_rating=int(mission12_transparency),
        cloud_cover_percent=float(mission12_cloud_cover),
        general_notes=mission12_general_notes,
    )


mission12_build_button = st.button(
    translate("log_build_session", language),
    type="primary",
    key="mission12_build_button",
    width="stretch",
)

if mission12_build_button:
    try:
        mission12_built_session = build_mission12_session()
    except ValueError as error:
        st.error(f"{translate('log_validation_error', language)}: {error}")
    else:
        st.session_state["mission12_current_session"] = mission12_built_session

        st.success(
            translate(
                "log_session_ready",
                language,
            )
        )

st.caption(translate("log_rebuild_note", language))

mission12_current_session = st.session_state.get("mission12_current_session")

if mission12_current_session is not None:
    mission12_summary = calculate_session_summary(mission12_current_session)

    st.subheader(translate("log_summary", language))

    mission12_summary_columns = st.columns(6)

    mission12_summary_columns[0].metric(
        translate(
            "log_session_duration",
            language,
        ),
        (f"{mission12_summary.session_duration_minutes:.1f} min"),
    )

    mission12_summary_columns[1].metric(
        translate(
            "log_observation_count",
            language,
        ),
        mission12_summary.observation_count,
    )

    mission12_summary_columns[2].metric(
        translate("log_completion", language),
        (f"{mission12_summary.weighted_completion_percent:.1f}%"),
    )

    mission12_summary_columns[3].metric(
        translate(
            "log_average_quality",
            language,
        ),
        (f"{mission12_summary.average_quality_rating:.2f}/5"),
    )

    mission12_summary_columns[4].metric(
        translate(
            "log_frame_acceptance",
            language,
        ),
        (f"{mission12_summary.frame_acceptance_percent:.1f}%"),
    )

    mission12_summary_columns[5].metric(
        translate("log_integration", language),
        (f"{mission12_summary.accepted_integration_seconds:.1f} s"),
    )

    mission12_mode_names = {
        mode_key: translate(
            f"log_mode_{mode_key}",
            language,
        )
        for mode_key in (
            "visual",
            "imaging",
            "mixed",
        )
    }

    mission12_outcome_names = {
        outcome_key: translate(
            f"log_outcome_{outcome_key}",
            language,
        )
        for outcome_key in (
            "observed",
            "partial",
            "not_observed",
        )
    }

    mission12_category_names = {
        category_key: translate(
            f"log_category_{category_key}",
            language,
        )
        for category_key in mission12_categories
    }

    mission12_report_labels = ObservationReportLabels(
        title=translate(
            "log_report_title",
            language,
        ),
        session_details=translate(
            "log_report_session_details",
            language,
        ),
        conditions=translate(
            "log_conditions",
            language,
        ),
        equipment=translate(
            "log_equipment",
            language,
        ),
        observations=translate(
            "log_report_observations",
            language,
        ),
        summary=translate(
            "log_summary",
            language,
        ),
        session_id=translate(
            "log_session_id",
            language,
        ),
        observer=translate(
            "log_observer",
            language,
        ),
        location=translate(
            "log_location",
            language,
        ),
        mode=translate(
            "log_mode",
            language,
        ),
        start=translate(
            "log_start_time",
            language,
        ),
        end=translate(
            "log_end_time",
            language,
        ),
        session_duration=translate(
            "log_session_duration",
            language,
        ),
        seeing=translate(
            "seeing_arcseconds",
            language,
        ),
        transparency=translate(
            "log_transparency",
            language,
        ),
        cloud_cover=translate(
            "cloud_cover",
            language,
        ),
        telescope=translate(
            "log_telescope_name",
            language,
        ),
        aperture=translate(
            "telescope_aperture",
            language,
        ),
        focal_length=translate(
            "telescope_focal_length",
            language,
        ),
        eyepiece=translate(
            "log_eyepiece_name",
            language,
        ),
        camera=translate(
            "log_camera_name",
            language,
        ),
        pixel_size=translate(
            "pixel_size_um",
            language,
        ),
        mount=translate(
            "log_mount_name",
            language,
        ),
        filters=translate(
            "log_filters",
            language,
        ),
        object_name=translate(
            "log_display_name",
            language,
        ),
        category=translate(
            "log_category",
            language,
        ),
        observation_time=translate(
            "log_observation_start",
            language,
        ),
        duration_minutes=translate(
            "log_duration_minutes",
            language,
        ),
        outcome=translate(
            "log_outcome",
            language,
        ),
        quality=translate(
            "log_quality",
            language,
        ),
        altitude=translate(
            "log_altitude",
            language,
        ),
        exposure=translate(
            "log_exposure",
            language,
        ),
        frames=(
            f"{translate('log_frames_accepted', language)}"
            "/"
            f"{translate('log_frames_captured', language)}"
        ),
        accepted_integration=translate(
            "log_integration",
            language,
        ),
        notes=translate(
            "log_observation_notes",
            language,
        ),
        no_observations=translate(
            "log_report_no_observations",
            language,
        ),
        observation_count=translate(
            "log_observation_count",
            language,
        ),
        completion=translate(
            "log_completion",
            language,
        ),
        average_quality=translate(
            "log_average_quality",
            language,
        ),
        target_time=translate(
            "log_target_time",
            language,
        ),
        frame_acceptance=translate(
            "log_frame_acceptance",
            language,
        ),
        not_recorded=translate(
            "log_not_recorded",
            language,
        ),
    )

    mission12_json_text = session_to_json(mission12_current_session)

    mission12_csv_text = session_observations_to_csv(mission12_current_session)

    mission12_markdown_report = create_markdown_report(
        mission12_current_session,
        labels=mission12_report_labels,
        mode_names=mission12_mode_names,
        outcome_names=(mission12_outcome_names),
        category_names=(mission12_category_names),
    )

    mission12_safe_filename = "".join(
        character if (character.isalnum() or character in {"-", "_"}) else "_"
        for character in (mission12_current_session.session_id)
    ).strip("_")

    if not mission12_safe_filename:
        mission12_safe_filename = "observation_session"

    st.subheader(translate("log_exports", language))

    mission12_download_columns = st.columns(3)

    with mission12_download_columns[0]:
        st.download_button(
            translate(
                "log_download_json",
                language,
            ),
            data=mission12_json_text,
            file_name=(f"{mission12_safe_filename}.json"),
            mime="application/json",
            key="mission12_download_json",
            width="stretch",
        )

    with mission12_download_columns[1]:
        st.download_button(
            translate(
                "log_download_csv",
                language,
            ),
            data=mission12_csv_text,
            file_name=(f"{mission12_safe_filename}.csv"),
            mime="text/csv",
            key="mission12_download_csv",
            width="stretch",
        )

    with mission12_download_columns[2]:
        st.download_button(
            translate(
                "log_download_markdown",
                language,
            ),
            data=mission12_markdown_report,
            file_name=(f"{mission12_safe_filename}.md"),
            mime="text/markdown",
            key="mission12_download_markdown",
            width="stretch",
        )

    with st.expander(
        translate(
            "log_report_preview",
            language,
        ),
        expanded=True,
    ):
        st.markdown(mission12_markdown_report)


render_gaia_dashboard(language)
render_exoplanet_dashboard(language)

render_transit_schedule_dashboard(language)

st.markdown(f"## {translate('future_features', language)}")

st.markdown(
    "\n".join(
        [
            f"- {translate('feature_visibility', language)}",
            f"- {translate('feature_planetarium', language)}",
            f"- {translate('feature_telescope', language)}",
        ]
    )
)

# Mission 15: Exoplanet transit scheduler
