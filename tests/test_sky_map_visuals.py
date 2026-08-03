"""Characterization tests for local sky-map Plotly presentation."""

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import plotly.graph_objects as go

from astroscope.sky_map import SkyMapPoint
from astroscope.sky_map_visuals import SkyMapLabels, create_sky_map_figure

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKY_MAP_VISUALS_PATH = REPOSITORY_ROOT / "src/astroscope/sky_map_visuals.py"
BASELINE_AST_SHA256 = {
    "SkyMapLabels": "02dfd18e57c6d792429c3c46f40846ad22367f3ed821054107a7f3852ea6b1a1",
    "create_sky_map_figure": "edcd0de7e16176e2ebe20ea604acb0b76c9175979240777e8a54c8428f5fd8fd",
}
LABELS = SkyMapLabels(
    title="Test sky",
    catalog_trace="Catalogue",
    solar_system_trace="Solar System",
    altitude="Altitude",
    azimuth="Azimuth",
    direction="Direction",
    status="Status",
    zenith="Zenith",
    horizon="Horizon",
)
DIRECTION_NAMES = {
    "north": "North",
    "northeast": "Northeast",
    "east": "East",
    "southeast": "Southeast",
    "south": "South",
    "southwest": "Southwest",
    "west": "West",
    "northwest": "Northwest",
}


def _point(
    object_key: str,
    category: str,
    *,
    altitude_degrees: float,
    azimuth_degrees: float,
    cardinal_direction: str,
    status: str,
    is_above_horizon: bool = True,
) -> SkyMapPoint:
    return SkyMapPoint(
        object_key=object_key,
        category=category,
        altitude_degrees=altitude_degrees,
        azimuth_degrees=azimuth_degrees,
        radial_distance_degrees=90.0 - altitude_degrees,
        cardinal_direction=cardinal_direction,
        status=status,
        is_above_horizon=is_above_horizon,
    )


