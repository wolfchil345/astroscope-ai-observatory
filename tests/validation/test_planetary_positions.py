"""Mission 53 frozen references, offline replay and deliberate failure controls."""

import ast
import copy
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import datetime

import pytest
from astropy.utils import iers

from astroscope.solar_system import calculate_solar_system_body
from validation import planetary_positions as bench

MANIFEST, POLICY, FIXTURE = bench.load_inputs()


@pytest.fixture(scope="module")
def offline_record(tmp_path_factory):
    folder = tmp_path_factory.mktemp("m53-offline")
    (folder / "sitecustomize.py").write_text(
        "import socket,sys\n"
        "def deny(*a,**k): raise RuntimeError('Mission 53 network disabled')\n"
        "socket.socket.connect=deny\nsocket.socket.connect_ex=deny\n"
        "socket.create_connection=deny\n"
        "sys.modules['skyfield']=None\nsys.modules['skyfield_data']=None\n"
    )
    output = folder / "result.json"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(folder), str(bench.ROOT), str(bench.ROOT / "src")]),
    }
    run = subprocess.run(
        [sys.executable, "-m", "validation.planetary_positions", "--output", str(output)],
        cwd=bench.ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    return json.loads(output.read_text())


@pytest.mark.parametrize("index", range(623), ids=[c["id"] for c in FIXTURE["cases"]])
def test_independent_reference(index, offline_record):
    result = offline_record["results"][index]
    assert result["passed"], result


def test_denominators_and_qualification_boundaries(offline_record):
    assert offline_record["case_count"] == 623
    assert offline_record["failed_cases"] == 0
    assert offline_record["body_counts"] == {b: 89 for b in bench.PLANETS}
    assert offline_record["category_counts"] == MANIFEST["category_counts"]
    assert offline_record["classification_counts"]["boundary_indeterminate"] >= 14
    assert offline_record["summary"]["azimuth_arcsec"]["excluded_count"] >= 7
    assert offline_record["summary"]["equatorial_direction_arcsec"]["excluded_count"] > 0
    assert offline_record["summary"]["distance_km"]["eligible_count"] == 623
    assert all(
        s["eligible_count"] + s["excluded_count"] == 623 for s in offline_record["summary"].values()
    )
    assert not offline_record["physical_arrival_qualification_changed"]
    assert not offline_record["environment"]["network_required"]
    assert not offline_record["environment"]["runtime_reference_imports"]


def test_reference_provenance_and_coverage():
    tree = ast.parse((bench.ROOT / bench.GENERATOR).read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(m.startswith(("astroscope", "astropy", "erfa", "validation")) for m in imports)
    reference = FIXTURE["reference"]
    assert reference["generator_sha256"] == bench.sha(bench.ROOT / bench.GENERATOR)
    assert reference["eop_sha256"] == bench.sha(bench.ROOT / bench.EOP)
    assert reference["policy_sha256"] == bench.sha(bench.ROOT / bench.POLICY)
    previous = json.loads(
        (bench.ROOT / "validation/fixtures/solar_lunar_twilight_v1.json").read_text()
    )
    assert reference["kernel_sha256"] == previous["reference"]["kernel_sha256"]
    assert reference["versions"]["skyfield"] == "1.55"
    for planet in bench.PLANETS:
        cases = [c for c in FIXTURE["cases"] if c["body"] == planet]
        assert {datetime.fromisoformat(c["utc"]).month for c in cases} == set(range(1, 13))
        assert {c["site"]["name"] for c in cases if c["category"] == "season_grid"} == {
            "tokyo",
            "equator",
            "paranal",
            "greenwich",
            "arctic",
            "antarctic",
        }
        assert any(abs(c["reference"]["altitude_degrees"]) > 85 for c in cases)
        assert any(c["reference"]["altitude_degrees"] < 0 for c in cases)


@pytest.mark.parametrize("path", [bench.MANIFEST, *MANIFEST["files"]])
def test_tampered_inputs_rejected(tmp_path, path):
    for name in [bench.MANIFEST, *MANIFEST["files"]]:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bench.ROOT / name, dest)
    with (tmp_path / path).open("a") as f:
        f.write(" ")
    with pytest.raises(ValueError, match="checksum"):
        bench.load_inputs(tmp_path)


@pytest.mark.parametrize(
    "kind", ["duplicate", "missing", "wrong_body", "non_utc", "outside", "nonfinite", "eop_gap"]
)
def test_semantic_input_rejection(kind):
    fixture = copy.deepcopy(FIXTURE)
    rows = json.loads((bench.ROOT / bench.EOP).read_text())["rows"]
    if kind == "duplicate":
        fixture["cases"][1]["id"] = fixture["cases"][0]["id"]
    elif kind == "missing":
        fixture["cases"].pop()
    elif kind == "wrong_body":
        fixture["cases"][0]["body"] = "pluto"
    elif kind == "non_utc":
        fixture["cases"][0]["utc"] = "2024-03-20T00:00:00+09:00"
    elif kind == "outside":
        fixture["cases"][0]["utc"] = "2025-03-20T00:00:00+00:00"
    elif kind == "nonfinite":
        fixture["cases"][0]["reference"]["distance_km"] = math.nan
    else:
        rows.pop(20)
    with pytest.raises(ValueError):
        bench.validate_fixture(fixture, MANIFEST, rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("right_ascension_degrees", 15),
        ("declination_degrees", 5),
        ("altitude_degrees", 5),
        ("azimuth_degrees", 15),
        ("distance_km", 10000000),
        ("distance_au", 1),
        ("solar_elongation_degrees", 5),
        ("moon_separation_degrees", 5),
        ("right_ascension_hms", "12:00:00.000"),
        ("declination_dms", "+80:00:00.00"),
        ("body_key", "pluto"),
        ("ephemeris_name", "de421"),
        ("utc_datetime_iso", "wrong"),
        ("is_above_horizon", None),
        ("status", "wrong"),
        ("cardinal_direction", "wrong"),
    ],
)
def test_output_mutations_fail(field, value, monkeypatch):
    case = next(
        c
        for c in FIXTURE["cases"]
        if c["reference"]["solar_elongation_degrees"] > 10
        and 25 < abs(c["reference"]["altitude_degrees"]) < 60
    )
    with bench.frozen_environment():
        result = bench.body_at(case)
    if value is None:
        value = not result.is_above_horizon
    elif isinstance(value, (int, float)):
        value = getattr(result, field) + value
    monkeypatch.setattr(bench, "body_at", lambda _: replace(result, **{field: value}))
    assert not bench.evaluate(case, POLICY)["passed"]


