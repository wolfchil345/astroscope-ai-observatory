"""Mission 34 evidence, offline execution and failure-sensitivity checks."""

from __future__ import annotations

import ast
import copy
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest
from astropy.coordinates import solar_system_ephemeris
from astropy.utils import iers

from validation import solar_lunar_twilight as bench

POLICY, FIXTURE = bench.load_inputs()


@pytest.fixture(scope="module")
def offline_record(tmp_path_factory):
    folder = tmp_path_factory.mktemp("m34-offline")
    (folder / "sitecustomize.py").write_text(
        "import socket, sys\n"
        "def deny(*a, **k): raise RuntimeError('Mission 34 network disabled')\n"
        "socket.socket.connect = deny\nsocket.socket.connect_ex = deny\n"
        "socket.create_connection = deny\n"
        "sys.modules['skyfield'] = None\nsys.modules['skyfield_data'] = None\n"
    )
    output = folder / "record.json"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(folder), str(bench.ROOT), str(bench.ROOT / "src")]),
    }
    result = subprocess.run(
        [sys.executable, "-m", "validation.solar_lunar_twilight", "--output", str(output)],
        cwd=bench.ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text())


@pytest.mark.parametrize(
    "index", range(len(FIXTURE["cases"])), ids=[c["id"] for c in FIXTURE["cases"]]
)
def test_snapshot_reference(index, offline_record):
    result = offline_record["results"][index]
    assert result["status"] == "passed", result


@pytest.mark.parametrize(
    "index", range(len(FIXTURE["windows"])), ids=[c["id"] for c in FIXTURE["windows"]]
)
def test_event_window_reference(index, offline_record):
    result = offline_record["windows"][index]
    assert result["status"] == "passed", result
    assert result["actual"]["state"] == result["reference"]["state"]
    assert len(result["actual"]["events"]) == len(result["reference"]["events"])


def test_full_record_statistics_and_exclusions(offline_record):
    r = offline_record
    assert r["case_count"] == 354 and r["window_count"] == 120
    assert r["event_count"] == 188
    assert r["failed_cases"] == r["failed_windows"] == 0
    assert r["illumination_relative_diagnostic"]["excluded_near_new"] > 0
    assert any("boundary_indeterminate" in c["classifications"].values() for c in r["results"])
    for metric, summary in r["summary"].items():
        assert summary["count"] > 0, metric
        assert summary["inside_tolerance_percent"] == 100, metric
        assert summary["mean"] <= summary["rms"] + 1e-12
        assert summary["median"] <= summary["maximum"]
        assert summary["worst_case"] is not None
    assert len(r["event_summary_by_threshold"]) == 5
    assert all(len(v) == 64 for v in r["input_sha256"].values())


def test_coverage_and_no_events():
    assert len({c["site"]["name"] for c in FIXTURE["cases"]}) == 6
    phase = [c["reference"]["illumination_physical"] for c in FIXTURE["cases"]]
    assert min(phase) < 0.001 and max(phase) > 0.999
    assert any(0.4 < v < 0.6 for v in phase)
    for body in ["sun", "moon"]:
        for state in ["always_above", "always_below"]:
            assert any(
                w["body"] == body and w["reference"]["state"] == state for w in FIXTURE["windows"]
            )
    assert any(w["threshold"] == -18 and not w["reference"]["events"] for w in FIXTURE["windows"])
    assert all(
        datetime.fromisoformat(w["start_utc"]).date() != datetime.fromisoformat(w["end_utc"]).date()
        for w in FIXTURE["windows"]
    )
    assert {w["threshold"] for w in FIXTURE["windows"]} == {0, -6, -12, -18}


