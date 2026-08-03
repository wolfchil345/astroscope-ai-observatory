"""Characterization tests for the AstroScope Streamlit composition root."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from astroscope.i18n import SUPPORTED_LANGUAGES

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPOSITORY_ROOT / "app.py"


@dataclass(frozen=True, slots=True)
class RecordedPage:
    """Captured arguments from one ``st.Page`` call."""

    page: object
    title: str
    icon: str
    default: bool = False


class RecordedNavigation:
    """Small navigation object that records whether ``run`` was called."""

    def __init__(self, pages: list[RecordedPage]) -> None:
        self.pages = pages
        self.run_count = 0

    def run(self) -> None:
        self.run_count += 1


class RecordedSidebar:
    """Small sidebar replacement for the shared language selector."""

    def __init__(self) -> None:
        self.selected = "English"
        self.selectbox_calls: list[tuple[str, list[str]]] = []

    def selectbox(self, label: str, *, options: list[str]) -> str:
        self.selectbox_calls.append((label, options))
        return self.selected


class RecordedStreamlit(ModuleType):
    """Streamlit replacement for composition and delegation tests."""

    def __init__(self) -> None:
        super().__init__("streamlit")
        self.sidebar = RecordedSidebar()
        self.page_config_calls: list[dict[str, object]] = []
        self.pages: list[RecordedPage] = []
        self.navigation_calls: list[RecordedNavigation] = []

    def set_page_config(self, **kwargs: object) -> None:
        self.page_config_calls.append(kwargs)

    def Page(
        self,
        page: object,
        *,
        title: str,
        icon: str,
        default: bool = False,
    ) -> RecordedPage:
        result = RecordedPage(
            page=page,
            title=title,
            icon=icon,
            default=default,
        )
        self.pages.append(result)
        return result

    def navigation(self, pages: list[RecordedPage]) -> RecordedNavigation:
        result = RecordedNavigation(pages)
        self.navigation_calls.append(result)
        return result


@pytest.fixture
def loaded_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, RecordedStreamlit]:
    """Load a fresh composition-root module against recorded Streamlit calls."""

    for module_name in (
        "astroscope.exoplanet_dashboard",
        "astroscope.gaia_dashboard",
        "astroscope.light_curve_dashboard",
        "astroscope.observatory_dashboard",
        "astroscope.transit_schedule_dashboard",
    ):
        importlib.import_module(module_name)

    recorded_streamlit = RecordedStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", recorded_streamlit)

    specification = importlib.util.spec_from_file_location(
        "mission22_app_under_test",
        APP_PATH,
    )
    assert specification is not None
    assert specification.loader is not None

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module, recorded_streamlit


def test_page_configuration_is_the_first_streamlit_command() -> None:
    script = """
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
calls = []

class GuardedStreamlit(types.ModuleType):
    def __getattr__(self, name):
        def record(*args, **kwargs):
            calls.append((name, args, kwargs))
        return record

guarded_streamlit = GuardedStreamlit("streamlit")
guarded_streamlit.__file__ = "<guarded-streamlit>"
sys.modules["streamlit"] = guarded_streamlit
import app

assert [name for name, _, _ in calls] == ["set_page_config"], calls
assert calls[0][2] == {
    "page_title": "AstroScope AI Observatory",
    "page_icon": "🔭",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_navigation_metadata_and_default_page_are_unchanged(
    loaded_app: tuple[Any, RecordedStreamlit],
) -> None:
    app_module, recorded_streamlit = loaded_app

    app_module.run_app()

    assert len(recorded_streamlit.navigation_calls) == 1
    navigation = recorded_streamlit.navigation_calls[0]
    assert navigation.pages == recorded_streamlit.pages
    assert navigation.run_count == 1
    assert [page.page for page in navigation.pages] == [
        app_module.render_observatory_page,
        app_module.render_light_curve_page,
        app_module.render_gaia_page,
        app_module.render_exoplanet_page,
        app_module.render_transit_schedule_page,
    ]
    assert [page.title for page in navigation.pages] == [
        "Observatory",
        "Light Curve Laboratory",
        "Gaia DR3 Explorer",
        "Exoplanet Explorer",
        "Transit Schedule",
    ]
    assert [page.icon for page in navigation.pages] == ["🔭", "📈", "🛰️", "🪐", "🗓️"]
    assert [page.default for page in navigation.pages] == [True, False, False, False, False]


def test_select_language_preserves_label_options_and_mapping(
    loaded_app: tuple[Any, RecordedStreamlit],
) -> None:
    app_module, recorded_streamlit = loaded_app

    for language_name, language_code in SUPPORTED_LANGUAGES.items():
        recorded_streamlit.sidebar.selected = language_name
        assert app_module.select_language() == language_code

    assert recorded_streamlit.sidebar.selectbox_calls == [
        (
            "Language / 言語 / 언어 / ภาษา",
            list(SUPPORTED_LANGUAGES),
        )
    ] * len(SUPPORTED_LANGUAGES)


def test_render_observatory_page_delegates_once_with_selected_language(
    loaded_app: tuple[Any, RecordedStreamlit],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_module, _ = loaded_app
    rendered_languages: list[str] = []
    monkeypatch.setattr(app_module, "select_language", lambda: "th")
    monkeypatch.setattr(
        app_module,
        "render_observatory_dashboard",
        rendered_languages.append,
    )

    app_module.render_observatory_page()

    assert rendered_languages == ["th"]


def test_specialist_page_wrappers_pass_selected_language_unchanged(
    loaded_app: tuple[Any, RecordedStreamlit],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_module, _ = loaded_app
    monkeypatch.setattr(app_module, "select_language", lambda: "ko")

    wrapper_and_renderer_names = (
        ("render_light_curve_page", "render_light_curve_dashboard"),
        ("render_gaia_page", "render_gaia_dashboard"),
        ("render_exoplanet_page", "render_exoplanet_dashboard"),
        ("render_transit_schedule_page", "render_transit_schedule_dashboard"),
    )

    for wrapper_name, renderer_name in wrapper_and_renderer_names:
        rendered_languages: list[str] = []
        monkeypatch.setattr(app_module, renderer_name, rendered_languages.append)
        getattr(app_module, wrapper_name)()
        assert rendered_languages == ["ko"]


def test_app_source_contains_only_composition_and_thin_wrappers() -> None:
    tree = ast.parse(APP_PATH.read_text())

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assignments = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    assert imported_modules == {
        "astroscope.exoplanet_dashboard",
        "astroscope.gaia_dashboard",
        "astroscope.i18n",
        "astroscope.light_curve_dashboard",
        "astroscope.observatory_dashboard",
        "astroscope.transit_schedule_dashboard",
    }
    assert "TIMEZONE_OPTIONS" not in assignments
    assert set(functions) == {
        "select_language",
        "render_observatory_page",
        "render_light_curve_page",
        "render_gaia_page",
        "render_exoplanet_page",
        "render_transit_schedule_page",
        "run_app",
    }
    assert ast.unparse(functions["render_observatory_page"]) == (
        "def render_observatory_page() -> None:\n"
        "    language = select_language()\n"
        "    render_observatory_dashboard(language)"
    )
