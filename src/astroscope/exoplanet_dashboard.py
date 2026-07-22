"""Streamlit dashboard for the NASA exoplanet explorer."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import streamlit as st

from astroscope.exoplanet_catalog import (
    ExoplanetCatalogError,
    ExoplanetRecord,
    ExoplanetSearchRequest,
    ExoplanetSearchResult,
    ExoplanetServiceError,
    TemperateStatus,
    fetch_exoplanets,
)
from astroscope.exoplanet_export import exoplanets_to_csv
from astroscope.exoplanet_visuals import (
    ExoplanetChartLabels,
    create_climate_figure,
    create_mass_radius_figure,
    create_radius_period_figure,
    create_transit_simulation_figure,
)
from astroscope.i18n import translate

RESULT_STATE_KEY: Final[str] = "mission14_exoplanet_result"

DISCOVERY_METHODS: Final[tuple[str, ...]] = (
    "Transit",
    "Radial Velocity",
    "Imaging",
    "Microlensing",
    "Astrometry",
    "Transit Timing Variations",
    "Eclipse Timing Variations",
)


@dataclass(frozen=True, slots=True)
class OptionalFilterConfig:
    """Configuration for one optional numerical search filter."""

    label_key: str
    widget_key: str
    default: float
    minimum: float
    maximum: float
    step: float
    format_string: str


def _t(
    key: str,
    language: str,
) -> str:
    """Translate one Mission 14 interface key."""

    return translate(key, language)


def _display_number(
    value: float | int | None,
    *,
    digits: int = 2,
    suffix: str = "",
) -> str:
    """Format one optional numerical value."""

    if value is None:
        return "N/A"

    if isinstance(value, int):
        return f"{value}{suffix}"

    return f"{value:.{digits}f}{suffix}"


def _status_names(
    language: str,
) -> dict[TemperateStatus, str]:
    """Return translated temperate-screening labels."""

    return {
        "temperate_terrestrial_candidate": _t(
            "exoplanet_status_temperate_terrestrial",
            language,
        ),
        "temperate_non_terrestrial": _t(
            "exoplanet_status_temperate_non_terrestrial",
            language,
        ),
        "outside_temperate_range": _t(
            "exoplanet_status_outside_temperate",
            language,
        ),
        "insufficient_data": _t(
            "exoplanet_status_insufficient_data",
            language,
        ),
    }


def _chart_labels(
    language: str,
) -> ExoplanetChartLabels:
    """Build translated labels for Plotly figures."""

    return ExoplanetChartLabels(
        radius_period_title=_t(
            "exoplanet_radius_period_title",
            language,
        ),
        mass_radius_title=_t(
            "exoplanet_mass_radius_title",
            language,
        ),
        climate_title=_t(
            "exoplanet_climate_title",
            language,
        ),
        transit_title=_t(
            "exoplanet_transit_title",
            language,
        ),
        orbital_period=_t(
            "exoplanet_orbital_period",
            language,
        ),
        radius=_t(
            "exoplanet_radius",
            language,
        ),
        mass=_t(
            "exoplanet_mass",
            language,
        ),
        equilibrium_temperature=_t(
            "exoplanet_equilibrium_temperature",
            language,
        ),
        insolation=_t(
            "exoplanet_insolation",
            language,
        ),
        transit_time=_t(
            "exoplanet_transit_time",
            language,
        ),
        relative_flux=_t(
            "exoplanet_relative_flux",
            language,
        ),
        planet_name=_t(
            "exoplanet_planet_name",
            language,
        ),
        host_name=_t(
            "exoplanet_host_name",
            language,
        ),
        discovery_method=_t(
            "exoplanet_discovery_method",
            language,
        ),
        temperate_status=_t(
            "exoplanet_temperate_status",
            language,
        ),
        simulated_transit=_t(
            "exoplanet_simulated_transit",
            language,
        ),
        no_data=_t(
            "exoplanet_no_chart_data",
            language,
        ),
    )


def _optional_number_input(
    language: str,
    config: OptionalFilterConfig,
) -> float | None:
    """Render one optional numerical filter."""

    label = _t(
        config.label_key,
        language,
    )

    enabled = st.checkbox(
        (f"{_t('exoplanet_optional_filter', language)}: {label}"),
        value=False,
        key=f"{config.widget_key}_enabled",
    )

    value = st.number_input(
        label,
        min_value=config.minimum,
        max_value=config.maximum,
        value=config.default,
        step=config.step,
        format=config.format_string,
        disabled=not enabled,
        key=config.widget_key,
    )

    if not enabled:
        return None

    return float(value)


def _render_search_form(
    language: str,
) -> ExoplanetSearchRequest | None:
    """Render catalogue filters and return a submitted request."""

    method_options = (
        _t(
            "exoplanet_all_methods",
            language,
        ),
        *DISCOVERY_METHODS,
    )

    with st.expander(
        _t(
            "exoplanet_search_controls",
            language,
        ),
        expanded=True,
    ):
        with st.form("mission14_exoplanet_search_form"):
            first_column, second_column = st.columns(2)

            with first_column:
                row_limit = st.number_input(
                    _t(
                        "exoplanet_row_limit",
                        language,
                    ),
                    min_value=1,
                    max_value=5000,
                    value=200,
                    step=50,
                )

                transiting_only = st.checkbox(
                    _t(
                        "exoplanet_transiting_only",
                        language,
                    ),
                    value=False,
                )

                selected_method = st.selectbox(
                    _t(
                        "exoplanet_discovery_method",
                        language,
                    ),
                    options=method_options,
                )

                maximum_distance = _optional_number_input(
                    language,
                    OptionalFilterConfig(
                        label_key=("exoplanet_max_distance_pc"),
                        widget_key=("mission14_max_distance"),
                        default=100.0,
                        minimum=0.1,
                        maximum=100000.0,
                        step=10.0,
                        format_string="%.1f",
                    ),
                )

            with second_column:
                maximum_radius = _optional_number_input(
                    language,
                    OptionalFilterConfig(
                        label_key=("exoplanet_max_radius_earth"),
                        widget_key=("mission14_max_radius"),
                        default=4.0,
                        minimum=0.1,
                        maximum=100.0,
                        step=0.5,
                        format_string="%.1f",
                    ),
                )

                minimum_temperature = _optional_number_input(
                    language,
                    OptionalFilterConfig(
                        label_key=("exoplanet_min_temperature_k"),
                        widget_key=("mission14_min_temperature"),
                        default=180.0,
                        minimum=1.0,
                        maximum=10000.0,
                        step=10.0,
                        format_string="%.1f",
                    ),
                )

                maximum_temperature = _optional_number_input(
                    language,
                    OptionalFilterConfig(
                        label_key=("exoplanet_max_temperature_k"),
                        widget_key=("mission14_max_temperature"),
                        default=310.0,
                        minimum=1.0,
                        maximum=10000.0,
                        step=10.0,
                        format_string="%.1f",
                    ),
                )

                timeout_seconds = st.number_input(
                    _t(
                        "exoplanet_timeout_seconds",
                        language,
                    ),
                    min_value=1.0,
                    max_value=120.0,
                    value=30.0,
                    step=1.0,
                    format="%.0f",
                )

            submitted = st.form_submit_button(
                _t(
                    "exoplanet_search_button",
                    language,
                )
            )

    if not submitted:
        return None

    discovery_method = None

    if selected_method != method_options[0]:
        discovery_method = selected_method

    try:
        return ExoplanetSearchRequest(
            row_limit=int(row_limit),
            transiting_only=bool(transiting_only),
            discovery_method=discovery_method,
            maximum_distance_pc=(maximum_distance),
            maximum_planet_radius_earth=(maximum_radius),
            minimum_equilibrium_temperature_k=(minimum_temperature),
            maximum_equilibrium_temperature_k=(maximum_temperature),
            timeout_seconds=float(timeout_seconds),
        )
    except ExoplanetCatalogError as error:
        st.error(f"{_t('exoplanet_search_error', language)} {error}")

        return None


def _run_search(
    request: ExoplanetSearchRequest,
    language: str,
) -> None:
    """Execute a submitted archive query."""

    try:
        with st.spinner(
            _t(
                "exoplanet_searching",
                language,
            )
        ):
            result = fetch_exoplanets(request)

    except (
        ExoplanetCatalogError,
        ExoplanetServiceError,
    ) as error:
        st.session_state.pop(
            RESULT_STATE_KEY,
            None,
        )

        st.error(f"{_t('exoplanet_search_error', language)} {error}")

        return

    st.session_state[RESULT_STATE_KEY] = result


def _summary_planet_text(
    planet: ExoplanetRecord | None,
    *,
    value: float | None,
    suffix: str,
) -> str:
    """Format one summary highlight."""

    if planet is None:
        return "N/A"

    value_text = _display_number(
        value,
        digits=2,
        suffix=suffix,
    )

    return f"{planet.planet_name} · {value_text}"


def _render_summary(
    result: ExoplanetSearchResult,
    language: str,
) -> None:
    """Render catalogue summary metrics."""

    summary = result.summary

    columns = st.columns(4)

    columns[0].metric(
        _t(
            "exoplanet_planet_count",
            language,
        ),
        summary.planet_count,
    )

    columns[1].metric(
        _t(
            "exoplanet_transiting_count",
            language,
        ),
        summary.transiting_count,
    )

    columns[2].metric(
        _t(
            "exoplanet_temperate_candidates",
            language,
        ),
        summary.temperate_candidate_count,
    )

    columns[3].metric(
        _t(
            "exoplanet_median_radius",
            language,
        ),
        _display_number(
            summary.median_radius_earth,
            digits=2,
            suffix=" R⊕",
        ),
    )

    nearest_text = _summary_planet_text(
        summary.nearest_planet,
        value=(None if summary.nearest_planet is None else summary.nearest_planet.distance_pc),
        suffix=" pc",
    )

    smallest_text = _summary_planet_text(
        summary.smallest_planet,
        value=(None if summary.smallest_planet is None else summary.smallest_planet.radius_earth),
        suffix=" R⊕",
    )

    st.caption(f"**{_t('exoplanet_nearest_planet', language)}:** {nearest_text}")

    st.caption(f"**{_t('exoplanet_smallest_planet', language)}:** {smallest_text}")


def _table_rows(
    planets: Sequence[ExoplanetRecord],
    language: str,
) -> list[dict[str, object]]:
    """Convert planets into localized table rows."""

    names = _status_names(language)

    return [
        {
            _t(
                "exoplanet_planet_name",
                language,
            ): planet.planet_name,
            _t(
                "exoplanet_host_name",
                language,
            ): planet.hostname,
            _t(
                "exoplanet_discovery_method",
                language,
            ): planet.discovery_method,
            _t(
                "exoplanet_discovery_year",
                language,
            ): planet.discovery_year,
            _t(
                "exoplanet_orbital_period",
                language,
            ): planet.orbital_period_days,
            _t(
                "exoplanet_radius",
                language,
            ): planet.radius_earth,
            _t(
                "exoplanet_mass",
                language,
            ): planet.mass_earth,
            _t(
                "exoplanet_equilibrium_temperature",
                language,
            ): planet.equilibrium_temperature_k,
            _t(
                "exoplanet_distance",
                language,
            ): planet.distance_pc,
            _t(
                "exoplanet_temperate_status",
                language,
            ): names[planet.temperate_status],
        }
        for planet in planets
    ]


def _render_population_charts(
    planets: Sequence[ExoplanetRecord],
    language: str,
) -> None:
    """Render the three exoplanet population diagrams."""

    labels = _chart_labels(language)
    names = _status_names(language)

    radius_tab, mass_tab, climate_tab = st.tabs(
        [
            _t(
                "exoplanet_radius_period_tab",
                language,
            ),
            _t(
                "exoplanet_mass_radius_tab",
                language,
            ),
            _t(
                "exoplanet_climate_tab",
                language,
            ),
        ]
    )

    with radius_tab:
        st.plotly_chart(
            create_radius_period_figure(
                planets,
                labels=labels,
                status_names=names,
            ),
            width="stretch",
            key="mission14_radius_period_chart",
        )

    with mass_tab:
        st.plotly_chart(
            create_mass_radius_figure(
                planets,
                labels=labels,
                status_names=names,
            ),
            width="stretch",
            key="mission14_mass_radius_chart",
        )

    with climate_tab:
        st.plotly_chart(
            create_climate_figure(
                planets,
                labels=labels,
                status_names=names,
            ),
            width="stretch",
            key="mission14_climate_chart",
        )


def _find_planet(
    planets: Sequence[ExoplanetRecord],
    planet_name: str,
) -> ExoplanetRecord:
    """Return one selected planet."""

    return next(planet for planet in planets if planet.planet_name == planet_name)


def _render_transit_simulator(
    planets: Sequence[ExoplanetRecord],
    language: str,
) -> None:
    """Render an educational transit light-curve simulator."""

    selected_name = st.selectbox(
        _t(
            "exoplanet_select_planet",
            language,
        ),
        options=[planet.planet_name for planet in planets],
        key="mission14_transit_planet",
    )

    selected_planet = _find_planet(
        planets,
        selected_name,
    )

    default_depth = (
        selected_planet.transit_depth_ppm
        if (
            selected_planet.transit_depth_ppm is not None
            and selected_planet.transit_depth_ppm > 0.0
        )
        else 1000.0
    )

    first_column, second_column, third_column = st.columns(3)

    with first_column:
        depth_ppm = st.number_input(
            _t(
                "exoplanet_transit_depth",
                language,
            ),
            min_value=0.1,
            max_value=1_000_000.0,
            value=float(default_depth),
            step=10.0,
            format="%.1f",
        )

    with second_column:
        duration_hours = st.number_input(
            _t(
                "exoplanet_transit_duration",
                language,
            ),
            min_value=0.1,
            max_value=72.0,
            value=3.0,
            step=0.25,
            format="%.2f",
        )

    with third_column:
        ingress_fraction = st.number_input(
            _t(
                "exoplanet_ingress_fraction",
                language,
            ),
            min_value=0.01,
            max_value=0.49,
            value=0.15,
            step=0.01,
            format="%.2f",
        )

    figure = create_transit_simulation_figure(
        depth_ppm=float(depth_ppm),
        duration_hours=float(duration_hours),
        ingress_fraction=float(ingress_fraction),
        labels=_chart_labels(language),
    )

    st.plotly_chart(
        figure,
        width="stretch",
        key="mission14_transit_chart",
    )

    st.info(
        _t(
            "exoplanet_simulator_note",
            language,
        )
    )


def _render_planet_inspector(
    planets: Sequence[ExoplanetRecord],
    language: str,
) -> None:
    """Render detailed values for one selected planet."""

    selected_name = st.selectbox(
        _t(
            "exoplanet_select_planet",
            language,
        ),
        options=[planet.planet_name for planet in planets],
        key="mission14_inspector_planet",
    )

    planet = _find_planet(
        planets,
        selected_name,
    )

    first_row = st.columns(4)

    first_row[0].metric(
        _t(
            "exoplanet_radius",
            language,
        ),
        _display_number(
            planet.radius_earth,
            suffix=" R⊕",
        ),
    )

    first_row[1].metric(
        _t(
            "exoplanet_mass",
            language,
        ),
        _display_number(
            planet.mass_earth,
            suffix=" M⊕",
        ),
    )

    first_row[2].metric(
        _t(
            "exoplanet_density",
            language,
        ),
        _display_number(
            planet.density_g_cm3,
            suffix=" g/cm³",
        ),
    )

    first_row[3].metric(
        _t(
            "exoplanet_distance",
            language,
        ),
        _display_number(
            planet.distance_pc,
            suffix=" pc",
        ),
    )

    second_row = st.columns(4)

    second_row[0].metric(
        _t(
            "exoplanet_orbital_period",
            language,
        ),
        _display_number(
            planet.orbital_period_days,
            digits=3,
            suffix=" d",
        ),
    )

    second_row[1].metric(
        _t(
            "exoplanet_semi_major_axis",
            language,
        ),
        _display_number(
            planet.semi_major_axis_au,
            digits=3,
            suffix=" AU",
        ),
    )

    second_row[2].metric(
        _t(
            "exoplanet_transit_depth",
            language,
        ),
        _display_number(
            planet.transit_depth_ppm,
            digits=1,
            suffix=" ppm",
        ),
    )

    second_row[3].metric(
        _t(
            "exoplanet_transit_probability",
            language,
        ),
        _display_number(
            planet.transit_probability_percent,
            digits=2,
            suffix="%",
        ),
    )

    status_label = _status_names(language)[planet.temperate_status]

    st.markdown(f"**{_t('exoplanet_host_name', language)}:** {planet.hostname}")

    st.markdown(
        f"**{_t('exoplanet_discovery_method', language)}:** {planet.discovery_method or 'N/A'}"
    )

    st.markdown(f"**{_t('exoplanet_discovery_year', language)}:** {planet.discovery_year or 'N/A'}")

    st.markdown(f"**{_t('exoplanet_temperate_status', language)}:** {status_label}")

    st.warning(
        _t(
            "exoplanet_calculation_warning",
            language,
        )
    )


def _render_export(
    result: ExoplanetSearchResult,
    language: str,
) -> None:
    """Render CSV download and archive query preview."""

    csv_bytes = exoplanets_to_csv(result.planets).encode("utf-8-sig")

    st.download_button(
        _t(
            "exoplanet_download_csv",
            language,
        ),
        data=csv_bytes,
        file_name=("astroscope_exoplanet_catalog.csv"),
        mime="text/csv",
        width="stretch",
    )

    with st.expander(
        _t(
            "exoplanet_adql_query",
            language,
        )
    ):
        st.code(
            result.adql_query,
            language="sql",
        )


def _render_result_tabs(
    result: ExoplanetSearchResult,
    language: str,
) -> None:
    """Render catalogue results and scientific tools."""

    planets = result.planets

    population_tab, transit_tab, table_tab = st.tabs(
        [
            _t(
                "exoplanet_results",
                language,
            ),
            _t(
                "exoplanet_transit_tab",
                language,
            ),
            _t(
                "exoplanet_table_tab",
                language,
            ),
        ]
    )

    with population_tab:
        _render_population_charts(
            planets,
            language,
        )

    with transit_tab:
        _render_transit_simulator(
            planets,
            language,
        )

    with table_tab:
        st.dataframe(
            _table_rows(
                planets,
                language,
            ),
            hide_index=True,
            width="stretch",
        )

    inspector_tab, export_tab = st.tabs(
        [
            _t(
                "exoplanet_inspector_tab",
                language,
            ),
            _t(
                "exoplanet_export_tab",
                language,
            ),
        ]
    )

    with inspector_tab:
        _render_planet_inspector(
            planets,
            language,
        )

    with export_tab:
        _render_export(
            result,
            language,
        )


def _stored_result() -> ExoplanetSearchResult | None:
    """Return the current session result when valid."""

    result = st.session_state.get(RESULT_STATE_KEY)

    if isinstance(
        result,
        ExoplanetSearchResult,
    ):
        return result

    return None


def render_exoplanet_dashboard(
    language: str,
) -> None:
    """Render the complete Mission 14 dashboard."""

    st.divider()

    st.markdown(f"## 🪐 {_t('exoplanet_title', language)}")

    st.write(
        _t(
            "exoplanet_subtitle",
            language,
        )
    )

    st.info(
        _t(
            "exoplanet_archive_note",
            language,
        )
    )

    request = _render_search_form(language)

    if request is not None:
        _run_search(
            request,
            language,
        )

    result = _stored_result()

    if result is None:
        return

    if not result.planets:
        st.warning(
            _t(
                "exoplanet_no_results",
                language,
            )
        )

        _render_export(
            result,
            language,
        )

        return

    st.markdown(f"### {_t('exoplanet_results', language)}")

    _render_summary(
        result,
        language,
    )

    _render_result_tabs(
        result,
        language,
    )
