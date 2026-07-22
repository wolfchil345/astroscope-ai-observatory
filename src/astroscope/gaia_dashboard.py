"""Streamlit interface for the Gaia DR3 catalogue explorer."""

from collections.abc import Sequence

import streamlit as st

from astroscope.gaia_catalog import (
    GaiaCatalogError,
    GaiaConeSearchRequest,
    GaiaSearchResult,
    GaiaServiceError,
    GaiaSource,
    fetch_gaia_sources,
)
from astroscope.gaia_export import (
    gaia_sources_to_csv,
)
from astroscope.gaia_visuals import (
    GaiaChartLabels,
    create_hr_diagram,
    create_local_sky_figure,
    create_proper_motion_figure,
)
from astroscope.i18n import translate


def _optional_text(
    value: float | None,
    *,
    digits: int,
    suffix: str,
) -> str:
    """Format one optional catalogue value."""

    if value is None:
        return "N/A"

    return f"{value:.{digits}f}{suffix}"


def _source_table_rows(
    sources: Sequence[GaiaSource],
) -> list[dict[str, object]]:
    """Convert Gaia sources into table rows."""

    return [
        {
            "designation": source.designation,
            "source_id": str(source.source_id),
            "ra": source.ra_deg,
            "dec": source.dec_deg,
            "distance": (source.angular_distance_deg * 60.0),
            "g": source.phot_g_mean_mag,
            "bp_rp": source.bp_rp_mag,
            "parallax": source.parallax_mas,
            "parallax_snr": (source.parallax_snr),
            "pmra": source.pmra_mas_per_year,
            "pmdec": source.pmdec_mas_per_year,
            "total_pm": (source.proper_motion_total_mas_per_year),
            "distance_pc": (source.naive_distance_parsecs),
            "absolute_g": (source.absolute_g_magnitude),
        }
        for source in sources
    ]


def _chart_labels(
    language: str,
) -> GaiaChartLabels:
    """Create translated Gaia chart labels."""

    return GaiaChartLabels(
        local_sky_title=translate(
            "gaia_local_sky",
            language,
        ),
        hr_diagram_title=translate(
            "gaia_hr_diagram",
            language,
        ),
        proper_motion_title=translate(
            "gaia_proper_motion",
            language,
        ),
        ra_offset=translate(
            "gaia_ra_offset",
            language,
        ),
        dec_offset=translate(
            "gaia_dec_offset",
            language,
        ),
        color_index=translate(
            "gaia_bp_rp",
            language,
        ),
        absolute_g=translate(
            "gaia_absolute_g",
            language,
        ),
        pmra=translate(
            "gaia_pmra",
            language,
        ),
        pmdec=translate(
            "gaia_pmdec",
            language,
        ),
        designation=translate(
            "gaia_designation",
            language,
        ),
        source_id=translate(
            "gaia_source_id",
            language,
        ),
        g_magnitude=translate(
            "gaia_g_mag",
            language,
        ),
        angular_distance=translate(
            "gaia_angular_distance",
            language,
        ),
        naive_distance=translate(
            "gaia_naive_distance",
            language,
        ),
        catalog_sources=translate(
            "gaia_source_count",
            language,
        ),
        missing_color=translate(
            "gaia_missing_color",
            language,
        ),
        no_data=translate(
            "gaia_no_chart_data",
            language,
        ),
    )


def _source_label(
    source: GaiaSource,
) -> str:
    """Create a compact source selector label."""

    magnitude = _optional_text(
        source.phot_g_mean_mag,
        digits=2,
        suffix="",
    )

    return f"{source.designation} (G={magnitude})"


