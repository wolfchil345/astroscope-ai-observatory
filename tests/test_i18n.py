import pytest

from astroscope.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, translate


def test_four_languages_are_supported() -> None:
    assert SUPPORTED_LANGUAGES == {
        "English": "en",
        "日本語": "ja",
        "한국어": "ko",
        "ไทย": "th",
    }


def test_every_translation_key_has_all_languages() -> None:
    expected_languages = set(SUPPORTED_LANGUAGES.values())

    for key, translations in TRANSLATIONS.items():
        assert set(translations) == expected_languages, f"Translation key {key!r} is incomplete."


@pytest.mark.parametrize("language", ["en", "ja", "ko", "th"])
def test_app_title_translation_exists(language: str) -> None:
    assert translate("app_title", language)


def test_unknown_translation_key_raises_error() -> None:
    with pytest.raises(KeyError):
        translate("nonexistent_key", "en")


def test_schedule_transition_messages_have_four_language_coverage() -> None:
    keys = (
        "schedule_start_date",
        "schedule_end_date",
        "schedule_start_ambiguous",
        "schedule_end_ambiguous",
        "schedule_endpoint_selection_required",
        "schedule_nonexistent_start",
        "schedule_nonexistent_end",
    )

    for key in keys:
        assert all(translate(key, language) for language in SUPPORTED_LANGUAGES.values())
