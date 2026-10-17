"""Source-coordinate preview and explicit legacy workflow selection."""

from __future__ import annotations

import streamlit as st

from astroscope.transit_schedule_i18n import translate_transit
from astroscope.transit_timing import (
    CoordinateTransitPrediction,
    EphemerisProvenance,
    EphemerisUncertainty,
    StrictTransitEphemeris,
    TimeCoordinate,
    TransitTimingError,
    UncertaintyComponent,
    coordinate_prediction_to_json,
    predict_coordinate_transit,
)

_PREVIEW_KEY = "mission37_coordinate_prediction"
_LEGACY_KEY = "mission15_transit_schedule_result"


def render_timing_workflow(language: str) -> bool:
    """Return true only after the user explicitly selects and acknowledges legacy timing."""

    def tr(key: str) -> str:
        return translate_transit(key, language)

    mode = st.radio(
        tr("timing_mode"),
        ("strict", "legacy"),
        format_func=lambda value: tr("timing_" + value),
        key="mission37_timing_mode",
    )
    if st.session_state.get("mission37_previous_mode") != mode:
        st.session_state.pop(_LEGACY_KEY, None)
        st.session_state.pop(_PREVIEW_KEY, None)
        st.session_state["mission37_legacy_ack"] = False
        st.session_state["mission37_previous_mode"] = mode
    if mode == "legacy":
        st.warning(tr("timing_legacy_warning"))
        acknowledged = st.checkbox(tr("timing_legacy_ack"), key="mission37_legacy_ack")
        if not acknowledged:
            st.session_state.pop(_LEGACY_KEY, None)
        return acknowledged

    st.caption(tr("timing_preview_caption"))
    with st.form("mission37_preview_form"):
        name = st.text_input(tr("planet_name"), value="Synthetic b", key="mission37_name")
        coordinate = st.selectbox(
            tr("timing_coordinate"),
            ("BJD TDB", "Observer JD TAI", "HJD UTC", "Unknown"),
            format_func=lambda value: (
                tr("timing_unknown")
                if value == "Unknown"
                else tr("timing_observer_tai")
                if value == "Observer JD TAI"
                else value
            ),
            key="mission37_coordinate",
        )
        source = st.text_input(tr("timing_source"), key="mission37_source")
        parameter_set = st.text_input(tr("timing_parameter_set"), key="mission37_parameter_set")
        evidence = st.text_input(tr("timing_evidence"), key="mission37_evidence")
        joint_fit = st.checkbox(tr("timing_joint_fit"), key="mission37_joint_fit")
        epoch = st.text_input(tr("reference_midpoint"), value="2451545.0", key="mission37_epoch")
        period = st.text_input(tr("orbital_period"), value="2.0", key="mission37_period")
        duration = st.text_input(tr("transit_duration"), value="2.0", key="mission37_duration")
        epoch_known = st.checkbox(tr("timing_epoch_known"), key="mission37_epoch_known")
        epoch_sigma = st.text_input(
            tr("epoch_uncertainty"), value="0.001", key="mission37_epoch_sigma"
        )
        period_known = st.checkbox(tr("timing_period_known"), key="mission37_period_known")
        period_sigma = st.text_input(
            tr("period_uncertainty"), value="0.0001", key="mission37_period_sigma"
        )
        zero_covariance = st.checkbox(tr("timing_covariance_zero"), key="mission37_zero_covariance")
        cycle = st.number_input(
            tr("timing_cycle"),
            min_value=-10000,
            max_value=10000,
            value=0,
            step=1,
            key="mission37_cycle",
        )
        submitted = st.form_submit_button(tr("timing_preview_button"))
    if submitted:
        st.session_state.pop(_PREVIEW_KEY, None)
        try:
            scale, position, basis = {
                "BJD TDB": ("tdb", "barycentric", "ephemeris_coordinate"),
                "Observer JD TAI": ("tai", "observer", "observer_elapsed"),
                "HJD UTC": ("utc", "heliocentric", "ephemeris_coordinate"),
                "Unknown": ("unknown", "unknown", "ephemeris_coordinate"),
            }[coordinate]
            ephemeris = StrictTransitEphemeris(
                name,
                epoch,
                period,
                duration,
                TimeCoordinate("jd", scale, position, coordinate),
                EphemerisProvenance(source, parameter_set, evidence, evidence, evidence, joint_fit),
                EphemerisUncertainty(
                    UncertaintyComponent(epoch_sigma if epoch_known else None, evidence),
                    UncertaintyComponent(period_sigma if period_known else None, evidence),
                    zero_covariance_assumption=(
                        "User explicitly assumes zero epoch-period covariance"
                        if zero_covariance
                        else None
                    ),
                ),
                duration_basis=basis,
            )
            st.session_state[_PREVIEW_KEY] = predict_coordinate_transit(ephemeris, int(cycle))
        except TransitTimingError:
            st.error(tr("timing_invalid"))
    prediction = st.session_state.get(_PREVIEW_KEY)
    if isinstance(prediction, CoordinateTransitPrediction):
        st.metric(tr("timing_midpoint"), prediction.midpoint_jd_decimal)
        st.metric(
            tr("timing_sigma"), prediction.timing_uncertainty.value_days or tr("timing_unknown")
        )
        st.info(tr("timing_ineligible"))
        st.caption(tr("timing_validity"))
        st.download_button(
            tr("timing_download"),
            coordinate_prediction_to_json(prediction),
            file_name="transit_coordinate_prediction.json",
            mime="application/json",
            key="mission37_download_prediction",
        )
    return False
