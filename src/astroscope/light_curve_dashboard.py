"""Streamlit interface for the astronomical light-curve laboratory."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from astroscope.light_curve import LightCurveMetadata
from astroscope.light_curve_i18n import (
    LightCurveTranslations,
    build_light_curve_visual_labels,
    get_light_curve_translations,
)
from astroscope.light_curve_io import (
    detect_light_curve_csv_columns,
    import_light_curve_csv,
)
from astroscope.light_curve_processing import (
    normalize_light_curve,
    sigma_clip_light_curve,
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
            photometry_kind=detection.photometry_kind,
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
        st.success(translations.analysis_complete_message)

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
    st.subheader(translations.transit_search_section)
    st.subheader(translations.exports_section)

    return LightCurveDashboardState(
        uploaded_file=uploaded_file,
        object_name=object_name.strip(),
        photometry_kind=photometry_kind,
    )
