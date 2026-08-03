"""Tests for the interactive local sky map."""

import subprocess
import sys
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from astropy.utils import iers

from astroscope import sky_map as sky_map_module
from astroscope.sky_map import (
    SkyMapPoint,
    altitude_to_radial_distance,
    calculate_sky_map_points,
)

iers.conf.auto_download = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (90.0, 0.0),
        (60.0, 30.0),
        (30.0, 60.0),
        (0.0, 90.0),
        (-30.0, 120.0),
        (-90.0, 180.0),
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
    with pytest.raises(ValueError) as error:
        altitude_to_radial_distance(altitude)

    assert str(error.value) == "Altitude must be between -90 and 90 degrees."


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


def test_catalog_points_preserve_order_arguments_and_result_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    presets = {
        "alpha": SimpleNamespace(
            right_ascension="01h 00m 00s",
            declination="-02d 00m 00s",
        ),
        "beta": SimpleNamespace(
            right_ascension="03h 00m 00s",
            declination="+04d 00m 00s",
        ),
    }
    coordinate_results = (
        SimpleNamespace(
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            cardinal_direction="south",
            status="observable",
            is_above_horizon=True,
        ),
        SimpleNamespace(
            altitude_degrees=-15.0,
            azimuth_degrees=0.0,
            cardinal_direction="north",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )
    coordinate_calls: list[dict[str, object]] = []

    def fake_calculate_horizontal_coordinates(**kwargs: object) -> SimpleNamespace:
        coordinate_calls.append(kwargs)
        return coordinate_results[len(coordinate_calls) - 1]

    monkeypatch.setattr(sky_map_module, "CELESTIAL_PRESETS", presets)
    monkeypatch.setattr(
        sky_map_module,
        "calculate_horizontal_coordinates",
        fake_calculate_horizontal_coordinates,
    )

    points = calculate_sky_map_points(
        latitude_deg=34.6937,
        longitude_deg=135.5023,
        elevation_m=15.0,
        timezone_name="Asia/Tokyo",
        local_date=date(2024, 1, 1),
        local_time=time(21, 30),
        minimum_altitude_degrees=27.0,
        include_catalog_objects=True,
        include_solar_system_objects=False,
    )

    assert coordinate_calls == [
        {
            "right_ascension": "01h 00m 00s",
            "declination": "-02d 00m 00s",
            "latitude_deg": 34.6937,
            "longitude_deg": 135.5023,
            "elevation_m": 15.0,
            "timezone_name": "Asia/Tokyo",
            "local_date": date(2024, 1, 1),
            "local_time": time(21, 30),
            "minimum_altitude_degrees": 27.0,
        },
        {
            "right_ascension": "03h 00m 00s",
            "declination": "+04d 00m 00s",
            "latitude_deg": 34.6937,
            "longitude_deg": 135.5023,
            "elevation_m": 15.0,
            "timezone_name": "Asia/Tokyo",
            "local_date": date(2024, 1, 1),
            "local_time": time(21, 30),
            "minimum_altitude_degrees": 27.0,
        },
    ]
    assert points == (
        SkyMapPoint(
            object_key="alpha",
            category="catalog",
            altitude_degrees=45.0,
            azimuth_degrees=180.0,
            radial_distance_degrees=45.0,
            cardinal_direction="south",
            status="observable",
            is_above_horizon=True,
        ),
        SkyMapPoint(
            object_key="beta",
            category="catalog",
            altitude_degrees=-15.0,
            azimuth_degrees=0.0,
            radial_distance_degrees=105.0,
            cardinal_direction="north",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )


def test_solar_system_points_preserve_order_arguments_and_result_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solar_results = (
        SimpleNamespace(
            altitude_degrees=30.0,
            azimuth_degrees=90.0,
            cardinal_direction="east",
            status="observable",
            is_above_horizon=True,
        ),
        SimpleNamespace(
            altitude_degrees=-20.0,
            azimuth_degrees=270.0,
            cardinal_direction="west",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )
    solar_calls: list[dict[str, object]] = []

    def fake_calculate_solar_system_body(**kwargs: object) -> SimpleNamespace:
        solar_calls.append(kwargs)
        return solar_results[len(solar_calls) - 1]

    monkeypatch.setattr(sky_map_module, "SOLAR_SYSTEM_BODIES", ("mars", "venus"))
    monkeypatch.setattr(
        sky_map_module,
        "calculate_solar_system_body",
        fake_calculate_solar_system_body,
    )

    points = calculate_sky_map_points(
        latitude_deg=-33.8688,
        longitude_deg=151.2093,
        elevation_m=58.0,
        timezone_name="Australia/Sydney",
        local_date=date(2024, 6, 1),
        local_time=time(5, 15),
        minimum_altitude_degrees=33.0,
        include_catalog_objects=False,
        include_solar_system_objects=True,
    )

    assert solar_calls == [
        {
            "body": body,
            "latitude_deg": -33.8688,
            "longitude_deg": 151.2093,
            "elevation_m": 58.0,
            "timezone_name": "Australia/Sydney",
            "local_date": date(2024, 6, 1),
            "local_time": time(5, 15),
            "minimum_altitude_degrees": 33.0,
        }
        for body in ("mars", "venus")
    ]
    assert points == (
        SkyMapPoint(
            object_key="mars",
            category="solar_system",
            altitude_degrees=30.0,
            azimuth_degrees=90.0,
            radial_distance_degrees=60.0,
            cardinal_direction="east",
            status="observable",
            is_above_horizon=True,
        ),
        SkyMapPoint(
            object_key="venus",
            category="solar_system",
            altitude_degrees=-20.0,
            azimuth_degrees=270.0,
            radial_distance_degrees=110.0,
            cardinal_direction="west",
            status="below_horizon",
            is_above_horizon=False,
        ),
    )


def test_clean_sky_map_import_does_not_load_plotly_or_visuals() -> None:
    script = """
import importlib.abc
import sys

sys.path.insert(0, sys.argv[1])

class RejectPlotly(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "plotly" or fullname.startswith("plotly."):
            raise AssertionError(f"Unexpected Plotly import: {fullname}")
        return None

sys.meta_path.insert(0, RejectPlotly())

from astroscope.sky_map import (
    SkyMapPoint,
    SkyObjectCategory,
    altitude_to_radial_distance,
    calculate_sky_map_points,
)

assert SkyMapPoint
assert SkyObjectCategory
assert altitude_to_radial_distance
assert calculate_sky_map_points
assert not any(name == "plotly" or name.startswith("plotly.") for name in sys.modules)
assert "astroscope.sky_map_visuals" not in sys.modules
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(REPOSITORY_ROOT / "src")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
