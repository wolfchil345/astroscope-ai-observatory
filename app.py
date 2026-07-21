"""Main Streamlit entry point for AstroScope AI."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

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
from astroscope.visibility import calculate_horizontal_coordinates

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
