"""Tests for astrophotography imaging calculations."""

from math import atan, degrees

import pytest

from astroscope.imaging import (
    CAMERA_PRESETS,
    CameraSensorSpec,
    ImagingTargetSpec,
    calculate_astrophotography_setup,
    calculate_sensor_field_degrees,
    calculate_target_framing,
    classify_sampling,
    compare_camera_sensors,
)
from astroscope.telescope import TelescopeSpec


@pytest.fixture
def reflector() -> TelescopeSpec:
    """Return a common 130 mm reflector."""

    return TelescopeSpec(
        aperture_mm=130.0,
        focal_length_mm=650.0,
    )


@pytest.fixture
def aps_c_camera() -> CameraSensorSpec:
    """Return the generic APS-C camera preset."""

    return CAMERA_PRESETS["aps_c_camera"]


def test_camera_sensor_dimensions() -> None:
    camera = CameraSensorSpec(
        width_pixels=6000,
        height_pixels=4000,
        pixel_size_um=4.0,
    )

    assert camera.sensor_width_mm == pytest.approx(24.0)

    assert camera.sensor_height_mm == pytest.approx(16.0)

    assert camera.megapixels == pytest.approx(24.0)


def test_sensor_field_uses_exact_geometry() -> None:
    result = calculate_sensor_field_degrees(
        sensor_size_mm=24.0,
        effective_focal_length_mm=650.0,
    )

    expected = degrees(2.0 * atan(24.0 / (2.0 * 650.0)))

    assert result == pytest.approx(expected)


def test_typical_aps_c_imaging_setup(
    reflector: TelescopeSpec,
    aps_c_camera: CameraSensorSpec,
) -> None:
    result = calculate_astrophotography_setup(
        telescope=reflector,
        camera=aps_c_camera,
        seeing_arcseconds=2.0,
    )

    expected_scale = 206.265 * aps_c_camera.pixel_size_um / reflector.focal_length_mm

    assert result.effective_focal_length_mm == pytest.approx(650.0)

    assert result.effective_focal_ratio == (pytest.approx(5.0))

    assert result.image_scale_arcsec_per_pixel == pytest.approx(
        expected_scale,
        abs=0.0001,
    )

    assert result.field_width_degrees > (result.field_height_degrees)

    assert result.sampling_status == "undersampled"


def test_barlow_reduces_image_scale(
    reflector: TelescopeSpec,
    aps_c_camera: CameraSensorSpec,
) -> None:
    native_result = calculate_astrophotography_setup(
        telescope=reflector,
        camera=aps_c_camera,
    )

    barlow_result = calculate_astrophotography_setup(
        telescope=reflector,
        camera=aps_c_camera,
        barlow_factor=2.0,
    )

    assert barlow_result.effective_focal_length_mm == pytest.approx(1300.0)

    assert barlow_result.image_scale_arcsec_per_pixel == pytest.approx(
        native_result.image_scale_arcsec_per_pixel / 2.0,
        abs=0.0001,
    )

    assert barlow_result.field_width_degrees < native_result.field_width_degrees


def test_reducer_widens_sensor_field(
    reflector: TelescopeSpec,
    aps_c_camera: CameraSensorSpec,
) -> None:
    native_result = calculate_astrophotography_setup(
        telescope=reflector,
        camera=aps_c_camera,
    )

    reduced_result = calculate_astrophotography_setup(
        telescope=reflector,
        camera=aps_c_camera,
        reducer_factor=0.8,
    )

    assert reduced_result.effective_focal_length_mm == pytest.approx(520.0)

    assert reduced_result.field_width_degrees > native_result.field_width_degrees

    assert reduced_result.image_scale_arcsec_per_pixel > native_result.image_scale_arcsec_per_pixel


