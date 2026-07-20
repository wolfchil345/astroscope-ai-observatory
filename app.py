"""Main Streamlit entry point for AstroScope AI."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import streamlit as st
from astroscope.observer import (
    OBSERVER_PRESETS,
    calculate_astronomical_time,
)

from astroscope.i18n import SUPPORTED_LANGUAGES, translate

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

preset_key = st.selectbox(
    translate("observer_preset", language),
    options=list(OBSERVER_PRESETS),
    format_func=lambda key: translate(f"preset_{key}", language),
)

preset = OBSERVER_PRESETS[preset_key]

location_column, time_column = st.columns(2)

with location_column:
    latitude = st.number_input(
        translate("latitude", language),
        min_value=-90.0,
        max_value=90.0,
        value=float(preset.latitude_deg),
        step=0.0001,
        format="%.4f",
        key=f"latitude_{preset_key}",
    )

    longitude = st.number_input(
        translate("longitude", language),
        min_value=-180.0,
        max_value=180.0,
        value=float(preset.longitude_deg),
        step=0.0001,
        format="%.4f",
        help=translate("coordinate_help", language),
        key=f"longitude_{preset_key}",
    )

    elevation = st.number_input(
        translate("elevation", language),
        min_value=-500.0,
        max_value=10_000.0,
        value=float(preset.elevation_m),
        step=1.0,
        format="%.1f",
        key=f"elevation_{preset_key}",
    )

with time_column:
    timezone_index = TIMEZONE_OPTIONS.index(preset.timezone_name)

    timezone_name = st.selectbox(
        translate("timezone", language),
        options=TIMEZONE_OPTIONS,
        index=timezone_index,
        key=f"timezone_{preset_key}",
    )

    default_date = datetime.now(ZoneInfo(preset.timezone_name)).date()

    observation_date = st.date_input(
        translate("observation_date", language),
        value=default_date,
    )

    observation_time = st.time_input(
        translate("observation_time", language),
        value=time(21, 0),
    )

calculate_button = st.button(
    translate("calculate_time", language),
    type="primary",
    use_container_width=True,
)

if calculate_button:
    try:
        result = calculate_astronomical_time(
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

        first_row = st.columns(2)

        first_row[0].metric(
            translate("local_datetime", language),
            result.local_datetime_iso,
        )

        first_row[1].metric(
            translate("utc_datetime", language),
            result.utc_datetime_iso,
        )

        second_row = st.columns(3)

        second_row[0].metric(
            translate("julian_date", language),
            f"{result.julian_date:.5f}",
        )

        second_row[1].metric(
            translate("modified_julian_date", language),
            f"{result.modified_julian_date:.5f}",
        )

        second_row[2].metric(
            translate("local_sidereal_time", language),
            result.local_sidereal_time_hms,
        )

        st.caption(translate("result_note", language))

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
