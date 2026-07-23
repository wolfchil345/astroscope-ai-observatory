"""Tests for light-curve laboratory translations."""

from dataclasses import fields

import pytest

from astroscope.light_curve_i18n import (
    LightCurveTranslationError,
    LightCurveTranslations,
    build_light_curve_analysis_visual_labels,
    build_light_curve_visual_labels,
    get_light_curve_translations,
    supported_light_curve_languages,
    translate_light_curve,
)


def test_four_light_curve_languages_are_supported() -> None:
    assert supported_light_curve_languages() == (
        "en",
        "ja",
        "ko",
        "th",
    )


@pytest.mark.parametrize(
    "language",
    [
        "en",
        "ja",
        "ko",
        "th",
    ],
)
def test_every_translation_value_is_nonempty(
    language: str,
) -> None:
    catalog = get_light_curve_translations(language)

    for field in fields(LightCurveTranslations):
        value = getattr(
            catalog,
            field.name,
        )

        assert isinstance(
            value,
            str,
        )
        assert value.strip()


def test_language_codes_are_normalized() -> None:
    assert get_light_curve_translations(" JA ").laboratory_title == "天文ライトカーブ解析ラボ"


def test_unknown_language_is_rejected() -> None:
    with pytest.raises(
        LightCurveTranslationError,
        match="Unsupported",
    ):
        get_light_curve_translations("de")


def test_unknown_translation_key_is_rejected() -> None:
    with pytest.raises(
        LightCurveTranslationError,
        match="Unknown",
    ):
        translate_light_curve(
            "en",
            "missing_key",
        )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            "en",
            "Period search",
        ),
        (
            "ja",
            "周期探索",
        ),
        (
            "ko",
            "주기 탐색",
        ),
        (
            "th",
            "การค้นหาคาบ",
        ),
    ],
)
def test_period_search_translation(
    language: str,
    expected: str,
) -> None:
    assert (
        translate_light_curve(
            language,
            "period_search_section",
        )
        == expected
    )


def test_basic_visual_labels_use_japanese_catalog() -> None:
    labels = build_light_curve_visual_labels("ja")

    assert labels.time_axis == "時刻"
    assert labels.flux_axis == "フラックス"
    assert labels.raw_series == "生データ"
    assert labels.processed_series == "処理済み"


def test_analysis_visual_labels_use_korean_catalog() -> None:
    labels = build_light_curve_analysis_visual_labels("ko")

    assert labels.period_axis == "주기"
    assert labels.phase_axis == "위상"
    assert labels.transit_candidates == "트랜싯 후보"
    assert labels.residual_series == "잔차"


def test_analysis_visual_labels_use_thai_catalog() -> None:
    labels = build_light_curve_analysis_visual_labels("th")

    assert labels.period_axis == "คาบ"
    assert labels.observed_series == "ค่าที่สังเกต"
    assert labels.model_series == "แบบจำลองทรานซิตรูปกล่อง"


def test_unicode_translations_remain_unescaped() -> None:
    japanese = translate_light_curve(
        "ja",
        "laboratory_title",
    )
    korean = translate_light_curve(
        "ko",
        "laboratory_title",
    )
    thai = translate_light_curve(
        "th",
        "laboratory_title",
    )

    assert "天文" in japanese
    assert "천문" in korean
    assert "ดาราศาสตร์" in thai
