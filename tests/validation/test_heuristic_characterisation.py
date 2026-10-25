"""Mission 55 independent scores, sensitivity and adversarial heuristic controls."""

import itertools
import json
import math
import socket
import subprocess
import sys
from dataclasses import fields, replace

import pytest

from astroscope import planner as p
from astroscope import transit_ranking as r
from astroscope import weather as w
from validation.heuristic_characterisation import (
    ROOT,
    candidate,
    controlled_schedule,
    evaluate,
    evaluate_ranking,
    evaluate_schedule,
    load_inputs,
    weights,
)

POLICY, FIXTURE = load_inputs()


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["id"])
def test_independent_scalar_or_plan(case):
    result = evaluate(case, POLICY)
    assert result["passed"], result


@pytest.mark.parametrize("case", FIXTURE["rankings"], ids=lambda c: c["id"])
def test_independent_weighted_score(case):
    result = evaluate_ranking(case, POLICY)
    assert result["passed"], result


@pytest.mark.parametrize("case", FIXTURE["schedules"], ids=lambda c: c["id"])
def test_exhaustive_schedule_control(case, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny)
    result = evaluate_schedule(case)
    assert result["passed"], result
    if case["id"] == "alternating-cost20":
        assert result["selected_path"] == [0, 1, 0]
        assert result["regret"] == 39
        assert result["optimal_paths"] == [[0, 0, 0]]


@pytest.mark.parametrize("profile", range(18))
def test_rank_order_all_input_permutations(profile):
    cases = [c for c in FIXTURE["rankings"] if c["profile"] == profile]
    expected = sorted(
        cases, key=lambda c: (-float(c["expected_total"]), -int(c["full"]), c["name"])
    )
    for permutation in itertools.permutations(cases):
        ranked = r.rank_transit_candidates(
            tuple(candidate(c) for c in permutation), weights=weights(cases[0])
        )
        assert [x.candidate.event.planet_name for x in ranked] == [c["name"] for c in expected]
        assert [x.rank for x in ranked] == [1, 2, 3]


def test_common_weight_scaling_invariance_and_missing_prior():
    cases = FIXTURE["rankings"]
    for name in ["alpha", "beta", "gamma"]:
        a = next(c for c in cases if c["profile"] == 0 and c["name"] == name)
        b = next(c for c in cases if c["profile"] == 1 and c["name"] == name)
        x = r.score_transit_candidate(candidate(a), weights=weights(a))
        y = r.score_transit_candidate(candidate(b), weights=weights(b))
        assert math.isclose(x.total_score, y.total_score, abs_tol=1e-10)
    a, b = [
        next(c for c in cases if c["profile"] == 0 and c["name"] == name)
        for name in ["alpha", "beta"]
    ]
    # Missing depth/brightness is better than known zero-depth/faint under the neutral prior.
    x = r.score_transit_candidate(candidate(a))
    y = r.score_transit_candidate(candidate(b))
    assert x.total_score - y.total_score == pytest.approx(7.5)
    assert x.missing_fields == ("transit_depth_ppm", "host_magnitude")


@pytest.mark.parametrize("field", [f.name for f in fields(r.RankingWeights)])
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_weight_rejection(field, value):
    with pytest.raises(r.TransitRankingError):
        r.RankingWeights(**{field: value})


def test_zero_weights_rejected():
    with pytest.raises(r.TransitRankingError):
        r.RankingWeights(**{f.name: 0 for f in fields(r.RankingWeights)})


def test_tie_order_is_stable_not_global_identifier():
    a = next(c for c in FIXTURE["rankings"] if c["profile"] == 0 and c["name"] == "alpha")
    x = candidate(a)
    # Casefold collisions with otherwise identical keys preserve input order.
    y = replace(
        x,
        event=replace(x.event, planet_name="ALPHA"),
        visibility=replace(x.visibility, planet_name="ALPHA"),
    )
    assert r.rank_transit_candidates((y, x))[0].candidate is y
    assert r.rank_transit_candidates((x, y))[0].candidate is x
    assert controlled_schedule([[70, 70]] * 3).top_target_key == "alpha"
    assert controlled_schedule([[70, 70]] * 3, reverse=True).top_target_key == "beta"