def _display_source_details(
    source: GaiaSource,
    *,
    language: str,
) -> None:
    """Display detailed information for one source."""

    st.markdown(f"### {source.designation}")

    primary_columns = st.columns(4)

    primary_columns[0].metric(
        translate("gaia_source_id", language),
        str(source.source_id),
    )

    primary_columns[1].metric(
        translate("gaia_g_mag", language),
        _optional_text(
            source.phot_g_mean_mag,
            digits=3,
            suffix=" mag",
        ),
    )

    primary_columns[2].metric(
        translate("gaia_bp_rp", language),
        _optional_text(
            source.bp_rp_mag,
            digits=3,
            suffix=" mag",
        ),
    )

    primary_columns[3].metric(
        translate(
            "gaia_angular_distance",
            language,
        ),
        (f"{source.angular_distance_deg * 60.0:.3f} arcmin"),
    )

    astrometry_columns = st.columns(4)

    astrometry_columns[0].metric(
        translate("gaia_parallax", language),
        _optional_text(
            source.parallax_mas,
            digits=4,
            suffix=" mas",
        ),
    )

    astrometry_columns[1].metric(
        translate(
            "gaia_parallax_snr",
            language,
        ),
        _optional_text(
            source.parallax_snr,
            digits=3,
            suffix="",
        ),
    )

    astrometry_columns[2].metric(
        translate("gaia_pmra", language),
        _optional_text(
            source.pmra_mas_per_year,
            digits=3,
            suffix=" mas/yr",
        ),
    )

    astrometry_columns[3].metric(
        translate("gaia_pmdec", language),
        _optional_text(
            source.pmdec_mas_per_year,
            digits=3,
            suffix=" mas/yr",
        ),
    )

    physical_columns = st.columns(4)

    physical_columns[0].metric(
        translate("gaia_total_pm", language),
        _optional_text(
            source.proper_motion_total_mas_per_year,
            digits=3,
            suffix=" mas/yr",
        ),
    )

    physical_columns[1].metric(
        translate(
            "gaia_radial_velocity",
            language,
        ),
        _optional_text(
            source.radial_velocity_km_per_s,
            digits=3,
            suffix=" km/s",
        ),
    )

    physical_columns[2].metric(
        translate(
            "gaia_temperature",
            language,
        ),
        _optional_text(
            source.effective_temperature_k,
            digits=0,
            suffix=" K",
        ),
    )

    physical_columns[3].metric(
        translate(
            "gaia_naive_distance",
            language,
        ),
        _optional_text(
            source.naive_distance_parsecs,
            digits=2,
            suffix=" pc",
        ),
    )

    photometry_columns = st.columns(3)

    photometry_columns[0].metric(
        translate("gaia_bp_mag", language),
        _optional_text(
            source.phot_bp_mean_mag,
            digits=3,
            suffix=" mag",
        ),
    )

    photometry_columns[1].metric(
        translate("gaia_rp_mag", language),
        _optional_text(
            source.phot_rp_mean_mag,
            digits=3,
            suffix=" mag",
        ),
    )

    photometry_columns[2].metric(
        translate("gaia_absolute_g", language),
        _optional_text(
            source.absolute_g_magnitude,
            digits=3,
            suffix=" mag",
        ),
    )

    st.caption(f"RA: {source.ra_deg:.8f}° | Dec: {source.dec_deg:.8f}°")


