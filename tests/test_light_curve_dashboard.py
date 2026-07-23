"""Tests for the multilingual light-curve dashboard shell."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from astroscope import light_curve_dashboard
from astroscope.light_curve_dashboard import (
    LightCurveDashboardError,
    build_light_curve_dashboard_copy,
    canonical_photometry_kind,
    render_light_curve_dashboard,
    translated_photometry_label,
)


@dataclass
class FakeStreamlit:
    """Small Streamlit replacement used by dashboard tests."""

    uploaded_file: object | None = None
    text_value: str = "Test Target"
    select_index: int = 0
    titles: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    subheaders: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)
    success_messages: list[str] = field(default_factory=list)
    uploader_calls: list[dict[str, object]] = field(default_factory=list)
    text_input_calls: list[dict[str, object]] = field(default_factory=list)
    selectbox_calls: list[dict[str, object]] = field(default_factory=list)

    def title(
        self,
        text: str,
    ) -> None:
        self.titles.append(text)

    def header(
        self,
        text: str,
    ) -> None:
        self.headers.append(text)

    def caption(
        self,
        text: str,
    ) -> None:
        self.captions.append(text)

    def subheader(
        self,
        text: str,
    ) -> None:
        self.subheaders.append(text)

    def info(
        self,
        text: str,
    ) -> None:
        self.info_messages.append(text)

    def success(
        self,
        text: str,
    ) -> None:
        self.success_messages.append(text)

    def file_uploader(
        self,
        label: str,
        *,
        type: tuple[str, ...],
        help: str,
        key: str,
    ) -> object | None:
        self.uploader_calls.append(
            {
                "label": label,
                "type": type,
                "help": help,
                "key": key,
            }
        )

        return self.uploaded_file

    def text_input(
        self,
        label: str,
        *,
        value: str,
        key: str,
    ) -> str:
        self.text_input_calls.append(
            {
                "label": label,
                "value": value,
                "key": key,
            }
        )

        return self.text_value

    def selectbox(
        self,
        label: str,
        *,
        options: tuple[str, str],
        index: int,
        key: str,
    ) -> str:
        self.selectbox_calls.append(
            {
                "label": label,
                "options": options,
                "index": index,
                "key": key,
            }
        )

        return options[self.select_index]


@pytest.mark.parametrize(
    "language",
    [
        "en",
        "ja",
        "ko",
        "th",
    ],
)
def test_dashboard_copy_contains_two_photometry_options(
    language: str,
) -> None:
    copy = build_light_curve_dashboard_copy(language)

    assert len(copy.photometry_options) == 2

    assert all(option.strip() for option in copy.photometry_options)


@pytest.mark.parametrize(
    ("language", "kind"),
    [
        (
            "en",
            "flux",
        ),
        (
            "ja",
            "magnitude",
        ),
        (
            "ko",
            "flux",
        ),
        (
            "th",
            "magnitude",
        ),
    ],
)
def test_photometry_translation_round_trip(
    language: str,
    kind: str,
) -> None:
    translated = translated_photometry_label(
        language,
        kind,
    )

    assert (
        canonical_photometry_kind(
            language,
            translated,
        )
        == kind
    )


def test_unknown_photometry_option_is_rejected() -> None:
    with pytest.raises(
        LightCurveDashboardError,
        match="Unknown",
    ):
        canonical_photometry_kind(
            "en",
            "Radio brightness",
        )


def test_dashboard_renders_japanese_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    state = render_light_curve_dashboard("ja")

    assert fake_streamlit.titles == ["天文ライトカーブ解析ラボ"]

    assert fake_streamlit.uploader_calls[0]["label"] == "ライトカーブデータをアップロード"

    assert fake_streamlit.selectbox_calls[0]["options"] == (
        "フラックス",
        "等級",
    )

    assert state.object_name == "Test Target"
    assert state.photometry_kind == "flux"
    assert state.has_uploaded_file is False


def test_dashboard_returns_magnitude_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit(
        select_index=1,
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    state = render_light_curve_dashboard("ko")

    assert state.photometry_kind == "magnitude"


def test_dashboard_shows_no_data_message_without_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("th")

    assert fake_streamlit.info_messages == ["อัปโหลดไฟล์กราฟแสงเพื่อเริ่มการวิเคราะห์"]
    assert fake_streamlit.success_messages == []


def test_dashboard_detects_uploaded_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = object()
    fake_streamlit = FakeStreamlit(
        uploaded_file=uploaded_file,
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    state = render_light_curve_dashboard("en")

    assert state.uploaded_file is uploaded_file
    assert state.has_uploaded_file is True

    assert fake_streamlit.success_messages == ["Analysis complete."]


def test_dashboard_uses_stable_widget_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("en")

    assert fake_streamlit.uploader_calls[0]["key"] == "light_curve_upload"
    assert fake_streamlit.text_input_calls[0]["key"] == "light_curve_object_name"
    assert fake_streamlit.selectbox_calls[0]["key"] == "light_curve_photometry_kind"


def test_embedded_dashboard_uses_section_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    state = render_light_curve_dashboard(
        "en",
        embedded=True,
    )

    assert fake_streamlit.titles == []
    assert fake_streamlit.headers == ["Astronomical Light Curve Laboratory"]
    assert state.photometry_kind == "flux"
