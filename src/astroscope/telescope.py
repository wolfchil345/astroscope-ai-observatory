"""Telescope and eyepiece optical simulation."""

from dataclasses import dataclass
from math import isfinite
from typing import Final, Literal

OpticalStatus = Literal[
    "excessive_exit_pupil",
    "wide_field",
    "general_purpose",
    "high_power",
    "excessive_magnification",
]

DAWES_CONSTANT_ARCSEC_MM: Final[float] = 116.0
RAYLEIGH_CONSTANT_ARCSEC_MM: Final[float] = 138.0
MAXIMUM_MAGNIFICATION_PER_MM: Final[float] = 2.0
MAXIMUM_EYE_PUPIL_MM: Final[float] = 7.0
MINIMUM_PRACTICAL_EXIT_PUPIL_MM: Final[float] = 0.5


def _validate_positive_finite(
    value: float,
    label: str,
) -> None:
    """Require a positive finite numeric value."""

    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be a positive finite number.")


@dataclass(frozen=True, slots=True)
class TelescopeSpec:
    """Physical telescope specifications."""

    aperture_mm: float
    focal_length_mm: float

    def __post_init__(self) -> None:
        _validate_positive_finite(
            self.aperture_mm,
            "Telescope aperture",
        )

        _validate_positive_finite(
            self.focal_length_mm,
            "Telescope focal length",
        )

    @property
    def focal_ratio(self) -> float:
        """Return the native focal ratio."""

        return self.focal_length_mm / self.aperture_mm


@dataclass(frozen=True, slots=True)
class EyepieceSpec:
    """Eyepiece optical specifications."""

    focal_length_mm: float
    apparent_field_degrees: float

    def __post_init__(self) -> None:
        _validate_positive_finite(
            self.focal_length_mm,
            "Eyepiece focal length",
        )

        _validate_positive_finite(
            self.apparent_field_degrees,
            "Apparent field of view",
        )

        if self.apparent_field_degrees > 180.0:
            raise ValueError("Apparent field of view cannot exceed 180 degrees.")


@dataclass(frozen=True, slots=True)
class OpticalSimulationResult:
    """Calculated telescope and eyepiece performance."""

    telescope: TelescopeSpec
    eyepiece: EyepieceSpec
    barlow_factor: float
    reducer_factor: float
    native_focal_ratio: float
    effective_focal_length_mm: float
    effective_focal_ratio: float
    magnification: float
    exit_pupil_mm: float
    true_field_degrees: float
    dawes_resolution_arcseconds: float
    rayleigh_resolution_arcseconds: float
    minimum_useful_magnification: float
    maximum_useful_magnification: float
    status: OpticalStatus


TELESCOPE_PRESETS: Final[dict[str, TelescopeSpec]] = {
    "small_refractor": TelescopeSpec(
        aperture_mm=70.0,
        focal_length_mm=700.0,
    ),
    "medium_refractor": TelescopeSpec(
        aperture_mm=100.0,
        focal_length_mm=900.0,
    ),
    "compact_reflector": TelescopeSpec(
        aperture_mm=130.0,
        focal_length_mm=650.0,
    ),
    "large_reflector": TelescopeSpec(
        aperture_mm=200.0,
        focal_length_mm=1000.0,
    ),
    "long_focus_cassegrain": TelescopeSpec(
        aperture_mm=203.0,
        focal_length_mm=2032.0,
    ),
}


EYEPIECE_PRESETS: Final[dict[str, EyepieceSpec]] = {
    "plossl_32": EyepieceSpec(
        focal_length_mm=32.0,
        apparent_field_degrees=50.0,
    ),
    "plossl_25": EyepieceSpec(
        focal_length_mm=25.0,
        apparent_field_degrees=50.0,
    ),
    "wide_24": EyepieceSpec(
        focal_length_mm=24.0,
        apparent_field_degrees=68.0,
    ),
    "plossl_10": EyepieceSpec(
        focal_length_mm=10.0,
        apparent_field_degrees=50.0,
    ),
    "planetary_6": EyepieceSpec(
        focal_length_mm=6.0,
        apparent_field_degrees=60.0,
    ),
}


