"""Observer-location and astronomical-time calculations."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from typing import Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time


@dataclass(frozen=True, slots=True)
class ObserverPreset:
    """A predefined observing location."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float
    timezone_name: str


@dataclass(frozen=True, slots=True)
class AstronomicalTimeResult:
    """Calculated astronomical time values."""

    local_datetime_iso: str
    utc_datetime_iso: str
    julian_date: float
    modified_julian_date: float
    local_sidereal_time_hours: float
    local_sidereal_time_hms: str


class CivilTimeStatus(StrEnum):
    """Classification of one named-zone civil time."""

    NORMAL = "normal"
    AMBIGUOUS = "ambiguous"
    NONEXISTENT = "nonexistent"


@dataclass(frozen=True, slots=True)
class CivilTimeCandidate:
    """One PEP 495 fold candidate and its round-trip evidence."""

    fold: Literal[0, 1]
    utc_datetime: datetime
    utc_offset: timedelta
    roundtrip_local_datetime: datetime
    roundtrip_fold: int
    roundtrip_matches: bool


@dataclass(frozen=True, slots=True)
class CivilTimeClassification:
    """Strict classification evidence for one local civil time."""

    timezone_name: str
    naive_local_datetime: datetime
    status: CivilTimeStatus
    candidates: tuple[CivilTimeCandidate, CivilTimeCandidate]
    previous_valid_local: datetime | None
    next_valid_local: datetime | None


class CivilTimeResolutionError(ValueError):
    """Base error for civil times that cannot be resolved safely."""

    def __init__(
        self,
        message: str,
        *,
        classification: CivilTimeClassification | None,
        requested_fold: int | None,
    ) -> None:
        super().__init__(message)
        self.classification = classification
        self.requested_fold = requested_fold


class AmbiguousCivilTimeError(CivilTimeResolutionError):
    """Raised when an ambiguous civil time lacks an explicit fold."""


class NonexistentCivilTimeError(CivilTimeResolutionError):
    """Raised when a civil time lies inside a skipped clock interval."""


OBSERVER_PRESETS: Final[dict[str, ObserverPreset]] = {
    "osaka": ObserverPreset(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
    ),
    "bangkok": ObserverPreset(
        latitude_deg=13.7563,
        longitude_deg=100.5018,
        elevation_m=2.0,
        timezone_name="Asia/Bangkok",
    ),
    "seoul": ObserverPreset(
        latitude_deg=37.5665,
        longitude_deg=126.9780,
        elevation_m=38.0,
        timezone_name="Asia/Seoul",
    ),
    "greenwich": ObserverPreset(
        latitude_deg=51.4769,
        longitude_deg=0.0005,
        elevation_m=46.0,
        timezone_name="UTC",
    ),
}


def validate_observer_coordinates(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
) -> None:
    """Validate geodetic observer coordinates."""

    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")

    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    if not -500.0 <= elevation_m <= 10_000.0:
        raise ValueError("Elevation must be between -500 and 10000 metres.")


def create_earth_location(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
) -> EarthLocation:
    """Create an Astropy EarthLocation from geodetic coordinates."""

    validate_observer_coordinates(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
    )

    return EarthLocation.from_geodetic(
        lon=longitude_deg * u.deg,
        lat=latitude_deg * u.deg,
        height=elevation_m * u.m,
    )


def get_timezone(timezone_name: str) -> ZoneInfo:
    """Return a validated time-zone object."""

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Unknown time zone: {timezone_name}") from error


def local_datetime_to_utc(
    local_date: date,
    local_time: time,
    timezone_name: str,
) -> datetime:
    """Convert a local date and time into UTC."""

    timezone_info = get_timezone(timezone_name)
    naive_time = local_time.replace(tzinfo=None)

    local_datetime = datetime.combine(
        local_date,
        naive_time,
        tzinfo=timezone_info,
    )

    return local_datetime.astimezone(UTC)


def _civil_time_candidate(
    naive_local_datetime: datetime,
    timezone_info: ZoneInfo,
    fold: Literal[0, 1],
) -> CivilTimeCandidate:
    """Build one fold candidate with UTC round-trip evidence."""

    aware_local_datetime = naive_local_datetime.replace(
        tzinfo=timezone_info,
        fold=fold,
    )
    utc_datetime = aware_local_datetime.astimezone(UTC)
    roundtrip_local_datetime = utc_datetime.astimezone(timezone_info)
    utc_offset = aware_local_datetime.utcoffset()

    if utc_offset is None:
        raise CivilTimeResolutionError(
            f"No UTC offset is available for {timezone_info.key}.",
            classification=None,
            requested_fold=None,
        )

    return CivilTimeCandidate(
        fold=fold,
        utc_datetime=utc_datetime,
        utc_offset=utc_offset,
        roundtrip_local_datetime=roundtrip_local_datetime,
        roundtrip_fold=roundtrip_local_datetime.fold,
        roundtrip_matches=(
            roundtrip_local_datetime.replace(tzinfo=None) == naive_local_datetime
        ),
    )


