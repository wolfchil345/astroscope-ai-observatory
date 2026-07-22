"""Tests for the exoplanet transit prediction engine."""

import math

import pytest

from astroscope.transit_scheduler import (
    TransitEphemeris,
    TransitSchedulerError,
    build_transit_event,
    calculate_mid_transit_jd,
    calculate_timing_uncertainty_days,
    calculate_transit_number_on_or_after,
    calculate_transit_number_on_or_before,
    predict_transits,
)


@pytest.fixture
def ephemeris() -> TransitEphemeris:
    """Return a reusable example ephemeris."""

    return TransitEphemeris(
        planet_name="Test Planet b",
        orbital_period_days=2.0,
        reference_mid_transit_jd=2_450_000.0,
        transit_duration_hours=3.0,
        period_uncertainty_days=0.0001,
        reference_epoch_uncertainty_days=0.001,
    )


def test_ephemeris_accepts_valid_values() -> None:
    ephemeris = TransitEphemeris(
        planet_name="Example b",
        orbital_period_days=4.5,
        reference_mid_transit_jd=2_460_000.25,
        transit_duration_hours=2.5,
    )

    assert ephemeris.planet_name == "Example b"
    assert ephemeris.orbital_period_days == 4.5


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("orbital_period_days", 0.0),
        ("orbital_period_days", -1.0),
        ("transit_duration_hours", 0.0),
        ("transit_duration_hours", -2.0),
        ("period_uncertainty_days", -0.1),
        ("reference_epoch_uncertainty_days", -0.1),
    ],
)
def test_ephemeris_rejects_invalid_values(
    field_name: str,
    field_value: float,
) -> None:
    values: dict[str, object] = {
        "planet_name": "Example b",
        "orbital_period_days": 3.0,
        "reference_mid_transit_jd": 2_460_000.0,
        "transit_duration_hours": 2.0,
        "period_uncertainty_days": None,
        "reference_epoch_uncertainty_days": None,
    }
    values[field_name] = field_value

    with pytest.raises(TransitSchedulerError):
        TransitEphemeris(**values)  # type: ignore[arg-type]


def test_ephemeris_rejects_empty_planet_name() -> None:
    with pytest.raises(
        TransitSchedulerError,
        match="Planet name",
    ):
        TransitEphemeris(
            planet_name="   ",
            orbital_period_days=3.0,
            reference_mid_transit_jd=2_460_000.0,
            transit_duration_hours=2.0,
        )


def test_calculate_mid_transit_jd(
    ephemeris: TransitEphemeris,
) -> None:
    result = calculate_mid_transit_jd(
        ephemeris,
        5,
    )

    assert result == pytest.approx(2_450_010.0)


def test_calculate_negative_transit_number(
    ephemeris: TransitEphemeris,
) -> None:
    result = calculate_mid_transit_jd(
        ephemeris,
        -3,
    )

    assert result == pytest.approx(2_449_994.0)


def test_transit_number_on_exact_epoch(
    ephemeris: TransitEphemeris,
) -> None:
    assert (
        calculate_transit_number_on_or_after(
            ephemeris,
            2_450_000.0,
        )
        == 0
    )
    assert (
        calculate_transit_number_on_or_before(
            ephemeris,
            2_450_000.0,
        )
        == 0
    )


def test_transit_numbers_around_epoch(
    ephemeris: TransitEphemeris,
) -> None:
    assert (
        calculate_transit_number_on_or_after(
            ephemeris,
            2_450_000.1,
        )
        == 1
    )
    assert (
        calculate_transit_number_on_or_before(
            ephemeris,
            2_450_000.1,
        )
        == 0
    )


def test_timing_uncertainty_propagation(
    ephemeris: TransitEphemeris,
) -> None:
    uncertainty = calculate_timing_uncertainty_days(
        ephemeris,
        5,
    )

    expected = math.sqrt(0.001**2 + (5 * 0.0001) ** 2)

    assert uncertainty == pytest.approx(expected)


