"""Tests for astronomical light-curve detrending."""

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_processing import (
    LightCurveProcessingError,
    detrend_light_curve,
)


def make_flux_curve(
    values: list[float],
    uncertainties: list[float] | None = None,
):
    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Detrending Flux Target",
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
            object_name="Detrending Magnitude Target",
            photometry_kind="magnitude",
        ),
        times=[float(index) for index in range(len(values))],
        values=values,
    )


def test_linear_flux_detrending_removes_slope() -> None:
    result = detrend_light_curve(
        make_flux_curve(
            [
                10.0,
                12.0,
                14.0,
                16.0,
                18.0,
            ]
        ),
        degree=1,
    )

    assert tuple(point.value for point in result.light_curve.points) == pytest.approx(
        (
            14.0,
            14.0,
            14.0,
            14.0,
            14.0,
        )
    )

    assert result.report.operation == "linear_detrending"
    assert result.report.center == pytest.approx(14.0)
    assert result.model.degree == 1
    assert result.model.reference_time == pytest.approx(2.0)
    assert result.model.evaluate(4.0) == pytest.approx(18.0)


def test_linear_flux_detrending_scales_uncertainties() -> None:
    result = detrend_light_curve(
        make_flux_curve(
            [
                10.0,
                12.0,
                14.0,
                16.0,
                18.0,
            ],
            uncertainties=[
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
        ),
        degree=1,
    )

    assert tuple(point.uncertainty for point in result.light_curve.points) == pytest.approx(
        (
            1.4,
            14.0 / 12.0,
            1.0,
            14.0 / 16.0,
            14.0 / 18.0,
        )
    )

    assert result.model.weighted is True


def test_linear_magnitude_detrending_removes_slope() -> None:
    result = detrend_light_curve(
        make_magnitude_curve(
            [
                12.0,
                12.2,
                12.4,
                12.6,
                12.8,
            ]
        ),
        degree=1,
    )

    assert tuple(point.value for point in result.light_curve.points) == pytest.approx(
        (
            12.4,
            12.4,
            12.4,
            12.4,
            12.4,
        )
    )


def test_quadratic_detrending_removes_curvature() -> None:
    result = detrend_light_curve(
        make_flux_curve(
            [
                9.0,
                6.0,
                5.0,
                6.0,
                9.0,
            ]
        ),
        degree=2,
    )

    assert tuple(point.value for point in result.light_curve.points) == pytest.approx(
        (
            6.0,
            6.0,
            6.0,
            6.0,
            6.0,
        ),
        abs=1.0e-10,
    )

    assert result.report.operation == "polynomial_detrending_degree_2"
    assert result.model.degree == 2


@pytest.mark.parametrize(
    "degree",
    [
        0,
        -1,
        6,
        1.5,
        True,
    ],
)
def test_detrending_rejects_invalid_degree(
    degree,
) -> None:
    with pytest.raises(
        LightCurveProcessingError,
        match="integer from 1 to 5",
    ):
        detrend_light_curve(
            make_flux_curve(
                [
                    1.0,
                    1.1,
                    1.2,
                    1.3,
                ]
            ),
            degree=degree,
        )


def test_detrending_rejects_degree_for_too_few_points() -> None:
    with pytest.raises(
        LightCurveProcessingError,
        match="smaller than the observation count",
    ):
        detrend_light_curve(
            make_flux_curve(
                [
                    1.0,
                    1.1,
                    1.2,
                ]
            ),
            degree=3,
        )


def test_flux_detrending_rejects_zero_median() -> None:
    with pytest.raises(
        LightCurveProcessingError,
        match="median is zero",
    ):
        detrend_light_curve(
            make_flux_curve(
                [
                    -1.0,
                    0.0,
                    1.0,
                ]
            ),
            degree=1,
        )


def test_detrending_preserves_times() -> None:
    light_curve = make_flux_curve(
        [
            1.0,
            1.1,
            1.2,
            1.3,
        ]
    )

    result = detrend_light_curve(
        light_curve,
        degree=1,
    )

    assert tuple(point.time for point in result.light_curve.points) == tuple(
        point.time for point in light_curve.points
    )
