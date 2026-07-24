"""Tests for light-curve phase folding and phase binning."""

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_phase import (
    LightCurvePhaseError,
    bin_phase_fold,
    fold_light_curve,
)


def make_curve(
    *,
    times: list[float],
    values: list[float],
    uncertainties: list[float] | None = None,
):
    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Phase Test Target",
            photometry_kind="flux",
        ),
        times=times,
        values=values,
        uncertainties=uncertainties,
    )


def test_phase_fold_uses_requested_period_and_epoch() -> None:
    result = fold_light_curve(
        make_curve(
            times=[
                0.0,
                0.5,
                1.0,
                1.5,
                2.0,
            ],
            values=[
                1.0,
                0.9,
                1.1,
                0.8,
                1.0,
            ],
        ),
        period=1.0,
        epoch=0.0,
    )

    assert tuple(point.phase for point in result.points) == pytest.approx(
        (
            0.0,
            0.0,
            0.0,
            0.5,
            0.5,
        )
    )

    assert tuple(point.cycle for point in result.points) == (
        0,
        1,
        2,
        0,
        1,
    )


def test_phase_fold_defaults_to_first_observation_epoch() -> None:
    result = fold_light_curve(
        make_curve(
            times=[
                10.0,
                10.5,
                11.0,
            ],
            values=[
                1.0,
                0.9,
                1.0,
            ],
        ),
        period=1.0,
    )

    assert result.epoch == pytest.approx(10.0)

    assert tuple(point.phase for point in result.points) == pytest.approx(
        (
            0.0,
            0.0,
            0.5,
        )
    )


def test_phase_fold_preserves_measurements() -> None:
    light_curve = make_curve(
        times=[
            0.0,
            0.5,
            1.0,
        ],
        values=[
            1.0,
            0.8,
            1.1,
        ],
        uncertainties=[
            0.01,
            0.02,
            0.03,
        ],
    )

    result = fold_light_curve(
        light_curve,
        period=1.0,
        epoch=0.0,
    )

    assert result.light_curve == light_curve
    assert result.observation_count == 3

    assert sorted(point.value for point in result.points) == pytest.approx(
        [
            0.8,
            1.0,
            1.1,
        ]
    )


@pytest.mark.parametrize(
    "period",
    [
        0.0,
        -1.0,
        float("inf"),
        float("nan"),
        True,
    ],
)
def test_phase_fold_rejects_invalid_period(
    period,
) -> None:
    with pytest.raises(
        LightCurvePhaseError,
        match="Period",
    ):
        fold_light_curve(
            make_curve(
                times=[
                    0.0,
                    1.0,
                    2.0,
                ],
                values=[
                    1.0,
                    0.9,
                    1.0,
                ],
            ),
            period=period,
        )


@pytest.mark.parametrize(
    "epoch",
    [
        float("inf"),
        float("nan"),
        True,
    ],
)
def test_phase_fold_rejects_invalid_epoch(
    epoch,
) -> None:
    with pytest.raises(
        LightCurvePhaseError,
        match="Epoch",
    ):
        fold_light_curve(
            make_curve(
                times=[
                    0.0,
                    1.0,
                    2.0,
                ],
                values=[
                    1.0,
                    0.9,
                    1.0,
                ],
            ),
            period=1.0,
            epoch=epoch,
        )


def test_unweighted_phase_binning_calculates_means() -> None:
    phase_fold = fold_light_curve(
        make_curve(
            times=[
                0.0,
                0.1,
                0.2,
                0.6,
                0.7,
            ],
            values=[
                1.0,
                3.0,
                5.0,
                10.0,
                14.0,
            ],
        ),
        period=1.0,
        epoch=0.0,
    )

    result = bin_phase_fold(
        phase_fold,
        bin_count=2,
    )

    assert result.weighted is False
    assert result.populated_bin_count == 2

    assert tuple(phase_bin.observation_count for phase_bin in result.bins) == (
        3,
        2,
    )

    assert tuple(phase_bin.value for phase_bin in result.bins) == pytest.approx(
        (
            3.0,
            12.0,
        )
    )


def test_weighted_phase_binning_uses_uncertainties() -> None:
    phase_fold = fold_light_curve(
        make_curve(
            times=[
                0.1,
                0.2,
                0.7,
            ],
            values=[
                1.0,
                3.0,
                10.0,
            ],
            uncertainties=[
                1.0,
                0.5,
                2.0,
            ],
        ),
        period=1.0,
        epoch=0.0,
    )

    result = bin_phase_fold(
        phase_fold,
        bin_count=2,
    )

    first_bin = result.bins[0]

    assert result.weighted is True
    assert first_bin.value == pytest.approx(2.6)
    assert first_bin.uncertainty == pytest.approx((1.0 / 5.0) ** 0.5)


def test_minimum_points_filters_sparse_bins() -> None:
    phase_fold = fold_light_curve(
        make_curve(
            times=[
                0.1,
                0.2,
                0.3,
                0.8,
            ],
            values=[
                1.0,
                1.1,
                0.9,
                2.0,
            ],
        ),
        period=1.0,
        epoch=0.0,
    )

    result = bin_phase_fold(
        phase_fold,
        bin_count=2,
        minimum_points=2,
    )

    assert result.populated_bin_count == 1
    assert result.bins[0].observation_count == 3


@pytest.mark.parametrize(
    "bin_count",
    [
        1,
        501,
        1.5,
        True,
    ],
)
def test_phase_binning_rejects_invalid_bin_count(
    bin_count,
) -> None:
    phase_fold = fold_light_curve(
        make_curve(
            times=[
                0.0,
                0.5,
                1.0,
            ],
            values=[
                1.0,
                0.9,
                1.0,
            ],
        ),
        period=1.0,
    )

    with pytest.raises(
        LightCurvePhaseError,
        match="Bin count",
    ):
        bin_phase_fold(
            phase_fold,
            bin_count=bin_count,
        )


@pytest.mark.parametrize(
    "minimum_points",
    [
        0,
        1.5,
        True,
    ],
)
def test_phase_binning_rejects_invalid_minimum_points(
    minimum_points,
) -> None:
    phase_fold = fold_light_curve(
        make_curve(
            times=[
                0.0,
                0.5,
                1.0,
            ],
            values=[
                1.0,
                0.9,
                1.0,
            ],
        ),
        period=1.0,
    )

    with pytest.raises(
        LightCurvePhaseError,
        match="Minimum points",
    ):
        bin_phase_fold(
            phase_fold,
            minimum_points=minimum_points,
        )
