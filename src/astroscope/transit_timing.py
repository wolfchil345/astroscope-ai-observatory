"""Strict source-coordinate transit predictions; no observer-arrival resolver.

This boundary never interprets a coordinate prediction as a UTC instant. The
older transit_scheduler API remains explicitly unvalidated numeric arithmetic.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, localcontext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astroscope.transit_scheduler import TransitEphemeris


class TransitTimingError(ValueError):
    """A machine-readable timing-contract rejection."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TransitTimingError("missing_provenance", f"{label} must be nonempty text")


def _decimal(value: str, label: str) -> Decimal:
    if not isinstance(value, str) or len(value) > 80:
        raise TransitTimingError("invalid_decimal", f"{label} requires a decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise TransitTimingError("invalid_decimal", label) from error
    if (
        not result.is_finite()
        or len(result.as_tuple().digits) > 24
        or (result != 0 and not Decimal("1e-24") <= result.copy_abs() <= Decimal("1e9"))
        or abs(result.as_tuple().exponent) > 48
    ):
        raise TransitTimingError("decimal_domain", label)
    return result


def _cycle(value: int) -> None:
    if type(value) is not int or not -10_000 <= value <= 10_000:
        raise TransitTimingError("cycle_domain", "cycle must be an integer in [-10000, 10000]")


@dataclass(frozen=True, slots=True)
class TimeCoordinate:
    """Date representation, time scale and reference position, kept distinct."""

    representation: str
    scale: str
    reference_position: str
    original_label: str
    offset_jd: str | None = None

    def __post_init__(self) -> None:
        _text(self.original_label, "original time label")
        if self.representation not in ("jd", "mjd", "offset"):
            raise TransitTimingError("unsupported_representation", self.representation)
        if self.scale not in ("tdb", "tai", "utc", "tt", "unknown"):
            raise TransitTimingError("unsupported_scale", self.scale)
        if self.reference_position not in (
            "barycentric",
            "heliocentric",
            "observer",
            "geocentric",
            "unknown",
        ):
            raise TransitTimingError("unsupported_position", self.reference_position)
        if self.representation == "offset":
            _decimal(self.offset_jd, "explicit offset zero point")
        elif self.offset_jd is not None:
            raise TransitTimingError("unexpected_offset", "JD/MJD have fixed zero points")

    def julian_date(self, value: str) -> Decimal:
        """Normalize representation without changing scale or reference position."""
        with localcontext() as context:
            context.prec = 80
            offset = {"jd": Decimal(0), "mjd": Decimal("2400000.5")}.get(self.representation)
            if offset is None:
                offset = _decimal(self.offset_jd, "offset")
            return _decimal(value, "epoch") + offset


@dataclass(frozen=True, slots=True)
class EphemerisProvenance:
    """Attribution supplied by the caller; it is not independently authenticated."""

    source_id: str
    parameter_set_id: str
    epoch_reference: str
    period_reference: str
    version_or_retrieval: str
    joint_fit: bool
    validity_note: str = "unknown"

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "parameter_set_id",
            "epoch_reference",
            "period_reference",
            "version_or_retrieval",
            "validity_note",
        ):
            _text(getattr(self, name), name)
        if type(self.joint_fit) is not bool:
            raise TransitTimingError("invalid_joint_fit", "joint_fit must be boolean")


@dataclass(frozen=True, slots=True)
class UncertaintyComponent:
    """A source component, preserving unknown or unsupported error semantics."""

    value_days: str | None = None
    source: str = ""
    kind: str = "standard_deviation"
    original_description: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("standard_deviation", "asymmetric", "limit", "unknown_confidence"):
            raise TransitTimingError("unsupported_error_kind", self.kind)
        if not isinstance(self.source, str) or not isinstance(self.original_description, str):
            raise TransitTimingError("invalid_error_metadata", "error metadata must be text")
        if self.kind != "standard_deviation":
            _text(self.original_description, "original unsupported uncertainty description")
        if self.value_days is not None:
            if _decimal(self.value_days, "uncertainty") < 0:
                raise TransitTimingError(
                    "negative_uncertainty", "standard deviation is nonnegative"
                )
            _text(self.source, "uncertainty source or assumption")


