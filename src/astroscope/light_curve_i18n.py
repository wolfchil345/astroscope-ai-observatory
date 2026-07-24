"""Internationalization support for the light-curve laboratory."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Final

from astroscope.light_curve_analysis_visuals import (
    LightCurveAnalysisVisualLabels,
)
from astroscope.light_curve_visuals import (
    LightCurveVisualLabels,
)


class LightCurveTranslationError(ValueError):
    """Raised when a light-curve translation cannot be resolved."""


@dataclass(frozen=True, slots=True)
class LightCurveTranslations:
    """Complete user-interface catalog for one language."""

    laboratory_title: str
    laboratory_caption: str
    upload_label: str
    upload_help: str
    object_name_label: str
    unknown_target: str
    photometry_kind_label: str
    flux_option: str
    magnitude_option: str
    raw_data_section: str
    processing_section: str
    normalize_data: str
    sigma_clip_data: str
    period_search_section: str
    transit_search_section: str
    exports_section: str
    run_lomb_scargle: str
    run_bls: str
    download_csv: str
    download_json: str
    no_data_message: str
    analysis_complete_message: str
    time_axis: str
    flux_axis: str
    magnitude_axis: str
    period_axis: str
    power_axis: str
    phase_axis: str
    phase_time_axis: str
    residual_axis: str
    rank_label: str
    raw_series: str
    processed_series: str
    lomb_scargle_series: str
    period_candidates: str
    folded_series: str
    binned_series: str
    bls_series: str
    transit_candidates: str
    observed_series: str
    model_series: str
    residual_series: str


SUPPORTED_LIGHT_CURVE_LANGUAGES: Final[tuple[str, ...]] = (
    "en",
    "ja",
    "ko",
    "th",
)


_TRANSLATIONS: Final[dict[str, LightCurveTranslations]] = {
    "en": LightCurveTranslations(
        laboratory_title="Astronomical Light Curve Laboratory",
        laboratory_caption=("Import, process, analyze, and export time-series photometry."),
        upload_label="Upload light-curve data",
        upload_help=("CSV or TSV containing time, value, and optional uncertainty columns."),
        object_name_label="Object name",
        unknown_target="Unknown target",
        photometry_kind_label="Photometry type",
        flux_option="Flux",
        magnitude_option="Magnitude",
        raw_data_section="Raw observations",
        processing_section="Processing",
        normalize_data="Normalize data",
        sigma_clip_data="Remove 3σ outliers",
        period_search_section="Period search",
        transit_search_section="Transit search",
        exports_section="Exports",
        run_lomb_scargle="Run Lomb-Scargle search",
        run_bls="Run transit search",
        download_csv="Download CSV",
        download_json="Download JSON report",
        no_data_message="Upload a light-curve file to begin.",
        analysis_complete_message="Analysis complete.",
        time_axis="Time",
        flux_axis="Flux",
        magnitude_axis="Magnitude",
        period_axis="Period",
        power_axis="Power",
        phase_axis="Phase",
        phase_time_axis="Time from transit midpoint",
        residual_axis="Residual",
        rank_label="Rank",
        raw_series="Raw",
        processed_series="Processed",
        lomb_scargle_series="Lomb-Scargle power",
        period_candidates="Period candidates",
        folded_series="Folded observations",
        binned_series="Phase bins",
        bls_series="BLS power",
        transit_candidates="Transit candidates",
        observed_series="Observed",
        model_series="Box transit model",
        residual_series="Residual",
    ),
    "ja": LightCurveTranslations(
        laboratory_title="天文ライトカーブ解析ラボ",
        laboratory_caption=("時系列測光データを読み込み、前処理・解析・出力します。"),
        upload_label="ライトカーブデータをアップロード",
        upload_help=("時刻、測定値、任意の不確かさ列を含むCSVまたはTSV。"),
        object_name_label="天体名",
        unknown_target="不明な天体",
        photometry_kind_label="測光量",
        flux_option="フラックス",
        magnitude_option="等級",
        raw_data_section="生データ",
        processing_section="前処理",
        normalize_data="データを正規化",
        sigma_clip_data="3σ外れ値を除去",
        period_search_section="周期探索",
        transit_search_section="トランジット探索",
        exports_section="エクスポート",
        run_lomb_scargle="ロンバーグ・スキャーグル解析を実行",
        run_bls="トランジット探索を実行",
        download_csv="CSVをダウンロード",
        download_json="JSONレポートをダウンロード",
        no_data_message=("解析を開始するにはライトカーブファイルをアップロードしてください。"),
        analysis_complete_message="解析が完了しました。",
        time_axis="時刻",
        flux_axis="フラックス",
        magnitude_axis="等級",
        period_axis="周期",
        power_axis="パワー",
        phase_axis="位相",
        phase_time_axis="トランジット中心からの時間",
        residual_axis="残差",
        rank_label="順位",
        raw_series="生データ",
        processed_series="処理済み",
        lomb_scargle_series="ロンバーグ・スキャーグルパワー",
        period_candidates="周期候補",
        folded_series="位相折り畳み観測値",
        binned_series="位相ビン",
        bls_series="BLSパワー",
        transit_candidates="トランジット候補",
        observed_series="観測値",
        model_series="ボックス型トランジットモデル",
        residual_series="残差",
    ),
    "ko": LightCurveTranslations(
        laboratory_title="천문 광도곡선 분석실",
        laboratory_caption=("시계열 측광 데이터를 불러오고 전처리, 분석, 내보내기를 수행합니다."),
        upload_label="광도곡선 데이터 업로드",
        upload_help=("시간, 측정값, 선택적 불확도 열이 포함된 CSV 또는 TSV 파일입니다."),
        object_name_label="천체 이름",
        unknown_target="알 수 없는 천체",
        photometry_kind_label="측광 유형",
        flux_option="플럭스",
        magnitude_option="등급",
        raw_data_section="원시 관측값",
        processing_section="전처리",
        normalize_data="데이터 정규화",
        sigma_clip_data="3σ 이상치 제거",
        period_search_section="주기 탐색",
        transit_search_section="트랜싯 탐색",
        exports_section="내보내기",
        run_lomb_scargle="롬-스카글 탐색 실행",
        run_bls="트랜싯 탐색 실행",
        download_csv="CSV 다운로드",
        download_json="JSON 보고서 다운로드",
        no_data_message="분석을 시작하려면 광도곡선 파일을 업로드하세요.",
        analysis_complete_message="분석이 완료되었습니다.",
        time_axis="시간",
        flux_axis="플럭스",
        magnitude_axis="등급",
        period_axis="주기",
        power_axis="파워",
        phase_axis="위상",
        phase_time_axis="트랜싯 중심으로부터의 시간",
        residual_axis="잔차",
        rank_label="순위",
        raw_series="원시 데이터",
        processed_series="처리된 데이터",
        lomb_scargle_series="롬-스카글 파워",
        period_candidates="주기 후보",
        folded_series="위상 접기 관측값",
        binned_series="위상 구간",
        bls_series="BLS 파워",
        transit_candidates="트랜싯 후보",
        observed_series="관측값",
        model_series="박스형 트랜싯 모델",
        residual_series="잔차",
    ),
    "th": LightCurveTranslations(
        laboratory_title="ห้องปฏิบัติการวิเคราะห์กราฟแสงทางดาราศาสตร์",
        laboratory_caption=("นำเข้า ประมวลผล วิเคราะห์ และส่งออกข้อมูลโฟโตเมทรีแบบอนุกรมเวลา"),
        upload_label="อัปโหลดข้อมูลกราฟแสง",
        upload_help=("ไฟล์ CSV หรือ TSV ที่มีคอลัมน์เวลา ค่าที่วัด และค่าความไม่แน่นอนถ้ามี"),
        object_name_label="ชื่อวัตถุท้องฟ้า",
        unknown_target="วัตถุท้องฟ้าที่ไม่ทราบชื่อ",
        photometry_kind_label="ประเภทโฟโตเมทรี",
        flux_option="ฟลักซ์",
        magnitude_option="โชติมาตร",
        raw_data_section="ข้อมูลสังเกตดิบ",
        processing_section="การประมวลผล",
        normalize_data="ปรับข้อมูลให้เป็นมาตรฐาน",
        sigma_clip_data="ลบค่าผิดปกติ 3σ",
        period_search_section="การค้นหาคาบ",
        transit_search_section="การค้นหาทรานซิต",
        exports_section="การส่งออก",
        run_lomb_scargle="เริ่มการค้นหาแบบลอมบ์-สการ์เกิล",
        run_bls="เริ่มการค้นหาทรานซิต",
        download_csv="ดาวน์โหลด CSV",
        download_json="ดาวน์โหลดรายงาน JSON",
        no_data_message="อัปโหลดไฟล์กราฟแสงเพื่อเริ่มการวิเคราะห์",
        analysis_complete_message="การวิเคราะห์เสร็จสมบูรณ์",
        time_axis="เวลา",
        flux_axis="ฟลักซ์",
        magnitude_axis="โชติมาตร",
        period_axis="คาบ",
        power_axis="กำลัง",
        phase_axis="เฟส",
        phase_time_axis="เวลาจากกึ่งกลางทรานซิต",
        residual_axis="ค่าคงเหลือ",
        rank_label="อันดับ",
        raw_series="ข้อมูลดิบ",
        processed_series="ข้อมูลที่ประมวลผลแล้ว",
        lomb_scargle_series="กำลังลอมบ์-สการ์เกิล",
        period_candidates="คาบที่เป็นไปได้",
        folded_series="ข้อมูลพับเฟส",
        binned_series="ช่วงเฟส",
        bls_series="กำลัง BLS",
        transit_candidates="ทรานซิตที่เป็นไปได้",
        observed_series="ค่าที่สังเกต",
        model_series="แบบจำลองทรานซิตรูปกล่อง",
        residual_series="ค่าคงเหลือ",
    ),
}


_TRANSLATION_FIELDS: Final[frozenset[str]] = frozenset(
    field.name for field in fields(LightCurveTranslations)
)


def supported_light_curve_languages() -> tuple[str, ...]:
    """Return the supported language codes."""

    return SUPPORTED_LIGHT_CURVE_LANGUAGES


def get_light_curve_translations(
    language: str,
) -> LightCurveTranslations:
    """Return the complete translation catalog for one language."""

    if not isinstance(language, str):
        raise LightCurveTranslationError("Language code must be a string.")

    normalized_language = language.strip().lower()

    try:
        return _TRANSLATIONS[normalized_language]
    except KeyError as exc:
        raise LightCurveTranslationError(
            f"Unsupported light-curve language: {language!r}."
        ) from exc


def translate_light_curve(
    language: str,
    key: str,
) -> str:
    """Return one translated light-curve interface string."""

    if not isinstance(key, str):
        raise LightCurveTranslationError("Translation key must be a string.")

    if key not in _TRANSLATION_FIELDS:
        raise LightCurveTranslationError(f"Unknown light-curve translation key: {key!r}.")

    catalog = get_light_curve_translations(language)

    return str(
        getattr(
            catalog,
            key,
        )
    )


def build_light_curve_visual_labels(
    language: str,
) -> LightCurveVisualLabels:
    """Create translated labels for basic light-curve figures."""

    catalog = get_light_curve_translations(language)

    return LightCurveVisualLabels(
        time_axis=catalog.time_axis,
        flux_axis=catalog.flux_axis,
        magnitude_axis=catalog.magnitude_axis,
        raw_series=catalog.raw_series,
        processed_series=catalog.processed_series,
    )


def build_light_curve_analysis_visual_labels(
    language: str,
) -> LightCurveAnalysisVisualLabels:
    """Create translated labels for scientific analysis figures."""

    catalog = get_light_curve_translations(language)

    return LightCurveAnalysisVisualLabels(
        period_axis=catalog.period_axis,
        power_axis=catalog.power_axis,
        phase_axis=catalog.phase_axis,
        phase_time_axis=catalog.phase_time_axis,
        flux_axis=catalog.flux_axis,
        magnitude_axis=catalog.magnitude_axis,
        residual_axis=catalog.residual_axis,
        rank_label=catalog.rank_label,
        lomb_scargle_series=catalog.lomb_scargle_series,
        period_candidates=catalog.period_candidates,
        folded_series=catalog.folded_series,
        binned_series=catalog.binned_series,
        bls_series=catalog.bls_series,
        transit_candidates=catalog.transit_candidates,
        observed_series=catalog.observed_series,
        model_series=catalog.model_series,
        residual_series=catalog.residual_series,
    )