def _utc_offset_at(
    utc_datetime: datetime,
    timezone_info: ZoneInfo,
) -> timedelta:
    """Return the named-zone offset in effect at one UTC instant."""

    utc_offset = utc_datetime.astimezone(timezone_info).utcoffset()
    if utc_offset is None:
        raise CivilTimeResolutionError(
            f"No UTC offset is available for {timezone_info.key}.",
            classification=None,
            requested_fold=None,
        )
    return utc_offset


def _find_gap_boundaries(
    naive_local_datetime: datetime,
    timezone_info: ZoneInfo,
    candidates: tuple[CivilTimeCandidate, CivilTimeCandidate],
) -> tuple[datetime, datetime]:
    """Find the exact local boundaries surrounding one nonexistent time."""

    if candidates[0].utc_offset == candidates[1].utc_offset:
        raise CivilTimeResolutionError(
            "Nonexistent civil-time candidates must have different UTC offsets.",
            classification=None,
            requested_fold=None,
        )

    lower_utc, upper_utc = sorted(candidate.utc_datetime for candidate in candidates)
    lower_offset = _utc_offset_at(lower_utc, timezone_info)
    upper_offset = _utc_offset_at(upper_utc, timezone_info)

    if lower_offset == upper_offset:
        raise CivilTimeResolutionError(
            "A unique UTC offset transition could not be bracketed.",
            classification=None,
            requested_fold=None,
        )

    one_microsecond = timedelta(microseconds=1)
    transition_lower = lower_utc
    transition_upper = upper_utc

    while transition_upper - transition_lower > one_microsecond:
        midpoint = transition_lower + (transition_upper - transition_lower) // 2
        midpoint_offset = _utc_offset_at(midpoint, timezone_info)

        if midpoint_offset == lower_offset:
            transition_lower = midpoint
        elif midpoint_offset == upper_offset:
            transition_upper = midpoint
        else:
            raise CivilTimeResolutionError(
                "More than one UTC offset transition was found between candidates.",
                classification=None,
                requested_fold=None,
            )

    if transition_upper - transition_lower != one_microsecond:
        raise CivilTimeResolutionError(
            "The UTC offset transition could not be located at microsecond precision.",
            classification=None,
            requested_fold=None,
        )

    previous_valid_local = transition_lower.astimezone(timezone_info)
    next_valid_local = transition_upper.astimezone(timezone_info)
    previous_offset = previous_valid_local.utcoffset()
    next_offset = next_valid_local.utcoffset()

    if (
        previous_offset is None
        or next_offset is None
        or previous_offset != lower_offset
        or next_offset != upper_offset
        or next_offset <= previous_offset
    ):
        raise CivilTimeResolutionError(
            "The bracketed transition does not describe a forward civil-time gap.",
            classification=None,
            requested_fold=None,
        )

    previous_naive = previous_valid_local.replace(tzinfo=None)
    next_naive = next_valid_local.replace(tzinfo=None)

    if not previous_naive < naive_local_datetime < next_naive:
        raise CivilTimeResolutionError(
            "The located transition does not bracket the nonexistent civil time.",
            classification=None,
            requested_fold=None,
        )

    missing_duration = next_naive - previous_naive - one_microsecond
    if missing_duration != next_offset - previous_offset:
        raise CivilTimeResolutionError(
            "The located civil-time gap does not match the UTC offset transition.",
            classification=None,
            requested_fold=None,
        )

    if (
        previous_valid_local.astimezone(UTC) != transition_lower
        or next_valid_local.astimezone(UTC) != transition_upper
    ):
        raise CivilTimeResolutionError(
            "The located gap boundaries failed UTC round-trip validation.",
            classification=None,
            requested_fold=None,
        )

    return previous_valid_local, next_valid_local


