"""Tests for astronomical light-curve preprocessing."""

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_processing import (
    LightCurveProcessingError,
    normalize_light_curve,
    sigma_clip_light_curve,
)


def make_flux_curve(
    values: list[float],
    uncertainties: list[float] | None = None,
):
    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Test Flux Target",
            photometry_kind="flux",
        ),
        times=[float(index) for index in range(len(values))],
        values=values,
        uncertainties=uncertainties,
    )


def make_magnitude_curve(
    values: list[float],
):
    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Test Magnitude Target",
            photometry_kind="magnitude",
        ),
        times=[float(index) for index in range(len(values))],
        values=values,
    )


def test_normalize_flux_uses_median() -> None:
    result = normalize_light_curve(
        make_flux_curve(
            [
                10.0,
                20.0,
                30.0,
            ]
        )
    )

    assert tuple(point.value for point in result.light_curve.points) == pytest.approx(
        (
            0.5,
            1.0,
            1.5,
        )
    )
    assert result.report.center == pytest.approx(20.0)
    assert result.report.removed_count == 0


def test_normalize_flux_scales_uncertainties() -> None:
    result = normalize_light_curve(
        make_flux_curve(
            [
                10.0,
                20.0,
                30.0,
            ],
            uncertainties=[
                1.0,
                2.0,
                3.0,
            ],
        )
    )

    assert tuple(point.uncertainty for point in result.light_curve.points) == pytest.approx(
        (
            0.05,
            0.10,
            0.15,
        )
    )


def test_normalize_flux_rejects_zero_median() -> None:
    with pytest.raises(
        LightCurveProcessingError,
        match="median is zero",
    ):
        normalize_light_curve(
            make_flux_curve(
                [
                    -1.0,
                    0.0,
                    1.0,
                ]
            )
        )


def test_center_magnitudes_uses_median() -> None:
    result = normalize_light_curve(
        make_magnitude_curve(
            [
                12.0,
                13.0,
                14.0,
            ]
        )
    )

    assert tuple(point.value for point in result.light_curve.points) == pytest.approx(
        (
            -1.0,
            0.0,
            1.0,
        )
    )
    assert result.report.operation == "median_magnitude_centering"


def test_sigma_clipping_removes_outlier() -> None:
    result = sigma_clip_light_curve(
        make_flux_curve(
            [
                0.99,
                1.00,
                1.01,
                1.00,
                5.00,
            ]
        ),
        sigma=3.0,
    )

    assert result.light_curve.observation_count == 4
    assert result.report.removed_count == 1
    assert all(point.value < 2.0 for point in result.light_curve.points)


def test_sigma_clipping_preserves_times_and_uncertainties() -> None:
    result = sigma_clip_light_curve(
        make_flux_curve(
            [
                1.00,
                1.01,
                0.99,
                1.00,
                8.00,
            ],
            uncertainties=[
                0.01,
                0.02,
                0.03,
                0.04,
                0.50,
            ],
        ),
        sigma=3.0,
    )

    assert tuple(point.time for point in result.light_curve.points) == (
        0.0,
        1.0,
        2.0,
        3.0,
    )
    assert tuple(point.uncertainty for point in result.light_curve.points) == pytest.approx(
        (
            0.01,
            0.02,
            0.03,
            0.04,
        )
    )


def test_sigma_clipping_with_zero_scale_keeps_data() -> None:
    light_curve = make_flux_curve(
        [
            1.0,
            1.0,
            1.0,
            1.0,
        ]
    )

    result = sigma_clip_light_curve(
        light_curve,
        sigma=3.0,
    )

    assert result.light_curve == light_curve
    assert result.report.removed_count == 0
    assert result.report.scale == pytest.approx(0.0)


@pytest.mark.parametrize(
    "sigma",
    [
        0.0,
        -1.0,
        float("inf"),
        float("nan"),
    ],
)
def test_sigma_clipping_rejects_invalid_threshold(
    sigma: float,
) -> None:
    with pytest.raises(
        LightCurveProcessingError,
        match="greater than zero",
    ):
        sigma_clip_light_curve(
            make_flux_curve(
                [
                    1.0,
                    1.1,
                    0.9,
                ]
            ),
            sigma=sigma,
        )
