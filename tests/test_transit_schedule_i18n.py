"""Tests for transit-scheduler interface translations."""

import pytest

from astroscope.transit_schedule_i18n import (
    SUPPORTED_TRANSIT_LANGUAGES,
    normalize_transit_language,
    transit_translation_keys,
    translate_transit,
    validate_transit_translations,
)


@pytest.mark.parametrize(
    ("language", "expected_code"),
    [
        ("English", "en"),
        ("en", "en"),
        ("日本語", "ja"),
        ("Japanese", "ja"),
        ("한국어", "ko"),
        ("Korean", "ko"),
        ("ไทย", "th"),
        ("Thai", "th"),
        ("unknown", "en"),
    ],
)
def test_normalize_transit_language(
    language: str,
    expected_code: str,
) -> None:
    assert normalize_transit_language(language) == expected_code


def test_supported_languages_are_complete() -> None:
    assert SUPPORTED_TRANSIT_LANGUAGES == (
        "English",
        "日本語",
        "한국어",
        "ไทย",
    )


@pytest.mark.parametrize(
    "language",
    SUPPORTED_TRANSIT_LANGUAGES,
)
def test_every_language_translates_title(
    language: str,
) -> None:
    result = translate_transit(
        "title",
        language,
    )

    assert result
    assert isinstance(result, str)


@pytest.mark.parametrize(
    "language",
    SUPPORTED_TRANSIT_LANGUAGES,
)
def test_formatting_values_are_inserted(
    language: str,
) -> None:
    result = translate_transit(
        "target_number",
        language,
        number=3,
    )

    assert "3" in result


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(
        KeyError,
        match="Unknown transit scheduler",
    ):
        translate_transit(
            "missing_key",
            "English",
        )


def test_translation_key_collection_is_substantial() -> None:
    assert len(transit_translation_keys()) >= 50


def test_all_translation_dictionaries_match() -> None:
    validate_transit_translations()