def test_wrong_epoch_axes_detected(monkeypatch):
    case = next(c for c in FIXTURE["cases"] if c["reference"]["solar_elongation_degrees"] > 10)
    with bench.frozen_environment():
        result = bench.body_at(case)
    # Precession over 24 years is of order 0.3 degrees, not an ICRS-axis coordinate.
    monkeypatch.setattr(
        bench,
        "body_at",
        lambda _: replace(
            result, right_ascension_degrees=(result.right_ascension_degrees + 0.3) % 360
        ),
    )
    assert not bench.evaluate(case, POLICY)["passed"]


def test_zenith_exclusion_does_not_hide_direction_error(monkeypatch):
    case = next(
        c
        for c in FIXTURE["cases"]
        if c["category"] == "zenith" and c["reference"]["solar_elongation_degrees"] > 3
    )
    with bench.frozen_environment():
        result = bench.body_at(case)
    monkeypatch.setattr(bench, "body_at", lambda _: replace(result, altitude_degrees=70))
    evaluated = bench.evaluate(case, POLICY)
    assert evaluated["exclusions"]["azimuth_arcsec"] == "zenith_nadir"
    assert not evaluated["metrics"]["horizontal_direction_arcsec"]["passed"]
    assert not evaluated["passed"]


def test_solar_exclusion_keeps_range_contract(monkeypatch):
    case = next(c for c in FIXTURE["cases"] if c["reference"]["solar_elongation_degrees"] < 3)
    with bench.frozen_environment():
        result = bench.body_at(case)
    monkeypatch.setattr(
        bench, "body_at", lambda _: replace(result, distance_km=result.distance_km * 1000)
    )
    evaluated = bench.evaluate(case, POLICY)
    assert evaluated["exclusions"]["equatorial_direction_arcsec"] == "solar_proximity"
    assert not evaluated["metrics"]["distance_km"]["passed"]
    assert not evaluated["passed"]


def test_frozen_eop_restores_state_on_exception():
    old_download = iers.conf.auto_download
    old_table = iers.earth_orientation_table.get()
    with pytest.raises(RuntimeError), bench.frozen_environment():
        assert not iers.conf.auto_download
        raise RuntimeError("intentional")
    assert iers.conf.auto_download == old_download
    assert iers.earth_orientation_table.get() is old_table


@pytest.mark.parametrize("body", ["pluto", "earth", "ceres", ""])
def test_no_new_body_support(body):
    with pytest.raises(ValueError, match="Unsupported"):
        calculate_solar_system_body(
            body, 0, 0, 0, "UTC", datetime(2024, 1, 1).date(), datetime(2024, 1, 1).time()
        )


def test_wrap_and_sexagesimal_controls():
    assert bench.circular_error(359.999, 0.001, 360) == pytest.approx(0.002)
    assert bench.sexagesimal("23:59:59.000", True) == pytest.approx(360 - 15 / 3600)
    assert bench.sexagesimal("-00:00:01.00") == pytest.approx(-1 / 3600)
    assert bench.direction_error(90, 0, 90, 180) < 1e-9


def test_initial_label_failure_is_retained():
    record = json.loads(
        (
            bench.ROOT / "validation/results/planetary_positions_initial_label_failure.json"
        ).read_text()
    )
    assert record["failed_cases"] == 623 and not record["overall_passed"]
    assert all(not r["contracts"]["cardinal_internal"] for r in record["results"])
    assert all(m["passed"] for r in record["results"] for m in r["metrics"].values())
    assert record["environment"]["git_dirty"] is True


@pytest.mark.parametrize(
    "azimuth,label",
    [
        (0, "north"),
        (45, "northeast"),
        (90, "east"),
        (135, "southeast"),
        (180, "south"),
        (225, "southwest"),
        (270, "west"),
        (315, "northwest"),
    ],
)
def test_cardinal_contract_uses_api_keys(azimuth, label, monkeypatch):
    case = copy.deepcopy(FIXTURE["cases"][0])
    with bench.frozen_environment():
        result = bench.body_at(case)
    monkeypatch.setattr(
        bench,
        "body_at",
        lambda _: replace(result, azimuth_degrees=azimuth, cardinal_direction=label),
    )
    assert bench.evaluate(case, POLICY)["contracts"]["cardinal_internal"]
