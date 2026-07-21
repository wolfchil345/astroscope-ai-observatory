"""Tests for the interactive local sky map."""

from datetime import date, time

import pytest
from astropy.utils import iers

from astroscope.sky_map import (
    SkyMapLabels,
    SkyMapPoint,
    altitude_to_radial_distance,
    calculate_sky_map_points,
    create_sky_map_figure,
)

iers.conf.auto_download = False


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (90.0, 0.0),
        (60.0, 30.0),
        (30.0, 60.0),
        (0.0, 90.0),
        (-30.0, 120.0),
    ],
)
def test_altitude_to_radial_distance(
    altitude: float,
    expected: float,
) -> None:
    assert altitude_to_radial_distance(altitude) == pytest.approx(expected)


@pytest.mark.parametrize(
    "altitude",
    [-91.0, 91.0],
)
def test_invalid_altitude_raises_error(
    altitude: float,
) -> None:
    with pytest.raises(ValueError):
        altitude_to_radial_distance(altitude)


def test_catalog_sky_map_contains_all_presets() -> None:
    points = calculate_sky_map_points(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_objects=True,
        include_solar_system_objects=False,
    )

    assert len(points) == 5
    assert all(point.category == "catalog" for point in points)


def test_polaris_is_visible_from_osaka() -> None:
    points = calculate_sky_map_points(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_objects=True,
        include_solar_system_objects=False,
    )

    polaris = next(point for point in points if point.object_key == "polaris")

    assert polaris.is_above_horizon
    assert 0.0 <= polaris.radial_distance_degrees <= 90.0
    assert polaris.cardinal_direction == "north"


def test_empty_category_selection_returns_no_points() -> None:
    points = calculate_sky_map_points(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 0),
        include_catalog_objects=False,
        include_solar_system_objects=False,
    )

    assert points == ()


def test_figure_only_plots_above_horizon_points() -> None:
    points = (
        SkyMapPoint(
            object_key="visible",
            category="catalog",
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            radial_distance_degrees=45.0,
            cardinal_direction="south",
            status="observable",
            is_above_horizon=True,
        ),
        SkyMapPoint(
            object_key="hidden",
            category="catalog",
            altitude_degrees=-20.0,
            azimuth_degrees=0.0,
            radial_distance_degrees=110.0,
            cardinal_direction="north",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )

    labels = SkyMapLabels(
        title="Test sky",
        catalog_trace="Catalogue",
        solar_system_trace="Solar System",
        altitude="Altitude",
        azimuth="Azimuth",
        direction="Direction",
        status="Status",
        zenith="Zenith",
        horizon="Horizon",
    )

    figure = create_sky_map_figure(
        points=points,
        display_names={
            "visible": "Visible",
            "hidden": "Hidden",
        },
        direction_names={
            "north": "North",
            "south": "South",
        },
        status_names={
            "observable": "Observable",
            "below_horizon": "Below horizon",
        },
        labels=labels,
    )

    assert len(figure.data) == 1
    assert list(figure.data[0].text) == ["Visible"]
    assert list(figure.data[0].r) == [45.0]
    assert list(figure.data[0].theta) == [180.0]


def test_sky_map_orientation() -> None:
    labels = SkyMapLabels(
        title="Test sky",
        catalog_trace="Catalogue",
        solar_system_trace="Solar System",
        altitude="Altitude",
        azimuth="Azimuth",
        direction="Direction",
        status="Status",
        zenith="Zenith",
        horizon="Horizon",
    )

    figure = create_sky_map_figure(
        points=(),
        display_names={},
        direction_names={},
        status_names={},
        labels=labels,
    )

    assert figure.layout.polar.angularaxis.rotation == 90
    assert figure.layout.polar.angularaxis.direction == "clockwise"
    assert list(figure.layout.polar.radialaxis.range) == [0, 90]
