"""Mission 58 independent finite-grid oracle and production regression checks."""

import hashlib
import itertools
import math
from pathlib import Path

import numpy as np
import pytest
from astropy.timeseries import BoxLeastSquares

from astroscope._physical_bls import physical_bls_power
from astroscope.light_curve import LightCurveMetadata, build_light_curve
from astroscope.light_curve_transit_search import search_box_least_squares
from validation.physical_bls_reference import brute_grid


@pytest.mark.parametrize(
    "seed,period,objective,weighted",
    list(itertools.product(range(8), [1.0, 1.25, 1.5], ["snr", "likelihood"], [False, True])),
)
def test_exact_fraction_grid(seed, period, objective, weighted):
    rng = np.random.default_rng(seed)
    t = np.arange(24) / 32
    y = rng.integers(-5, 6, len(t)).astype(float)
    errors = 2.0 ** (np.arange(len(t)) % 3) if weighted else np.ones(len(t))
    durations = [0.125, 0.25, 0.375]
    ref = brute_grid(t, y, errors, period, durations, 2, objective)
    out = physical_bls_power(t, y, errors if weighted else None, [period], durations, 2, objective)
    assert out.power[0] == pytest.approx(ref[0]["power"], abs=1e-8)
    match = [
        r
        for r in ref
        if r["duration"] == out.duration[0] and r["transit_time"] == out.transit_time[0]
    ]
    assert match
    for k, target in [("depth", "depth"), ("depth_err", "depth_error"), ("depth_snr", "depth_snr")]:
        assert getattr(out, k)[0] == pytest.approx(match[0][target], abs=1e-8)


def test_mission57_witness_is_corrected_and_full_periods_reranked():
    t = np.array([0, 0.02, 0.82, 0.92, 0.5, 0.6])
    y = np.array([0, 0, 0, 10, 10, 10])
    out = physical_bls_power(t, y, np.ones(6), [1.0], [0.2], 2, "snr")
    assert out.depth_snr[0] == pytest.approx(math.sqrt(75))
    assert out.depth_snr[0] < math.sqrt(150)
    # Exercise production minimum count and compare every newly computed period,
    # independently of the upstream fast periodogram and its previous ranking.
    times = np.concatenate([t + i for i in range(4)])
    curve = build_light_curve(
        metadata=LightCurveMetadata("witness", "flux", "elapsed days"),
        times=times,
        values=np.tile(y, 4),
        uncertainties=np.ones(24),
    )
    result = search_box_least_squares(
        curve,
        minimum_period=0.9,
        maximum_period=1.1,
        durations=[0.2],
        oversample=2,
        frequency_factor=10,
    )
    assert result.best_candidate.power == max(s.power for s in result.samples)
    grid = BoxLeastSquares(times, np.tile(y, 4), dy=np.ones(24)).autoperiod(
        [0.2], minimum_period=0.9, maximum_period=1.1, frequency_factor=10
    )
    assert [s.period for s in result.samples] == pytest.approx(
        grid[(grid >= 0.9 - 1e-14) & (grid <= 1.1 + 1e-14)]
    )


@pytest.mark.parametrize("origin", [0.0, 2450000.0])
@pytest.mark.parametrize("objective", ["snr", "likelihood"])
def test_wrapping_duplicate_phases_epoch_and_affine_invariance(origin, objective):
    t = np.arange(32) / 16 + origin
    y = np.array([0, 0, 3, 4] * 8, dtype=float)
    e = np.array([1, 2, 4, 1] * 8, dtype=float)
    ref = brute_grid(t, y, e, 1.0, [0.125, 0.25], 4, objective)
    out = physical_bls_power(t, y, e, [1.0], [0.125, 0.25], 4, objective)
    scaled = physical_bls_power(t, 3 * y + 17, 3 * e, [1.0], [0.125, 0.25], 4, objective)
    assert out.power[0] == pytest.approx(ref[0]["power"], abs=1e-8)
    assert scaled.power[0] == pytest.approx(out.power[0], abs=1e-8)


def test_historical_engine_is_byte_sealed():
    path = (
        Path(__file__).parents[2] / "validation/historical/mission57_light_curve_transit_search.py"
    )
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "daa92537c91274c774379385de85dfce3862fda73ccd891c2001054ecd2fd55a"
    )


def test_production_does_not_call_upstream_fast_search(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Legacy phase bin search forbidden")

    monkeypatch.setattr(BoxLeastSquares, "autopower", forbidden)
    monkeypatch.setattr(BoxLeastSquares, "power", forbidden)
    t = np.arange(32) / 16
    curve = build_light_curve(
        metadata=LightCurveMetadata("test", "flux", "elapsed days"),
        times=t,
        values=np.tile([0.0, 1.0, 1.0, 1.0], 8),
    )
    assert search_box_least_squares(
        curve, minimum_period=0.4, maximum_period=0.8, durations=[0.125], frequency_factor=20
    ).samples


def test_excessive_phase_grid_rejected_before_allocation():
    with pytest.raises(ValueError, match="million phases"):
        physical_bls_power([0, 0.5], [0, 1], None, [1.0], [1e-9], 10, "snr")


@pytest.mark.parametrize("objective", ["snr", "likelihood"])
def test_all_period_samples_against_independent_enumeration(objective):
    t = np.arange(24) / 32
    y = np.array([0.0, 0.0, 3.0, 4.0] * 6)
    periods = [1.0, 1.25, 1.5]
    durations = [0.125, 0.25, 0.375]
    out = physical_bls_power(t, y, None, periods, durations, 2, objective)
    refs = [brute_grid(t, y, np.ones(len(t)), p, durations, 2, objective)[0] for p in periods]
    assert out.power == pytest.approx([r["power"] for r in refs], abs=1e-8)
    assert int(np.argmax(out.power)) == int(np.argmax([r["power"] for r in refs]))
