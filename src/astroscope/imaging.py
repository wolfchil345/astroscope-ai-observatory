"""Astrophotography camera, sampling, and framing calculations."""

from dataclasses import dataclass
from math import atan, ceil, degrees, hypot, isfinite
from typing import Final, Literal

from astroscope.telescope import (
    DAWES_CONSTANT_ARCSEC_MM,
    TelescopeSpec,
)

SamplingStatus = Literal[
    "oversampled",
    "well_sampled",
    "undersampled",
    "severely_undersampled",
]

FramingStatus = Literal[
    "comfortable",
    "tight",
    "mosaic_required",
]

PLATE_SCALE_CONSTANT: Final[float] = 206.265
COMFORTABLE_FRAME_FRACTION: Final[float] = 0.80


def _validate_positive_finite(
    value: float,
    label: str,
) -> None:
    """Require a positive finite numeric value."""

    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be a positive finite number.")


def _validate_pixel_count(
    value: int,
    label: str,
) -> None:
    """Require a positive integer pixel count."""

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer.")


@dataclass(frozen=True, slots=True)
class CameraSensorSpec:
    """Physical specifications of a digital camera sensor."""

    width_pixels: int
    height_pixels: int
    pixel_size_um: float

    def __post_init__(self) -> None:
        _validate_pixel_count(
            self.width_pixels,
            "Sensor width",
        )

        _validate_pixel_count(
            self.height_pixels,
            "Sensor height",
        )

        _validate_positive_finite(
            self.pixel_size_um,
            "Pixel size",
        )

    @property
    def sensor_width_mm(self) -> float:
        """Return the physical sensor width."""

        return self.width_pixels * self.pixel_size_um / 1000.0

    @property
    def sensor_height_mm(self) -> float:
        """Return the physical sensor height."""

        return self.height_pixels * self.pixel_size_um / 1000.0

    @property
    def megapixels(self) -> float:
        """Return the approximate sensor resolution."""

        return self.width_pixels * self.height_pixels / 1_000_000.0


@dataclass(frozen=True, slots=True)
class ImagingTargetSpec:
    """Approximate angular dimensions of an imaging target."""

    key: str
    width_degrees: float
    height_degrees: float

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("Imaging target key cannot be empty.")

        _validate_positive_finite(
            self.width_degrees,
            "Target width",
        )

        _validate_positive_finite(
            self.height_degrees,
            "Target height",
        )


@dataclass(frozen=True, slots=True)
class AstrophotographyResult:
    """Calculated telescope and camera performance."""

    telescope: TelescopeSpec
    camera: CameraSensorSpec
    seeing_arcseconds: float
    barlow_factor: float
    reducer_factor: float
    effective_focal_length_mm: float
    effective_focal_ratio: float
    sensor_width_mm: float
    sensor_height_mm: float
    megapixels: float
    image_scale_arcsec_per_pixel: float
    field_width_degrees: float
    field_height_degrees: float
    field_diagonal_degrees: float
    seeing_disk_pixels: float
    dawes_resolution_arcseconds: float
    dawes_resolution_pixels: float
    ideal_scale_min_arcsec_per_pixel: float
    ideal_scale_max_arcsec_per_pixel: float
    sampling_status: SamplingStatus


@dataclass(frozen=True, slots=True)
class TargetFramingResult:
    """Target fit and mosaic requirements."""

    target: ImagingTargetSpec
    field_width_degrees: float
    field_height_degrees: float
    overlap_percent: float
    width_fill_percent: float
    height_fill_percent: float
    panels_horizontal: int
    panels_vertical: int
    total_panels: int
    covered_width_degrees: float
    covered_height_degrees: float
    status: FramingStatus


CAMERA_PRESETS: Final[dict[str, CameraSensorSpec]] = {
    "planetary_camera": CameraSensorSpec(
        width_pixels=1936,
        height_pixels=1096,
        pixel_size_um=2.90,
    ),
    "square_cooled_camera": CameraSensorSpec(
        width_pixels=3008,
        height_pixels=3008,
        pixel_size_um=3.76,
    ),
    "four_thirds_camera": CameraSensorSpec(
        width_pixels=4144,
        height_pixels=2822,
        pixel_size_um=4.63,
    ),
    "aps_c_camera": CameraSensorSpec(
        width_pixels=6248,
        height_pixels=4176,
        pixel_size_um=3.76,
    ),
    "full_frame_camera": CameraSensorSpec(
        width_pixels=9576,
        height_pixels=6388,
        pixel_size_um=3.76,
    ),
}


