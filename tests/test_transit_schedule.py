"""Tests for ranked exoplanet transit schedule generation."""

import pytest

from astroscope.transit_schedule import (
    TransitScheduleError,
    TransitScheduleRequest,
    TransitScheduleTarget,
    generate_transit_schedule,
)
from astroscope.transit_scheduler import (
    TransitEphemeris,
    TransitEvent,
)
from astroscope.transit_visibility import (
    ObserverSite,
    TransitTarget,
    TransitVisibilitySample,
    TransitVisibilitySummary,
)


@pytest.fixture
def site() -> ObserverSite:
    """Return a reusable observing site."""

    return ObserverSite(
        name="Test Observatory",
        latitude_degrees=35.0,
        longitude_degrees=135.0,
        elevation_meters=100.0,
    )


def make_schedule_target(
    *,
    planet_name: str,
    reference_mid_transit_jd: float = 2_460_000.0,
    orbital_period_days: float = 5.0,
    transit_depth_ppm: float | None = 2_000.0,
    host_magnitude: float | None = 10.0,
) -> TransitScheduleTarget:
    """Create one reusable schedule target."""

    return TransitScheduleTarget(
        ephemeris=TransitEphemeris(
            planet_name=planet_name,
            orbital_period_days=orbital_period_days,
            reference_mid_transit_jd=(reference_mid_transit_jd),
            transit_duration_hours=2.0,
            period_uncertainty_days=0.0001,
            reference_epoch_uncertainty_days=0.001,
        ),
        target=TransitTarget(
            name=f"{planet_name} host",
            right_ascension_degrees=120.0,
            declination_degrees=25.0,
        ),
        transit_depth_ppm=transit_depth_ppm,
        host_magnitude=host_magnitude,
    )


def make_visibility_summary(
    event: TransitEvent,
    target: TransitTarget,
    site: ObserverSite,
    *,
    altitude_degrees: float,
    observable_fraction: float,
    dark_fraction: float,
    moon_separation_degrees: float,
    full_window_visible: bool,
) -> TransitVisibilitySummary:
    """Create a deterministic visibility summary."""

    midpoint_sample = TransitVisibilitySample(
        julian_date=event.mid_transit_jd,
        target_altitude_degrees=altitude_degrees,
        target_azimuth_degrees=180.0,
        airmass=1.2,
        sun_altitude_degrees=(-25.0 if dark_fraction > 0.0 else -5.0),
        moon_altitude_degrees=10.0,
        moon_separation_degrees=(moon_separation_degrees),
        moon_illumination_fraction=0.4,
        target_above_minimum_altitude=(observable_fraction > 0.0),
        is_astronomical_dark=(dark_fraction > 0.0),
    )

    return TransitVisibilitySummary(
        planet_name=event.planet_name,
        target_name=target.name,
        site_name=site.name,
        samples=(midpoint_sample,),
        midpoint_sample=midpoint_sample,
        minimum_target_altitude_degrees=(altitude_degrees),
        maximum_target_altitude_degrees=(altitude_degrees),
        maximum_airmass=1.2,
        minimum_moon_separation_degrees=(moon_separation_degrees),
        altitude_sample_fraction=(observable_fraction),
        dark_sample_fraction=dark_fraction,
        observable_sample_fraction=(observable_fraction),
        full_observation_window_visible=(full_window_visible),
    )


def test_request_accepts_valid_settings() -> None:
    request = TransitScheduleRequest(
        start_jd=2_460_000.0,
        end_jd=2_460_010.0,
    )

    assert request.visibility_sample_count == 25
    assert request.maximum_total_events == 5_000


def test_request_rejects_reversed_range() -> None:
    with pytest.raises(
        TransitScheduleError,
        match="End Julian date",
    ):
        TransitScheduleRequest(
            start_jd=2_460_010.0,
            end_jd=2_460_000.0,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("baseline_before_hours", -1.0),
        ("baseline_after_hours", -1.0),
        ("uncertainty_sigma_multiplier", -1.0),
        ("visibility_sample_count", 2),
        ("visibility_sample_count", True),
        ("maximum_events_per_target", 0),
        ("maximum_total_events", 0),
    ],
)
def test_request_rejects_invalid_settings(
    field_name: str,
    field_value: object,
) -> None:
    values: dict[str, object] = {
        "start_jd": 2_460_000.0,
        "end_jd": 2_460_010.0,
    }
    values[field_name] = field_value

    with pytest.raises(TransitScheduleError):
        TransitScheduleRequest(
            **values,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("transit_depth_ppm", "host_magnitude"),
    [
        (-1.0, 10.0),
        (float("nan"), 10.0),
        (1_000.0, float("inf")),
    ],
)
def test_target_rejects_invalid_metadata(
    transit_depth_ppm: float,
    host_magnitude: float,
) -> None:
    with pytest.raises(TransitScheduleError):
        make_schedule_target(
            planet_name="Invalid b",
            transit_depth_ppm=transit_depth_ppm,
            host_magnitude=host_magnitude,
        )


