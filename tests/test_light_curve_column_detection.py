"""Tests for automatic light-curve column detection."""

import pytest

from astroscope.light_curve_io import (
    LightCurveIOError,
    detect_light_curve_columns,
    detect_light_curve_csv_columns,
)


def test_detects_flux_columns() -> None:
    detection = detect_light_curve_columns(
        [
            "BJD",
            "flux",
            "flux_error",
        ]
    )

    assert detection.columns.time == "BJD"
    assert detection.columns.value == "flux"
    assert detection.columns.uncertainty == "flux_error"
    assert detection.photometry_kind == "flux"
    assert detection.suggested_time_standard == "BJD"


def test_detects_normalized_headers() -> None:
    detection = detect_light_curve_columns(
        [
            "BJD TDB",
            "Normalized Flux",
            "Flux Error",
        ]
    )

    assert detection.columns.time == "BJD TDB"
    assert detection.columns.value == "Normalized Flux"
    assert detection.columns.uncertainty == "Flux Error"
    assert detection.photometry_kind == "flux"
    assert detection.suggested_time_standard == "BJD_TDB"


def test_detects_magnitude_photometry() -> None:
    detection = detect_light_curve_columns(
        [
            "JD",
            "mag",
            "mag_err",
        ]
    )

    assert detection.columns.time == "JD"
    assert detection.columns.value == "mag"
    assert detection.columns.uncertainty == "mag_err"
    assert detection.photometry_kind == "magnitude"
    assert detection.suggested_time_standard == "JD"


def test_uncertainty_column_is_optional() -> None:
    detection = detect_light_curve_columns(
        [
            "time",
            "relative_flux",
        ]
    )

    assert detection.columns.time == "time"
    assert detection.columns.value == "relative_flux"
    assert detection.columns.uncertainty is None
    assert detection.suggested_time_standard is None


def test_detects_columns_from_csv_text() -> None:
    detection = detect_light_curve_csv_columns(
        "mjd,flux,sigma\n60000.0,1.0,0.01\n60000.1,0.99,0.01\n"
    )

    assert detection.columns.time == "mjd"
    assert detection.columns.value == "flux"
    assert detection.columns.uncertainty == "sigma"
    assert detection.suggested_time_standard == "MJD"


def test_rejects_flux_and_magnitude_ambiguity() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="Both flux and magnitude",
    ):
        detect_light_curve_columns(
            [
                "time",
                "flux",
                "mag",
            ]
        )


def test_rejects_multiple_time_candidates() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="Multiple possible time columns",
    ):
        detect_light_curve_columns(
            [
                "jd",
                "bjd",
                "flux",
            ]
        )


def test_rejects_multiple_flux_candidates() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="Multiple possible flux columns",
    ):
        detect_light_curve_columns(
            [
                "time",
                "sap_flux",
                "pdcsap_flux",
            ]
        )


def test_rejects_missing_photometry_column() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="flux or magnitude",
    ):
        detect_light_curve_columns(
            [
                "time",
                "temperature",
            ]
        )


def test_rejects_empty_csv() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="must not be empty",
    ):
        detect_light_curve_csv_columns("   ")
