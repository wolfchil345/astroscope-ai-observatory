"""CSV and JSON exports for scientific light-curve analysis."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from io import StringIO
from typing import Protocol

from astroscope.light_curve import LightCurve
from astroscope.light_curve_exports import LightCurveExportError
from astroscope.light_curve_transit_diagnostics import (
    TransitCandidateDiagnostics,
)
from astroscope.light_curve_transit_search import (
    BoxLeastSquaresSearchResult,
    TransitSearchCandidate,
)


class PeriodCandidateLike(Protocol):
    """Structural type for one ranked period candidate."""

    rank: int
    period: float
    power: float


class PeriodSearchResultLike(Protocol):
    """Structural type for a result containing period candidates."""

    candidates: tuple[PeriodCandidateLike, ...]


def _write_csv(
    headers: tuple[str, ...],
    rows: Iterable[tuple[object, ...]],
) -> str:
    """Write deterministic CSV text with Unix line endings."""

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
    """Return a numeric value or a blank CSV cell."""

    if value is None:
        return ""

    return value


def _json_optional_number(
    value: float | None,
) -> float | None:
    """Return a JSON-compatible optional floating-point value."""

    if value is None:
        return None

    return float(value)


def _extract_period_candidates(
    result: PeriodSearchResultLike,
) -> tuple[PeriodCandidateLike, ...]:
    """Extract candidates from a structural period-search result."""

    try:
        return tuple(result.candidates)
    except (AttributeError, TypeError) as exc:
        raise LightCurveExportError(
            "Period-candidate export requires a result with an iterable candidates attribute."
        ) from exc


def period_candidates_to_csv(
    result: PeriodSearchResultLike,
) -> str:
    """Export ranked Lomb-Scargle or similar period candidates."""

    candidates = _extract_period_candidates(result)

    rows = (
        (
            candidate.rank,
            candidate.period,
            candidate.power,
        )
        for candidate in candidates
    )

    return _write_csv(
        (
            "rank",
            "period",
            "power",
        ),
        rows,
    )


def transit_candidates_to_csv(
    result: BoxLeastSquaresSearchResult,
) -> str:
    """Export ranked Box Least Squares transit candidates."""

    if not isinstance(
        result,
        BoxLeastSquaresSearchResult,
    ):
        raise LightCurveExportError(
            "Transit-candidate export requires a BoxLeastSquaresSearchResult instance."
        )

    rows = (
        (
            candidate.rank,
            candidate.period,
            candidate.power,
            candidate.duration,
            candidate.transit_time,
            candidate.depth,
            _optional_number(candidate.depth_error),
            candidate.depth_snr,
        )
        for candidate in result.candidates
    )

    return _write_csv(
        (
            "rank",
            "period",
            "power",
            "duration",
            "transit_time",
            "depth",
            "depth_error",
            "depth_snr",
        ),
        rows,
    )


def transit_diagnostics_to_csv(
    diagnostics: TransitCandidateDiagnostics,
) -> str:
    """Export every observation from transit diagnostics."""

    if not isinstance(
        diagnostics,
        TransitCandidateDiagnostics,
    ):
        raise LightCurveExportError(
            "Transit-diagnostic export requires a TransitCandidateDiagnostics instance."
        )

    candidate = diagnostics.candidate

    rows = (
        (
            candidate.rank,
            candidate.period,
            candidate.duration,
            candidate.transit_time,
            candidate.depth,
            diagnostics.measured_depth,
            diagnostics.depth_difference,
            diagnostics.residual_rms,
            diagnostics.in_transit_rms,
            diagnostics.out_of_transit_rms,
            point.time,
            point.phase,
            point.phase_time,
            point.cycle,
            point.in_transit,
            point.observed_flux,
            point.model_flux,
            point.residual,
            _optional_number(point.uncertainty),
        )
        for point in diagnostics.points
    )

    return _write_csv(
        (
            "candidate_rank",
            "period",
            "duration",
            "transit_time",
            "predicted_depth",
            "measured_depth",
            "depth_difference",
            "residual_rms",
            "in_transit_rms",
            "out_of_transit_rms",
            "time",
            "phase",
            "phase_time",
            "cycle",
            "in_transit",
            "observed_flux",
            "model_flux",
            "residual",
            "uncertainty",
        ),
        rows,
    )


def _period_candidate_payload(
    candidate: PeriodCandidateLike,
) -> dict[str, object]:
    """Convert one period candidate into JSON-compatible data."""

    return {
        "rank": int(candidate.rank),
        "period": float(candidate.period),
        "power": float(candidate.power),
    }


def _transit_candidate_payload(
    candidate: TransitSearchCandidate,
) -> dict[str, object]:
    """Convert one transit candidate into JSON-compatible data."""

    return {
        "rank": int(candidate.rank),
        "period": float(candidate.period),
        "power": float(candidate.power),
        "duration": float(candidate.duration),
        "transit_time": float(candidate.transit_time),
        "depth": float(candidate.depth),
        "depth_error": _json_optional_number(candidate.depth_error),
        "depth_snr": float(candidate.depth_snr),
    }


def _transit_search_payload(
    result: BoxLeastSquaresSearchResult,
) -> dict[str, object]:
    """Convert a BLS search result into summary data."""

    return {
        "minimum_period": float(result.minimum_period),
        "maximum_period": float(result.maximum_period),
        "durations": [float(duration) for duration in result.durations],
        "objective": result.objective,
        "observation_baseline": float(result.observation_baseline),
        "weighted": bool(result.weighted),
        "candidates": [_transit_candidate_payload(candidate) for candidate in result.candidates],
    }


def _diagnostic_payload(
    diagnostics: TransitCandidateDiagnostics,
) -> dict[str, object]:
    """Convert transit diagnostics into JSON summary data."""

    return {
        "candidate": _transit_candidate_payload(diagnostics.candidate),
        "measured_depth": float(diagnostics.measured_depth),
        "depth_difference": float(diagnostics.depth_difference),
        "residual_rms": float(diagnostics.residual_rms),
        "in_transit_rms": float(diagnostics.in_transit_rms),
        "out_of_transit_rms": float(diagnostics.out_of_transit_rms),
        "in_transit_count": int(diagnostics.in_transit_count),
        "out_of_transit_count": int(diagnostics.out_of_transit_count),
        "model": {
            "baseline_flux": float(diagnostics.model.baseline_flux),
            "in_transit_flux": float(diagnostics.model.in_transit_flux),
        },
        "windows": [
            {
                "cycle": int(window.cycle),
                "midpoint": float(window.midpoint),
                "ingress": float(window.ingress),
                "egress": float(window.egress),
            }
            for window in diagnostics.windows
        ],
    }


def build_analysis_report(
    light_curve: LightCurve,
    *,
    period_result: PeriodSearchResultLike | None = None,
    transit_result: BoxLeastSquaresSearchResult | None = None,
    transit_diagnostics: TransitCandidateDiagnostics | None = None,
) -> dict[str, object]:
    """Build a machine-readable summary of light-curve analyses."""

    if not isinstance(
        light_curve,
        LightCurve,
    ):
        raise LightCurveExportError("Analysis reports require a LightCurve instance.")

    if not light_curve.points:
        raise LightCurveExportError("Analysis reports require at least one observation.")

    first_time = float(light_curve.points[0].time)
    last_time = float(light_curve.points[-1].time)

    report: dict[str, object] = {
        "schema_version": "1.0",
        "dataset": {
            "object_name": (light_curve.metadata.object_name),
            "photometry_kind": (light_curve.metadata.photometry_kind),
            "observation_count": len(light_curve.points),
            "time_start": first_time,
            "time_end": last_time,
            "time_span": last_time - first_time,
            "has_uncertainties": bool(light_curve.has_uncertainties),
        },
    }

    if period_result is not None:
        candidates = _extract_period_candidates(period_result)

        report["period_search"] = {
            "candidates": [_period_candidate_payload(candidate) for candidate in candidates]
        }

    if transit_result is not None:
        if not isinstance(
            transit_result,
            BoxLeastSquaresSearchResult,
        ):
            raise LightCurveExportError(
                "Transit report data requires a BoxLeastSquaresSearchResult instance."
            )

        report["transit_search"] = _transit_search_payload(transit_result)

    if transit_diagnostics is not None:
        if not isinstance(
            transit_diagnostics,
            TransitCandidateDiagnostics,
        ):
            raise LightCurveExportError(
                "Diagnostic report data requires a TransitCandidateDiagnostics instance."
            )

        report["transit_diagnostics"] = _diagnostic_payload(transit_diagnostics)

    return report


def analysis_report_to_json(
    light_curve: LightCurve,
    *,
    period_result: PeriodSearchResultLike | None = None,
    transit_result: BoxLeastSquaresSearchResult | None = None,
    transit_diagnostics: TransitCandidateDiagnostics | None = None,
    indent: int | None = 2,
) -> str:
    """Serialize a complete analysis report as deterministic JSON."""

    if indent is not None and (
        isinstance(indent, bool) or not isinstance(indent, int) or indent < 0
    ):
        raise LightCurveExportError("JSON indentation must be a nonnegative integer or None.")

    report = build_analysis_report(
        light_curve,
        period_result=period_result,
        transit_result=transit_result,
        transit_diagnostics=transit_diagnostics,
    )

    try:
        content = json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            indent=indent,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise LightCurveExportError(
            "The analysis report contains data that cannot be represented as valid JSON."
        ) from exc

    return f"{content}\n"
