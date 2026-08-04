"""Characterization tests for the Observatory presentation boundary."""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from datetime import date, time
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from astroscope import observatory_dashboard
from astroscope.i18n import SUPPORTED_LANGUAGES, translate

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPOSITORY_ROOT / "app.py"
OBSERVATORY_PATH = REPOSITORY_ROOT / "src/astroscope/observatory_dashboard.py"
BASELINE_BODY_SHA256 = "759460af93b55718e99e1bff8e3c12c3c25dd93ed9e2d816bf8cf5ddc2d85c8c"
SUPPORTED_LANGUAGES_FOR_APPTEST = ("English", "日本語", "한국어", "ไทย")
DEFAULT_TIMEZONE_OPTIONS = (
    "Asia/Tokyo",
    "Asia/Bangkok",
    "Asia/Seoul",
    "UTC",
    "America/New_York",
    "Europe/London",
    "Australia/Lord_Howe",
)
TRANSITION_TIMEZONE_OPTIONS = (
    *DEFAULT_TIMEZONE_OPTIONS,
)
SINGLE_INSTANT_BUTTON_LABELS = (
    "Calculate astronomical time",
    "Calculate local sky position",
    "Calculate Solar System position",
    "Generate interactive sky map",
    "Create ranked observation plan",
)
CIVIL_TIME_TRANSLATION_KEYS = (
    "civil_time_ambiguous_title",
    "civil_time_ambiguous_explanation",
    "civil_time_earlier_occurrence",
    "civil_time_later_occurrence",
    "civil_time_selection_required",
    "civil_time_utc_candidate",
    "civil_time_utc_offset",
    "civil_time_nonexistent_title",
    "civil_time_skipped_explanation",
    "civil_time_previous_valid_local",
    "civil_time_next_valid_local",
    "civil_time_actions_blocked",
)


def _run_observatory_app() -> AppTest:
    source_path = str(REPOSITORY_ROOT / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    return AppTest.from_file(APP_PATH, default_timeout=30).run(timeout=30)


def _set_observer_instant(
    app_test: AppTest,
    *,
    timezone_name: str,
    local_date: date,
    local_time: time,
) -> None:
    app_test.selectbox[1].select(timezone_name)
    app_test.date_input[0].set_value(local_date)
    app_test.time_input[0].set_value(local_time)


def _button_by_label(app_test: AppTest, label: str) -> Any:
    return next(button for button in app_test.button if button.label == label)


def _single_instant_buttons(app_test: AppTest) -> list[Any]:
    return [_button_by_label(app_test, label) for label in SINGLE_INSTANT_BUTTON_LABELS]


def _civil_time_text(app_test: AppTest) -> str:
    elements = [
        *app_test.warning,
        *app_test.error,
        *app_test.info,
        *app_test.markdown,
    ]
    return "\n".join(str(element.value) for element in elements)


def test_extracted_observatory_body_matches_mission21_baseline_ast() -> None:
    tree = ast.parse(OBSERVATORY_PATH.read_text())
    render_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "render_observatory_dashboard"
    )
    body_tree = ast.Module(body=render_function.body, type_ignores=[])
    serialized_body = ast.dump(
        body_tree,
        annotate_fields=True,
        include_attributes=False,
    )
    digest = hashlib.sha256(serialized_body.encode()).hexdigest()

    assert digest == BASELINE_BODY_SHA256