IMAGING_TARGET_PRESETS: Final[dict[str, ImagingTargetSpec]] = {
    "moon": ImagingTargetSpec(
        key="moon",
        width_degrees=0.50,
        height_degrees=0.50,
    ),
    "m31": ImagingTargetSpec(
        key="m31",
        width_degrees=3.10,
        height_degrees=1.00,
    ),
    "pleiades": ImagingTargetSpec(
        key="pleiades",
        width_degrees=1.80,
        height_degrees=1.80,
    ),
    "orion_nebula": ImagingTargetSpec(
        key="orion_nebula",
        width_degrees=1.10,
        height_degrees=1.00,
    ),
    "rosette_nebula": ImagingTargetSpec(
        key="rosette_nebula",
        width_degrees=1.30,
        height_degrees=1.30,
    ),
    "lagoon_nebula": ImagingTargetSpec(
        key="lagoon_nebula",
        width_degrees=1.50,
        height_degrees=0.70,
    ),
}


def calculate_sensor_field_degrees(
    sensor_size_mm: float,
    effective_focal_length_mm: float,
) -> float:
    """Calculate an exact angular sensor dimension."""

    _validate_positive_finite(
        sensor_size_mm,
        "Sensor size",
    )

    _validate_positive_finite(
        effective_focal_length_mm,
        "Effective focal length",
    )

    field_radians = 2.0 * atan(sensor_size_mm / (2.0 * effective_focal_length_mm))

    return degrees(field_radians)


def classify_sampling(
    *,
    image_scale_arcsec_per_pixel: float,
    seeing_arcseconds: float,
) -> SamplingStatus:
    """Classify sensor sampling relative to seeing."""

    _validate_positive_finite(
        image_scale_arcsec_per_pixel,
        "Image scale",
    )

    _validate_positive_finite(
        seeing_arcseconds,
        "Seeing",
    )

    ideal_minimum = seeing_arcseconds / 3.0
    ideal_maximum = seeing_arcseconds / 2.0

    if image_scale_arcsec_per_pixel < ideal_minimum:
        return "oversampled"

    if image_scale_arcsec_per_pixel <= ideal_maximum:
        return "well_sampled"

    if image_scale_arcsec_per_pixel <= seeing_arcseconds:
        return "undersampled"

    return "severely_undersampled"


def calculate_astrophotography_setup(
    telescope: TelescopeSpec,
    camera: CameraSensorSpec,
    *,
    seeing_arcseconds: float = 2.0,
    barlow_factor: float = 1.0,
    reducer_factor: float = 1.0,
) -> AstrophotographyResult:
    """Calculate a telescope and camera imaging setup."""

    _validate_positive_finite(
        seeing_arcseconds,
        "Seeing",
    )

    _validate_positive_finite(
        barlow_factor,
        "Barlow factor",
    )

    _validate_positive_finite(
        reducer_factor,
        "Reducer factor",
    )

    if barlow_factor < 1.0:
        raise ValueError("Barlow factor must be at least 1.0.")

    if reducer_factor > 1.0:
        raise ValueError("Reducer factor cannot exceed 1.0.")

    effective_focal_length = telescope.focal_length_mm * barlow_factor * reducer_factor

    effective_focal_ratio = effective_focal_length / telescope.aperture_mm

    image_scale = PLATE_SCALE_CONSTANT * camera.pixel_size_um / effective_focal_length

    field_width = calculate_sensor_field_degrees(
        sensor_size_mm=camera.sensor_width_mm,
        effective_focal_length_mm=(effective_focal_length),
    )

    field_height = calculate_sensor_field_degrees(
        sensor_size_mm=camera.sensor_height_mm,
        effective_focal_length_mm=(effective_focal_length),
    )

    field_diagonal = hypot(
        field_width,
        field_height,
    )

    seeing_disk_pixels = seeing_arcseconds / image_scale

    dawes_resolution = DAWES_CONSTANT_ARCSEC_MM / telescope.aperture_mm

    dawes_resolution_pixels = dawes_resolution / image_scale

    sampling_status = classify_sampling(
        image_scale_arcsec_per_pixel=image_scale,
        seeing_arcseconds=seeing_arcseconds,
    )

    return AstrophotographyResult(
        telescope=telescope,
        camera=camera,
        seeing_arcseconds=seeing_arcseconds,
        barlow_factor=barlow_factor,
        reducer_factor=reducer_factor,
        effective_focal_length_mm=round(
            effective_focal_length,
            3,
        ),
        effective_focal_ratio=round(
            effective_focal_ratio,
            3,
        ),
        sensor_width_mm=round(
            camera.sensor_width_mm,
            3,
        ),
        sensor_height_mm=round(
            camera.sensor_height_mm,
            3,
        ),
        megapixels=round(
            camera.megapixels,
            3,
        ),
        image_scale_arcsec_per_pixel=round(
            image_scale,
            4,
        ),
        field_width_degrees=round(
            field_width,
            4,
        ),
        field_height_degrees=round(
            field_height,
            4,
        ),
        field_diagonal_degrees=round(
            field_diagonal,
            4,
        ),
        seeing_disk_pixels=round(
            seeing_disk_pixels,
            3,
        ),
        dawes_resolution_arcseconds=round(
            dawes_resolution,
            4,
        ),
        dawes_resolution_pixels=round(
            dawes_resolution_pixels,
            3,
        ),
        ideal_scale_min_arcsec_per_pixel=round(
            seeing_arcseconds / 3.0,
            4,
        ),
        ideal_scale_max_arcsec_per_pixel=round(
            seeing_arcseconds / 2.0,
            4,
        ),
        sampling_status=sampling_status,
    )


