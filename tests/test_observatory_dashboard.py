"""Characterization tests for the Observatory presentation boundary."""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from astroscope import observatory_dashboard

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPOSITORY_ROOT / "app.py"
OBSERVATORY_PATH = REPOSITORY_ROOT / "src/astroscope/observatory_dashboard.py"
BASELINE_BODY_SHA256 = "6553386c8949508da8437ca6fc3196ec53ffd67098016443e71f99bf5e2227ed"
SUPPORTED_LANGUAGES_FOR_APPTEST = ("English", "日本語", "한국어", "ไทย")


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
    assert len(app_test.sidebar.selectbox) == 1
    language_selector = app_test.sidebar.selectbox[0]
    assert language_selector.label == "Language / 言語 / 언어 / ภาษา"
    assert language_selector.options == list(SUPPORTED_LANGUAGES_FOR_APPTEST)

    expected_state_keys = {
        "latitude_osaka",
        "longitude_osaka",
        "elevation_osaka",
        "timezone_osaka",
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

    app_test.sidebar.selectbox[0].select("日本語")
    app_test.run(timeout=30)

    assert len(app_test.exception) == 0
    assert app_test.title[0].value == "🔭 AstroScope AI 天文台"
