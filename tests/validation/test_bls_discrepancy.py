"""Mission 57 source-trace checks do not relabel upstream failures as passes."""

import json
import math
import socket
from fractions import Fraction

import numpy as np
import pytest

from validation import bls_discrepancy as b


@pytest.fixture(scope="module")
def record():
    with pytest.MonkeyPatch.context() as m:

        def deny(*args, **kwargs):
            raise AssertionError("Network forbidden")

        m.setattr(socket.socket, "connect", deny)
        m.setattr(socket.socket, "connect_ex", deny)
        m.setattr(socket, "create_connection", deny)
        return b.run()


@pytest.mark.parametrize("i", range(19))
@pytest.mark.parametrize("j", range(5))
def test_source_trace_and_physical_refit(i, j, record):
    row = record["rows"][i]["measurements"][j]
    assert row["trace_passed"]
    assert row["physical_refit_within_bound"]
    assert row["trace_absolute_snr_error"] <= 1e-8
    assert row["fast_within_bound"] == (row["fast_minus_bound"] <= 1e-5)


def test_retained_failures_and_causal_intervention(record):
    assert record["mechanism_checks_passed"]
    assert record["measurement_count"] == 95
    assert record["selected_trial_count"] == 19
    assert record["fast_bound_violations"] == 22
    assert not record["production_scientific_failures_resolved"]
    assert not record["physical_arrival_qualification_changed"]
    failures = [r for r in record["rows"] if r["mission56_failed"]]
    assert len(failures) == 9
    for r in failures:
        m = next(m for m in r["measurements"] if m["oversample"] == 10)
        assert not m["fast_within_bound"]
        assert m["fast_snr"] == pytest.approx(r["original_fast_snr"], abs=1e-8)
        assert m["trace"]["legacy_vs_physical_changed_indices"]
        assert m["trace"]["legacy_vs_intervention_changed_indices"]
        assert m["trace"]["padding_intervention_fit"]["snr"] <= m["independent_max_snr"] + 1e-5
        assert m["trace"]["physical_candidate_fit"] is not None


def test_high_oversampling_is_not_a_correction(record):
    red = next(r for r in record["rows"] if r["id"] == "red_null-uniform-2")
    assert not red["measurements"][-1]["fast_within_bound"]
    assert red["measurements"][0]["fast_within_bound"]


def test_witness_analytic_fraction_bound(record):
    # Two zero-valued points versus four outside points with total flux 30.
    max_depth = Fraction(30, 4)
    variance = Fraction(1, 2) + Fraction(1, 4)
    physical_max_squared = max_depth**2 / variance
    legacy_squared = Fraction(10) ** 2 / (Fraction(1, 3) + Fraction(1, 3))
    assert physical_max_squared == 75 and legacy_squared == 150
    w = record["witness"]
    assert w["independent_max_snr"] ** 2 == pytest.approx(float(physical_max_squared))
    assert w["fast_snr"] ** 2 == pytest.approx(float(legacy_squared))
    assert w["trace"]["legacy_fit"]["indices"] == [0, 1, 2]
    # TIME=0 lies exactly on the open window endpoint; floating modulo can
    # admit it. Both explicit memberships remain below the independent bound.
    assert w["trace"]["physical_candidate_fit"]["indices"] in ([2, 3], [0, 2, 3])
    assert w["trace"]["padding_intervention_fit"]["indices"] == [2, 3]
    assert w["trace"]["physical_candidate_fit"]["snr"] <= math.sqrt(75)


@pytest.mark.parametrize("scale,offset", [(1, 0), (3, 10), (0.1, -20)])
def test_direct_fit_affine_flux_invariance(scale, offset):
    y = np.asarray([0, 0, 0, 10, 10, 10]) * scale + offset
    fit = b.weighted_fit(y, [scale] * 6, [1, 1, 0, 0, 0, 0])
    assert fit["snr"] == pytest.approx(math.sqrt(75))


@pytest.mark.parametrize("counts", [[0] * 6, [1] * 6])
def test_empty_partition_is_explicit(counts):
    assert b.weighted_fit(range(6), [1] * 6, counts) is None


@pytest.mark.parametrize("value", [-1, 2])
def test_duplicated_or_negative_membership_rejected(value):
    with pytest.raises(ValueError, match="partition"):
        b.weighted_fit(range(6), [1] * 6, [value, 0, 0, 0, 0, 0])


def test_padding_and_duration_grid_dependence():
    t = [0, 0.02, 0.82, 0.92, 0.5, 0.6]
    legacy, meta = b.bin_membership(t, 1, [0.2], 2, 8, 0.2)
    repaired, _ = b.bin_membership(t, 1, [0.2], 2, 8, 0.2, True)
    assert meta["overwritten_original_indices"] == [3]
    assert np.flatnonzero(legacy).tolist() == [0, 1, 2]
    assert np.flatnonzero(repaired).tolist() == [2, 3]
    _, multi = b.bin_membership(t, 1, [0.1, 0.2], 2, 8, 0.2)
    assert multi["bin_width"] == meta["bin_width"] / 2


def test_unreviewed_source_rejected(monkeypatch):
    monkeypatch.setattr(b, "sha", lambda p: "wrong")
    with pytest.raises(ValueError, match="Unreviewed upstream"):
        b.run()


def test_cli_preserves_failure_semantics(record, tmp_path, monkeypatch):
    import sys

    monkeypatch.setattr(b, "run", lambda: record)
    path = tmp_path / "record.json"
    monkeypatch.setattr(sys, "argv", ["audit", "--output", str(path)])
    assert b.main() == 0
    saved = json.loads(path.read_text())
    assert saved["mechanism_checks_passed"] and not saved["production_scientific_failures_resolved"]