def test_temporal_sampling_can_skip_preferred_target():
    scores = [[90, 89], [89, 90], [90, 89]]
    coarse = controlled_schedule(scores, interval=120)
    hourly = controlled_schedule(scores, interval=60)
    half_hour = controlled_schedule(scores, interval=30)
    assert [b.object_key for b in coarse.schedule_blocks] == ["alpha"]
    assert [b.object_key for b in hourly.schedule_blocks] == ["alpha", "beta", "alpha"]
    assert [b.object_key for b in half_hour.schedule_blocks] == ["alpha", "beta", "alpha"]
    assert (
        coarse.scheduled_minutes == hourly.scheduled_minutes == half_hour.scheduled_minutes == 180
    )


@pytest.mark.parametrize(
    "field", list(next(c for c in FIXTURE["cases"] if c["family"] == "weather")["inputs"])
)
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), None])
def test_weather_required_numeric_inputs(field, value):
    inputs = dict(next(c for c in FIXTURE["cases"] if c["family"] == "weather")["inputs"])
    inputs[field] = value
    with pytest.raises((ValueError, TypeError)):
        w.calculate_weather_score(**inputs)


@pytest.mark.parametrize(
    "key,direction",
    [
        ("cloud_cover_percent", -1),
        ("precipitation_probability_percent", -1),
        ("precipitation_mm", -1),
        ("visibility_m", 1),
        ("relative_humidity_percent", -1),
        ("wind_speed_kmh", -1),
        ("wind_gusts_kmh", -1),
    ],
)
def test_weather_monotonic_sweeps(key, direction):
    base = dict(
        cloud_cover_percent=25,
        precipitation_probability_percent=25,
        precipitation_mm=0,
        visibility_m=10000,
        relative_humidity_percent=70,
        wind_speed_kmh=20,
        wind_gusts_kmh=10,
    )
    xs = (
        [0, 0.499, 0.5, 1, 10]
        if key == "precipitation_mm"
        else ([0, 1000, 10000, 20000, 30000] if key == "visibility_m" else list(range(101)))
    )
    values = [w.calculate_weather_score(**dict(base, **{key: x})) for x in xs]
    assert all(direction * (b - a) >= 0 for a, b in zip(values[:-1], values[1:], strict=True))


def test_planner_thresholds_and_moon_exception():
    args = dict(
        object_key="synthetic",
        category="catalog",
        altitude_degrees=20,
        azimuth_degrees=0,
        cardinal_direction="north",
        airmass=2,
        moon_separation_degrees=30,
        sun_altitude_degrees=-18,
        status="observable",
        minimum_altitude_degrees=20,
        minimum_moon_separation_degrees=30,
        minimum_score=0,
    )
    assert p.create_plan_entry(**args).recommended
    assert not p.create_plan_entry(**dict(args, minimum_altitude_degrees=20.001)).recommended
    assert not p.create_plan_entry(**dict(args, minimum_moon_separation_degrees=30.001)).recommended
    assert p.create_plan_entry(
        **dict(args, object_key="moon", moon_separation_degrees=0)
    ).recommended


def test_regeneration_is_independent_and_byte_identical():
    code = """
import sys, socket, json
from pathlib import Path
def deny(*a, **k): raise AssertionError('Network forbidden')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
for name in ['astroscope','astropy','numpy','erfa']: sys.modules[name]=None
from validation.reference_generation.heuristic_characterisation import generate
actual=json.dumps(generate(),indent=2,sort_keys=True,allow_nan=False)+'\\n'
assert actual==Path('validation/fixtures/heuristic_characterisation_v1.json').read_text()
"""
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, timeout=30)


def test_offline_runner(tmp_path):
    output = tmp_path / "result.json"
    code = """
import sys,socket
def deny(*a,**k): raise AssertionError('Network forbidden')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
sys.modules['validation.reference_generation.heuristic_characterisation']=None
from validation.heuristic_characterisation import main
sys.argv=['benchmark','--output',sys.argv[1]]
raise SystemExit(main())
"""
    subprocess.run([sys.executable, "-c", code, str(output)], cwd=ROOT, check=True, timeout=60)
    result = json.loads(output.read_text())
    assert result["case_count"] == 355
    assert result["overall_passed"]
    assert result["maximum_schedule_regret"] == 39
    assert not result["physical_arrival_qualification_changed"]
    assert not result["observational_calibration_established"]


@pytest.mark.parametrize("index", range(3))
def test_weight_tradeoff_reversal(index):
    from validation.heuristic_characterisation import weight_tradeoffs

    row = weight_tradeoffs(FIXTURE)[index]
    assert row["passed"], row
    assert row["a_minus_b"] == pytest.approx([20, -100, 100][index])
