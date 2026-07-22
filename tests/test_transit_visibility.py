"""Tests for exoplanet transit visibility calculations."""

from collections.abc import Iterator

import pytest
from astropy import units as u
from astropy.time import Time
from astropy.utils import iers

from astroscope.transit_scheduler import TransitEvent
from astroscope.transit_visibility import (
    MAXIMUM_VISIBILITY_SAMPLES,
    ObserverSite,
    TransitTarget,
    TransitVisibilityError,
    TransitVisibilitySample,
    analyze_transit_visibility,
    calculate_airmass_from_altitude_degrees,
    calculate_moon_illumination_fraction,
    sample_transit_visibility,
)


@pytest.fixture(autouse=True)
def disable_iers_download() -> Iterator[None]:
    """Prevent astronomy tests from making network requests."""

    previous_value = iers.conf.auto_download
    iers.conf.auto_download = False

    yield

    iers.conf.auto_download = previous_value


@pytest.fixture
def greenwich() -> ObserverSite:
    """Return the Royal Observatory Greenwich location."""

    return ObserverSite(
        name="Greenwich",
        latitude_degrees=51.4769,
        longitude_degrees=0.0,
        elevation_meters=46.0,
    )


@pytest.fixture
def polaris() -> TransitTarget:
    """Return approximate ICRS coordinates for Polaris."""

    return TransitTarget(
        name="Polaris",
        right_ascension_degrees=37.9546,
        declination_degrees=89.2641,
    )


@pytest.fixture
def transit_event() -> TransitEvent:
    """Return a chronological example transit event."""

    return TransitEvent(
        planet_name="Example b",
        transit_number=12,
        mid_transit_jd=2_460_000.20,
        ingress_jd=2_460_000.15,
        egress_jd=2_460_000.25,
        observation_start_jd=2_460_000.10,
        observation_end_jd=2_460_000.30,
        timing_uncertainty_days=0.001,
    )


def test_observer_site_creates_earth_location(
    greenwich: ObserverSite,
) -> None:
    location = greenwich.earth_location()

    longitude = location.lon.to_value(u.deg)
    latitude = location.lat.to_value(u.deg)
    height = location.height.to_value(u.m)

    assert longitude == pytest.approx(0.0)
    assert latitude == pytest.approx(51.4769)
    assert height == pytest.approx(46.0)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("latitude_degrees", -90.1),
        ("latitude_degrees", 90.1),
        ("longitude_degrees", -180.1),
        ("longitude_degrees", 180.1),
        ("latitude_degrees", float("nan")),
        ("longitude_degrees", float("inf")),
        ("elevation_meters", float("nan")),
    ],
)
def test_observer_site_rejects_invalid_values(
    field_name: str,
    field_value: float,
) -> None:
    values: dict[str, object] = {
        "name": "Test Site",
        "latitude_degrees": 35.0,
        "longitude_degrees": 135.0,
        "elevation_meters": 50.0,
    }
    values[field_name] = field_value

    with pytest.raises(TransitVisibilityError):
        ObserverSite(**values)  # type: ignore[arg-type]


def test_observer_site_rejects_empty_name() -> None:
    with pytest.raises(
        TransitVisibilityError,
        match="name",
    ):
        ObserverSite(
            name="   ",
            latitude_degrees=35.0,
            longitude_degrees=135.0,
        )


def test_transit_target_creates_sky_coordinate(
    polaris: TransitTarget,
) -> None:
    coordinate = polaris.sky_coordinate()

    assert coordinate.ra.deg == pytest.approx(37.9546)
    assert coordinate.dec.deg == pytest.approx(89.2641)


@pytest.mark.parametrize(
    ("right_ascension", "declination"),
    [
        (-0.1, 0.0),
        (360.0, 0.0),
        (0.0, -90.1),
        (0.0, 90.1),
        (float("nan"), 0.0),
        (0.0, float("inf")),
    ],
)
def test_transit_target_rejects_invalid_coordinates(
    right_ascension: float,
    declination: float,
) -> None:
    with pytest.raises(TransitVisibilityError):
        TransitTarget(
            name="Invalid Target",
            right_ascension_degrees=right_ascension,
            declination_degrees=declination,
        )


def test_transit_target_rejects_empty_name() -> None:
    with pytest.raises(
        TransitVisibilityError,
        match="name",
    ):
        TransitTarget(
            name="",
            right_ascension_degrees=10.0,
            declination_degrees=20.0,
        )


@pytest.mark.parametrize(
    ("altitude_degrees", "expected_airmass"),
    [
        (90.0, 1.0),
        (30.0, 2.0),
        (0.0, None),
        (-10.0, None),
    ],
)
def test_calculate_airmass_from_altitude(
    altitude_degrees: float,
    expected_airmass: float | None,
) -> None:
    result = calculate_airmass_from_altitude_degrees(altitude_degrees)

    if expected_airmass is None:
        assert result is None
    else:
        assert result == pytest.approx(expected_airmass)


