"""Tests for exoplanet transit scoring and ranking."""

from dataclasses import replace

import pytest

from astroscope.transit_ranking import (
    RankingWeights,
    TransitObservationCandidate,
    TransitRankingError,
    rank_transit_candidates,
    score_host_brightness,
    score_midpoint_altitude,
    score_moon_separation,
    score_timing_confidence,
    score_transit_candidate,
    score_transit_depth,
)
from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import (
    TransitVisibilitySample,
    TransitVisibilitySummary,
)


def make_event(
    *,
    planet_name: str = "Example b",
    transit_number: int = 1,
    uncertainty_hours: float = 0.25,
) -> TransitEvent:
    """Build a reusable transit event."""

    midpoint = 2_460_000.20

    return TransitEvent(
        planet_name=planet_name,
        transit_number=transit_number,
        mid_transit_jd=midpoint,
        ingress_jd=midpoint - 0.05,
        egress_jd=midpoint + 0.05,
        observation_start_jd=midpoint - 0.10,
        observation_end_jd=midpoint + 0.10,
        timing_uncertainty_days=(uncertainty_hours / 24.0),
    )


def make_sample(
    *,
    julian_date: float = 2_460_000.20,
    altitude_degrees: float = 60.0,
    moon_separation_degrees: float = 100.0,
    observable: bool = True,
) -> TransitVisibilitySample:
    """Build a reusable visibility sample."""

    return TransitVisibilitySample(
        julian_date=julian_date,
        target_altitude_degrees=altitude_degrees,
        target_azimuth_degrees=180.0,
        airmass=1.15,
        sun_altitude_degrees=(-25.0 if observable else -5.0),
        moon_altitude_degrees=10.0,
        moon_separation_degrees=(moon_separation_degrees),
        moon_illumination_fraction=0.4,
        target_above_minimum_altitude=observable,
        is_astronomical_dark=observable,
    )


def make_summary(
    *,
    planet_name: str = "Example b",
    altitude_degrees: float = 60.0,
    observable_fraction: float = 0.8,
    dark_fraction: float = 1.0,
    moon_separation_degrees: float = 100.0,
    full_window_visible: bool = False,
) -> TransitVisibilitySummary:
    """Build a reusable visibility summary."""

    midpoint_sample = make_sample(
        altitude_degrees=altitude_degrees,
        moon_separation_degrees=(moon_separation_degrees),
        observable=observable_fraction > 0.0,
    )

    return TransitVisibilitySummary(
        planet_name=planet_name,
        target_name="Example Star",
        site_name="Example Observatory",
        samples=(midpoint_sample,),
        midpoint_sample=midpoint_sample,
        minimum_target_altitude_degrees=(altitude_degrees),
        maximum_target_altitude_degrees=(altitude_degrees),
        maximum_airmass=1.5,
        minimum_moon_separation_degrees=(moon_separation_degrees),
        altitude_sample_fraction=(observable_fraction),
        dark_sample_fraction=dark_fraction,
        observable_sample_fraction=(observable_fraction),
        full_observation_window_visible=(full_window_visible),
    )


def make_candidate(
    *,
    planet_name: str = "Example b",
    transit_number: int = 1,
    uncertainty_hours: float = 0.25,
    altitude_degrees: float = 60.0,
    observable_fraction: float = 0.8,
    dark_fraction: float = 1.0,
    moon_separation_degrees: float = 100.0,
    full_window_visible: bool = False,
    transit_depth_ppm: float | None = 2_000.0,
    host_magnitude: float | None = 10.0,
) -> TransitObservationCandidate:
    """Build a complete ranking candidate."""

    return TransitObservationCandidate(
        event=make_event(
            planet_name=planet_name,
            transit_number=transit_number,
            uncertainty_hours=uncertainty_hours,
        ),
        visibility=make_summary(
            planet_name=planet_name,
            altitude_degrees=altitude_degrees,
            observable_fraction=(observable_fraction),
            dark_fraction=dark_fraction,
            moon_separation_degrees=(moon_separation_degrees),
            full_window_visible=(full_window_visible),
        ),
        transit_depth_ppm=transit_depth_ppm,
        host_magnitude=host_magnitude,
    )


def test_default_weights_have_positive_total() -> None:
    weights = RankingWeights()

    assert weights.total == pytest.approx(1.0)


def test_weights_reject_all_zero_values() -> None:
    with pytest.raises(
        TransitRankingError,
        match="At least one",
    ):
        RankingWeights(
            observable_fraction=0.0,
            midpoint_altitude=0.0,
            darkness_fraction=0.0,
            moon_separation=0.0,
            transit_depth=0.0,
            timing_confidence=0.0,
            host_brightness=0.0,
            full_window_visibility=0.0,
        )


def test_weights_reject_negative_value() -> None:
    with pytest.raises(
        TransitRankingError,
        match="must not be negative",
    ):
        RankingWeights(observable_fraction=-0.1)


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (-10.0, 0.0),
        (0.0, 0.0),
        (45.0, 0.5),
        (90.0, 1.0),
        (100.0, 1.0),
    ],
)
def test_midpoint_altitude_score(
    altitude: float,
    expected: float,
) -> None:
    assert score_midpoint_altitude(altitude) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("separation", "expected"),
    [
        (0.0, 0.0),
        (45.0, 0.5),
        (90.0, 1.0),
        (180.0, 1.0),
    ],
)
def test_moon_separation_score(
    separation: float,
    expected: float,
) -> None:
    assert score_moon_separation(separation) == pytest.approx(expected)