def _display_search_result(
    result: GaiaSearchResult,
    *,
    language: str,
) -> None:
    """Display one completed Gaia search."""

    summary = result.summary

    st.subheader(translate("gaia_results", language))

    if not result.sources:
        st.warning(translate("gaia_no_sources", language))

        with st.expander(
            translate(
                "gaia_adql_preview",
                language,
            )
        ):
            st.code(
                result.adql_query,
                language="sql",
            )

        return

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        translate(
            "gaia_source_count",
            language,
        ),
        summary.source_count,
    )

    summary_columns[1].metric(
        translate("gaia_median_g", language),
        _optional_text(
            summary.median_g_magnitude,
            digits=3,
            suffix=" mag",
        ),
    )

    closest_name = "N/A"

    if summary.nearest_source is not None:
        closest_name = summary.nearest_source.designation

    summary_columns[2].metric(
        translate(
            "gaia_closest_center",
            language,
        ),
        closest_name,
    )

    brightest_name = "N/A"

    if summary.brightest_source is not None:
        brightest_name = summary.brightest_source.designation

    summary_columns[3].metric(
        translate("gaia_brightest", language),
        brightest_name,
    )

    labels = _chart_labels(language)

    sky_tab, hr_tab, motion_tab = st.tabs(
        (
            translate("gaia_local_sky", language),
            translate("gaia_hr_diagram", language),
            translate(
                "gaia_proper_motion",
                language,
            ),
        )
    )

    with sky_tab:
        sky_figure = create_local_sky_figure(
            result.sources,
            center_ra_deg=(result.request.center_ra_deg),
            center_dec_deg=(result.request.center_dec_deg),
            labels=labels,
        )

        st.plotly_chart(
            sky_figure,
            width="stretch",
            key="mission13_local_sky",
        )

    with hr_tab:
        hr_figure = create_hr_diagram(
            result.sources,
            labels=labels,
        )

        st.plotly_chart(
            hr_figure,
            width="stretch",
            key="mission13_hr_diagram",
        )

        st.warning(
            translate(
                "gaia_distance_warning",
                language,
            )
        )

    with motion_tab:
        motion_figure = create_proper_motion_figure(
            result.sources,
            labels=labels,
        )

        st.plotly_chart(
            motion_figure,
            width="stretch",
            key="mission13_proper_motion",
        )

    st.subheader(
        translate(
            "gaia_catalog_table",
            language,
        )
    )

    st.dataframe(
        _source_table_rows(result.sources),
        width="stretch",
        hide_index=True,
        column_config={
            "designation": translate(
                "gaia_designation",
                language,
            ),
            "source_id": translate(
                "gaia_source_id",
                language,
            ),
            "ra": st.column_config.NumberColumn(
                "RA",
                format="%.8f°",
            ),
            "dec": st.column_config.NumberColumn(
                "Dec",
                format="%.8f°",
            ),
            "distance": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_angular_distance",
                        language,
                    ),
                    format="%.3f arcmin",
                )
            ),
            "g": st.column_config.NumberColumn(
                translate("gaia_g_mag", language),
                format="%.3f mag",
            ),
            "bp_rp": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_bp_rp",
                        language,
                    ),
                    format="%.3f mag",
                )
            ),
            "parallax": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_parallax",
                        language,
                    ),
                    format="%.4f mas",
                )
            ),
            "parallax_snr": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_parallax_snr",
                        language,
                    ),
                    format="%.3f",
                )
            ),
            "pmra": st.column_config.NumberColumn(
                translate("gaia_pmra", language),
                format="%.3f mas/yr",
            ),
            "pmdec": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_pmdec",
                        language,
                    ),
                    format="%.3f mas/yr",
                )
            ),
            "total_pm": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_total_pm",
                        language,
                    ),
                    format="%.3f mas/yr",
                )
            ),
            "distance_pc": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_naive_distance",
                        language,
                    ),
                    format="%.2f pc",
                )
            ),
            "absolute_g": (
                st.column_config.NumberColumn(
                    translate(
                        "gaia_absolute_g",
                        language,
                    ),
                    format="%.3f mag",
                )
            ),
        },
    )

    st.subheader(
        translate(
            "gaia_source_details",
            language,
        )
    )

    sources_by_id = {source.source_id: source for source in result.sources}

    selected_source_id = st.selectbox(
        translate(
            "gaia_select_source",
            language,
        ),
        options=tuple(sources_by_id),
        format_func=lambda source_id: _source_label(sources_by_id[source_id]),
        key="mission13_selected_source",
    )

    selected_source = sources_by_id[selected_source_id]

    _display_source_details(
        selected_source,
        language=language,
    )

    export_columns = st.columns(2)

    with export_columns[0]:
        st.download_button(
            translate(
                "gaia_download_csv",
                language,
            ),
            data=gaia_sources_to_csv(result.sources),
            file_name="gaia_dr3_sources.csv",
            mime="text/csv",
            width="stretch",
            key="mission13_download_csv",
        )

    with export_columns[1]:
        with st.expander(
            translate(
                "gaia_adql_preview",
                language,
            )
        ):
            st.code(
                result.adql_query,
                language="sql",
            )

    st.warning(
        translate(
            "gaia_distance_warning",
            language,
        )
    )

    st.caption(
        translate(
            "gaia_attribution",
            language,
        )
    )


