"""CSV ingestion utilities for astronomical light curves."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Literal

from astroscope.light_curve import (
    LightCurve,
    LightCurveError,
    LightCurveMetadata,
    LightCurvePoint,
    PhotometryKind,
)

DuplicatePolicy = Literal["error", "keep-first"]


class LightCurveIOError(LightCurveError):
    """Raised when light-curve input cannot be imported."""


@dataclass(frozen=True, slots=True)
class LightCurveColumnMap:
    """Map CSV column names to light-curve properties."""

    time: str
    value: str
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        required_names = (self.time, self.value)

        if any(not name.strip() for name in required_names):
            raise LightCurveIOError("Time and photometry column names must not be empty.")

        names = [
            self.time,
            self.value,
        ]

        if self.uncertainty is not None:
            if not self.uncertainty.strip():
                raise LightCurveIOError("Uncertainty column name must not be empty.")

            names.append(self.uncertainty)

        if len(names) != len(set(names)):
            raise LightCurveIOError("CSV column mappings must use distinct columns.")


@dataclass(frozen=True, slots=True)
class LightCurveImportResult:
    """Imported light curve and its CSV processing report."""

    light_curve: LightCurve
    total_rows: int
    imported_rows: int
    skipped_rows: int
    duplicate_rows: int
    original_was_sorted: bool


def _validate_columns(
    *,
    fieldnames: list[str] | None,
    columns: LightCurveColumnMap,
) -> None:
    """Confirm that all mapped columns exist."""

    if not fieldnames:
        raise LightCurveIOError("CSV input must contain a header row.")

    required = {
        columns.time,
        columns.value,
    }

    if columns.uncertainty is not None:
        required.add(columns.uncertainty)

    missing = sorted(required.difference(fieldnames))

    if missing:
        formatted = ", ".join(missing)

        raise LightCurveIOError(f"CSV input is missing mapped columns: {formatted}.")


def _parse_optional_float(
    raw_value: str | None,
) -> float | None:
    """Parse an optional floating-point value."""

    if raw_value is None:
        return None

    stripped = raw_value.strip()

    if not stripped:
        return None

    return float(stripped)


def import_light_curve_csv(
    *,
    csv_text: str,
    metadata: LightCurveMetadata,
    columns: LightCurveColumnMap,
    duplicate_policy: DuplicatePolicy = "error",
) -> LightCurveImportResult:
    """Import an astronomical light curve from CSV text."""

    if duplicate_policy not in {"error", "keep-first"}:
        raise LightCurveIOError("Duplicate policy must be 'error' or 'keep-first'.")

    if not csv_text.strip():
        raise LightCurveIOError("CSV input must not be empty.")

    reader = csv.DictReader(StringIO(csv_text))

    if reader.fieldnames is not None:
        reader.fieldnames = [fieldname.strip() for fieldname in reader.fieldnames]

    _validate_columns(
        fieldnames=reader.fieldnames,
        columns=columns,
    )

    points: list[LightCurvePoint] = []
    seen_times: set[float] = set()
    source_times: list[float] = []

    total_rows = 0
    skipped_rows = 0
    duplicate_rows = 0

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1

        try:
            time = float(row[columns.time].strip())
            value = float(row[columns.value].strip())

            uncertainty = (
                _parse_optional_float(row.get(columns.uncertainty))
                if columns.uncertainty is not None
                else None
            )

            point = LightCurvePoint(
                time=time,
                value=value,
                uncertainty=uncertainty,
            )
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            LightCurveError,
        ):
            skipped_rows += 1
            continue

        if point.time in seen_times:
            duplicate_rows += 1

            if duplicate_policy == "error":
                raise LightCurveIOError(
                    f"Duplicate observation time {point.time} found on CSV row {row_number}."
                )

            skipped_rows += 1
            continue

        seen_times.add(point.time)
        source_times.append(point.time)
        points.append(point)

    if len(points) < 3:
        raise LightCurveIOError("CSV input must contain at least three valid, unique observations.")

    original_was_sorted = source_times == sorted(source_times)

    ordered_points = tuple(
        sorted(
            points,
            key=lambda point: point.time,
        )
    )

    light_curve = LightCurve(
        metadata=metadata,
        points=ordered_points,
    )

    return LightCurveImportResult(
        light_curve=light_curve,
        total_rows=total_rows,
        imported_rows=len(points),
        skipped_rows=skipped_rows,
        duplicate_rows=duplicate_rows,
        original_was_sorted=original_was_sorted,
    )


_TIME_COLUMN_ALIASES = (
    "time",
    "timestamp",
    "bjd_tdb",
    "bjd",
    "jd",
    "hjd",
    "mjd",
    "btjd",
)

_FLUX_COLUMN_ALIASES = (
    "normalized_flux",
    "normalised_flux",
    "norm_flux",
    "relative_flux",
    "detrended_flux",
    "pdcsap_flux",
    "sap_flux",
    "flux",
)

_MAGNITUDE_COLUMN_ALIASES = (
    "differential_magnitude",
    "differential_mag",
    "magnitude",
    "mag",
)

_FLUX_UNCERTAINTY_ALIASES = (
    "flux_error",
    "flux_err",
    "flux_uncertainty",
    "flux_sigma",
)

_MAGNITUDE_UNCERTAINTY_ALIASES = (
    "magnitude_error",
    "magnitude_err",
    "mag_error",
    "mag_err",
    "mag_uncertainty",
    "mag_sigma",
)

_GENERIC_UNCERTAINTY_ALIASES = (
    "uncertainty",
    "error",
    "err",
    "sigma",
    "stddev",
    "standard_deviation",
)

_TIME_STANDARD_BY_HEADER = {
    "bjd_tdb": "BJD_TDB",
    "bjd": "BJD",
    "jd": "JD",
    "hjd": "HJD",
    "mjd": "MJD",
    "btjd": "BTJD",
}


@dataclass(frozen=True, slots=True)
class LightCurveColumnDetection:
    """Automatically detected light-curve CSV columns."""

    columns: LightCurveColumnMap
    photometry_kind: PhotometryKind
    suggested_time_standard: str | None = None


def _normalize_column_name(name: str) -> str:
    """Normalize a CSV header for alias matching."""

    normalized = "".join(
        character if character.isalnum() else "_" for character in name.strip().casefold()
    )

    return "_".join(part for part in normalized.split("_") if part)


def _matching_columns(
    fieldnames: list[str],
    aliases: tuple[str, ...],
) -> tuple[str, ...]:
    """Return original headers matching a collection of aliases."""

    alias_set = set(aliases)

    return tuple(
        fieldname for fieldname in fieldnames if _normalize_column_name(fieldname) in alias_set
    )


def _require_single_match(
    *,
    matches: tuple[str, ...],
    category: str,
) -> str:
    """Require exactly one automatic match."""

    if not matches:
        raise LightCurveIOError(f"Could not automatically detect a {category} column.")

    if len(matches) > 1:
        formatted = ", ".join(matches)

        raise LightCurveIOError(
            f"Multiple possible {category} columns were found: "
            f"{formatted}. Select the column explicitly."
        )

    return matches[0]


def detect_light_curve_columns(
    fieldnames: list[str],
) -> LightCurveColumnDetection:
    """Automatically detect common astronomical CSV columns."""

    cleaned_fieldnames = [
        fieldname.strip() for fieldname in fieldnames if fieldname and fieldname.strip()
    ]

    if not cleaned_fieldnames:
        raise LightCurveIOError("CSV input must contain named columns.")

    time_column = _require_single_match(
        matches=_matching_columns(
            cleaned_fieldnames,
            _TIME_COLUMN_ALIASES,
        ),
        category="time",
    )

    flux_matches = _matching_columns(
        cleaned_fieldnames,
        _FLUX_COLUMN_ALIASES,
    )
    magnitude_matches = _matching_columns(
        cleaned_fieldnames,
        _MAGNITUDE_COLUMN_ALIASES,
    )

    if flux_matches and magnitude_matches:
        raise LightCurveIOError(
            "Both flux and magnitude columns were detected. "
            "Select the photometry column explicitly."
        )

    if flux_matches:
        value_column = _require_single_match(
            matches=flux_matches,
            category="flux",
        )
        photometry_kind: PhotometryKind = "flux"
        uncertainty_aliases = _FLUX_UNCERTAINTY_ALIASES + _GENERIC_UNCERTAINTY_ALIASES
    elif magnitude_matches:
        value_column = _require_single_match(
            matches=magnitude_matches,
            category="magnitude",
        )
        photometry_kind = "magnitude"
        uncertainty_aliases = _MAGNITUDE_UNCERTAINTY_ALIASES + _GENERIC_UNCERTAINTY_ALIASES
    else:
        raise LightCurveIOError("Could not automatically detect a flux or magnitude column.")

    uncertainty_matches = _matching_columns(
        cleaned_fieldnames,
        uncertainty_aliases,
    )

    if len(uncertainty_matches) > 1:
        formatted = ", ".join(uncertainty_matches)

        raise LightCurveIOError(
            "Multiple possible uncertainty columns were found: "
            f"{formatted}. Select the column explicitly."
        )

    uncertainty_column = uncertainty_matches[0] if uncertainty_matches else None

    normalized_time_column = _normalize_column_name(time_column)

    return LightCurveColumnDetection(
        columns=LightCurveColumnMap(
            time=time_column,
            value=value_column,
            uncertainty=uncertainty_column,
        ),
        photometry_kind=photometry_kind,
        suggested_time_standard=_TIME_STANDARD_BY_HEADER.get(normalized_time_column),
    )


def detect_light_curve_csv_columns(
    csv_text: str,
) -> LightCurveColumnDetection:
    """Detect light-curve columns directly from CSV text."""

    if not csv_text.strip():
        raise LightCurveIOError("CSV input must not be empty.")

    reader = csv.DictReader(StringIO(csv_text))

    if not reader.fieldnames:
        raise LightCurveIOError("CSV input must contain a header row.")

    return detect_light_curve_columns(reader.fieldnames)