def classify_local_datetime(
    local_date: date,
    local_time: time,
    timezone_name: str,
) -> CivilTimeClassification:
    """Classify one local civil time through both PEP 495 folds."""

    timezone_info = get_timezone(timezone_name)
    naive_time = local_time.replace(tzinfo=None, fold=0)
    naive_local_datetime = datetime.combine(local_date, naive_time)
    candidates = (
        _civil_time_candidate(naive_local_datetime, timezone_info, 0),
        _civil_time_candidate(naive_local_datetime, timezone_info, 1),
    )
    real_utc_instants = {
        candidate.utc_datetime
        for candidate in candidates
        if candidate.roundtrip_matches
    }

    if len(real_utc_instants) == 1:
        status = CivilTimeStatus.NORMAL
        previous_valid_local = None
        next_valid_local = None
    elif len(real_utc_instants) == 2 and all(
        candidate.roundtrip_matches for candidate in candidates
    ):
        status = CivilTimeStatus.AMBIGUOUS
        previous_valid_local = None
        next_valid_local = None
    elif not real_utc_instants and not any(
        candidate.roundtrip_matches for candidate in candidates
    ):
        status = CivilTimeStatus.NONEXISTENT
        previous_valid_local, next_valid_local = _find_gap_boundaries(
            naive_local_datetime,
            timezone_info,
            candidates,
        )
    else:
        raise CivilTimeResolutionError(
            "Unexpected civil-time candidate structure.",
            classification=None,
            requested_fold=None,
        )

    return CivilTimeClassification(
        timezone_name=timezone_name,
        naive_local_datetime=naive_local_datetime,
        status=status,
        candidates=candidates,
        previous_valid_local=previous_valid_local,
        next_valid_local=next_valid_local,
    )


def resolve_local_datetime(
    local_date: date,
    local_time: time,
    timezone_name: str,
    *,
    fold: int | None = None,
) -> datetime:
    """Resolve one classified local civil time to UTC without silent policy."""

    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError("fold must be None, 0, or 1.")

    classification = classify_local_datetime(
        local_date=local_date,
        local_time=local_time,
        timezone_name=timezone_name,
    )

    if classification.status is CivilTimeStatus.NORMAL:
        return next(
            candidate.utc_datetime
            for candidate in classification.candidates
            if candidate.roundtrip_matches
        )

    if classification.status is CivilTimeStatus.AMBIGUOUS:
        if fold is None:
            raise AmbiguousCivilTimeError(
                "Ambiguous civil time requires an explicit fold of 0 or 1.",
                classification=classification,
                requested_fold=fold,
            )
        return classification.candidates[fold].utc_datetime

    if classification.status is CivilTimeStatus.NONEXISTENT:
        raise NonexistentCivilTimeError(
            "Nonexistent civil time cannot be resolved to UTC.",
            classification=classification,
            requested_fold=fold,
        )

    raise CivilTimeResolutionError(
        "Unexpected civil-time classification status.",
        classification=classification,
        requested_fold=fold,
    )


def decimal_hours_to_hms(hours: float) -> str:
    """Convert decimal hours into HH:MM:SS format."""

    wrapped_hours = hours % 24.0
    total_seconds = int(round(wrapped_hours * 3600.0)) % 86_400

    hour_value, remaining_seconds = divmod(total_seconds, 3600)
    minute_value, second_value = divmod(remaining_seconds, 60)

    return f"{hour_value:02d}:{minute_value:02d}:{second_value:02d}"


def calculate_astronomical_time(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    *,
    fold: int | None = None,
) -> AstronomicalTimeResult:
    """Calculate UTC, Julian dates, and local sidereal time."""

    location = create_earth_location(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        elevation_m=elevation_m,
    )

    timezone_info = get_timezone(timezone_name)

    utc_datetime = resolve_local_datetime(
        local_date=local_date,
        local_time=local_time,
        timezone_name=timezone_name,
        fold=fold,
    )

    local_datetime = utc_datetime.astimezone(timezone_info)

    astronomical_time = Time(
        utc_datetime,
        scale="utc",
        location=location,
    )

    sidereal_time = astronomical_time.sidereal_time("apparent")
    sidereal_hours = float(sidereal_time.hour)

    return AstronomicalTimeResult(
        local_datetime_iso=local_datetime.isoformat(timespec="seconds"),
        utc_datetime_iso=utc_datetime.isoformat(timespec="seconds"),
        julian_date=float(astronomical_time.jd),
        modified_julian_date=float(astronomical_time.mjd),
        local_sidereal_time_hours=sidereal_hours,
        local_sidereal_time_hms=decimal_hours_to_hms(sidereal_hours),
    )