@dataclass(frozen=True, slots=True)
class EphemerisUncertainty:
    epoch: UncertaintyComponent = UncertaintyComponent()
    period: UncertaintyComponent = UncertaintyComponent()
    covariance_days_squared: str | None = None
    covariance_source: str = ""
    zero_covariance_assumption: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.epoch, UncertaintyComponent) or not isinstance(
            self.period, UncertaintyComponent
        ):
            raise TransitTimingError("invalid_uncertainty", "typed components are required")
        if not isinstance(self.covariance_source, str):
            raise TransitTimingError("invalid_covariance_source", "source must be text")
        if self.zero_covariance_assumption is not None:
            _text(self.zero_covariance_assumption, "zero-covariance assumption")
            if self.covariance_days_squared is not None:
                raise TransitTimingError(
                    "conflicting_covariance", "supply covariance or assumption"
                )
        if self.covariance_days_squared is not None:
            covariance = _decimal(self.covariance_days_squared, "covariance")
            _text(self.covariance_source, "covariance source")
            if any(
                c.kind != "standard_deviation" or c.value_days is None
                for c in (self.epoch, self.period)
            ):
                raise TransitTimingError(
                    "covariance_without_marginals", "known standard errors required"
                )
            with localcontext() as context:
                context.prec = 80
                bound = _decimal(self.epoch.value_days, "epoch sigma") * _decimal(
                    self.period.value_days, "period sigma"
                )
                if abs(covariance) > bound:
                    raise TransitTimingError("invalid_covariance", "covariance matrix is not PSD")


@dataclass(frozen=True, slots=True)
class ObserverTimingContext:
    """Optional source context retained for a future validated arrival adapter."""

    site_name: str
    latitude_degrees: str
    longitude_degrees: str
    elevation_meters: str
    target_ra_icrs_degrees: str
    target_dec_icrs_degrees: str
    coordinate_reference_epoch: str
    motion_assumption: str
    geodetic_datum: str = "WGS84"

    def __post_init__(self) -> None:
        for name in ("site_name", "coordinate_reference_epoch", "motion_assumption"):
            _text(getattr(self, name), name)
        if self.geodetic_datum != "WGS84":
            raise TransitTimingError("unsupported_site_datum", "only WGS84 metadata is supported")
        for name, lower, upper in (
            ("latitude_degrees", -90, 90),
            ("longitude_degrees", -180, 180),
            ("target_ra_icrs_degrees", 0, 360),
            ("target_dec_icrs_degrees", -90, 90),
        ):
            value = _decimal(getattr(self, name), name)
            if not lower <= value <= upper or (name == "target_ra_icrs_degrees" and value == 360):
                raise TransitTimingError("invalid_observer_context", name)
        _decimal(self.elevation_meters, "elevation")


@dataclass(frozen=True, slots=True)
class StrictTransitEphemeris:
    planet_name: str
    epoch_value: str
    period_days: str
    duration_hours: str
    coordinate: TimeCoordinate
    provenance: EphemerisProvenance
    uncertainty: EphemerisUncertainty = EphemerisUncertainty()
    duration_basis: str = "ephemeris_coordinate"
    duration_uncertainty: UncertaintyComponent = UncertaintyComponent()
    valid_cycle_start: int | None = None
    valid_cycle_end: int | None = None
    observer_context: ObserverTimingContext | None = None

    def __post_init__(self) -> None:
        _text(self.planet_name, "planet name")
        if not isinstance(self.coordinate, TimeCoordinate) or not isinstance(
            self.provenance, EphemerisProvenance
        ):
            raise TransitTimingError("invalid_metadata", "typed coordinate and provenance required")
        if not isinstance(self.uncertainty, EphemerisUncertainty) or not isinstance(
            self.duration_uncertainty, UncertaintyComponent
        ):
            raise TransitTimingError("invalid_uncertainty", "typed uncertainty required")
        if self.observer_context is not None and not isinstance(
            self.observer_context, ObserverTimingContext
        ):
            raise TransitTimingError("invalid_observer_context", "typed context required")
        epoch = self.coordinate.julian_date(self.epoch_value)
        if not Decimal(2400000) <= epoch <= Decimal(2500000):
            raise TransitTimingError("epoch_domain", "normalized epoch outside bounded JD domain")
        period = _decimal(self.period_days, "period")
        if not Decimal("0.125") <= period <= Decimal("365.25"):
            raise TransitTimingError("period_domain", "period outside [0.125,365.25] days")
        duration = _decimal(self.duration_hours, "T14 duration")
        if not 0 < duration <= Decimal(24):
            raise TransitTimingError("duration_domain", "T14 must be in (0,24] hours")
        if self.duration_basis not in ("ephemeris_coordinate", "observer_elapsed"):
            raise TransitTimingError("unsupported_duration_basis", self.duration_basis)
        if (self.valid_cycle_start is None) != (self.valid_cycle_end is None):
            raise TransitTimingError("incomplete_validity", "both cycle limits are required")
        if self.valid_cycle_start is not None:
            _cycle(self.valid_cycle_start)
            _cycle(self.valid_cycle_end)
            if self.valid_cycle_end < self.valid_cycle_start:
                raise TransitTimingError("reversed_validity", "invalid cycle interval")


