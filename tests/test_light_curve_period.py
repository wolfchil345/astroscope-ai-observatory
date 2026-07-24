"""Tests for Lomb-Scargle light-curve period analysis."""

from math import pi, sin

import numpy as np
import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_period import (
    LightCurvePeriodError,
    analyze_lomb_scargle,
)


def make_periodic_curve(
    *,
    period: float = 2.5,
    with_uncertainties: bool = False,
):
    times = np.linspace(
        0.0,
        30.0,
        600,
    )

    values = [1.0 + 0.02 * sin(2.0 * pi * float(time) / period) for time in times]

    uncertainties = [0.005 for _ in times] if with_uncertainties else None

    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Periodic Test Star",
            photometry_kind="flux",
        ),
        times=times,
        values=values,
        uncertainties=uncertainties,
    )


def test_lomb_scargle_recovers_period() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(period=2.5),
        minimum_period=0.5,
        maximum_period=5.0,
    )

    assert result.best_period == pytest.approx(
        2.5,
        abs=0.03,
    )
    assert result.best_frequency == pytest.approx(
        0.4,
        abs=0.005,
    )
    assert result.best_candidate.rank == 1
    assert result.best_candidate.power > 0.9


def test_periodogram_samples_remain_inside_range() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(),
        minimum_period=0.5,
        maximum_period=5.0,
    )

    assert result.samples

    assert all(0.5 - 1.0e-12 <= sample.period <= 5.0 + 1.0e-12 for sample in result.samples)


def test_candidates_are_ranked_by_power() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(),
        minimum_period=0.5,
        maximum_period=5.0,
        candidate_count=4,
    )

    powers = [candidate.power for candidate in result.candidates]

    assert powers == sorted(
        powers,
        reverse=True,
    )

    assert tuple(candidate.rank for candidate in result.candidates) == tuple(
        range(
            1,
            len(result.candidates) + 1,
        )
    )


def test_weighted_analysis_uses_uncertainties() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(
            with_uncertainties=True,
        ),
        minimum_period=0.5,
        maximum_period=5.0,
    )

    assert result.weighted is True
    assert result.best_period == pytest.approx(
        2.5,
        abs=0.03,
    )


def test_unweighted_analysis_without_uncertainties() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(
            with_uncertainties=False,
        ),
        minimum_period=0.5,
        maximum_period=5.0,
    )

    assert result.weighted is False


def test_false_alarm_probability_is_bounded() -> None:
    result = analyze_lomb_scargle(
        make_periodic_curve(),
        minimum_period=0.5,
        maximum_period=5.0,
    )

    probability = result.best_candidate.false_alarm_probability

    assert probability is None or 0.0 <= probability <= 1.0


@pytest.mark.parametrize(
    ("minimum_period", "maximum_period", "message"),
    [
        (
            0.0,
            5.0,
            "Minimum period",
        ),
        (
            -1.0,
            5.0,
            "Minimum period",
        ),
        (
            5.0,
            5.0,
            "Maximum period",
        ),
        (
            6.0,
            5.0,
            "Maximum period",
        ),
    ],
)
def test_period_analysis_rejects_invalid_range(
    minimum_period: float,
    maximum_period: float,
    message: str,
) -> None:
    with pytest.raises(
        LightCurvePeriodError,
        match=message,
    ):
        analyze_lomb_scargle(
            make_periodic_curve(),
            minimum_period=minimum_period,
            maximum_period=maximum_period,
        )


@pytest.mark.parametrize(
    "samples_per_peak",
    [
        0,
        101,
        1.5,
        True,
    ],
)
def test_period_analysis_rejects_invalid_samples_per_peak(
    samples_per_peak,
) -> None:
    with pytest.raises(
        LightCurvePeriodError,
        match="Samples per peak",
    ):
        analyze_lomb_scargle(
            make_periodic_curve(),
            minimum_period=0.5,
            maximum_period=5.0,
            samples_per_peak=samples_per_peak,
        )


@pytest.mark.parametrize(
    "candidate_count",
    [
        0,
        21,
        1.5,
        True,
    ],
)
def test_period_analysis_rejects_invalid_candidate_count(
    candidate_count,
) -> None:
    with pytest.raises(
        LightCurvePeriodError,
        match="Candidate count",
    ):
        analyze_lomb_scargle(
            make_periodic_curve(),
            minimum_period=0.5,
            maximum_period=5.0,
            candidate_count=candidate_count,
        )


def test_period_analysis_requires_five_observations() -> None:
    light_curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Small Test Curve",
            photometry_kind="flux",
        ),
        times=[
            0.0,
            1.0,
            2.0,
            3.0,
        ],
        values=[
            1.0,
            0.9,
            1.1,
            1.0,
        ],
    )

    with pytest.raises(
        LightCurvePeriodError,
        match="at least five",
    ):
        analyze_lomb_scargle(
            light_curve,
            minimum_period=0.5,
            maximum_period=5.0,
        )