def test_transit_depth_score_is_monotonic() -> None:
    shallow = score_transit_depth(100.0)
    medium = score_transit_depth(1_000.0)
    deep = score_transit_depth(10_000.0)

    assert 0.0 < shallow < medium < deep
    assert deep == pytest.approx(1.0)


def test_timing_confidence_decreases_with_uncertainty() -> None:
    precise = score_timing_confidence(0.1)
    moderate = score_timing_confidence(1.0)
    uncertain = score_timing_confidence(5.0)

    assert precise > moderate > uncertain
    assert score_timing_confidence(0.0) == 1.0


@pytest.mark.parametrize(
    ("magnitude", "expected"),
    [
        (4.0, 1.0),
        (5.0, 1.0),
        (10.5, 0.5),
        (16.0, 0.0),
        (18.0, 0.0),
    ],
)
def test_host_brightness_score(
    magnitude: float,
    expected: float,
) -> None:
    assert score_host_brightness(magnitude) == pytest.approx(expected)


def test_candidate_rejects_mismatched_planet_names() -> None:
    event = make_event(
        planet_name="Planet A",
    )
    visibility = make_summary(
        planet_name="Planet B",
    )

    with pytest.raises(
        TransitRankingError,
        match="planet names",
    ):
        TransitObservationCandidate(
            event=event,
            visibility=visibility,
        )


@pytest.mark.parametrize(
    "invalid_depth",
    [-1.0, float("nan"), float("inf")],
)
def test_candidate_rejects_invalid_depth(
    invalid_depth: float,
) -> None:
    with pytest.raises(TransitRankingError):
        replace(
            make_candidate(),
            transit_depth_ppm=invalid_depth,
        )


@pytest.mark.parametrize(
    "invalid_magnitude",
    [float("nan"), float("inf")],
)
def test_candidate_rejects_invalid_magnitude(
    invalid_magnitude: float,
) -> None:
    with pytest.raises(TransitRankingError):
        replace(
            make_candidate(),
            host_magnitude=invalid_magnitude,
        )


def test_score_is_between_zero_and_one_hundred() -> None:
    score = score_transit_candidate(make_candidate())

    assert 0.0 <= score.total_score <= 100.0


def test_missing_optional_data_receives_neutral_score() -> None:
    candidate = make_candidate(
        transit_depth_ppm=None,
        host_magnitude=None,
    )

    score = score_transit_candidate(candidate)

    assert score.transit_depth_score == 0.5
    assert score.host_brightness_score == 0.5
    assert score.missing_fields == (
        "transit_depth_ppm",
        "host_magnitude",
    )


def test_custom_weights_can_isolate_visibility() -> None:
    candidate = make_candidate(
        observable_fraction=0.75,
    )

    weights = RankingWeights(
        observable_fraction=1.0,
        midpoint_altitude=0.0,
        darkness_fraction=0.0,
        moon_separation=0.0,
        transit_depth=0.0,
        timing_confidence=0.0,
        host_brightness=0.0,
        full_window_visibility=0.0,
    )

    score = score_transit_candidate(
        candidate,
        weights=weights,
    )

    assert score.total_score == pytest.approx(75.0)


def test_strong_candidate_outranks_weak_candidate() -> None:
    strong_candidate = make_candidate(
        planet_name="Strong b",
        altitude_degrees=80.0,
        observable_fraction=1.0,
        dark_fraction=1.0,
        moon_separation_degrees=140.0,
        full_window_visible=True,
        uncertainty_hours=0.05,
        transit_depth_ppm=8_000.0,
        host_magnitude=7.0,
    )

    weak_candidate = make_candidate(
        planet_name="Weak b",
        altitude_degrees=20.0,
        observable_fraction=0.2,
        dark_fraction=0.3,
        moon_separation_degrees=15.0,
        full_window_visible=False,
        uncertainty_hours=8.0,
        transit_depth_ppm=100.0,
        host_magnitude=15.5,
    )

    ranked = rank_transit_candidates(
        (
            weak_candidate,
            strong_candidate,
        )
    )

    assert ranked[0].rank == 1
    assert ranked[0].candidate.event.planet_name == "Strong b"
    assert ranked[0].score.total_score > ranked[1].score.total_score


def test_ranking_is_deterministic_for_equal_scores() -> None:
    candidate_b = make_candidate(
        planet_name="Beta b",
        transit_number=2,
    )
    candidate_a = make_candidate(
        planet_name="Alpha b",
        transit_number=1,
    )

    ranked = rank_transit_candidates(
        (
            candidate_b,
            candidate_a,
        )
    )

    assert [item.candidate.event.planet_name for item in ranked] == [
        "Alpha b",
        "Beta b",
    ]


def test_empty_candidate_collection_returns_empty_tuple() -> None:
    assert rank_transit_candidates(()) == ()