def test_independent_generator_provenance():
    tree = ast.parse(bench.GENERATOR.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(n.startswith(("astroscope", "astropy", "erfa", "validation")) for n in imports)
    ref = FIXTURE["reference"]
    assert bench.sha(bench.GENERATOR) == ref["generator_sha256"]
    assert bench.sha(bench.EOP) == ref["eop_sha256"]
    assert bench.sha(bench.POLICY) == ref["policy_sha256"]
    assert ref["versions"]["skyfield"] == "1.55"
    assert ref["kernel"] == "de421.bsp" and len(ref["kernel_sha256"]) == 64


@pytest.mark.parametrize("kind", ["manifest", "fixture", "policy"])
def test_corruption_fails(kind, tmp_path, monkeypatch):
    manifest = json.loads(bench.MANIFEST.read_text())
    target = (
        "validation/fixtures/solar_lunar_twilight_v1.json"
        if kind != "policy"
        else ("validation/manifests/solar_lunar_twilight_policy_v1.json")
    )
    manifest["files"][target] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(bench, "MANIFEST", path)
    if kind != "manifest":
        monkeypatch.setattr(bench, "EXPECTED_MANIFEST_SHA256", bench.sha(path))
    with pytest.raises(ValueError, match="checksum"):
        bench.load_inputs()


@pytest.mark.parametrize(
    "metric",
    [
        "sun_altitude",
        "moon_altitude",
        "azimuth",
        "illumination",
        "separation",
        "horizon",
        "darkness",
    ],
)
def test_snapshot_perturbations_fail(metric, monkeypatch):
    from dataclasses import replace

    original = bench.body_at
    case = FIXTURE["cases"][0]

    def wrong(site, dt, body):
        result = original(site, dt, body)
        if metric == "sun_altitude" and body == "sun":
            return replace(result, altitude_degrees=result.altitude_degrees + 1)
        if metric == "moon_altitude" and body == "moon":
            return replace(result, altitude_degrees=result.altitude_degrees + 1)
        if metric == "azimuth":
            return replace(result, azimuth_degrees=(result.azimuth_degrees + 5) % 360)
        if metric == "illumination":
            return replace(
                result, moon_illumination_fraction=result.moon_illumination_fraction + 0.1
            )
        if metric == "separation":
            return replace(result, moon_separation_degrees=result.moon_separation_degrees + 1)
        if metric == "horizon":
            return replace(result, is_above_horizon=not result.is_above_horizon)
        return result

    monkeypatch.setattr(bench, "body_at", wrong)
    if metric == "darkness":
        monkeypatch.setattr(bench, "calculate_darkness_score", lambda _: 100.0)
    with bench.frozen_environment():
        result = bench.evaluate_snapshot(case, POLICY)
    assert result["status"] == "failed", result


def test_event_solver_known_roots_and_hidden_pair():
    rising = bench.search_events(lambda t: (t - 40000) / 3600, 0, POLICY)
    assert rising["events"][0]["seconds"] == pytest.approx(40000, abs=0.02)
    assert rising["events"][0]["direction"] == "rising"
    # Both crossings lie between hourly samples; extremum refinement must find them.
    pair = bench.search_events(lambda t: ((t - 19000) / 100) ** 2 - 1, 0, POLICY)
    assert [e["seconds"] for e in pair["events"]] == pytest.approx([18900, 19100], abs=0.02)
    tangent = bench.search_events(lambda t: ((t - 18000) / 100) ** 2, 0, POLICY)
    assert tangent["events"] == [] and tangent["state"] == "grazing_indeterminate"
    for value, state in [(1, "always_above"), (-1, "always_below")]:
        result = bench.search_events(lambda t, value=value: value, 0, POLICY)
        assert result["events"] == [] and result["state"] == state


def test_event_time_and_missing_event_fail():
    window = copy.deepcopy(next(w for w in FIXTURE["windows"] if w["reference"]["events"]))
    start = datetime.fromisoformat(window["start_utc"])
    window["reference"] = {
        "state": "crossings",
        "minimum_altitude": -10,
        "maximum_altitude": 10,
        "events": [{"seconds": 40000, "direction": "rising", "slope_arcsec_per_second": 1}],
    }
    window["body"], window["threshold"] = "sun", 0.0

    def shifted(body, dt):
        return SimpleNamespace(altitude_degrees=((dt - start).total_seconds() - 40100) / 3600)

    result = bench.evaluate_window(window, POLICY, shifted)
    assert "event_0" in result["failures"]
    result = bench.evaluate_window(
        window, POLICY, lambda *args: SimpleNamespace(altitude_degrees=10.0)
    )
    assert "event_topology" in result["failures"]


def test_ill_conditioned_timing_is_explicit():
    window = copy.deepcopy(next(w for w in FIXTURE["windows"] if w["reference"]["events"]))
    start = datetime.fromisoformat(window["start_utc"])
    window["reference"] = {
        "state": "crossings",
        "minimum_altitude": -1,
        "maximum_altitude": 1,
        "events": [{"seconds": 40000, "direction": "rising", "slope_arcsec_per_second": 0.1}],
    }
    window["body"], window["threshold"] = "sun", 0.0
    result = bench.evaluate_window(
        window,
        POLICY,
        lambda b, dt: SimpleNamespace(
            altitude_degrees=((dt - start).total_seconds() - 40100) / 36000
        ),
    )
    assert result["status"] == "passed"
    assert result["event_comparisons"][0]["excluded_metrics"]
    assert result["event_comparisons"][0]["errors"]["sun_event_seconds"] > 10


def test_wraparound_and_nonfinite():
    assert bench.circular_error(359.99, 0.01, 360) == pytest.approx(0.02)
    with pytest.raises(ValueError, match="Nonfinite"):
        bench.search_events(lambda _: math.nan, 0, POLICY)


def test_global_state_restored():
    table, ephemeris = iers.earth_orientation_table.get(), solar_system_ephemeris.get()
    download = iers.conf.auto_download
    with pytest.raises(RuntimeError), bench.frozen_environment():
        raise RuntimeError("deliberate failure")
    assert iers.earth_orientation_table.get() is table
    assert solar_system_ephemeris.get() == ephemeris
    assert iers.conf.auto_download == download


def test_cli_failed_record_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bench,
        "run_benchmark",
        lambda _: {
            "aggregate_status": "failed",
            "case_count": 1,
            "window_count": 1,
            "event_count": 0,
        },
    )
    monkeypatch.setattr(sys, "argv", ["benchmark", "--output", str(tmp_path / "failed.json")])
    assert bench.main() == 1