@pytest.mark.parametrize(
    "invalid_altitude",
    [-90.1, 90.1, float("nan"), float("inf")],
)
def test_airmass_rejects_invalid_altitude(
    invalid_altitude: float,
) -> None:
    with pytest.raises(TransitVisibilityError):
        calculate_airmass_from_altitude_degrees(invalid_altitude)


@pytest.mark.parametrize(
    ("elongation_degrees", "expected_fraction"),
    [
        (0.0, 0.0),
        (90.0, 0.5),
        (180.0, 1.0),
    ],
)
def test_calculate_moon_illumination(
    elongation_degrees: float,
    expected_fraction: float,
) -> None:
    result = calculate_moon_illumination_fraction(elongation_degrees)

    assert result == pytest.approx(expected_fraction)


@pytest.mark.parametrize(
    "invalid_elongation",
    [-0.1, 180.1, float("nan"), float("inf")],
)
def test_moon_illumination_rejects_invalid_angle(
    invalid_elongation: float,
) -> None:
    with pytest.raises(TransitVisibilityError):
        calculate_moon_illumination_fraction(invalid_elongation)


@pytest.mark.parametrize(
    (
        "above_altitude",
        "astronomical_dark",
        "expected_observable",
    ),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_visibility_sample_observable_property(
    above_altitude: bool,
    astronomical_dark: bool,
    expected_observable: bool,
) -> None:
    sample = TransitVisibilitySample(
        julian_date=2_460_000.0,
        target_altitude_degrees=45.0,
        target_azimuth_degrees=180.0,
        airmass=1.4,
        sun_altitude_degrees=-25.0,
        moon_altitude_degrees=20.0,
        moon_separation_degrees=90.0,
        moon_illumination_fraction=0.5,
        target_above_minimum_altitude=above_altitude,
        is_astronomical_dark=astronomical_dark,
    )

    assert sample.is_observable is expected_observable


def test_polaris_is_above_greenwich_horizon_at_night(
    greenwich: ObserverSite,
    polaris: TransitTarget,
) -> None:
    observation_time = Time(
        "2024-03-20T00:00:00",
        format="isot",
        scale="utc",
    )

    sample = sample_transit_visibility(
        greenwich,
        polaris,
        float(observation_time.jd),
    )

    assert 45.0 < sample.target_altitude_degrees < 60.0
    assert 0.0 <= sample.target_azimuth_degrees < 360.0
    assert sample.airmass is not None
    assert sample.is_astronomical_dark
    assert sample.target_above_minimum_altitude
    assert sample.is_observable


def test_sun_altitude_distinguishes_day_and_night(
    greenwich: ObserverSite,
    polaris: TransitTarget,
) -> None:
    midnight = Time(
        "2024-03-20T00:00:00",
        format="isot",
        scale="utc",
    )
    noon = Time(
        "2024-03-20T12:00:00",
        format="isot",
        scale="utc",
    )

    night_sample = sample_transit_visibility(
        greenwich,
        polaris,
        float(midnight.jd),
    )
    day_sample = sample_transit_visibility(
        greenwich,
        polaris,
        float(noon.jd),
    )

    assert night_sample.sun_altitude_degrees < -18.0
    assert night_sample.is_astronomical_dark

    assert day_sample.sun_altitude_degrees > 0.0
    assert not day_sample.is_astronomical_dark


def test_target_at_lower_culmination_is_below_horizon(
    greenwich: ObserverSite,
) -> None:
    observation_time = Time(
        "2024-03-20T00:00:00",
        format="isot",
        scale="utc",
    )

    local_sidereal_degrees = observation_time.sidereal_time(
        "apparent",
        longitude=(greenwich.longitude_degrees * u.deg),
    ).deg

    target = TransitTarget(
        name="Lower culmination target",
        right_ascension_degrees=(local_sidereal_degrees + 180.0) % 360.0,
        declination_degrees=0.0,
    )

    sample = sample_transit_visibility(
        greenwich,
        target,
        float(observation_time.jd),
    )

    assert sample.target_altitude_degrees < 0.0
    assert sample.airmass is None
    assert not sample.target_above_minimum_altitude
    assert not sample.is_observable


def test_analyze_transit_visibility_builds_summary(
    monkeypatch: pytest.MonkeyPatch,
    transit_event: TransitEvent,
    greenwich: ObserverSite,
    polaris: TransitTarget,
) -> None:
    altitudes = (10.0, 30.0, 45.0, 30.0, 10.0)
    darkness = (False, True, True, True, False)

    def fake_sample(
        site: ObserverSite,
        target: TransitTarget,
        julian_date: float,
        *,
        minimum_altitude_degrees: float,
        darkness_sun_altitude_degrees: float,
    ) -> TransitVisibilitySample:
        del site
        del target
        del darkness_sun_altitude_degrees

        fraction = (julian_date - transit_event.observation_start_jd) / (
            transit_event.observation_end_jd - transit_event.observation_start_jd
        )

        index = round(fraction * 4)
        altitude = altitudes[index]
        is_dark = darkness[index]

        return TransitVisibilitySample(
            julian_date=julian_date,
            target_altitude_degrees=altitude,
            target_azimuth_degrees=100.0 + index,
            airmass=(calculate_airmass_from_altitude_degrees(altitude)),
            sun_altitude_degrees=(-25.0 if is_dark else -5.0),
            moon_altitude_degrees=20.0,
            moon_separation_degrees=80.0 - index,
            moon_illumination_fraction=0.4,
            target_above_minimum_altitude=(altitude >= minimum_altitude_degrees),
            is_astronomical_dark=is_dark,
        )

    monkeypatch.setattr(
        "astroscope.transit_visibility.sample_transit_visibility",
        fake_sample,
    )

    summary = analyze_transit_visibility(
        transit_event,
        greenwich,
        polaris,
        sample_count=5,
        minimum_altitude_degrees=20.0,
    )

    assert len(summary.samples) == 5
    assert summary.planet_name == "Example b"
    assert summary.target_name == "Polaris"
    assert summary.site_name == "Greenwich"

    assert summary.minimum_target_altitude_degrees == pytest.approx(10.0)
    assert summary.maximum_target_altitude_degrees == pytest.approx(45.0)
    assert summary.minimum_moon_separation_degrees == pytest.approx(76.0)

    assert summary.altitude_sample_fraction == pytest.approx(3.0 / 5.0)
    assert summary.dark_sample_fraction == pytest.approx(3.0 / 5.0)
    assert summary.observable_sample_fraction == pytest.approx(3.0 / 5.0)

    assert summary.midpoint_sample.target_altitude_degrees == pytest.approx(45.0)
    assert not summary.full_observation_window_visible


def test_analyze_visibility_can_report_full_window(
    monkeypatch: pytest.MonkeyPatch,
    transit_event: TransitEvent,
    greenwich: ObserverSite,
    polaris: TransitTarget,
) -> None:
    def fake_sample(
        site: ObserverSite,
        target: TransitTarget,
        julian_date: float,
        *,
        minimum_altitude_degrees: float,
        darkness_sun_altitude_degrees: float,
    ) -> TransitVisibilitySample:
        del site
        del target
        del minimum_altitude_degrees
        del darkness_sun_altitude_degrees

        return TransitVisibilitySample(
            julian_date=julian_date,
            target_altitude_degrees=60.0,
            target_azimuth_degrees=180.0,
            airmass=1.15,
            sun_altitude_degrees=-25.0,
            moon_altitude_degrees=-10.0,
            moon_separation_degrees=120.0,
            moon_illumination_fraction=0.1,
            target_above_minimum_altitude=True,
            is_astronomical_dark=True,
        )

    monkeypatch.setattr(
        "astroscope.transit_visibility.sample_transit_visibility",
        fake_sample,
    )

    summary = analyze_transit_visibility(
        transit_event,
        greenwich,
        polaris,
        sample_count=3,
    )

    assert summary.altitude_sample_fraction == 1.0
    assert summary.dark_sample_fraction == 1.0
    assert summary.observable_sample_fraction == 1.0
    assert summary.full_observation_window_visible


@pytest.mark.parametrize(
    "sample_count",
    [
        2,
        0,
        -1,
        True,
        MAXIMUM_VISIBILITY_SAMPLES + 1,
    ],
)
def test_analyze_visibility_rejects_invalid_sample_count(
    transit_event: TransitEvent,
    greenwich: ObserverSite,
    polaris: TransitTarget,
    sample_count: int,
) -> None:
    with pytest.raises(TransitVisibilityError):
        analyze_transit_visibility(
            transit_event,
            greenwich,
            polaris,
            sample_count=sample_count,
        )


def test_analyze_visibility_rejects_invalid_event_order(
    greenwich: ObserverSite,
    polaris: TransitTarget,
) -> None:
    invalid_event = TransitEvent(
        planet_name="Broken b",
        transit_number=1,
        mid_transit_jd=2_460_000.20,
        ingress_jd=2_460_000.15,
        egress_jd=2_460_000.25,
        observation_start_jd=2_460_000.18,
        observation_end_jd=2_460_000.30,
        timing_uncertainty_days=0.0,
    )

    with pytest.raises(
        TransitVisibilityError,
        match="chronological order",
    ):
        analyze_transit_visibility(
            invalid_event,
            greenwich,
            polaris,
        )


@pytest.mark.parametrize(
    ("minimum_altitude", "sun_altitude"),
    [
        (-90.1, -18.0),
        (90.1, -18.0),
        (20.0, -90.1),
        (20.0, 90.1),
        (float("nan"), -18.0),
        (20.0, float("inf")),
    ],
)
def test_visibility_rejects_invalid_thresholds(
    greenwich: ObserverSite,
    polaris: TransitTarget,
    minimum_altitude: float,
    sun_altitude: float,
) -> None:
    observation_time = Time(
        "2024-03-20T00:00:00",
        format="isot",
        scale="utc",
    )

    with pytest.raises(TransitVisibilityError):
        sample_transit_visibility(
            greenwich,
            polaris,
            float(observation_time.jd),
            minimum_altitude_degrees=minimum_altitude,
            darkness_sun_altitude_degrees=sun_altitude,
        )