@dataclass(frozen=True, slots=True)
class UncertaintyEstimate:
    value_days: str | None
    reasons: tuple[str, ...]
    assumptions: tuple[str, ...]

    @property
    def status(self) -> str:
        return "unknown" if self.value_days is None else "known"


def propagate_uncertainty(ephemeris: StrictTransitEphemeris, cycle: int) -> UncertaintyEstimate:
    """Propagate symmetric input errors without substituting zero for missing data."""
    _cycle(cycle)
    if not isinstance(ephemeris, StrictTransitEphemeris):
        raise TransitTimingError("strict_metadata_required", "use a strict ephemeris")
    errors = ephemeris.uncertainty
    needed = (
        (("epoch", errors.epoch),)
        if cycle == 0
        else (("epoch", errors.epoch), ("period", errors.period))
    )
    reasons = tuple(
        f"{name}_{'unknown' if c.value_days is None else 'unsupported_error_kind'}"
        for name, c in needed
        if c.value_days is None or c.kind != "standard_deviation"
    )
    if cycle != 0 and not ephemeris.provenance.joint_fit:
        reasons += ("unrelated_parameter_sets",)
    if (
        cycle != 0
        and errors.covariance_days_squared is None
        and (errors.zero_covariance_assumption is None)
    ):
        reasons += ("covariance_unknown",)
    assumptions = (
        ()
        if cycle == 0 or errors.zero_covariance_assumption is None
        else (errors.zero_covariance_assumption,)
    )
    if reasons:
        return UncertaintyEstimate(None, reasons, assumptions)
    with localcontext() as context:
        context.prec = 80
        epoch_sigma = _decimal(errors.epoch.value_days, "epoch sigma")
        if cycle == 0:
            return UncertaintyEstimate(str(epoch_sigma), (), ())
        period_sigma = _decimal(errors.period.value_days, "period sigma")
        covariance = (
            Decimal(0)
            if errors.covariance_days_squared is None
            else _decimal(errors.covariance_days_squared, "covariance")
        )
        variance = epoch_sigma**2 + cycle**2 * period_sigma**2 + 2 * cycle * covariance
        if variance < 0:
            raise TransitTimingError("invalid_variance", "negative variance is not clamped")
        return UncertaintyEstimate(str(variance.sqrt()), (), assumptions)


@dataclass(frozen=True, slots=True)
class CoordinateTransitPrediction:
    """An unresolved prediction, deliberately without legacy *_jd properties."""

    ephemeris: StrictTransitEphemeris
    cycle: int
    midpoint_jd_decimal: str
    ingress_jd_decimal: str
    egress_jd_decimal: str
    timing_uncertainty: UncertaintyEstimate
    validity_status: str