def test_figure_only_plots_above_horizon_points() -> None:
    points = (
        _point(
            "visible",
            "catalog",
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            cardinal_direction="south",
            status="observable",
        ),
        _point(
            "hidden",
            "catalog",
            altitude_degrees=-20.0,
            azimuth_degrees=0.0,
            cardinal_direction="north",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )

    figure = create_sky_map_figure(
        points=points,
        display_names={
            "visible": "Visible",
            "hidden": "Hidden",
        },
        direction_names={
            "north": "North",
            "south": "South",
        },
        status_names={
            "observable": "Observable",
            "below_horizon": "Below horizon",
        },
        labels=LABELS,
    )

    assert len(figure.data) == 1
    assert list(figure.data[0].text) == ["Visible"]
    assert list(figure.data[0].r) == [45.0]
    assert list(figure.data[0].theta) == [180.0]


def test_sky_map_orientation_and_layout_are_unchanged() -> None:
    figure = create_sky_map_figure(
        points=(),
        display_names={},
        direction_names=DIRECTION_NAMES,
        status_names={},
        labels=LABELS,
    )

    assert figure.data == ()
    assert figure.layout.title.text == "Test sky"
    assert figure.layout.height == 720
    assert figure.layout.showlegend is True
    assert figure.layout.margin.to_plotly_json() == {
        "l": 40,
        "r": 40,
        "t": 80,
        "b": 40,
    }
    assert list(figure.layout.polar.radialaxis.range) == [0, 90]
    assert figure.layout.polar.radialaxis.tickmode == "array"
    assert list(figure.layout.polar.radialaxis.tickvals) == [0, 30, 60, 90]
    assert list(figure.layout.polar.radialaxis.ticktext) == [
        "Zenith",
        "60°",
        "30°",
        "Horizon",
    ]
    assert figure.layout.polar.angularaxis.rotation == 90
    assert figure.layout.polar.angularaxis.direction == "clockwise"
    assert figure.layout.polar.angularaxis.tickmode == "array"
    assert list(figure.layout.polar.angularaxis.tickvals) == [
        0,
        45,
        90,
        135,
        180,
        225,
        270,
        315,
    ]
    assert list(figure.layout.polar.angularaxis.ticktext) == list(
        DIRECTION_NAMES.values()
    )


def test_traces_preserve_category_order_type_names_markers_and_values() -> None:
    points = (
        _point(
            "mars",
            "solar_system",
            altitude_degrees=70.0,
            azimuth_degrees=200.0,
            cardinal_direction="south",
            status="observable",
        ),
        _point(
            "sirius",
            "catalog",
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            cardinal_direction="south",
            status="observable",
        ),
        _point(
            "fallback_object",
            "catalog",
            altitude_degrees=30.0,
            azimuth_degrees=90.0,
            cardinal_direction="east",
            status="low_altitude",
        ),
    )

    figure = create_sky_map_figure(
        points=points,
        display_names={"mars": "Mars", "sirius": "Sirius"},
        direction_names=DIRECTION_NAMES,
        status_names={"observable": "Observable"},
        labels=LABELS,
    )

    assert len(figure.data) == 2
    assert all(isinstance(trace, go.Scatterpolar) for trace in figure.data)
    assert [trace.type for trace in figure.data] == ["scatterpolar", "scatterpolar"]
    assert [trace.name for trace in figure.data] == ["Catalogue", "Solar System"]
    assert [trace.mode for trace in figure.data] == [
        "markers+text",
        "markers+text",
    ]
    assert [trace.textposition for trace in figure.data] == [
        "top center",
        "top center",
    ]
    assert [trace.marker.size for trace in figure.data] == [12, 15]
    assert list(figure.data[0].r) == [45.0, 60.0]
    assert list(figure.data[0].theta) == [180.0, 90.0]
    assert list(figure.data[0].text) == ["Sirius", "fallback_object"]
    assert list(figure.data[1].r) == [20.0]
    assert list(figure.data[1].theta) == [200.0]
    assert list(figure.data[1].text) == ["Mars"]


def test_customdata_translations_fallbacks_and_hovertemplate_are_unchanged() -> None:
    points = (
        _point(
            "sirius",
            "catalog",
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            cardinal_direction="south",
            status="observable",
        ),
        _point(
            "mars",
            "solar_system",
            altitude_degrees=20.0,
            azimuth_degrees=90.0,
            cardinal_direction="east",
            status="low_altitude",
        ),
    )

    figure = create_sky_map_figure(
        points=points,
        display_names={"sirius": "Sirius", "mars": "Mars"},
        direction_names={"south": "South"},
        status_names={"observable": "Observable"},
        labels=LABELS,
    )

    assert [list(row) for row in figure.data[0].customdata] == [
        [45.0, 180.0, "South", "Observable"]
    ]
    assert [list(row) for row in figure.data[1].customdata] == [
        [20.0, 90.0, "east", "low_altitude"]
    ]
    expected_hovertemplate = (
        "<b>%{text}</b><br>"
        "Altitude: %{customdata[0]:.2f}°<br>"
        "Azimuth: %{customdata[1]:.2f}°<br>"
        "Direction: %{customdata[2]}<br>"
        "Status: %{customdata[3]}"
        "<extra></extra>"
    )
    assert all(
        trace.hovertemplate == expected_hovertemplate for trace in figure.data
    )


def test_empty_category_and_empty_point_behavior_are_unchanged() -> None:
    solar_only = create_sky_map_figure(
        points=(
            _point(
                "mars",
                "solar_system",
                altitude_degrees=20.0,
                azimuth_degrees=90.0,
                cardinal_direction="east",
                status="observable",
            ),
        ),
        display_names={},
        direction_names={},
        status_names={},
        labels=LABELS,
    )
    empty = create_sky_map_figure(
        points=(),
        display_names={},
        direction_names={},
        status_names={},
        labels=LABELS,
    )

    assert len(solar_only.data) == 1
    assert solar_only.data[0].name == "Solar System"
    assert list(solar_only.data[0].text) == ["mars"]
    assert empty.data == ()


def test_legacy_sky_map_visual_imports_preserve_identity_in_fresh_process() -> None:
    script = """
import sys

sys.path.insert(0, sys.argv[1])

import astroscope.sky_map as sky_map
import astroscope.sky_map_visuals as sky_map_visuals

assert sky_map.SkyMapLabels is sky_map_visuals.SkyMapLabels
assert sky_map.create_sky_map_figure is sky_map_visuals.create_sky_map_figure

try:
    sky_map.unrelated_missing_attribute
except AttributeError as error:
    assert "unrelated_missing_attribute" in str(error)
else:
    raise AssertionError("Missing sky_map attribute did not raise AttributeError")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPOSITORY_ROOT / "src")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_moved_visual_definitions_match_synchronized_main_ast() -> None:
    tree = ast.parse(SKY_MAP_VISUALS_PATH.read_text())

    for name, expected_digest in BASELINE_AST_SHA256.items():
        node = next(
            node
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name
        )
        serialized_node = ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )
        digest = hashlib.sha256(serialized_node.encode()).hexdigest()

        assert digest == expected_digest