def test_clean_import_has_no_ui_side_effects_or_forbidden_dependencies() -> None:
    script = """
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
streamlit_attribute_accesses = []

class GuardedStreamlit(types.ModuleType):
    def __getattr__(self, name):
        streamlit_attribute_accesses.append(name)
        raise AssertionError(f"Streamlit attribute accessed during import: {name}")

guarded_streamlit = GuardedStreamlit("streamlit")
guarded_streamlit.__file__ = "<guarded-streamlit>"
sys.modules["streamlit"] = guarded_streamlit
import astroscope.observatory_dashboard

assert streamlit_attribute_accesses == []
for forbidden in (
    "app",
    "astroscope.exoplanet_dashboard",
    "astroscope.gaia_dashboard",
    "astroscope.light_curve_dashboard",
    "astroscope.transit_schedule_dashboard",
):
    assert forbidden not in sys.modules, forbidden
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_default_observatory_apptest_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_live_weather_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("AppTest must not call the live weather service")

    monkeypatch.setattr(
        observatory_dashboard,
        "fetch_observing_weather",
        reject_live_weather_call,
    )
    source_path = str(REPOSITORY_ROOT / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)

    app_test = AppTest.from_file(APP_PATH, default_timeout=30).run(timeout=30)

    assert len(app_test.exception) == 0
    assert len(app_test.title) == 1
    assert app_test.title[0].value == "🔭 AstroScope AI Observatory"
    assert len(app_test.header) == 11
    assert len(app_test.selectbox) == 21
    assert len(app_test.button) == 13
    assert len(app_test.radio) == 0
    assert len(app_test.sidebar.selectbox) == 1
    language_selector = app_test.sidebar.selectbox[0]
    assert language_selector.label == "Language / 言語 / 언어 / ภาษา"
    assert language_selector.options == list(SUPPORTED_LANGUAGES_FOR_APPTEST)

    expected_state_keys = {
        "latitude_osaka",
        "longitude_osaka",
        "elevation_osaka",
        "timezone_osaka",
        "observer_civil_time_fingerprint",
        "observer_civil_time_selected_fold",
        "right_ascension_sirius",
        "declination_sirius",
        "schedule_start_time_input",
        "schedule_end_time_input",
        "weather_start_time_input",
        "weather_end_time_input",
        "telescope_input_mode",
        "eyepiece_input_mode",
        "planner_include_catalog",
        "planner_include_solar_system",
        "mission11_telescope_mode",
        "mission11_camera_mode",
        "mission11_telescope_preset",
        "mission11_camera_preset",
        "mission11_barlow",
        "mission11_reducer",
        "mission11_seeing",
        "mission11_run_imaging",
        "mission12_session_id",
        "mission12_session_title",
        "mission12_observer",
        "mission12_location",
        "mission12_latitude",
        "mission12_longitude",
        "mission12_elevation",
        "mission12_timezone",
        "mission12_start_date",
        "mission12_start_time",
        "mission12_end_date",
        "mission12_end_time",
        "mission12_mode",
        "mission12_seeing",
        "mission12_transparency",
        "mission12_cloud_cover",
        "mission12_general_notes",
        "mission12_telescope_name",
        "mission12_aperture",
        "mission12_focal_length",
        "mission12_eyepiece_name",
        "mission12_camera_name",
        "mission12_pixel_size",
        "mission12_mount_name",
        "mission12_filters",
        "mission12_observations",
        "mission12_observation_counter",
        "mission12_current_session",
    }
    assert expected_state_keys <= set(app_test.session_state.filtered_state)
    assert app_test.session_state["observer_civil_time_selected_fold"] is None

    app_test.sidebar.selectbox[0].select("日本語")
    app_test.run(timeout=30)

    assert len(app_test.exception) == 0
    assert app_test.title[0].value == "🔭 AstroScope AI 天文台"


def test_ambiguous_civil_time_requires_choice_and_propagates_selected_fold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        observatory_dashboard,
        "TIMEZONE_OPTIONS",
        list(TRANSITION_TIMEZONE_OPTIONS),
    )
    workflow_attributes = {
        "astronomical_time": "calculate_astronomical_time",
        "visibility": "calculate_horizontal_coordinates",
        "solar_system": "calculate_solar_system_body",
        "sky_map": "calculate_sky_map_points",
        "planner": "calculate_observation_plan",
    }
    calls: list[tuple[str, dict[str, object]]] = []

    def capture_workflow(name: str) -> Any:
        def captured(**kwargs: object) -> None:
            calls.append((name, kwargs))
            raise ValueError(f"captured {name}")

        return captured

    for name, attribute in workflow_attributes.items():
        monkeypatch.setattr(
            observatory_dashboard,
            attribute,
            capture_workflow(name),
        )

    for selected_fold in (0, 1):
        calls.clear()
        app_test = _run_observatory_app()
        _set_observer_instant(
            app_test,
            timezone_name="America/New_York",
            local_date=date(2024, 11, 3),
            local_time=time(1, 30, fold=1 - selected_fold),
        )
        app_test.run(timeout=30)

        assert len(app_test.exception) == 0
        assert len(app_test.radio) == 1
        assert app_test.radio[0].value is None
        assert app_test.radio[0].options == ["Earlier occurrence", "Later occurrence"]
        assert all(button.disabled for button in _single_instant_buttons(app_test))
        rendered_text = _civil_time_text(app_test)
        assert "2024-11-03T05:30:00.000000+00:00" in rendered_text
        assert "2024-11-03T06:30:00.000000+00:00" in rendered_text
        assert "UTC offset: `-04:00`" in rendered_text
        assert "UTC offset: `-05:00`" in rendered_text
        assert "fold" not in rendered_text.casefold()

        app_test.radio[0].set_value(selected_fold)
        app_test.run(timeout=30)

        assert app_test.radio[0].value == selected_fold
        assert all(not button.disabled for button in _single_instant_buttons(app_test))

        for label in SINGLE_INSTANT_BUTTON_LABELS:
            _button_by_label(app_test, label).click()
            app_test.run(timeout=30)

        assert [name for name, _ in calls] == list(workflow_attributes)
        for name, kwargs in calls:
            effective_time = kwargs["local_time"]
            assert isinstance(effective_time, time)
            assert effective_time.fold == selected_fold
            if name == "astronomical_time":
                assert kwargs["fold"] == selected_fold
            else:
                assert "fold" not in kwargs


def test_civil_time_selection_resets_for_date_time_and_timezone_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        observatory_dashboard,
        "TIMEZONE_OPTIONS",
        list(TRANSITION_TIMEZONE_OPTIONS),
    )
    app_test = _run_observatory_app()
    _set_observer_instant(
        app_test,
        timezone_name="America/New_York",
        local_date=date(2024, 11, 3),
        local_time=time(1, 30),
    )
    app_test.run(timeout=30)
    app_test.radio[0].set_value(1)
    app_test.run(timeout=30)
    assert app_test.session_state["observer_civil_time_selected_fold"] == 1

    app_test.date_input[0].set_value(date(2024, 11, 4))
    app_test.run(timeout=30)
    assert app_test.session_state["observer_civil_time_selected_fold"] is None

    app_test.date_input[0].set_value(date(2024, 11, 3))
    app_test.run(timeout=30)
    app_test.radio[0].set_value(0)
    app_test.run(timeout=30)
    app_test.time_input[0].set_value(time(1, 31, 15, 123456))
    app_test.run(timeout=30)
    assert app_test.session_state["observer_civil_time_selected_fold"] is None
    assert app_test.session_state["observer_civil_time_fingerprint"] == (
        "America/New_York",
        "2024-11-03",
        1,
        31,
        0,
        0,
    )

    app_test.radio[0].set_value(1)
    app_test.run(timeout=30)
    app_test.selectbox[1].select("UTC")
    app_test.run(timeout=30)
    assert app_test.session_state["observer_civil_time_selected_fold"] is None
    assert app_test.session_state["observer_civil_time_fingerprint"][0] == "UTC"


def test_nonexistent_civil_times_remain_unchanged_and_block_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        observatory_dashboard,
        "TIMEZONE_OPTIONS",
        list(TRANSITION_TIMEZONE_OPTIONS),
    )
    cases = (
        (
            "America/New_York",
            date(2024, 3, 10),
            time(2, 30),
            "2024-03-10T01:59:59.999999-05:00",
            "2024-03-10T03:00:00.000000-04:00",
        ),
        (
            "Australia/Lord_Howe",
            date(2024, 10, 6),
            time(2, 15),
            "2024-10-06T01:59:59.999999+10:30",
            "2024-10-06T02:30:00.000000+11:00",
        ),
    )

    for timezone_name, local_date, local_time, previous_iso, next_iso in cases:
        app_test = _run_observatory_app()
        _set_observer_instant(
            app_test,
            timezone_name=timezone_name,
            local_date=local_date,
            local_time=local_time,
        )
        app_test.run(timeout=30)

        assert len(app_test.exception) == 0
        assert len(app_test.radio) == 0
        assert app_test.time_input[0].value == local_time
        assert app_test.session_state["observer_civil_time_selected_fold"] is None
        assert all(button.disabled for button in _single_instant_buttons(app_test))
        rendered_text = _civil_time_text(app_test)
        assert "This local time does not exist" in rendered_text
        assert previous_iso in rendered_text
        assert next_iso in rendered_text


def test_civil_time_localization_is_complete_without_expanding_timezones() -> None:
    assert tuple(observatory_dashboard.TIMEZONE_OPTIONS) == DEFAULT_TIMEZONE_OPTIONS
    assert set(SUPPORTED_LANGUAGES.values()) == {"en", "ja", "ko", "th"}

    for key in CIVIL_TIME_TRANSLATION_KEYS:
        translated_values = {
            language: translate(key, language)
            for language in SUPPORTED_LANGUAGES.values()
        }
        assert all(translated_values.values())
        assert set(translated_values) == {"en", "ja", "ko", "th"}

    assert "fold" not in translate("civil_time_ambiguous_explanation", "en").casefold()
    assert "fold" not in translate("civil_time_selection_required", "en").casefold()


def test_schedule_reference_timezones_are_available() -> None:
    assert tuple(observatory_dashboard.TIMEZONE_OPTIONS) == DEFAULT_TIMEZONE_OPTIONS


def test_schedule_exposes_explicit_start_and_end_dates() -> None:
    app_test = _run_observatory_app()

    assert [widget.label for widget in app_test.date_input][:3] == [
        "Observation date",
        "Schedule start date",
        "Schedule end date",
    ]


def test_schedule_ambiguous_start_requires_its_own_occurrence() -> None:
    app_test = _run_observatory_app()
    app_test.selectbox[1].select("America/New_York")
    app_test.date_input[1].set_value(date(2026, 11, 1))
    app_test.date_input[2].set_value(date(2026, 11, 1))
    app_test.time_input[1].set_value(time(1, 0))
    app_test.time_input[2].set_value(time(2, 0))
    app_test.run(timeout=30)

    schedule_button = _button_by_label(app_test, "Generate night schedule")
    assert len(app_test.radio) == 1
    assert schedule_button.disabled


def test_schedule_start_and_end_folds_are_independent() -> None:
    app_test = _run_observatory_app()
    app_test.selectbox[1].select("America/New_York")
    app_test.date_input[1].set_value(date(2026, 11, 1))
    app_test.date_input[2].set_value(date(2026, 11, 1))
    app_test.time_input[1].set_value(time(1, 0))
    app_test.time_input[2].set_value(time(1, 30))
    app_test.run(timeout=30)

    assert len(app_test.radio) == 2
    app_test.radio[0].set_value(0)
    app_test.radio[1].set_value(1)
    app_test.run(timeout=30)
    assert all(radio.value in (0, 1) for radio in app_test.radio)
    assert not _button_by_label(app_test, "Generate night schedule").disabled


def test_schedule_nonexistent_start_blocks_generation() -> None:
    app_test = _run_observatory_app()
    app_test.selectbox[1].select("America/New_York")
    app_test.date_input[1].set_value(date(2026, 3, 8))
    app_test.date_input[2].set_value(date(2026, 3, 8))
    app_test.time_input[1].set_value(time(2, 0))
    app_test.time_input[2].set_value(time(3, 0))
    app_test.run(timeout=30)

    assert _button_by_label(app_test, "Generate night schedule").disabled
    assert any("schedule start time does not exist" in error.value for error in app_test.error)