def test_missing_uncertainties_produce_zero() -> None:
    ephemeris = TransitEphemeris(
        planet_name="Certain b",
        orbital_period_days=5.0,
        reference_mid_transit_jd=2_460_000.0,
        transit_duration_hours=2.0,
    )

    assert (
        calculate_timing_uncertainty_days(
            ephemeris,
            100,
        )
        == 0.0
    )


def test_build_transit_event_contacts(
    ephemeris: TransitEphemeris,
) -> None:
    event = build_transit_event(
        ephemeris,
        0,
        baseline_before_hours=0.0,
        baseline_after_hours=0.0,
        uncertainty_sigma_multiplier=0.0,
    )

    assert event.mid_transit_jd == pytest.approx(2_450_000.0)
    assert event.ingress_jd == pytest.approx(2_450_000.0 - 1.5 / 24.0)
    assert event.egress_jd == pytest.approx(2_450_000.0 + 1.5 / 24.0)


def test_build_transit_event_adds_baseline(
    ephemeris: TransitEphemeris,
) -> None:
    event = build_transit_event(
        ephemeris,
        0,
        baseline_before_hours=1.0,
        baseline_after_hours=2.0,
        uncertainty_sigma_multiplier=0.0,
    )

    assert event.observation_start_jd == pytest.approx(event.ingress_jd - 1.0 / 24.0)
    assert event.observation_end_jd == pytest.approx(event.egress_jd + 2.0 / 24.0)
    assert event.observation_window_hours == pytest.approx(6.0)


def test_build_transit_event_adds_uncertainty_margin(
    ephemeris: TransitEphemeris,
) -> None:
    event = build_transit_event(
        ephemeris,
        5,
        baseline_before_hours=0.0,
        baseline_after_hours=0.0,
        uncertainty_sigma_multiplier=2.0,
    )

    expected_uncertainty = math.sqrt(0.001**2 + (5 * 0.0001) ** 2)

    assert event.timing_uncertainty_days == pytest.approx(expected_uncertainty)
    assert event.observation_start_jd == pytest.approx(
        event.ingress_jd - 2.0 * expected_uncertainty
    )
    assert event.observation_end_jd == pytest.approx(event.egress_jd + 2.0 * expected_uncertainty)


def test_predict_transits_inclusive_range(
    ephemeris: TransitEphemeris,
) -> None:
    events = predict_transits(
        ephemeris,
        2_450_000.0,
        2_450_006.0,
    )

    assert [event.transit_number for event in events] == [0, 1, 2, 3]

    assert [event.mid_transit_jd for event in events] == pytest.approx(
        [
            2_450_000.0,
            2_450_002.0,
            2_450_004.0,
            2_450_006.0,
        ]
    )


def test_predict_transits_returns_empty_tuple(
    ephemeris: TransitEphemeris,
) -> None:
    events = predict_transits(
        ephemeris,
        2_450_000.1,
        2_450_001.9,
    )

    assert events == ()


def test_predict_transits_rejects_reversed_range(
    ephemeris: TransitEphemeris,
) -> None:
    with pytest.raises(
        TransitSchedulerError,
        match="End Julian date",
    ):
        predict_transits(
            ephemeris,
            2_450_010.0,
            2_450_000.0,
        )


def test_predict_transits_enforces_event_limit(
    ephemeris: TransitEphemeris,
) -> None:
    with pytest.raises(
        TransitSchedulerError,
        match="exceeding",
    ):
        predict_transits(
            ephemeris,
            2_450_000.0,
            2_450_010.0,
            maximum_events=3,
        )


@pytest.mark.parametrize(
    "invalid_value",
    [-1.0, float("inf"), float("nan")],
)
def test_build_transit_event_rejects_invalid_baseline(
    ephemeris: TransitEphemeris,
    invalid_value: float,
) -> None:
    with pytest.raises(TransitSchedulerError):
        build_transit_event(
            ephemeris,
            0,
            baseline_before_hours=invalid_value,
        )
