"""Main Streamlit entry point for AstroScope AI."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st

from astroscope.coordinates import (
    CELESTIAL_PRESETS,
    calculate_coordinate_details,
)
from astroscope.i18n import SUPPORTED_LANGUAGES, translate
from astroscope.observer import (
    OBSERVER_PRESETS,
    calculate_astronomical_time,
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
