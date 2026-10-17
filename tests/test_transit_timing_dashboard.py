"""Strict default, form submission and stale-result isolation across languages."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from astroscope.transit_schedule_i18n import SUPPORTED_TRANSIT_LANGUAGES, translate_transit
from astroscope.transit_timing import coordinate_prediction_to_json


def app(language="English"):
    return AppTest.from_string(
        "from astroscope.transit_schedule_dashboard import render_transit_schedule_dashboard\n"
        f"render_transit_schedule_dashboard({language!r})\n",
        default_timeout=30,
    ).run()


def supply_source(at):
    for key, value in (
        ("mission37_source", "synthetic"),
        ("mission37_parameter_set", "joint-1"),
        ("mission37_evidence", "analytic case v1"),
    ):
        at.text_input(key=key).set_value(value)


def submit(at, language="English"):
    label = translate_transit("timing_preview_button", language)
    next(b for b in at.button if b.label == label).click().run()


@pytest.mark.parametrize("language", SUPPORTED_TRANSIT_LANGUAGES)
def test_strict_default_and_unknown_state_survive_form_submission(language):
    at = app(language)
    assert len(at.exception) == 0
    assert at.radio(key="mission37_timing_mode").value == "strict"
    assert not any(b.label == translate_transit("generate_schedule", language) for b in at.button)
    supply_source(at)
    submit(at, language)
    assert len(at.exception) == 0
    assert len(at.error) == 0
    prediction = at.session_state["mission37_coordinate_prediction"]
    assert prediction.timing_uncertainty.value_days is None
    assert at.metric[1].value == translate_transit("timing_unknown", language)
    assert any(translate_transit("timing_ineligible", language) == v.value for v in at.info)
    assert json.loads(coordinate_prediction_to_json(prediction))["observing_eligible"] is False


@pytest.mark.parametrize("language", SUPPORTED_TRANSIT_LANGUAGES)
def test_legacy_requires_acknowledgement_and_mode_changes_clear_cached_results(language):
    at = app(language)
    at.session_state["mission15_transit_schedule_result"] = "stale legacy result"
    at.radio(key="mission37_timing_mode").set_value("legacy").run()
    assert "mission15_transit_schedule_result" not in at.session_state
    assert not any(b.label == translate_transit("generate_schedule", language) for b in at.button)
    assert at.warning[0].value == translate_transit("timing_legacy_warning", language)
    at.checkbox(key="mission37_legacy_ack").check().run()
    assert any(b.label == translate_transit("generate_schedule", language) for b in at.button)
    at.session_state["mission15_transit_schedule_result"] = "stale after revocation"
    at.checkbox(key="mission37_legacy_ack").uncheck().run()
    assert "mission15_transit_schedule_result" not in at.session_state
    at.radio(key="mission37_timing_mode").set_value("strict").run()
    assert "mission15_transit_schedule_result" not in at.session_state
    assert len(at.exception) == 0


@pytest.mark.parametrize("coordinate", ["Unknown", "HJD UTC"])
def test_failed_prediction_clears_previous_downloadable_result(coordinate):
    at = app()
    supply_source(at)
    submit(at)
    assert "mission37_coordinate_prediction" in at.session_state
    at.selectbox(key="mission37_coordinate").set_value(coordinate)
    submit(at)
    assert "mission37_coordinate_prediction" not in at.session_state
    assert len(at.error) == 1
    assert len(at.exception) == 0
    assert len(at.metric) == 0


def test_known_zero_is_distinct_from_unknown_in_preview():
    at = app()
    supply_source(at)
    at.checkbox(key="mission37_epoch_known").check()
    at.text_input(key="mission37_epoch_sigma").set_value("0")
    submit(at)
    assert at.metric[1].value == "0"
    assert at.session_state["mission37_coordinate_prediction"].timing_uncertainty.status == "known"
    at.checkbox(key="mission37_epoch_known").uncheck()
    submit(at)
    assert at.metric[1].value == "Unknown"


def test_core_import_is_offline_and_has_no_astronomy_or_ui_dependency():
    root = Path(__file__).resolve().parents[1]
    script = """
import socket,sys
from importlib.abc import MetaPathFinder
class Block(MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'astropy','streamlit','plotly','numpy','skyfield'}:
            raise RuntimeError('Forbidden dependency: '+fullname)
sys.meta_path.insert(0,Block())
def reject(*args,**kwargs):
    raise RuntimeError('Network is forbidden')
socket.create_connection=reject
socket.socket.connect=reject
from astroscope.transit_timing import (
    StrictTransitEphemeris,TimeCoordinate,EphemerisProvenance,predict_coordinate_transit
)
e=StrictTransitEphemeris('b','2451545','2','3',
    TimeCoordinate('jd','tdb','barycentric','BJD TDB'),
    EphemerisProvenance('synthetic','fit','test','test','v1',True))
assert predict_coordinate_transit(e,1).midpoint_jd_decimal=='2451547'
"""
    subprocess.run([sys.executable, "-c", script], cwd=root, check=True, capture_output=True)


def test_legacy_exports_are_labelled_without_promoting_schema():
    from test_transit_schedule_dashboard import make_ranked_transit

    from astroscope.transit_schedule import TransitScheduleRequest, TransitScheduleResult
    from astroscope.transit_schedule_exports import (
        transit_schedule_to_csv,
        transit_schedule_to_ics,
        transit_schedule_to_json,
    )
    from astroscope.transit_visibility import ObserverSite

    result = TransitScheduleResult(
        ObserverSite("Osaka", 34.6937, 135.5023),
        TransitScheduleRequest(2460000.0, 2460001.0),
        1,
        1,
        (make_ranked_transit(),),
        (),
    )
    payload = json.loads(transit_schedule_to_json(result))
    assert payload["schema_version"] == 1
    assert payload["timing_status"] == "legacy_unvalidated"
    assert payload["events"][0]["timing_status"] == "legacy_unvalidated"
    assert "legacy_unvalidated" in transit_schedule_to_csv(result)
    assert "X-ASTROSCOPE-TIMING-STATUS:LEGACY-UNVALIDATED" in transit_schedule_to_ics(result)
    # Even an empty legacy result remains explicitly labelled.
    assert (
        json.loads(transit_schedule_to_json(replace(result, ranked_transits=())))["timing_status"]
        == "legacy_unvalidated"
    )
