"""Streamlit interface for the astronomical light-curve laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

import streamlit as st

from astroscope.light_curve import LightCurve, LightCurveMetadata
from astroscope.light_curve_analysis_visuals import (
    build_bls_periodogram_figure,
    build_lomb_scargle_periodogram_figure,
    build_phase_folded_figure,
    build_transit_model_figure,
    build_transit_residual_figure,
)
from astroscope.light_curve_i18n import (
    LightCurveTranslations,
    build_light_curve_analysis_visual_labels,
    build_light_curve_visual_labels,
    get_light_curve_translations,
)
from astroscope.light_curve_io import (
    detect_light_curve_csv_columns,
    import_light_curve_csv,
)
from astroscope.light_curve_period import (
    LightCurvePeriodError,
    analyze_lomb_scargle,
)
from astroscope.light_curve_phase import (
    LightCurvePhaseError,
    bin_phase_fold,
    fold_light_curve,
)
from astroscope.light_curve_processing import (
    normalize_light_curve,
    sigma_clip_light_curve,
)
from astroscope.light_curve_transit_diagnostics import (
    LightCurveTransitDiagnosticError,
    diagnose_transit_candidate,
)
from astroscope.light_curve_transit_search import (
    LightCurveTransitSearchError,
    search_box_least_squares,
)
from astroscope.light_curve_visuals import build_light_curve_figure


class LightCurveDashboardError(ValueError):
    """Raised when dashboard input cannot be normalized."""


@dataclass(frozen=True, slots=True)
class LightCurveDashboardCopy:
    """Translated text and options used by the dashboard."""

    translations: LightCurveTranslations
    photometry_options: tuple[str, str]


@dataclass(frozen=True, slots=True)
class LightCurveDashboardState:
    """Current values selected in the dashboard shell."""

    uploaded_file: object | None
    object_name: str
    photometry_kind: str

    @property
    def has_uploaded_file(self) -> bool:
        """Return whether the user supplied a light-curve file."""

        return self.uploaded_file is not None


@dataclass(frozen=True, slots=True)
class PeriodSearchBounds:
    """Default Lomb-Scargle period interval for the dashboard."""

    minimum_period: float
    maximum_period: float


@dataclass(frozen=True, slots=True)
class TransitSearchDefaults:
    """Default Box Least Squares settings for the dashboard."""

    minimum_period: float
    maximum_period: float
    duration: float


def build_default_period_search_bounds(
    light_curve: LightCurve,
) -> PeriodSearchBounds:
    """Estimate a practical search interval from cadence and baseline."""

    if not isinstance(light_curve, LightCurve):
        raise LightCurveDashboardError("Period-search defaults require a LightCurve instance.")

    if light_curve.observation_count < 5:
        raise LightCurveDashboardError("Default period search requires at least five observations.")

    cadences = tuple(
        current.time - previous.time
        for previous, current in zip(
            light_curve.points,
            light_curve.points[1:],
            strict=False,
        )
    )
    representative_cadence = float(median(cadences))

    maximum_period = light_curve.duration / 2.0
    minimum_period = 2.0 * representative_cadence

    if minimum_period >= maximum_period:
        minimum_period = maximum_period / 10.0

    return PeriodSearchBounds(
        minimum_period=minimum_period,
        maximum_period=maximum_period,
    )


def build_default_transit_search_settings(
    light_curve: LightCurve,
) -> TransitSearchDefaults:
    """Estimate practical Box Least Squares settings."""

    if not isinstance(light_curve, LightCurve):
        raise LightCurveDashboardError("Transit-search defaults require a LightCurve instance.")

    if light_curve.metadata.photometry_kind != "flux":
        raise LightCurveDashboardError("Transit-search defaults require flux measurements.")

    if light_curve.observation_count < 20:
        raise LightCurveDashboardError(
            "Default transit search requires at least twenty observations."
        )

    cadences = tuple(
        current.time - previous.time
        for previous, current in zip(
            light_curve.points,
            light_curve.points[1:],
            strict=False,
        )
    )
    representative_cadence = float(median(cadences))

    maximum_period = light_curve.duration / 2.0
    minimum_period = 5.0 * representative_cadence

    if minimum_period >= maximum_period:
        minimum_period = maximum_period / 5.0

    duration = min(
        minimum_period / 5.0,
        2.0 * representative_cadence,
    )

    if duration >= minimum_period:
        duration = minimum_period / 5.0

    return TransitSearchDefaults(
        minimum_period=minimum_period,
        maximum_period=maximum_period,
        duration=duration,
    )


def build_light_curve_dashboard_copy(
    language: str,
) -> LightCurveDashboardCopy:
    """Build translated dashboard text for one language."""

    translations = get_light_curve_translations(language)

    return LightCurveDashboardCopy(
        translations=translations,
        photometry_options=(
            translations.flux_option,
            translations.magnitude_option,
        ),
    )


def canonical_photometry_kind(
    language: str,
    translated_label: str,
) -> str:
    """Convert a translated selector value into a canonical kind."""

    if not isinstance(translated_label, str):
        raise LightCurveDashboardError("Photometry label must be a string.")

    copy = build_light_curve_dashboard_copy(language)
    translations = copy.translations

    if translated_label == translations.flux_option:
        return "flux"

    if translated_label == translations.magnitude_option:
        return "magnitude"

    raise LightCurveDashboardError(f"Unknown photometry option: {translated_label!r}.")


def translated_photometry_label(
    language: str,
    photometry_kind: str,
) -> str:
    """Convert a canonical photometry kind into a translated label."""

    if not isinstance(photometry_kind, str):
        raise LightCurveDashboardError("Photometry kind must be a string.")

    copy = build_light_curve_dashboard_copy(language)
    translations = copy.translations
    normalized_kind = photometry_kind.strip().lower()

    if normalized_kind == "flux":
        return translations.flux_option

    if normalized_kind == "magnitude":
        return translations.magnitude_option

    raise LightCurveDashboardError(f"Unsupported photometry kind: {photometry_kind!r}.")


def render_light_curve_dashboard(
    language: str,
    *,
    embedded: bool = False,
) -> LightCurveDashboardState:
    """Render the multilingual light-curve laboratory shell."""

    copy = build_light_curve_dashboard_copy(language)
    translations = copy.translations

    if embedded:
        st.header(translations.laboratory_title)
    else:
        st.title(translations.laboratory_title)

    st.caption(translations.laboratory_caption)

    uploaded_file = st.file_uploader(
        translations.upload_label,
        type=(
            "csv",
            "tsv",
            "txt",
        ),
        help=translations.upload_help,
        key="light_curve_upload",
    )

    object_name = st.text_input(
        translations.object_name_label,
        value=translations.unknown_target,
        key=f"light_curve_object_name_{language}",
    )

    translated_kind = st.selectbox(
        translations.photometry_kind_label,
        options=copy.photometry_options,
        index=0,
        key="light_curve_photometry_kind",
    )

    photometry_kind = canonical_photometry_kind(
        language,
        translated_kind,
    )

    st.subheader(translations.raw_data_section)

    if uploaded_file is None:
        st.info(translations.no_data_message)
    else:
        raw_csv = uploaded_file.getvalue()
        csv_text = raw_csv.decode("utf-8")
        detection = detect_light_curve_csv_columns(csv_text)
        metadata = LightCurveMetadata(
            object_name=object_name.strip() or translations.unknown_target,
            photometry_kind=photometry_kind,
            time_standard=detection.suggested_time_standard or "BJD_TDB",
        )
        import_result = import_light_curve_csv(
            csv_text=csv_text,
            metadata=metadata,
            columns=detection.columns,
            duplicate_policy="keep-first",
        )
        figure = build_light_curve_figure(
            import_result.light_curve,
            labels=build_light_curve_visual_labels(language),
        )
        st.plotly_chart(
            figure,
            width="stretch",
            key="light_curve_raw_chart",
        )
        st.success(translations.import_success_message)

    st.subheader(translations.processing_section)
    if uploaded_file is not None:
        normalize_data = st.checkbox(
            translations.normalize_data,
            value=False,
            key="light_curve_normalize_data",
        )
        sigma_clip_data = st.checkbox(
            translations.sigma_clip_data,
            value=False,
            key="light_curve_sigma_clip_data",
        )

        processed_curve = import_result.light_curve
        processed_chart_key: str | None = None

        if sigma_clip_data:
            sigma_clipped_result = sigma_clip_light_curve(
                processed_curve,
                sigma=3.0,
            )
            processed_curve = sigma_clipped_result.light_curve
            processed_chart_key = "light_curve_sigma_clipped_chart"

        if normalize_data:
            normalized_result = normalize_light_curve(processed_curve)
            processed_curve = normalized_result.light_curve
            processed_chart_key = "light_curve_normalized_chart"

        if sigma_clip_data and normalize_data:
            processed_chart_key = "light_curve_processed_chart"

        if processed_chart_key is not None:
            processed_figure = build_light_curve_figure(
                processed_curve,
                labels=build_light_curve_visual_labels(language),
            )
            st.plotly_chart(
                processed_figure,
                width="stretch",
                key=processed_chart_key,
            )

    st.subheader(translations.period_search_section)

    if uploaded_file is not None and processed_curve.observation_count < 5:
        st.info(translations.period_search_requires_five_observations)
    elif uploaded_file is not None:
        period_bounds = build_default_period_search_bounds(
            processed_curve,
        )
        period_step = max(
            period_bounds.minimum_period / 10.0,
            1.0e-6,
        )

        st.caption(translations.period_unit_help)

        minimum_period = st.number_input(
            translations.minimum_period_label,
            value=period_bounds.minimum_period,
            step=period_step,
            format="%.6f",
            help=translations.period_unit_help,
            key="light_curve_minimum_period",
        )
        maximum_period = st.number_input(
            translations.maximum_period_label,
            value=period_bounds.maximum_period,
            step=period_step,
            format="%.6f",
            help=translations.period_unit_help,
            key="light_curve_maximum_period",
        )
        phase_bin_count = st.number_input(
            translations.phase_bin_count_label,
            value=20,
            step=1,
            format="%d",
            help=None,
            key="light_curve_phase_bin_count",
        )

        run_period_search = st.button(
            translations.run_lomb_scargle,
            type="primary",
            key="light_curve_run_lomb_scargle",
        )

        if run_period_search:
            try:
                period_result = analyze_lomb_scargle(
                    processed_curve,
                    minimum_period=float(minimum_period),
                    maximum_period=float(maximum_period),
                )
                phase_fold = fold_light_curve(
                    processed_curve,
                    period=period_result.best_period,
                )
                phase_binning = bin_phase_fold(
                    phase_fold,
                    bin_count=int(phase_bin_count),
                )
            except (
                LightCurvePeriodError,
                LightCurvePhaseError,
            ) as error:
                st.error(str(error))
            else:
                st.metric(
                    translations.best_period_label,
                    f"{period_result.best_period:.6g}",
                )

                analysis_labels = build_light_curve_analysis_visual_labels(
                    language,
                )

                periodogram_figure = build_lomb_scargle_periodogram_figure(
                    period_result,
                    title=translations.period_search_section,
                    labels=analysis_labels,
                )
                st.plotly_chart(
                    periodogram_figure,
                    width="stretch",
                    key="light_curve_lomb_scargle_chart",
                )

                phase_figure = build_phase_folded_figure(
                    phase_fold,
                    phase_binning=phase_binning,
                    title=translations.folded_series,
                    labels=analysis_labels,
                )
                st.plotly_chart(
                    phase_figure,
                    width="stretch",
                    key="light_curve_phase_folded_chart",
                )

    st.subheader(translations.transit_search_section)

    if uploaded_file is not None and processed_curve.metadata.photometry_kind != "flux":
        st.info(translations.transit_search_requires_flux)
    elif uploaded_file is not None and processed_curve.observation_count < 20:
        st.info(translations.transit_search_requires_twenty_observations)
    elif uploaded_file is not None:
        transit_defaults = build_default_transit_search_settings(
            processed_curve,
        )
        transit_step = max(
            transit_defaults.duration / 10.0,
            1.0e-6,
        )

        st.caption(translations.transit_unit_help)

        transit_minimum_period = st.number_input(
            translations.minimum_period_label,
            value=transit_defaults.minimum_period,
            step=transit_step,
            format="%.6f",
            help=translations.transit_unit_help,
            key="light_curve_transit_minimum_period",
        )
        transit_maximum_period = st.number_input(
            translations.maximum_period_label,
            value=transit_defaults.maximum_period,
            step=transit_step,
            format="%.6f",
            help=translations.transit_unit_help,
            key="light_curve_transit_maximum_period",
        )
        transit_duration = st.number_input(
            translations.transit_duration_label,
            value=transit_defaults.duration,
            step=transit_step,
            format="%.6f",
            help=translations.transit_unit_help,
            key="light_curve_transit_duration",
        )

        run_transit_search = st.button(
            translations.run_bls,
            type="primary",
            key="light_curve_run_bls",
        )

        if run_transit_search:
            try:
                transit_result = search_box_least_squares(
                    processed_curve,
                    minimum_period=float(transit_minimum_period),
                    maximum_period=float(transit_maximum_period),
                    durations=(float(transit_duration),),
                )
                best_transit = transit_result.best_candidate
                transit_diagnostics = diagnose_transit_candidate(
                    processed_curve,
                    best_transit,
                )
            except (
                LightCurveTransitSearchError,
                LightCurveTransitDiagnosticError,
            ) as error:
                st.error(str(error))
            else:
                best_transit = transit_result.best_candidate

                st.metric(
                    translations.best_transit_period_label,
                    f"{best_transit.period:.6g}",
                )
                st.metric(
                    translations.best_transit_duration_label,
                    f"{best_transit.duration:.6g}",
                )
                st.metric(
                    translations.transit_depth_label,
                    f"{best_transit.depth:.6g}",
                )
                st.metric(
                    translations.transit_depth_snr_label,
                    f"{best_transit.depth_snr:.6g}",
                )

                transit_periodogram = build_bls_periodogram_figure(
                    transit_result,
                    title=translations.transit_search_section,
                    labels=(
                        build_light_curve_analysis_visual_labels(
                            language,
                        )
                    ),
                )
                st.plotly_chart(
                    transit_periodogram,
                    width="stretch",
                    key="light_curve_bls_chart",
                )

                transit_model_figure = build_transit_model_figure(
                    transit_diagnostics,
                    labels=build_light_curve_analysis_visual_labels(
                        language,
                    ),
                )
                st.plotly_chart(
                    transit_model_figure,
                    width="stretch",
                    key="light_curve_transit_model_chart",
                )

                transit_residual_figure = build_transit_residual_figure(
                    transit_diagnostics,
                    labels=(
                        build_light_curve_analysis_visual_labels(
                            language,
                        )
                    ),
                )
                st.plotly_chart(
                    transit_residual_figure,
                    width="stretch",
                    key="light_curve_transit_residual_chart",
                )

    st.subheader(translations.exports_section)

    return LightCurveDashboardState(
        uploaded_file=uploaded_file,
        object_name=object_name.strip(),
        photometry_kind=photometry_kind,
    )
