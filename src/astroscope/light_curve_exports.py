"""CSV exports for astronomical light-curve analysis results."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO

from astroscope.light_curve import LightCurve, LightCurveError
from astroscope.light_curve_phase import (
    PhaseBinningResult,
    PhaseFoldResult,
)


class LightCurveExportError(LightCurveError):
    """Raised when a light-curve result cannot be exported."""


def _write_csv(
    headers: tuple[str, ...],
    rows: Iterable[tuple[object, ...]],
) -> str:
    """Write deterministic CSV text using Unix line endings."""

    output = StringIO(
        newline="",
    )

    writer = csv.writer(
        output,
        lineterminator="\n",
    )

    writer.writerow(headers)
    writer.writerows(rows)

    return output.getvalue()


def _optional_number(
    value: float | None,
) -> float | str:
    """Return a number or a blank CSV cell."""

    if value is None:
        return ""

    return value


def light_curve_to_csv(
    light_curve: LightCurve,
) -> str:
    """Export one imported or processed light curve."""

    if not isinstance(
        light_curve,
        LightCurve,
    ):
        raise LightCurveExportError("Light-curve export requires a LightCurve instance.")

    metadata = light_curve.metadata

    rows = (
        (
            metadata.object_name,
            metadata.photometry_kind,
            point.time,
            point.value,
            _optional_number(point.uncertainty),
        )
        for point in light_curve.points
    )

    return _write_csv(
        (
            "object_name",
            "photometry_kind",
            "time",
            "value",
            "uncertainty",
        ),
        rows,
    )


def phase_fold_to_csv(
    phase_fold: PhaseFoldResult,
) -> str:
    """Export every observation from a phase-folded light curve."""

    if not isinstance(
        phase_fold,
        PhaseFoldResult,
    ):
        raise LightCurveExportError("Phase-fold export requires a PhaseFoldResult instance.")

    metadata = phase_fold.light_curve.metadata

    rows = (
        (
            metadata.object_name,
            metadata.photometry_kind,
            phase_fold.period,
            phase_fold.epoch,
            point.time,
            point.phase,
            point.cycle,
            point.value,
            _optional_number(point.uncertainty),
        )
        for point in phase_fold.points
    )

    return _write_csv(
        (
            "object_name",
            "photometry_kind",
            "period",
            "epoch",
            "time",
            "phase",
            "cycle",
            "value",
            "uncertainty",
        ),
        rows,
    )


def phase_bins_to_csv(
    phase_binning: PhaseBinningResult,
) -> str:
    """Export populated phase-bin summaries."""

    if not isinstance(
        phase_binning,
        PhaseBinningResult,
    ):
        raise LightCurveExportError("Phase-bin export requires a PhaseBinningResult instance.")

    phase_fold = phase_binning.phase_fold
    metadata = phase_fold.light_curve.metadata

    rows = (
        (
            metadata.object_name,
            metadata.photometry_kind,
            phase_fold.period,
            phase_fold.epoch,
            phase_binning.bin_count,
            phase_binning.minimum_points,
            phase_binning.weighted,
            phase_bin.index,
            phase_bin.phase_start,
            phase_bin.phase_end,
            phase_bin.phase_center,
            phase_bin.observation_count,
            phase_bin.value,
            _optional_number(phase_bin.uncertainty),
        )
        for phase_bin in phase_binning.bins
    )

    return _write_csv(
        (
            "object_name",
            "photometry_kind",
            "period",
            "epoch",
            "bin_count",
            "minimum_points",
            "weighted",
            "bin_index",
            "phase_start",
            "phase_end",
            "phase_center",
            "observation_count",
            "value",
            "uncertainty",
        ),
        rows,
    )
