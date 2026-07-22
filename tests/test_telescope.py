"""Tests for the telescope and eyepiece simulator."""

import pytest

from astroscope.telescope import (
    EyepieceSpec,
    TelescopeSpec,
    calculate_optical_simulation,
    classify_optical_setup,
    compare_eyepieces,
)


@pytest.fixture
def reflector() -> TelescopeSpec:
    """Return a common compact reflector."""

    return TelescopeSpec(
        aperture_mm=130.0,
        focal_length_mm=650.0,
    )


@pytest.fixture
def eyepiece_25mm() -> EyepieceSpec:
    """Return a common 25 mm eyepiece."""

    return EyepieceSpec(
        focal_length_mm=25.0,
        apparent_field_degrees=50.0,
    )


def test_standard_optical_simulation(
    reflector: TelescopeSpec,
    eyepiece_25mm: EyepieceSpec,
) -> None:
    result = calculate_optical_simulation(
        telescope=reflector,
        eyepiece=eyepiece_25mm,
    )

    assert result.native_focal_ratio == pytest.approx(5.0)

    assert result.magnification == pytest.approx(26.0)

    assert result.exit_pupil_mm == pytest.approx(5.0)

    assert result.true_field_degrees == pytest.approx(
        50.0 / 26.0,
        abs=0.0001,
    )

    assert result.maximum_useful_magnification == (pytest.approx(260.0))

    assert result.status == "wide_field"


def test_two_times_barlow_doubles_magnification(
    reflector: TelescopeSpec,
    eyepiece_25mm: EyepieceSpec,
) -> None:
    result = calculate_optical_simulation(
        telescope=reflector,
        eyepiece=eyepiece_25mm,
        barlow_factor=2.0,
    )

    assert result.effective_focal_length_mm == (pytest.approx(1300.0))

    assert result.magnification == pytest.approx(52.0)

    assert result.exit_pupil_mm == pytest.approx(2.5)


def test_focal_reducer_reduces_magnification(
    reflector: TelescopeSpec,
    eyepiece_25mm: EyepieceSpec,
) -> None:
    result = calculate_optical_simulation(
        telescope=reflector,
        eyepiece=eyepiece_25mm,
        reducer_factor=0.8,
    )

    assert result.effective_focal_length_mm == (pytest.approx(520.0))

    assert result.magnification == pytest.approx(20.8)

    assert result.exit_pupil_mm == pytest.approx(6.25)


@pytest.mark.parametrize(
    (
        "exit_pupil",
        "magnification",
        "maximum_magnification",
        "expected",
    ),
    [
        (
            8.0,
            20.0,
            200.0,
            "excessive_exit_pupil",
        ),
        (
            4.0,
            40.0,
            200.0,
            "wide_field",
        ),
        (
            1.5,
            100.0,
            200.0,
            "general_purpose",
        ),
        (
            0.75,
            150.0,
            200.0,
            "high_power",
        ),
        (
            0.4,
            250.0,
            200.0,
            "excessive_magnification",
        ),
    ],
)
def test_optical_status_classification(
    exit_pupil: float,
    magnification: float,
    maximum_magnification: float,
    expected: str,
) -> None:
    result = classify_optical_setup(
        exit_pupil_mm=exit_pupil,
        magnification=magnification,
        maximum_useful_magnification=(maximum_magnification),
    )

    assert result == expected


def test_compare_eyepieces_sorts_by_magnification(
    reflector: TelescopeSpec,
) -> None:
    eyepieces = (
        EyepieceSpec(
            focal_length_mm=10.0,
            apparent_field_degrees=50.0,
        ),
        EyepieceSpec(
            focal_length_mm=25.0,
            apparent_field_degrees=50.0,
        ),
    )

    results = compare_eyepieces(
        telescope=reflector,
        eyepieces=eyepieces,
    )

    assert [result.magnification for result in results] == [26.0, 65.0]


@pytest.mark.parametrize(
    ("aperture", "focal_length"),
    [
        (0.0, 650.0),
        (-130.0, 650.0),
        (130.0, 0.0),
    ],
)
def test_invalid_telescope_values_raise_error(
    aperture: float,
    focal_length: float,
) -> None:
    with pytest.raises(ValueError):
        TelescopeSpec(
            aperture_mm=aperture,
            focal_length_mm=focal_length,
        )


def test_invalid_eyepiece_field_raises_error() -> None:
    with pytest.raises(ValueError):
        EyepieceSpec(
            focal_length_mm=25.0,
            apparent_field_degrees=200.0,
        )


def test_invalid_barlow_factor_raises_error(
    reflector: TelescopeSpec,
    eyepiece_25mm: EyepieceSpec,
) -> None:
    with pytest.raises(ValueError):
        calculate_optical_simulation(
            telescope=reflector,
            eyepiece=eyepiece_25mm,
            barlow_factor=0.5,
        )


def test_invalid_reducer_factor_raises_error(
    reflector: TelescopeSpec,
    eyepiece_25mm: EyepieceSpec,
) -> None:
    with pytest.raises(ValueError):
        calculate_optical_simulation(
            telescope=reflector,
            eyepiece=eyepiece_25mm,
            reducer_factor=1.5,
        )
