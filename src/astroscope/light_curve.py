"""Scientific data models for astronomical light curves."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Final, Literal

PhotometryKind = Literal["flux", "magnitude"]

_MINIMUM_OBSERVATION_COUNT: Final[int] = 3


class LightCurveError(ValueError):
    """Raised when light-curve data is invalid."""


@dataclass(frozen=True, slots=True)
class LightCurveMetadata:
    """Descriptive information for an astronomical light curve."""

    object_name: str
    photometry_kind: PhotometryKind
    time_standard: str = "BJD_TDB"
    filter_name: str | None = None
    observatory_name: str | None = None
    telescope_name: str | None = None

    def __post_init__(self) -> None:
        if not self.object_name.strip():
            raise LightCurveError("Object name must not be empty.")

        if self.photometry_kind not in {"flux", "magnitude"}:
            raise LightCurveError("Photometry kind must be 'flux' or 'magnitude'.")

        if not self.time_standard.strip():
            raise LightCurveError("Time standard must not be empty.")


@dataclass(frozen=True, slots=True)
class LightCurvePoint:
    """One astronomical photometry measurement."""

    time: float
    value: float
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.time):
            raise LightCurveError("Observation time must be finite.")

        if not isfinite(self.value):
            raise LightCurveError("Photometry value must be finite.")

        if self.uncertainty is not None:
            if not isfinite(self.uncertainty):
                raise LightCurveError("Measurement uncertainty must be finite.")

            if self.uncertainty <= 0.0:
                raise LightCurveError("Measurement uncertainty must be greater than zero.")


@dataclass(frozen=True, slots=True)
class LightCurve:
    """Validated and time-ordered astronomical photometry."""

    metadata: LightCurveMetadata
    points: tuple[LightCurvePoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) < _MINIMUM_OBSERVATION_COUNT:
            raise LightCurveError("A light curve requires at least three observations.")

        times = tuple(point.time for point in self.points)

        if times != tuple(sorted(times)):
            raise LightCurveError("Light-curve observations must be ordered by time.")

        if len(times) != len(set(times)):
            raise LightCurveError("Light-curve observation times must be unique.")

    @property
    def observation_count(self) -> int:
        """Return the number of measurements."""

        return len(self.points)

    @property
    def start_time(self) -> float:
        """Return the first observation time."""

        return self.points[0].time

    @property
    def end_time(self) -> float:
        """Return the final observation time."""

        return self.points[-1].time

    @property
    def duration(self) -> float:
        """Return the observation duration in time-axis units."""

        return self.end_time - self.start_time

    @property
    def has_uncertainties(self) -> bool:
        """Return whether every observation has an uncertainty."""

        return all(point.uncertainty is not None for point in self.points)


def build_light_curve(
    *,
    metadata: LightCurveMetadata,
    times: Sequence[float],
    values: Sequence[float],
    uncertainties: Sequence[float] | None = None,
) -> LightCurve:
    """Build a validated light curve from parallel sequences."""

    if len(times) != len(values):
        raise LightCurveError("Times and photometry values must have equal lengths.")

    if uncertainties is not None and len(uncertainties) != len(times):
        raise LightCurveError("Uncertainties must have the same length as the observations.")

    points = []

    for index, (time, value) in enumerate(zip(times, values, strict=True)):
        uncertainty = uncertainties[index] if uncertainties is not None else None

        points.append(
            LightCurvePoint(
                time=float(time),
                value=float(value),
                uncertainty=(float(uncertainty) if uncertainty is not None else None),
            )
        )

    ordered_points = tuple(
        sorted(
            points,
            key=lambda point: point.time,
        )
    )

    return LightCurve(
        metadata=metadata,
        points=ordered_points,
    )
