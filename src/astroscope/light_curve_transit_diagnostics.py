"""Transit models and diagnostics for light-curve candidates."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite, sqrt
from numbers import Real
from statistics import fmean, median

from astroscope.light_curve import LightCurve, LightCurveError
from astroscope.light_curve_transit_search import TransitSearchCandidate


class LightCurveTransitDiagnosticError(LightCurveError):
    """Raised when transit diagnostics cannot be calculated."""


@dataclass(frozen=True, slots=True)
class TransitWindow:
    """One predicted periodic transit window."""

    cycle: int
    midpoint: float
    ingress: float
    egress: float


@dataclass(frozen=True, slots=True)
class BoxTransitModel:
    """Box-shaped transit model evaluated at observation times."""

    baseline_flux: float
    in_transit_flux: float
    mask: tuple[bool, ...]
    fluxes: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class TransitDiagnosticPoint:
    """Observed and modelled values for one light-curve point."""

    time: float
    phase: float
    phase_time: float
    cycle: int
    in_transit: bool
    observed_flux: float
    model_flux: float
    residual: float
    uncertainty: float | None


@dataclass(frozen=True, slots=True)
class TransitCandidateDiagnostics:
    """Diagnostic summary for one transit-search candidate."""

    candidate: TransitSearchCandidate
    model: BoxTransitModel
    windows: tuple[TransitWindow, ...]
    points: tuple[TransitDiagnosticPoint, ...]
    measured_depth: float
    depth_difference: float
    residual_rms: float
    in_transit_rms: float
    out_of_transit_rms: float

    @property
    def in_transit_count(self) -> int:
        """Return the number of observations inside transit."""

        return sum(point.in_transit for point in self.points)

    @property
    def out_of_transit_count(self) -> int:
        """Return the number of observations outside transit."""

        return len(self.points) - self.in_transit_count


def _finite_float(
    value: object,
    *,
    name: str,
) -> float:
    """Convert one finite real value to float."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise LightCurveTransitDiagnosticError(f"{name} must be a finite real number.")

    converted = float(value)

    if not isfinite(converted):
        raise LightCurveTransitDiagnosticError(f"{name} must be a finite real number.")

    return converted


def _validate_candidate(
    light_curve: LightCurve,
    candidate: TransitSearchCandidate,
) -> None:
    """Validate a candidate for transit diagnostics."""

    if light_curve.metadata.photometry_kind != "flux":
        raise LightCurveTransitDiagnosticError("Transit diagnostics require flux measurements.")

    period = _finite_float(
        candidate.period,
        name="Transit period",
    )
    duration = _finite_float(
        candidate.duration,
        name="Transit duration",
    )
    _finite_float(
        candidate.transit_time,
        name="Transit midpoint",
    )
    depth = _finite_float(
        candidate.depth,
        name="Transit depth",
    )

    if period <= 0.0:
        raise LightCurveTransitDiagnosticError("Transit period must be greater than zero.")

    if duration <= 0.0:
        raise LightCurveTransitDiagnosticError("Transit duration must be greater than zero.")

    if duration >= period:
        raise LightCurveTransitDiagnosticError("Transit duration must be shorter than the period.")

    if depth <= 0.0:
        raise LightCurveTransitDiagnosticError("Transit depth must be greater than zero.")


def transit_phase_time(
    time: float,
    candidate: TransitSearchCandidate,
) -> float:
    """Return signed time from the nearest predicted transit midpoint."""

    resolved_time = _finite_float(
        time,
        name="Observation time",
    )
    period = _finite_float(
        candidate.period,
        name="Transit period",
    )
    transit_time = _finite_float(
        candidate.transit_time,
        name="Transit midpoint",
    )

    if period <= 0.0:
        raise LightCurveTransitDiagnosticError("Transit period must be greater than zero.")

    return ((resolved_time - transit_time + 0.5 * period) % period) - 0.5 * period


def build_transit_mask(
    light_curve: LightCurve,
    candidate: TransitSearchCandidate,
) -> tuple[bool, ...]:
    """Mark observations strictly inside predicted transit windows."""

    _validate_candidate(
        light_curve,
        candidate,
    )

    half_duration = candidate.duration / 2.0

    boundary_tolerance = 1.0e-12 * max(
        1.0,
        abs(candidate.period),
        abs(candidate.duration),
    )

    interior_limit = max(
        0.0,
        half_duration - boundary_tolerance,
    )

    return tuple(
        abs(
            transit_phase_time(
                point.time,
                candidate,
            )
        )
        < interior_limit
        for point in light_curve.points
    )


