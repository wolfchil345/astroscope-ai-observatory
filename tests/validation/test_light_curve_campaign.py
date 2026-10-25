"""Historical Mission 56 controls and explicit reproduction of pre-correction failures."""

import copy
import itertools
import json
import math
import socket

import numpy as np
import pytest

from validation.light_curve_campaign import (
    FIXTURE,
    ROOT,
    audit_observations,
    build,
    classify_period,
    load_inputs,
    observation_mismatches,
    processed,
    run_benchmark,
)
from validation.light_curve_references import exact_box_snr, ls_power, raw_checksum, wilson
from validation.reference_generation.light_curve_campaign import published, synthetic

POLICY, FIXTURES = load_inputs()
TRIALS = [
    (c["id"], s, a) for c in FIXTURES["cases"] for s in POLICY["stages"] for a in ["ls", "bls"]
]


@pytest.fixture(scope="module")
def record():
    with pytest.MonkeyPatch.context() as m:

        def deny(*args, **kwargs):
            raise AssertionError("Network forbidden in campaign")

        m.setattr(socket.socket, "connect", deny)
        result = run_benchmark()
        return result


@pytest.fixture(scope="module")
def matched_baseline(record):
    audit = audit_observations(record)
    assert audit["passed"], audit["mismatches"]
    return json.loads((ROOT / audit["matched_variants"][0]).read_text())


@pytest.mark.parametrize("index", range(252), ids=["/".join(t) for t in TRIALS])
def test_every_trial_reproduces_retained_observation(index, record, matched_baseline):
    baseline = matched_baseline
    assert not observation_mismatches(
        record["results"][index], baseline["observations"]["results"][index]
    )


def test_scientific_failure_is_explicit_and_separate_from_reproduction(record):
    assert record["execution_target"] == "historical pre-Mission-58 fast wrapper"
    assert record["overall_passed"] is False
    assert record["failed_trials"] == 9
    assert record["required_recovery_count"] == record["required_recovery_successes"] == 10
    assert audit_observations(record)["passed"]
    failed = [r for r in record["results"] if not r["passed"]]
    assert all(r["algorithm"] == "bls" and not r["numeric_reference_passed"] for r in failed)
    assert record["physical_arrival_qualification_changed"] is False
    assert record["universal_fap_calibration_established"] is False


@pytest.mark.parametrize("mutation", ["drop", "improve", "worsen", "flag", "metadata"])
def test_audit_rejects_changed_observations(record, mutation):
    changed = copy.deepcopy(record)
    if mutation == "drop":
        changed["results"].pop()
    elif mutation == "improve":
        changed["overall_passed"] = True
    elif mutation == "worsen":
        next(r for r in changed["results"] if not r["passed"])["best_candidate"]["depth_snr"] += 1
    elif mutation == "flag":
        changed["results"][0]["threshold_flag"] = not changed["results"][0]["threshold_flag"]
    else:
        changed["results"][0]["time_standard"] = "UTC"
    assert not audit_observations(changed)["passed"]


def test_reference_regeneration_matches_every_selected_sample():
    generated = {"mission": 56, "cases": synthetic() + [published()]}
    assert (
        json.dumps(generated, indent=2, sort_keys=True, allow_nan=False) + "\n"
        == (ROOT / FIXTURE).read_text()
    )


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda c: c["id"])
def test_time_labels_and_stage_input_are_preserved(case):
    before = copy.deepcopy(case)
    curve = build(case)
    assert [p.time for p in curve.points] == case["times"]
    for stage in POLICY["stages"]:
        result = processed(case, stage, POLICY)
        assert result.metadata.time_standard == case["time_standard"]
        assert set(p.time for p in result.points) <= set(case["times"])
    assert case == before


def test_archive_checksum_and_mutation():
    raw = (ROOT / "validation/fixtures/published/kplr006922244-2010078095331_llc.fits").read_bytes()
    provenance = FIXTURES["cases"][-1]["provenance"]
    for span in provenance["hdu_integrity"]:
        data = raw[span["start"] : span["end"]]
        assert raw_checksum(data) == 0xFFFFFFFF
        corrupted = bytearray(data)
        corrupted[-1] ^= 1
        assert raw_checksum(corrupted) != 0xFFFFFFFF
    assert len(FIXTURES["cases"][-1]["times"]) == 1322