def render_gaia_dashboard(
    language: str,
) -> None:
    """Render the complete Gaia catalogue interface."""

    st.divider()

    st.header(f"🛰️ {translate('gaia_section', language)}")

    st.info(
        translate(
            "gaia_explanation",
            language,
        )
    )

    coordinate_columns = st.columns(4)

    with coordinate_columns[0]:
        centre_ra = st.number_input(
            translate("gaia_ra", language),
            min_value=0.0,
            max_value=359.999999,
            value=83.82208,
            step=0.01,
            format="%.6f",
            key="mission13_ra",
        )

    with coordinate_columns[1]:
        centre_dec = st.number_input(
            translate("gaia_dec", language),
            min_value=-90.0,
            max_value=90.0,
            value=-5.39111,
            step=0.01,
            format="%.6f",
            key="mission13_dec",
        )

    with coordinate_columns[2]:
        radius_arcminutes = st.number_input(
            (f"{translate('gaia_radius_arcmin', language)} (arcmin)"),
            min_value=0.1,
            max_value=600.0,
            value=3.0,
            step=0.5,
            format="%.1f",
            key="mission13_radius",
        )

    with coordinate_columns[3]:
        row_limit = st.number_input(
            translate(
                "gaia_row_limit",
                language,
            ),
            min_value=1,
            max_value=5000,
            value=200,
            step=50,
            key="mission13_row_limit",
        )

    filter_columns = st.columns(5)

    with filter_columns[0]:
        apply_g_limit = st.checkbox(
            translate("gaia_limit_g", language),
            value=True,
            key="mission13_apply_g_limit",
        )

    with filter_columns[1]:
        maximum_g = st.number_input(
            translate("gaia_max_g", language),
            min_value=-5.0,
            max_value=30.0,
            value=16.0,
            step=0.5,
            disabled=not apply_g_limit,
            key="mission13_max_g",
        )

    with filter_columns[2]:
        apply_snr_filter = st.checkbox(
            translate(
                "gaia_filter_snr",
                language,
            ),
            value=False,
            key="mission13_apply_snr",
        )

    with filter_columns[3]:
        minimum_snr = st.number_input(
            translate("gaia_min_snr", language),
            min_value=0.0,
            max_value=1000.0,
            value=5.0,
            step=1.0,
            disabled=not apply_snr_filter,
            key="mission13_min_snr",
        )

    with filter_columns[4]:
        timeout_seconds = st.number_input(
            (f"{translate('gaia_timeout', language)} (s)"),
            min_value=1.0,
            max_value=120.0,
            value=30.0,
            step=1.0,
            format="%.0f",
            key="mission13_timeout",
        )

    search_clicked = st.button(
        translate("gaia_search", language),
        type="primary",
        width="stretch",
        key="mission13_search",
    )

    if search_clicked:
        try:
            request = GaiaConeSearchRequest(
                center_ra_deg=float(centre_ra),
                center_dec_deg=float(centre_dec),
                radius_deg=(float(radius_arcminutes) / 60.0),
                row_limit=int(row_limit),
                maximum_g_magnitude=(float(maximum_g) if apply_g_limit else None),
                minimum_parallax_snr=(float(minimum_snr) if apply_snr_filter else None),
                timeout_seconds=float(timeout_seconds),
            )

            with st.spinner(
                translate(
                    "gaia_searching",
                    language,
                )
            ):
                result = fetch_gaia_sources(request)

        except (
            GaiaCatalogError,
            GaiaServiceError,
            ValueError,
        ) as error:
            st.session_state.pop(
                "mission13_gaia_result",
                None,
            )

            st.error(f"{translate('gaia_error', language)}: {error}")

        else:
            st.session_state["mission13_gaia_result"] = result

    stored_result = st.session_state.get("mission13_gaia_result")

    if stored_result is not None:
        _display_search_result(
            stored_result,
            language=language,
        )