def predict_coordinate_transit(
    ephemeris: StrictTransitEphemeris, cycle: int
) -> CoordinateTransitPrediction:
    """Predict nominal symmetric contacts in one explicitly declared coordinate."""
    _cycle(cycle)
    if not isinstance(ephemeris, StrictTransitEphemeris):
        raise TransitTimingError("strict_metadata_required", "use a strict ephemeris")
    coordinate = ephemeris.coordinate
    supported = {
        ("barycentric", "tdb"): "ephemeris_coordinate",
        ("observer", "tai"): "observer_elapsed",
    }
    basis = supported.get((coordinate.reference_position, coordinate.scale))
    if basis is None:
        raise TransitTimingError("unsupported_time_coordinate", "no interpretation is inferred")
    if ephemeris.duration_basis != basis:
        raise TransitTimingError(
            "duration_basis_mismatch", "duration must match the arithmetic basis"
        )
    if ephemeris.valid_cycle_start is None:
        validity = "unknown"
    elif ephemeris.valid_cycle_start <= cycle <= ephemeris.valid_cycle_end:
        validity = "within_supplied_cycle_interval"
    else:
        raise TransitTimingError(
            "outside_model_validity", "cycle outside supplied validity interval"
        )
    with localcontext() as context:
        context.prec = 80
        midpoint = coordinate.julian_date(ephemeris.epoch_value) + cycle * _decimal(
            ephemeris.period_days, "period"
        )
        half_duration = _decimal(ephemeris.duration_hours, "duration") / Decimal(48)
        return CoordinateTransitPrediction(
            ephemeris,
            cycle,
            str(midpoint),
            str(midpoint - half_duration),
            str(midpoint + half_duration),
            propagate_uncertainty(ephemeris, cycle),
            validity,
        )


def require_observing_eligibility(prediction: CoordinateTransitPrediction) -> None:
    """Fail closed until an independently validated observer adapter exists."""
    if not isinstance(prediction, CoordinateTransitPrediction):
        raise TransitTimingError("strict_prediction_required", "legacy data cannot be promoted")
    raise TransitTimingError(
        "arrival_resolution_unavailable",
        "coordinate predictions cannot enter observing, ranking or UTC export workflows",
    )


def require_quantified_padding(prediction: CoordinateTransitPrediction, multiplier: str) -> None:
    """Check uncertainty eligibility without creating or resolving an observing window."""
    if not isinstance(prediction, CoordinateTransitPrediction):
        raise TransitTimingError("strict_prediction_required", "use a strict coordinate prediction")
    k = _decimal(multiplier, "sigma multiplier")
    if k < 0:
        raise TransitTimingError("negative_padding", "sigma multiplier must be nonnegative")
    if k != 0 and prediction.timing_uncertainty.value_days is None:
        raise TransitTimingError("unknown_timing_uncertainty", "sigma-based padding is not defined")


def reject_unresolved_timing(value: object) -> None:
    """Prevent strict records from being duck-typed into legacy numeric consumers."""
    if isinstance(
        value,
        (
            StrictTransitEphemeris,
            CoordinateTransitPrediction,
            TimeCoordinate,
            UncertaintyEstimate,
            UncertaintyComponent,
            EphemerisUncertainty,
        ),
    ):
        raise TransitTimingError("unresolved_timing_input", "use the source-coordinate preview")


def coordinate_prediction_to_json(prediction: CoordinateTransitPrediction) -> str:
    """Serialize provenance and unknown states without emitting UTC fields."""
    if not isinstance(prediction, CoordinateTransitPrediction):
        raise TransitTimingError("strict_prediction_required", "legacy data cannot be promoted")
    return (
        json.dumps(
            {
                "schema_version": 2,
                "record_kind": "unresolved_coordinate_prediction",
                "observing_eligible": False,
                "eligibility_reason": "arrival_resolution_unavailable",
                "coordinate_output_representation": "jd",
                "contact_model": "symmetric_constant_T14",
                "timing_uncertainty_status": prediction.timing_uncertainty.status,
                "prediction": asdict(prediction),
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def legacy_arithmetic_ephemeris(
    *, acknowledge_unvalidated: bool, **values: object
) -> TransitEphemeris:
    """Explicitly construct the old numeric model; never adapt a strict record."""
    if acknowledge_unvalidated is not True:
        raise TransitTimingError("legacy_acknowledgement_required", "legacy timing is unvalidated")
    from astroscope.transit_scheduler import TransitEphemeris

    for value in values.values():
        reject_unresolved_timing(value)
    return TransitEphemeris(**values)


def require_legacy_schedule_result(result: object) -> None:
    """Reject unresolved records even when nested in a legacy result container."""
    reject_unresolved_timing(result)
    for ranked in result.ranked_transits:
        reject_unresolved_timing(ranked.candidate.event)