def test_ls_analytic_sinusoid_and_affine_invariance():
    t = np.arange(200) * 0.037
    y = 7 + 0.4 * np.sin(2 * np.pi * t / 1.3)
    e = 1 + np.arange(200) % 3
    assert ls_power(t, y, e, 1 / 1.3) == pytest.approx(1, abs=1e-12)
    noisy = y + 0.1 * np.cos(2 * np.pi * t / 0.71)
    a = ls_power(t, noisy, e, 1 / 1.3)
    assert ls_power(t + 100, noisy * 3 + 20, e * 3, 1 / 1.3) == pytest.approx(a, abs=1e-12)
    assert ls_power(t, np.ones(len(t)), e, 1) is None


@pytest.mark.parametrize("errors", [[1, 1, 1, 1], [1, 2, 3, 4]])
def test_box_analytic_weighted_two_level(errors):
    t, y = [0, 0.1, 0.5, 0.6], [0, 0, 2, 2]
    w = 1 / np.asarray(errors, dtype=float) ** 2
    expected = 2 / math.sqrt(1 / sum(w[:2]) + 1 / sum(w[2:]))
    assert exact_box_snr(t, y, errors, 1, 0.2) == pytest.approx(expected)
    assert exact_box_snr(
        t, np.asarray(y) * 4 + 17, np.asarray(errors) * 4, 1, 0.2
    ) == pytest.approx(expected)


@pytest.mark.parametrize("values", list(itertools.product([0.0, 1.0, 3.0], repeat=4)))
def test_phase_oracle_against_all_dense_grid_memberships(values):
    # Rational grid: all transition boundaries and intervening states are sampled.
    # In particular, removal of a high point must be considered, not just additions.
    t = np.array([0, 0.125, 0.375, 0.75])
    expected = 0.0
    for start in np.arange(128) / 128:
        inside = ((t - start) % 1 > 0) & ((t - start) % 1 < 0.25)
        if not inside.any() or inside.all():
            continue
        y = np.asarray(values)
        depth = y[~inside].mean() - y[inside].mean()
        expected = max(expected, depth / math.sqrt(1 / inside.sum() + 1 / (~inside).sum()))
    assert exact_box_snr(t, values, [1] * 4, 1.0, 0.25) == pytest.approx(expected)


def test_wilson_and_alias_controls():
    assert wilson(0, 10) == pytest.approx([0, 0.2775327998628892])
    assert wilson(10, 10) == pytest.approx([0.7224672001371107, 1])
    for ratio, expected in [(1, "fundamental"), (0.5, "half_period"), (2, "double_period")]:
        assert classify_period(2.7 * ratio, 2.7, 0.01) == expected
    assert classify_period(1 / (1 / 2.7 + 1), 2.7, 0.01) == "daily_alias"
    assert classify_period(2, None, 0.01) == "no_periodic_truth"


@pytest.mark.parametrize(
    "trial_id,stage",
    [
        (f"{kind}-trend-{seed}", stage)
        for kind in ["sine", "box"]
        for seed in [0, 1]
        for stage in ["normalized", "sigma_clipped"]
    ]
    + [("red_null-uniform-2", "linear_detrended")],
)
@pytest.mark.xfail(strict=True, reason="Historical pre-Mission-58 BLS upper-bound violation")
def test_historical_bls_scientific_failure(trial_id, stage, record):
    row = next(
        r
        for r in record["results"]
        if (r["id"], r["stage"], r["algorithm"]) == (trial_id, stage, "bls")
    )
    assert row["numeric_reference_passed"], row["reference"]


@pytest.mark.parametrize(
    "audit,mutate,expected", [(False, False, 1), (True, False, 0), (True, True, 1)]
)
def test_cli_exit_distinguishes_science_and_reproduction(
    audit, mutate, expected, record, monkeypatch, tmp_path
):
    import sys

    from validation import light_curve_campaign as campaign

    result = copy.deepcopy(record)
    if mutate:
        result["results"].pop()
    monkeypatch.setattr(campaign, "run_benchmark", lambda: result)
    output = tmp_path / "record.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["campaign", "--output", str(output)] + (["--audit-observed-baseline"] if audit else []),
    )
    assert campaign.main() == expected
    assert json.loads(output.read_text())["overall_passed"] is False


def test_input_hash_mutation_rejected(monkeypatch):
    from validation import light_curve_campaign as campaign

    monkeypatch.setattr(campaign, "sha", lambda path: "invalid")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        campaign.load_inputs()


def test_audit_requires_one_complete_variant():
    from validation.light_curve_campaign import OBSERVED, OBSERVED_HASWELL

    a = json.loads((ROOT / OBSERVED).read_text())["observations"]
    b = json.loads((ROOT / OBSERVED_HASWELL).read_text())["observations"]
    assert audit_observations(a)["passed"] and audit_observations(b)["passed"]
    # Mix a Haswell constant result into the original campaign: neither full variant.
    a["results"][242] = b["results"][242]
    assert not audit_observations(a)["passed"]