@pytest.mark.parametrize(
    (
        "image_scale",
        "seeing",
        "expected",
    ),
    [
        (
            0.50,
            2.0,
            "oversampled",
        ),
        (
            0.80,
            2.0,
            "well_sampled",
        ),
        (
            1.50,
            2.0,
            "undersampled",
        ),
        (
            2.50,
            2.0,
            "severely_undersampled",
        ),
    ],
)
def test_sampling_classification(
    image_scale: float,
    seeing: float,
    expected: str,
) -> None:
    assert (
        classify_sampling(
            image_scale_arcsec_per_pixel=image_scale,
            seeing_arcseconds=seeing,
        )
        == expected
    )


def test_target_fits_comfortably() -> None:
    target = ImagingTargetSpec(
        key="test",
        width_degrees=1.0,
        height_degrees=1.0,
    )

    result = calculate_target_framing(
        field_width_degrees=2.0,
        field_height_degrees=2.0,
        target=target,
    )

    assert result.status == "comfortable"
    assert result.total_panels == 1


def test_target_fit_is_tight() -> None:
    target = ImagingTargetSpec(
        key="test",
        width_degrees=1.0,
        height_degrees=1.0,
    )

    result = calculate_target_framing(
        field_width_degrees=1.1,
        field_height_degrees=1.1,
        target=target,
    )

    assert result.status == "tight"
    assert result.total_panels == 1


def test_mosaic_panel_calculation() -> None:
    target = ImagingTargetSpec(
        key="large_target",
        width_degrees=5.0,
        height_degrees=2.0,
    )

    result = calculate_target_framing(
        field_width_degrees=2.0,
        field_height_degrees=1.0,
        target=target,
        overlap_percent=20.0,
    )

    assert result.status == "mosaic_required"
    assert result.panels_horizontal == 3
    assert result.panels_vertical == 3
    assert result.total_panels == 9
    assert result.covered_width_degrees >= 5.0
    assert result.covered_height_degrees >= 2.0


def test_camera_comparison_sorts_widest_first(
    reflector: TelescopeSpec,
) -> None:
    narrow_camera = CameraSensorSpec(
        width_pixels=1936,
        height_pixels=1096,
        pixel_size_um=2.9,
    )

    wide_camera = CameraSensorSpec(
        width_pixels=6248,
        height_pixels=4176,
        pixel_size_um=3.76,
    )

    results = compare_camera_sensors(
        telescope=reflector,
        cameras=(
            narrow_camera,
            wide_camera,
        ),
    )

    assert results[0].camera == wide_camera
    assert results[1].camera == narrow_camera

    assert results[0].field_diagonal_degrees > results[1].field_diagonal_degrees


@pytest.mark.parametrize(
    (
        "width_pixels",
        "height_pixels",
        "pixel_size_um",
    ),
    [
        (
            0,
            4000,
            4.0,
        ),
        (
            6000,
            -1,
            4.0,
        ),
        (
            6000,
            4000,
            0.0,
        ),
    ],
)
def test_invalid_camera_values_raise_error(
    width_pixels: int,
    height_pixels: int,
    pixel_size_um: float,
) -> None:
    with pytest.raises(ValueError):
        CameraSensorSpec(
            width_pixels=width_pixels,
            height_pixels=height_pixels,
            pixel_size_um=pixel_size_um,
        )


def test_invalid_overlap_raises_error() -> None:
    target = ImagingTargetSpec(
        key="test",
        width_degrees=1.0,
        height_degrees=1.0,
    )

    with pytest.raises(ValueError):
        calculate_target_framing(
            field_width_degrees=2.0,
            field_height_degrees=2.0,
            target=target,
            overlap_percent=100.0,
        )


def test_invalid_accessory_factors_raise_error(
    reflector: TelescopeSpec,
    aps_c_camera: CameraSensorSpec,
) -> None:
    with pytest.raises(ValueError):
        calculate_astrophotography_setup(
            telescope=reflector,
            camera=aps_c_camera,
            barlow_factor=0.5,
        )

    with pytest.raises(ValueError):
        calculate_astrophotography_setup(
            telescope=reflector,
            camera=aps_c_camera,
            reducer_factor=1.5,
        )