def classify_optical_setup(
    *,
    exit_pupil_mm: float,
    magnification: float,
    maximum_useful_magnification: float,
) -> OpticalStatus:
    """Classify the practical role of an optical setup."""

    _validate_positive_finite(
        exit_pupil_mm,
        "Exit pupil",
    )

    _validate_positive_finite(
        magnification,
        "Magnification",
    )

    _validate_positive_finite(
        maximum_useful_magnification,
        "Maximum useful magnification",
    )

    if (
        magnification > maximum_useful_magnification
        or exit_pupil_mm < MINIMUM_PRACTICAL_EXIT_PUPIL_MM
    ):
        return "excessive_magnification"

    if exit_pupil_mm > MAXIMUM_EYE_PUPIL_MM:
        return "excessive_exit_pupil"

    if exit_pupil_mm >= 2.0:
        return "wide_field"

    if exit_pupil_mm >= 1.0:
        return "general_purpose"

    return "high_power"


def calculate_optical_simulation(
    telescope: TelescopeSpec,
    eyepiece: EyepieceSpec,
    *,
    barlow_factor: float = 1.0,
    reducer_factor: float = 1.0,
) -> OpticalSimulationResult:
    """Calculate telescope and eyepiece performance."""

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

    magnification = effective_focal_length / eyepiece.focal_length_mm

    exit_pupil = telescope.aperture_mm / magnification

    true_field = eyepiece.apparent_field_degrees / magnification

    dawes_resolution = DAWES_CONSTANT_ARCSEC_MM / telescope.aperture_mm

    rayleigh_resolution = RAYLEIGH_CONSTANT_ARCSEC_MM / telescope.aperture_mm

    minimum_useful_magnification = telescope.aperture_mm / MAXIMUM_EYE_PUPIL_MM

    maximum_useful_magnification = telescope.aperture_mm * MAXIMUM_MAGNIFICATION_PER_MM

    status = classify_optical_setup(
        exit_pupil_mm=exit_pupil,
        magnification=magnification,
        maximum_useful_magnification=(maximum_useful_magnification),
    )

    return OpticalSimulationResult(
        telescope=telescope,
        eyepiece=eyepiece,
        barlow_factor=barlow_factor,
        reducer_factor=reducer_factor,
        native_focal_ratio=round(
            telescope.focal_ratio,
            3,
        ),
        effective_focal_length_mm=round(
            effective_focal_length,
            3,
        ),
        effective_focal_ratio=round(
            effective_focal_ratio,
            3,
        ),
        magnification=round(
            magnification,
            3,
        ),
        exit_pupil_mm=round(
            exit_pupil,
            3,
        ),
        true_field_degrees=round(
            true_field,
            4,
        ),
        dawes_resolution_arcseconds=round(
            dawes_resolution,
            4,
        ),
        rayleigh_resolution_arcseconds=round(
            rayleigh_resolution,
            4,
        ),
        minimum_useful_magnification=round(
            minimum_useful_magnification,
            3,
        ),
        maximum_useful_magnification=round(
            maximum_useful_magnification,
            3,
        ),
        status=status,
    )


def compare_eyepieces(
    telescope: TelescopeSpec,
    eyepieces: tuple[EyepieceSpec, ...],
    *,
    barlow_factor: float = 1.0,
    reducer_factor: float = 1.0,
) -> tuple[OpticalSimulationResult, ...]:
    """Compare eyepieces from lowest to highest power."""

    results = tuple(
        calculate_optical_simulation(
            telescope=telescope,
            eyepiece=eyepiece,
            barlow_factor=barlow_factor,
            reducer_factor=reducer_factor,
        )
        for eyepiece in eyepieces
    )

    return tuple(
        sorted(
            results,
            key=lambda result: result.magnification,
        )
    )