def _calculate_mosaic_panels(
    *,
    target_size_degrees: float,
    field_size_degrees: float,
    overlap_fraction: float,
) -> int:
    """Calculate panel count along one frame axis."""

    if target_size_degrees <= field_size_degrees:
        return 1

    panel_step = field_size_degrees * (1.0 - overlap_fraction)

    return 1 + ceil((target_size_degrees - field_size_degrees) / panel_step)


def calculate_target_framing(
    *,
    field_width_degrees: float,
    field_height_degrees: float,
    target: ImagingTargetSpec,
    overlap_percent: float = 15.0,
) -> TargetFramingResult:
    """Calculate target framing and mosaic requirements."""

    _validate_positive_finite(
        field_width_degrees,
        "Field width",
    )

    _validate_positive_finite(
        field_height_degrees,
        "Field height",
    )

    if not isfinite(overlap_percent) or not 0.0 <= overlap_percent < 100.0:
        raise ValueError("Mosaic overlap must be at least 0 and less than 100 percent.")

    comfortable_width = field_width_degrees * COMFORTABLE_FRAME_FRACTION

    comfortable_height = field_height_degrees * COMFORTABLE_FRAME_FRACTION

    if target.width_degrees <= comfortable_width and target.height_degrees <= comfortable_height:
        status: FramingStatus = "comfortable"

    elif (
        target.width_degrees <= field_width_degrees
        and target.height_degrees <= field_height_degrees
    ):
        status = "tight"

    else:
        status = "mosaic_required"

    overlap_fraction = overlap_percent / 100.0

    panels_horizontal = _calculate_mosaic_panels(
        target_size_degrees=target.width_degrees,
        field_size_degrees=field_width_degrees,
        overlap_fraction=overlap_fraction,
    )

    panels_vertical = _calculate_mosaic_panels(
        target_size_degrees=target.height_degrees,
        field_size_degrees=field_height_degrees,
        overlap_fraction=overlap_fraction,
    )

    horizontal_step = field_width_degrees * (1.0 - overlap_fraction)

    vertical_step = field_height_degrees * (1.0 - overlap_fraction)

    covered_width = field_width_degrees + (panels_horizontal - 1) * horizontal_step

    covered_height = field_height_degrees + (panels_vertical - 1) * vertical_step

    return TargetFramingResult(
        target=target,
        field_width_degrees=field_width_degrees,
        field_height_degrees=field_height_degrees,
        overlap_percent=overlap_percent,
        width_fill_percent=round(
            target.width_degrees / field_width_degrees * 100.0,
            2,
        ),
        height_fill_percent=round(
            target.height_degrees / field_height_degrees * 100.0,
            2,
        ),
        panels_horizontal=panels_horizontal,
        panels_vertical=panels_vertical,
        total_panels=(panels_horizontal * panels_vertical),
        covered_width_degrees=round(
            covered_width,
            4,
        ),
        covered_height_degrees=round(
            covered_height,
            4,
        ),
        status=status,
    )


def compare_camera_sensors(
    telescope: TelescopeSpec,
    cameras: tuple[CameraSensorSpec, ...],
    *,
    seeing_arcseconds: float = 2.0,
    barlow_factor: float = 1.0,
    reducer_factor: float = 1.0,
) -> tuple[AstrophotographyResult, ...]:
    """Compare cameras from widest to narrowest field."""

    results = tuple(
        calculate_astrophotography_setup(
            telescope=telescope,
            camera=camera,
            seeing_arcseconds=seeing_arcseconds,
            barlow_factor=barlow_factor,
            reducer_factor=reducer_factor,
        )
        for camera in cameras
    )

    return tuple(
        sorted(
            results,
            key=lambda result: result.field_diagonal_degrees,
            reverse=True,
        )
    )
