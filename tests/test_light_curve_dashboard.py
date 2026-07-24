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


@dataclass(frozen=True, slots=True)
class FakeUploadedFile:
    """Small uploaded-file replacement used by dashboard tests."""

    text: str

    def getvalue(self) -> bytes:
        return self.text.encode("utf-8")


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
    checkbox_values: dict[str, bool] = field(default_factory=dict)
    checkbox_calls: list[dict[str, object]] = field(default_factory=list)
    selectbox_calls: list[dict[str, object]] = field(default_factory=list)
    plotly_chart_calls: list[dict[str, object]] = field(default_factory=list)

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

    def checkbox(
        self,
        label: str,
        *,
        value: bool,
        key: str,
    ) -> bool:
        self.checkbox_calls.append(
            {
                "label": label,
                "value": value,
                "key": key,
            }
        )
        return self.checkbox_values.get(key, value)

    def plotly_chart(
        self,
        figure: object,
        *,
        width: str,
        key: str,
    ) -> None:
        self.plotly_chart_calls.append(
            {
                "figure": figure,
                "width": width,
                "key": key,
            }
        )

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
    uploaded_file = FakeUploadedFile(
        "time,flux\n0,1.0\n1,0.9\n2,1.1\n"
    )
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

    assert fake_streamlit.success_messages == ["Light curve imported successfully."]


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
    assert fake_streamlit.text_input_calls[0]["key"] == "light_curve_object_name_en"
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


def test_dashboard_renders_uploaded_light_curve_chart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = FakeUploadedFile(
        "time,flux,uncertainty\n"
        "0,1.0,0.01\n"
        "1,0.9,0.01\n"
        "2,1.1,0.01\n"
    )
    fake_streamlit = FakeStreamlit(uploaded_file=uploaded_file)

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("en")

    assert len(fake_streamlit.plotly_chart_calls) == 1
    assert fake_streamlit.plotly_chart_calls[0]["width"] == "stretch"
    assert fake_streamlit.plotly_chart_calls[0]["key"] == "light_curve_raw_chart"

def test_dashboard_renders_normalized_chart_when_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = FakeUploadedFile(
        "time,flux,uncertainty\n"
        "0,10.0,1.0\n"
        "1,20.0,2.0\n"
        "2,30.0,3.0\n"
    )
    fake_streamlit = FakeStreamlit(
        uploaded_file=uploaded_file,
        checkbox_values={
            "light_curve_normalize_data": True,
        },
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("en")

    assert [
        call["key"]
        for call in fake_streamlit.plotly_chart_calls
    ] == [
        "light_curve_raw_chart",
        "light_curve_normalized_chart",
    ]


def test_dashboard_renders_sigma_clipped_chart_when_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = FakeUploadedFile(
        "time,flux,uncertainty\n"
        "0,0.99,0.01\n"
        "1,1.00,0.01\n"
        "2,1.01,0.01\n"
        "3,1.00,0.01\n"
        "4,5.00,0.10\n"
    )
    fake_streamlit = FakeStreamlit(
        uploaded_file=uploaded_file,
        checkbox_values={
            "light_curve_sigma_clip_data": True,
        },
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("en")

    assert [
        call["key"]
        for call in fake_streamlit.plotly_chart_calls
    ] == [
        "light_curve_raw_chart",
        "light_curve_sigma_clipped_chart",
    ]


def test_dashboard_combines_sigma_clipping_and_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = FakeUploadedFile(
        "time,flux,uncertainty\n"
        "0,9.0,0.1\n"
        "1,10.0,0.1\n"
        "2,11.0,0.1\n"
        "3,10.0,0.1\n"
        "4,50.0,0.5\n"
    )
    fake_streamlit = FakeStreamlit(
        uploaded_file=uploaded_file,
        checkbox_values={
            "light_curve_normalize_data": True,
            "light_curve_sigma_clip_data": True,
        },
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    render_light_curve_dashboard("en")

    assert [
        call["key"]
        for call in fake_streamlit.plotly_chart_calls
    ] == [
        "light_curve_raw_chart",
        "light_curve_processed_chart",
    ]

    processed_figure = fake_streamlit.plotly_chart_calls[1]["figure"]
    processed_trace = processed_figure.data[0]

    assert tuple(processed_trace.x) == pytest.approx(
        (
            0.0,
            1.0,
            2.0,
            3.0,
        )
    )
    assert tuple(processed_trace.y) == pytest.approx(
        (
            0.9,
            1.0,
            1.1,
            1.0,
        )
    )


def test_uploaded_curve_uses_selected_photometry_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded_file = FakeUploadedFile(
        "time,flux\n"
        "0,12.0\n"
        "1,12.1\n"
        "2,11.9\n"
    )
    fake_streamlit = FakeStreamlit(
        uploaded_file=uploaded_file,
        select_index=1,
    )

    monkeypatch.setattr(
        light_curve_dashboard,
        "st",
        fake_streamlit,
    )

    state = render_light_curve_dashboard("en")

    figure = fake_streamlit.plotly_chart_calls[0]["figure"]

    assert state.photometry_kind == "magnitude"
    assert figure.layout.yaxis.title.text == "Magnitude"
    assert figure.layout.yaxis.autorange == "reversed"
