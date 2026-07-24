"""Tests for astronomical light-curve CSV ingestion."""

import pytest

from astroscope.light_curve import LightCurveMetadata
from astroscope.light_curve_io import (
    LightCurveColumnMap,
    LightCurveIOError,
    import_light_curve_csv,
)


def make_metadata() -> LightCurveMetadata:
    return LightCurveMetadata(
        object_name="WASP-12 b",
        photometry_kind="flux",
    )


def make_columns() -> LightCurveColumnMap:
    return LightCurveColumnMap(
        time="bjd",
        value="flux",
        uncertainty="flux_error",
    )


def test_import_csv_orders_observations() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n2460002.0,0.99,0.01\n2460000.0,1.00,0.01\n2460001.0,0.98,0.02\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.imported_rows == 3
    assert result.skipped_rows == 0
    assert result.original_was_sorted is False

    assert tuple(point.time for point in result.light_curve.points) == (
        2460000.0,
        2460001.0,
        2460002.0,
    )


def test_import_csv_skips_invalid_rows() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n"
            "2460000.0,1.00,0.01\n"
            "invalid,0.99,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.total_rows == 4
    assert result.imported_rows == 3
    assert result.skipped_rows == 1


def test_import_csv_accepts_blank_uncertainty() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n2460000.0,1.00,0.01\n2460001.0,0.98,\n2460002.0,1.01,0.02\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.light_curve.has_uncertainties is False
    assert result.light_curve.points[1].uncertainty is None


def test_import_csv_rejects_duplicate_time() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="Duplicate observation time",
    ):
        import_light_curve_csv(
            csv_text=(
                "bjd,flux,flux_error\n"
                "2460000.0,1.00,0.01\n"
                "2460000.0,0.99,0.01\n"
                "2460001.0,0.98,0.02\n"
                "2460002.0,1.01,0.01\n"
            ),
            metadata=make_metadata(),
            columns=make_columns(),
        )


def test_import_csv_can_keep_first_duplicate() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n"
            "2460000.0,1.00,0.01\n"
            "2460000.0,0.99,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
        duplicate_policy="keep-first",
    )

    assert result.imported_rows == 3
    assert result.duplicate_rows == 1
    assert result.skipped_rows == 1
    assert result.light_curve.points[0].value == pytest.approx(1.0)


def test_import_csv_rejects_missing_column() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="missing mapped columns",
    ):
        import_light_curve_csv(
            csv_text=("bjd,brightness\n2460000.0,1.00\n2460001.0,0.99\n2460002.0,1.01\n"),
            metadata=make_metadata(),
            columns=make_columns(),
        )


def test_column_mapping_requires_distinct_columns() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="distinct columns",
    ):
        LightCurveColumnMap(
            time="flux",
            value="flux",
        )


def test_import_csv_accepts_padded_header_names() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd   , flux   , flux_error\n"
            "2460000.0,1.00,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.imported_rows == 3