def calculate_transit_windows(
    light_curve: LightCurve,
    candidate: TransitSearchCandidate,
) -> tuple[TransitWindow, ...]:
    """Calculate predicted transit windows overlapping the observations."""

    _validate_candidate(
        light_curve,
        candidate,
    )

    observation_start = light_curve.points[0].time
    observation_end = light_curve.points[-1].time
    half_duration = candidate.duration / 2.0

    first_cycle = ceil(
        (observation_start - candidate.transit_time - half_duration) / candidate.period
    )

    last_cycle = floor(
        (observation_end - candidate.transit_time + half_duration) / candidate.period
    )

    windows: list[TransitWindow] = []

    for cycle in range(
        first_cycle,
        last_cycle + 1,
    ):
        midpoint = candidate.transit_time + cycle * candidate.period
        ingress = midpoint - half_duration
        egress = midpoint + half_duration

        if egress < observation_start or ingress > observation_end:
            continue

        windows.append(
            TransitWindow(
                cycle=cycle,
                midpoint=midpoint,
                ingress=ingress,
                egress=egress,
            )
        )

    return tuple(windows)


def _resolve_baseline_flux(
    light_curve: LightCurve,
    mask: tuple[bool, ...],
    baseline_flux: float | None,
) -> float:
    """Resolve an explicit or measured out-of-transit baseline."""

    if baseline_flux is not None:
        return _finite_float(
            baseline_flux,
            name="Baseline flux",
        )

    out_of_transit_values = tuple(
        point.value
        for point, in_transit in zip(
            light_curve.points,
            mask,
            strict=True,
        )
        if not in_transit
    )

    if not out_of_transit_values:
        raise LightCurveTransitDiagnosticError(
            "Baseline flux cannot be measured without out-of-transit observations."
        )

    return float(median(out_of_transit_values))


def generate_box_transit_model(
    light_curve: LightCurve,
    candidate: TransitSearchCandidate,
    *,
    baseline_flux: float | None = None,
) -> BoxTransitModel:
    """Generate a periodic box-shaped transit model."""

    mask = build_transit_mask(
        light_curve,
        candidate,
    )

    resolved_baseline = _resolve_baseline_flux(
        light_curve,
        mask,
        baseline_flux,
    )

    in_transit_flux = resolved_baseline - candidate.depth

    model_fluxes = tuple(
        (in_transit_flux if in_transit else resolved_baseline) for in_transit in mask
    )

    return BoxTransitModel(
        baseline_flux=resolved_baseline,
        in_transit_flux=in_transit_flux,
        mask=mask,
        fluxes=model_fluxes,
    )


def _rms(
    values: tuple[float, ...],
) -> float:
    """Calculate root-mean-square for a nonempty sequence."""

    if not values:
        raise LightCurveTransitDiagnosticError("RMS requires at least one value.")

    return sqrt(fmean(value * value for value in values))


def diagnose_transit_candidate(
    light_curve: LightCurve,
    candidate: TransitSearchCandidate,
    *,
    baseline_flux: float | None = None,
) -> TransitCandidateDiagnostics:
    """Calculate model residuals and depth diagnostics."""

    model = generate_box_transit_model(
        light_curve,
        candidate,
        baseline_flux=baseline_flux,
    )

    if not any(model.mask):
        raise LightCurveTransitDiagnosticError("No observations fall inside the predicted transit.")

    if all(model.mask):
        raise LightCurveTransitDiagnosticError(
            "No observations fall outside the predicted transit."
        )

    points: list[TransitDiagnosticPoint] = []

    for point, in_transit, model_flux in zip(
        light_curve.points,
        model.mask,
        model.fluxes,
        strict=True,
    ):
        phase_time = transit_phase_time(
            point.time,
            candidate,
        )
        phase = phase_time / candidate.period

        cycle = floor((point.time - candidate.transit_time) / candidate.period + 0.5)

        points.append(
            TransitDiagnosticPoint(
                time=point.time,
                phase=phase,
                phase_time=phase_time,
                cycle=cycle,
                in_transit=in_transit,
                observed_flux=point.value,
                model_flux=model_flux,
                residual=point.value - model_flux,
                uncertainty=point.uncertainty,
            )
        )

    diagnostic_points = tuple(points)

    in_transit_values = tuple(
        point.observed_flux for point in diagnostic_points if point.in_transit
    )
    out_of_transit_values = tuple(
        point.observed_flux for point in diagnostic_points if not point.in_transit
    )

    measured_depth = float(median(out_of_transit_values)) - float(median(in_transit_values))

    residuals = tuple(point.residual for point in diagnostic_points)
    in_transit_residuals = tuple(point.residual for point in diagnostic_points if point.in_transit)
    out_of_transit_residuals = tuple(
        point.residual for point in diagnostic_points if not point.in_transit
    )

    return TransitCandidateDiagnostics(
        candidate=candidate,
        model=model,
        windows=calculate_transit_windows(
            light_curve,
            candidate,
        ),
        points=diagnostic_points,
        measured_depth=measured_depth,
        depth_difference=(measured_depth - candidate.depth),
        residual_rms=_rms(residuals),
        in_transit_rms=_rms(in_transit_residuals),
        out_of_transit_rms=_rms(out_of_transit_residuals),
    )