def test_empty_target_collection_returns_empty_result(
    site: ObserverSite,
) -> None:
    result = generate_transit_schedule(
        (),
        site,
        TransitScheduleRequest(
            start_jd=2_460_000.0,
            end_jd=2_460_010.0,
        ),
    )

    assert result.target_count == 0
    assert result.predicted_event_count == 0
    assert result.ranked_transits == ()
    assert result.targets_without_events == ()
    assert result.best_transit is None


def test_schedule_records_targets_without_events(
    site: ObserverSite,
) -> None:
    target = make_schedule_target(
        planet_name="Quiet b",
        reference_mid_transit_jd=2_460_100.0,
        orbital_period_days=50.0,
    )

    result = generate_transit_schedule(
        (target,),
        site,
        TransitScheduleRequest(
            start_jd=2_460_001.0,
            end_jd=2_460_002.0,
        ),
    )

    assert result.predicted_event_count == 0
    assert result.ranked_transits == ()
    assert result.targets_without_events == ("Quiet b",)


def test_schedule_rejects_duplicate_planets(
    site: ObserverSite,
) -> None:
    first = make_schedule_target(
        planet_name="Duplicate b",
    )
    second = make_schedule_target(
        planet_name="duplicate B",
    )

    with pytest.raises(
        TransitScheduleError,
        match="duplicate planet",
    ):
        generate_transit_schedule(
            (first, second),
            site,
            TransitScheduleRequest(
                start_jd=2_460_000.0,
                end_jd=2_460_001.0,
            ),
        )


def test_schedule_combines_and_ranks_events(
    monkeypatch: pytest.MonkeyPatch,
    site: ObserverSite,
) -> None:
    strong_target = make_schedule_target(
        planet_name="Strong b",
        transit_depth_ppm=8_000.0,
        host_magnitude=7.0,
    )
    weak_target = make_schedule_target(
        planet_name="Weak b",
        transit_depth_ppm=100.0,
        host_magnitude=15.0,
    )

    def fake_analyze(
        event: TransitEvent,
        observer_site: ObserverSite,
        target: TransitTarget,
        *,
        sample_count: int,
        minimum_altitude_degrees: float,
        darkness_sun_altitude_degrees: float,
    ) -> TransitVisibilitySummary:
        del sample_count
        del minimum_altitude_degrees
        del darkness_sun_altitude_degrees

        if event.planet_name == "Strong b":
            return make_visibility_summary(
                event,
                target,
                observer_site,
                altitude_degrees=80.0,
                observable_fraction=1.0,
                dark_fraction=1.0,
                moon_separation_degrees=140.0,
                full_window_visible=True,
            )

        return make_visibility_summary(
            event,
            target,
            observer_site,
            altitude_degrees=20.0,
            observable_fraction=0.2,
            dark_fraction=0.3,
            moon_separation_degrees=15.0,
            full_window_visible=False,
        )

    monkeypatch.setattr(
        "astroscope.transit_schedule.analyze_transit_visibility",
        fake_analyze,
    )

    result = generate_transit_schedule(
        (
            weak_target,
            strong_target,
        ),
        site,
        TransitScheduleRequest(
            start_jd=2_460_000.0,
            end_jd=2_460_000.0,
        ),
    )

    assert result.target_count == 2
    assert result.predicted_event_count == 2
    assert len(result.ranked_transits) == 2

    assert result.ranked_transits[0].candidate.event.planet_name == "Strong b"
    assert result.ranked_transits[0].rank == 1
    assert result.fully_visible_count == 1
    assert result.observable_transit_count == 2
    assert result.best_transit is result.ranked_transits[0]


