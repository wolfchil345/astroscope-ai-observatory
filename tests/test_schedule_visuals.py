"""Characterization tests for observation-schedule Plotly presentation."""

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import plotly.graph_objects as go

from astroscope.schedule import TimelinePoint
from astroscope.schedule_visuals import ScheduleChartLabels, create_schedule_figure

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_VISUALS_PATH = REPOSITORY_ROOT / "src/astroscope/schedule_visuals.py"
BASELINE_AST_SHA256 = {
    "ScheduleChartLabels": "970d9474e8f64b68fe4ff2173728bbd9acd530230ad1ce75599800664d4daf85",
    "create_schedule_figure": "8a662433f8116c13a6d7fefa3cbace655a59865ca3724b9ecb27bc340e60dd7b",
}
LABELS = ScheduleChartLabels(
    title="Timeline",
    time_axis="Time",
    score_axis="Score",
    altitude="Altitude",
    moon_separation="Moon separation",
    rating="Rating",
    recommended="Recommended",
    yes="Yes",
    no="No",
)


def _point(
    object_key: str,
    local_datetime_iso: str,
    *,
    altitude_degrees: float,
    moon_separation_degrees: float,
    total_score: float,
    rating: str,
    recommended: bool,
) -> TimelinePoint:
    return TimelinePoint(
        object_key=object_key,
        category="catalog",
        local_datetime_iso=local_datetime_iso,
        utc_datetime_iso="2024-01-01T11:00:00+00:00",
        altitude_degrees=altitude_degrees,
        azimuth_degrees=150.0,
        moon_separation_degrees=moon_separation_degrees,
        total_score=total_score,
        rating=rating,
        status="observable",
        recommended=recommended,
        sun_altitude_degrees=-20.0,
    )


def test_schedule_figure_contains_target_trace() -> None:
    points = (
        _point(
            "sirius",
            "2024-01-01T20:00+09:00",
            altitude_degrees=30.0,
            moon_separation_degrees=70.0,
            total_score=65.0,
            rating="very_good",
            recommended=True,
        ),
        _point(
            "sirius",
            "2024-01-01T21:00+09:00",
            altitude_degrees=40.0,
            moon_separation_degrees=72.0,
            total_score=75.0,
            rating="very_good",
            recommended=True,
        ),
    )

    figure = create_schedule_figure(
        points=points,
        display_names={"sirius": "Sirius"},
        rating_names={"very_good": "Very good"},
        labels=LABELS,
    )

    assert len(figure.data) == 1
    assert figure.data[0].name == "Sirius"
    assert list(figure.data[0].y) == [65.0, 75.0]
    assert list(figure.layout.yaxis.range) == [0, 100]


def test_traces_preserve_name_order_type_mode_and_chronology() -> None:
    points = (
        _point(
            "zeta",
            "2024-01-01T22:00+09:00",
            altitude_degrees=50.0,
            moon_separation_degrees=62.0,
            total_score=72.0,
            rating="good",
            recommended=False,
        ),
        _point(
            "sirius",
            "2024-01-01T21:00+09:00",
            altitude_degrees=40.0,
            moon_separation_degrees=72.0,
            total_score=75.0,
            rating="very_good",
            recommended=True,
        ),
        _point(
            "sirius",
            "2024-01-01T20:00+09:00",
            altitude_degrees=30.0,
            moon_separation_degrees=70.0,
            total_score=65.0,
            rating="good",
            recommended=False,
        ),
    )

    figure = create_schedule_figure(
        points=points,
        display_names={"sirius": "Alpha Sirius"},
        rating_names={"very_good": "Very good"},
        labels=LABELS,
    )

    assert len(figure.data) == 2
    assert all(isinstance(trace, go.Scatter) for trace in figure.data)
    assert [trace.type for trace in figure.data] == ["scatter", "scatter"]
    assert [trace.mode for trace in figure.data] == [
        "lines+markers",
        "lines+markers",
    ]
    assert [trace.name for trace in figure.data] == ["Alpha Sirius", "zeta"]
    assert list(figure.data[0].x) == [
        "2024-01-01T20:00+09:00",
        "2024-01-01T21:00+09:00",
    ]
    assert list(figure.data[0].y) == [65.0, 75.0]
    assert list(figure.data[1].x) == ["2024-01-01T22:00+09:00"]
    assert list(figure.data[1].y) == [72.0]


def test_customdata_rating_recommendation_and_hovertemplate_are_unchanged() -> None:
    points = (
        _point(
            "sirius",
            "2024-01-01T20:00+09:00",
            altitude_degrees=30.0,
            moon_separation_degrees=70.0,
            total_score=65.0,
            rating="good",
            recommended=False,
        ),
        _point(
            "sirius",
            "2024-01-01T21:00+09:00",
            altitude_degrees=40.0,
            moon_separation_degrees=72.0,
            total_score=75.0,
            rating="very_good",
            recommended=True,
        ),
    )

    figure = create_schedule_figure(
        points=points,
        display_names={"sirius": "Sirius"},
        rating_names={"very_good": "Very good"},
        labels=LABELS,
    )
    trace = figure.data[0]

    assert [list(row) for row in trace.customdata] == [
        [30.0, 70.0, "good", "No"],
        [40.0, 72.0, "Very good", "Yes"],
    ]
    assert trace.hovertemplate == (
        "<b>%{fullData.name}</b><br>"
        "%{x}<br>"
        "Score: %{y:.1f}<br>"
        "Altitude: %{customdata[0]:.2f}°<br>"
        "Moon separation: %{customdata[1]:.2f}°<br>"
        "Rating: %{customdata[2]}<br>"
        "Recommended: %{customdata[3]}"
        "<extra></extra>"
    )


def test_empty_figure_preserves_exact_layout() -> None:
    figure = create_schedule_figure(
        points=(),
        display_names={},
        rating_names={},
        labels=LABELS,
    )

    assert figure.data == ()
    assert figure.layout.title.text == "Timeline"
    assert figure.layout.height == 620
    assert figure.layout.hovermode == "x unified"
    assert figure.layout.xaxis.title.text == "Time"
    assert figure.layout.xaxis.type == "date"
    assert figure.layout.yaxis.title.text == "Score"
    assert list(figure.layout.yaxis.range) == [0, 100]
    assert figure.layout.margin.to_plotly_json() == {
        "l": 40,
        "r": 40,
        "t": 70,
        "b": 40,
    }


def test_legacy_schedule_visual_imports_preserve_identity_in_fresh_process() -> None:
    script = """
import sys

sys.path.insert(0, sys.argv[1])

import astroscope.schedule as schedule
import astroscope.schedule_visuals as schedule_visuals

assert schedule.ScheduleChartLabels is schedule_visuals.ScheduleChartLabels
assert schedule.create_schedule_figure is schedule_visuals.create_schedule_figure

try:
    schedule.unrelated_missing_attribute
except AttributeError as error:
    assert "unrelated_missing_attribute" in str(error)
else:
    raise AssertionError("Missing schedule attribute did not raise AttributeError")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPOSITORY_ROOT / "src")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_moved_visual_definitions_match_synchronized_main_ast() -> None:
    tree = ast.parse(SCHEDULE_VISUALS_PATH.read_text())

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
