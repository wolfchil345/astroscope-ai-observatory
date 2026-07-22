"""Tests for astronomical light-curve data models."""

import pytest

from astroscope.light_curve import (
    LightCurve,
    LightCurveError,
    LightCurveMetadata,
    LightCurvePoint,
    build_light_curve,
)


def make_metadata() -> LightCurveMetadata:
    return LightCurveMetadata(
        object_name="WASP-12 b",
        photometry_kind="flux",
        filter_name="R",
        observatory_name="AstroScope Test Observatory",
    )


def test_metadata_requires_object_name() -> None:
    with pytest.raises(
        LightCurveError,
        match="Object name",
    ):
        LightCurveMetadata(
            object_name=" ",
            photometry_kind="flux",
        )


def test_light_curve_point_rejects_nonpositive_uncertainty() -> None:
    with pytest.raises(
        LightCurveError,
        match="greater than zero",
    ):
        LightCurvePoint(
            time=2_460_000.0,
            value=1.0,
            uncertainty=0.0,
        )


def test_build_light_curve_orders_observations() -> None:
    light_curve = build_light_curve(
        metadata=make_metadata(),
        times=[
            2_460_002.0,
            2_460_000.0,
            2_460_001.0,
        ],
        values=[
            0.99,
            1.00,
            0.98,
        ],
    )

    assert tuple(point.time for point in light_curve.points) == (
        2_460_000.0,
        2_460_001.0,
        2_460_002.0,
    )


def test_build_light_curve_rejects_length_mismatch() -> None:
    with pytest.raises(
        LightCurveError,
        match="equal lengths",
    ):
        build_light_curve(
            metadata=make_metadata(),
            times=[
                2_460_000.0,
                2_460_001.0,
                2_460_002.0,
            ],
            values=[
                1.0,
                0.99,
            ],
        )


def test_light_curve_rejects_duplicate_times() -> None:
    with pytest.raises(
        LightCurveError,
        match="must be unique",
    ):
        LightCurve(
            metadata=make_metadata(),
            points=(
                LightCurvePoint(
                    time=2_460_000.0,
                    value=1.0,
                ),
                LightCurvePoint(
                    time=2_460_000.0,
                    value=0.99,
                ),
                LightCurvePoint(
                    time=2_460_001.0,
                    value=1.01,
                ),
            ),
        )


def test_light_curve_summary_properties() -> None:
    light_curve = build_light_curve(
        metadata=make_metadata(),
        times=[
            2_460_000.0,
            2_460_001.0,
            2_460_003.0,
        ],
        values=[
            1.0,
            0.99,
            1.01,
        ],
        uncertainties=[
            0.01,
            0.01,
            0.02,
        ],
    )

    assert light_curve.observation_count == 3
    assert light_curve.start_time == pytest.approx(2_460_000.0)
    assert light_curve.end_time == pytest.approx(2_460_003.0)
    assert light_curve.duration == pytest.approx(3.0)
    assert light_curve.has_uncertainties is True


def test_partial_uncertainties_are_not_complete() -> None:
    light_curve = LightCurve(
        metadata=make_metadata(),
        points=(
            LightCurvePoint(
                time=1.0,
                value=1.0,
                uncertainty=0.01,
            ),
            LightCurvePoint(
                time=2.0,
                value=0.99,
            ),
            LightCurvePoint(
                time=3.0,
                value=1.01,
                uncertainty=0.01,
            ),
        ),
    )

    assert light_curve.has_uncertainties is False
