"""Tests for Box Least Squares light-curve transit searches."""

import numpy as np
import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_transit_search import (
    LightCurveTransitSearchError,
    search_box_least_squares,
)

TRUE_PERIOD = 2.5
TRUE_DURATION = 0.2
TRUE_TRANSIT_TIME = 0.4
TRUE_DEPTH = 0.03


def make_transit_curve(
    *,
    with_uncertainties: bool = True,
    photometry_kind: str = "flux",
):
    times = np.linspace(
        0.0,
        20.0,
        1200,
        endpoint=False,
    )

    phases = ((times - TRUE_TRANSIT_TIME + 0.5 * TRUE_PERIOD) % TRUE_PERIOD) - 0.5 * TRUE_PERIOD

    values = (
        1.0
        + 0.0010 * np.sin(2.0 * np.pi * times / 1.37)
        + 0.0005 * np.cos(2.0 * np.pi * times / 0.73)
    )

    values = values.copy()
    values[np.abs(phases) <= TRUE_DURATION / 2.0] -= TRUE_DEPTH

    uncertainties = (
        np.full(
            times.size,
            0.002,
        )
        if with_uncertainties
        else None
    )

    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Synthetic Transit Target",
            photometry_kind=photometry_kind,
        ),
        times=times,
        values=values,
        uncertainties=uncertainties,
    )


@pytest.fixture(scope="module")
def transit_result():
    return search_box_least_squares(
        make_transit_curve(),
        minimum_period=1.5,
        maximum_period=4.0,
        durations=(
            0.16,
            0.20,
            0.24,
        ),
        objective="snr",
        frequency_factor=2.0,
        candidate_count=5,
    )


def test_bls_recovers_transit_period(
    transit_result,
) -> None:
    candidate = transit_result.best_candidate

    assert candidate.period == pytest.approx(
        TRUE_PERIOD,
        abs=0.03,
    )


def test_bls_recovers_transit_depth(
    transit_result,
) -> None:
    candidate = transit_result.best_candidate

    assert candidate.depth == pytest.approx(
        TRUE_DEPTH,
        abs=0.005,
    )
    assert candidate.depth_error > 0.0
    assert candidate.depth_snr > 5.0


def test_bls_recovers_transit_duration(
    transit_result,
) -> None:
    candidate = transit_result.best_candidate

    assert candidate.duration == pytest.approx(
        TRUE_DURATION,
        abs=0.05,
    )


def test_bls_recovers_transit_midpoint(
    transit_result,
) -> None:
    candidate = transit_result.best_candidate

    phase_error = abs(
        ((candidate.transit_time - TRUE_TRANSIT_TIME + 0.5 * candidate.period) % candidate.period)
        - 0.5 * candidate.period
    )

    assert phase_error < 0.05


def test_bls_result_records_weighted_analysis(
    transit_result,
) -> None:
    assert transit_result.weighted is True
    assert transit_result.objective == "snr"
    assert transit_result.samples
    assert transit_result.candidates


def test_bls_samples_remain_inside_period_range(
    transit_result,
) -> None:
    assert all(1.5 - 1.0e-12 <= sample.period <= 4.0 + 1.0e-12 for sample in transit_result.samples)


def test_bls_candidates_are_ranked_by_power(
    transit_result,
) -> None:
    powers = [candidate.power for candidate in transit_result.candidates]

    assert powers == sorted(
        powers,
        reverse=True,
    )

    assert tuple(candidate.rank for candidate in transit_result.candidates) == tuple(
        range(
            1,
            len(transit_result.candidates) + 1,
        )
    )


def test_bls_supports_unweighted_flux() -> None:
    result = search_box_least_squares(
        make_transit_curve(
            with_uncertainties=False,
        ),
        minimum_period=2.2,
        maximum_period=2.8,
        durations=(0.20,),
        objective="likelihood",
        frequency_factor=4.0,
        candidate_count=2,
    )

    assert result.weighted is False
    assert result.best_candidate.period == pytest.approx(
        TRUE_PERIOD,
        abs=0.03,
    )


def test_bls_rejects_magnitude_measurements() -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="requires flux",
    ):
        search_box_least_squares(
            make_transit_curve(
                photometry_kind="magnitude",
            ),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(0.2,),
        )


@pytest.mark.parametrize(
    ("minimum_period", "maximum_period", "message"),
    [
        (
            0.0,
            4.0,
            "Minimum period",
        ),
        (
            -1.0,
            4.0,
            "Minimum period",
        ),
        (
            4.0,
            4.0,
            "Maximum period",
        ),
        (
            5.0,
            4.0,
            "Maximum period",
        ),
    ],
)
def test_bls_rejects_invalid_period_range(
    minimum_period: float,
    maximum_period: float,
    message: str,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match=message,
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=minimum_period,
            maximum_period=maximum_period,
            durations=(0.2,),
        )


@pytest.mark.parametrize(
    "durations",
    [
        (),
        (0.0,),
        (-0.2,),
        (float("inf"),),
        (float("nan"),),
    ],
)
def test_bls_rejects_invalid_durations(
    durations,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="duration",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=durations,
        )


def test_bls_rejects_duration_not_shorter_than_period() -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="shorter than the minimum period",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(1.5,),
        )


@pytest.mark.parametrize(
    "objective",
    [
        "power",
        "",
        "SNR",
    ],
)
def test_bls_rejects_invalid_objective(
    objective,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="Objective",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(0.2,),
            objective=objective,
        )


@pytest.mark.parametrize(
    "oversample",
    [
        0,
        101,
        1.5,
        True,
    ],
)
def test_bls_rejects_invalid_oversample(
    oversample,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="Oversample",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(0.2,),
            oversample=oversample,
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
def test_bls_rejects_invalid_candidate_count(
    candidate_count,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="Candidate count",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(0.2,),
            candidate_count=candidate_count,
        )


@pytest.mark.parametrize(
    "frequency_factor",
    [
        0.0,
        -1.0,
        float("inf"),
        float("nan"),
        True,
    ],
)
def test_bls_rejects_invalid_frequency_factor(
    frequency_factor,
) -> None:
    with pytest.raises(
        LightCurveTransitSearchError,
        match="Frequency factor",
    ):
        search_box_least_squares(
            make_transit_curve(),
            minimum_period=1.5,
            maximum_period=4.0,
            durations=(0.2,),
            frequency_factor=frequency_factor,
        )


def test_bls_requires_twenty_observations() -> None:
    light_curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Small Transit Curve",
            photometry_kind="flux",
        ),
        times=[float(index) for index in range(10)],
        values=[1.0 for _ in range(10)],
    )

    with pytest.raises(
        LightCurveTransitSearchError,
        match="at least twenty",
    ):
        search_box_least_squares(
            light_curve,
            minimum_period=1.0,
            maximum_period=4.0,
            durations=(0.2,),
        )
