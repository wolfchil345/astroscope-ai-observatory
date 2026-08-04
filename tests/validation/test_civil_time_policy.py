"""Tests for strict observer-instant civil-time classification and resolution."""

from __future__ import annotations

import zoneinfo
from collections.abc import Generator
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, reset_tzpath

import pytest

from astroscope.observer import (
    AmbiguousCivilTimeError,
    CivilTimeStatus,
    NonexistentCivilTimeError,
    calculate_astronomical_time,
    classify_local_datetime,
    local_datetime_to_utc,
    resolve_local_datetime,
)


@pytest.fixture(autouse=True)
def pinned_python_tzdata(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Use the same pinned timezone source as the Mission 25 benchmark."""

    original_tzpath = zoneinfo.TZPATH
    monkeypatch.setenv("PYTHONTZPATH", "")
    reset_tzpath()
    ZoneInfo.clear_cache()
    try:
        yield
    finally:
        reset_tzpath(original_tzpath)
        ZoneInfo.clear_cache()


def test_normal_classification_deduplicates_one_real_utc_instant() -> None:
    classification = classify_local_datetime(
        local_date=date(2024, 1, 1),
        local_time=time(12, 0),
        timezone_name="Asia/Tokyo",
    )

    assert classification.status is CivilTimeStatus.NORMAL
    assert classification.naive_local_datetime == datetime(2024, 1, 1, 12, 0)
    assert [candidate.fold for candidate in classification.candidates] == [0, 1]
    assert all(candidate.roundtrip_matches for candidate in classification.candidates)
    assert len({candidate.utc_datetime for candidate in classification.candidates}) == 1
    assert classification.previous_valid_local is None
    assert classification.next_valid_local is None


@pytest.mark.parametrize("fold", [0, 1])
def test_normal_resolution_accepts_either_explicit_fold(fold: int) -> None:
    resolved = resolve_local_datetime(
        local_date=date(2024, 1, 1),
        local_time=time(12, 0),
        timezone_name="Asia/Tokyo",
        fold=fold,
    )

    assert resolved == datetime(2024, 1, 1, 3, 0, tzinfo=UTC)


def test_new_york_ambiguous_classification_records_both_candidates() -> None:
    classification = classify_local_datetime(
        local_date=date(2024, 11, 3),
        local_time=time(1, 30),
        timezone_name="America/New_York",
    )

    assert classification.status is CivilTimeStatus.AMBIGUOUS
    assert [candidate.fold for candidate in classification.candidates] == [0, 1]
    assert [candidate.utc_datetime for candidate in classification.candidates] == [
        datetime(2024, 11, 3, 5, 30, tzinfo=UTC),
        datetime(2024, 11, 3, 6, 30, tzinfo=UTC),
    ]
    offsets = [
        int(candidate.utc_offset.total_seconds())
        for candidate in classification.candidates
    ]
    assert offsets == [
        -14_400,
        -18_000,
    ]
    assert all(candidate.roundtrip_matches for candidate in classification.candidates)
    assert [candidate.roundtrip_fold for candidate in classification.candidates] == [0, 1]


@pytest.mark.parametrize(
    ("fold", "expected_utc"),
    [
        (0, datetime(2024, 11, 3, 5, 30, tzinfo=UTC)),
        (1, datetime(2024, 11, 3, 6, 30, tzinfo=UTC)),
    ],
)
def test_new_york_ambiguous_time_requires_the_requested_fold(
    fold: int,
    expected_utc: datetime,
) -> None:
    resolved = resolve_local_datetime(
        local_date=date(2024, 11, 3),
        local_time=time(1, 30),
        timezone_name="America/New_York",
        fold=fold,
    )

    assert resolved == expected_utc


def test_stored_time_fold_does_not_resolve_ambiguity_without_explicit_policy() -> None:
    with pytest.raises(AmbiguousCivilTimeError) as captured:
        resolve_local_datetime(
            local_date=date(2024, 11, 3),
            local_time=time(1, 30, fold=1),
            timezone_name="America/New_York",
        )

    assert captured.value.requested_fold is None
    assert captured.value.classification is not None
    assert captured.value.classification.status is CivilTimeStatus.AMBIGUOUS


@pytest.mark.parametrize(
    ("timezone_name", "local_date", "local_time", "previous_iso", "next_iso"),
    [
        (
            "America/New_York",
            date(2024, 3, 10),
            time(2, 30),
            "2024-03-10T01:59:59.999999-05:00",
            "2024-03-10T03:00:00.000000-04:00",
        ),
        (
            "Australia/Lord_Howe",
            date(2024, 10, 6),
            time(2, 15),
            "2024-10-06T01:59:59.999999+10:30",
            "2024-10-06T02:30:00.000000+11:00",
        ),
    ],
)
def test_nonexistent_classification_finds_exact_gap_boundaries(
    timezone_name: str,
    local_date: date,
    local_time: time,
    previous_iso: str,
    next_iso: str,
) -> None:
    classification = classify_local_datetime(
        local_date=local_date,
        local_time=local_time,
        timezone_name=timezone_name,
    )

    assert classification.status is CivilTimeStatus.NONEXISTENT
    assert [candidate.fold for candidate in classification.candidates] == [0, 1]
    assert all(not candidate.roundtrip_matches for candidate in classification.candidates)
    assert classification.previous_valid_local is not None
    assert classification.next_valid_local is not None
    assert classification.previous_valid_local.isoformat(timespec="microseconds") == previous_iso
    assert classification.next_valid_local.isoformat(timespec="microseconds") == next_iso


@pytest.mark.parametrize("fold", [None, 0, 1])
def test_nonexistent_time_is_rejected_for_every_fold(fold: int | None) -> None:
    with pytest.raises(NonexistentCivilTimeError) as captured:
        resolve_local_datetime(
            local_date=date(2024, 3, 10),
            local_time=time(2, 30),
            timezone_name="America/New_York",
            fold=fold,
        )

    assert captured.value.requested_fold == fold
    assert captured.value.classification is not None
    assert captured.value.classification.status is CivilTimeStatus.NONEXISTENT


def test_seconds_and_microseconds_are_preserved() -> None:
    resolved = resolve_local_datetime(
        local_date=date(2024, 1, 1),
        local_time=time(12, 34, 56, 123456),
        timezone_name="Asia/Tokyo",
    )

    assert resolved == datetime(2024, 1, 1, 3, 34, 56, 123456, tzinfo=UTC)


def test_invalid_fold_values_and_bool_are_rejected() -> None:
    invalid_folds = (True, False, -1, 2, 1.0, "0", object())

    for invalid_fold in invalid_folds:
        with pytest.raises(ValueError, match="fold must be None, 0, or 1"):
            resolve_local_datetime(
                local_date=date(2024, 1, 1),
                local_time=time(12, 0),
                timezone_name="Asia/Tokyo",
                fold=invalid_fold,  # type: ignore[arg-type]
            )


def test_invalid_timezone_preserves_the_legacy_error_exactly() -> None:
    expected_message = "Unknown time zone: Planet/Mars"

    with pytest.raises(ValueError, match="^Unknown time zone: Planet/Mars$"):
        resolve_local_datetime(
            local_date=date(2024, 1, 1),
            local_time=time(12, 0),
            timezone_name="Planet/Mars",
        )

    with pytest.raises(ValueError) as captured:
        local_datetime_to_utc(
            local_date=date(2024, 1, 1),
            local_time=time(12, 0),
            timezone_name="Planet/Mars",
        )
    assert str(captured.value) == expected_message


def test_calculate_astronomical_time_normal_regression() -> None:
    result = calculate_astronomical_time(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
    )

    assert result.local_datetime_iso == "2024-01-01T21:00:00+09:00"
    assert result.utc_datetime_iso == "2024-01-01T12:00:00+00:00"
    assert result.modified_julian_date == pytest.approx(result.julian_date - 2_400_000.5)


@pytest.mark.parametrize(
    ("fold", "expected_utc_iso"),
    [
        (0, "2024-11-03T05:30:00+00:00"),
        (1, "2024-11-03T06:30:00+00:00"),
    ],
)
def test_calculate_astronomical_time_uses_explicit_fold(
    fold: int,
    expected_utc_iso: str,
) -> None:
    result = calculate_astronomical_time(
        latitude_deg=40.7128,
        longitude_deg=-74.0060,
        elevation_m=10.0,
        timezone_name="America/New_York",
        local_date=date(2024, 11, 3),
        local_time=time(1, 30, fold=1 - fold),
        fold=fold,
    )

    assert result.utc_datetime_iso == expected_utc_iso
    assert result.local_datetime_iso.endswith("-04:00" if fold == 0 else "-05:00")