def test_schedule_forwards_request_settings(
    monkeypatch: pytest.MonkeyPatch,
    site: ObserverSite,
) -> None:
    schedule_target = make_schedule_target(
        planet_name="Forwarded b",
    )

    captured_prediction: dict[str, object] = {}
    captured_visibility: dict[str, object] = {}

    event = TransitEvent(
        planet_name="Forwarded b",
        transit_number=0,
        mid_transit_jd=2_460_000.0,
        ingress_jd=2_459_999.95,
        egress_jd=2_460_000.05,
        observation_start_jd=2_459_999.90,
        observation_end_jd=2_460_000.10,
        timing_uncertainty_days=0.001,
    )

    def fake_predict(
        ephemeris: TransitEphemeris,
        start_jd: float,
        end_jd: float,
        *,
        baseline_before_hours: float,
        baseline_after_hours: float,
        uncertainty_sigma_multiplier: float,
        maximum_events: int,
    ) -> tuple[TransitEvent, ...]:
        captured_prediction.update(
            {
                "planet": ephemeris.planet_name,
                "start_jd": start_jd,
                "end_jd": end_jd,
                "baseline_before_hours": (baseline_before_hours),
                "baseline_after_hours": (baseline_after_hours),
                "uncertainty_sigma_multiplier": (uncertainty_sigma_multiplier),
                "maximum_events": maximum_events,
            }
        )
        return (event,)

    def fake_analyze(
        analyzed_event: TransitEvent,
        observer_site: ObserverSite,
        target: TransitTarget,
        *,
        sample_count: int,
        minimum_altitude_degrees: float,
        darkness_sun_altitude_degrees: float,
    ) -> TransitVisibilitySummary:
        captured_visibility.update(
            {
                "event": analyzed_event,
                "sample_count": sample_count,
                "minimum_altitude_degrees": (minimum_altitude_degrees),
                "darkness_sun_altitude_degrees": (darkness_sun_altitude_degrees),
            }
        )

        return make_visibility_summary(
            analyzed_event,
            target,
            observer_site,
            altitude_degrees=60.0,
            observable_fraction=1.0,
            dark_fraction=1.0,
            moon_separation_degrees=100.0,
            full_window_visible=True,
        )

    monkeypatch.setattr(
        "astroscope.transit_schedule.predict_transits",
        fake_predict,
    )
    monkeypatch.setattr(
        "astroscope.transit_schedule.analyze_transit_visibility",
        fake_analyze,
    )

    request = TransitScheduleRequest(
        start_jd=2_460_000.0,
        end_jd=2_460_005.0,
        baseline_before_hours=2.0,
        baseline_after_hours=3.0,
        uncertainty_sigma_multiplier=2.5,
        visibility_sample_count=41,
        minimum_altitude_degrees=30.0,
        darkness_sun_altitude_degrees=-12.0,
        maximum_events_per_target=75,
    )

    generate_transit_schedule(
        (schedule_target,),
        site,
        request,
    )

    assert captured_prediction == {
        "planet": "Forwarded b",
        "start_jd": 2_460_000.0,
        "end_jd": 2_460_005.0,
        "baseline_before_hours": 2.0,
        "baseline_after_hours": 3.0,
        "uncertainty_sigma_multiplier": 2.5,
        "maximum_events": 75,
    }

    assert captured_visibility["event"] is event
    assert captured_visibility["sample_count"] == 41
    assert captured_visibility["minimum_altitude_degrees"] == 30.0
    assert captured_visibility["darkness_sun_altitude_degrees"] == -12.0


def test_schedule_enforces_total_event_limit(
    monkeypatch: pytest.MonkeyPatch,
    site: ObserverSite,
) -> None:
    first_target = make_schedule_target(
        planet_name="First b",
    )
    second_target = make_schedule_target(
        planet_name="Second b",
    )

    def fake_predict(
        ephemeris: TransitEphemeris,
        start_jd: float,
        end_jd: float,
        **kwargs: object,
    ) -> tuple[TransitEvent, ...]:
        del start_jd
        del end_jd
        del kwargs

        return (
            TransitEvent(
                planet_name=ephemeris.planet_name,
                transit_number=0,
                mid_transit_jd=2_460_000.0,
                ingress_jd=2_459_999.95,
                egress_jd=2_460_000.05,
                observation_start_jd=2_459_999.90,
                observation_end_jd=2_460_000.10,
                timing_uncertainty_days=0.0,
            ),
        )

    monkeypatch.setattr(
        "astroscope.transit_schedule.predict_transits",
        fake_predict,
    )

    with pytest.raises(
        TransitScheduleError,
        match="schedule limit",
    ):
        generate_transit_schedule(
            (
                first_target,
                second_target,
            ),
            site,
            TransitScheduleRequest(
                start_jd=2_460_000.0,
                end_jd=2_460_001.0,
                maximum_total_events=1,
            ),
        )
