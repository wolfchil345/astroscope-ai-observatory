"""Interactive local sky-map calculations."""

from dataclasses import dataclass
from datetime import date, time
from typing import Literal

from astroscope.coordinates import CELESTIAL_PRESETS
from astroscope.solar_system import (
    SOLAR_SYSTEM_BODIES,
    calculate_solar_system_body,
)
from astroscope.visibility import (
    VisibilityStatus,
    calculate_horizontal_coordinates,
)

_LEGACY_VISUAL_NAMES = frozenset(
    {
        "SkyMapLabels",
        "create_sky_map_figure",
    }
)


def __getattr__(name: str) -> object:
    """Resolve the two legacy visualization imports without eager Plotly loading."""

    if name in _LEGACY_VISUAL_NAMES:
        from astroscope import sky_map_visuals

        return getattr(sky_map_visuals, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

SkyObjectCategory = Literal["catalog", "solar_system"]


@dataclass(frozen=True, slots=True)
class SkyMapPoint:
    """One celestial object plotted in the observer's local sky."""

    object_key: str
    category: SkyObjectCategory
    altitude_degrees: float
    azimuth_degrees: float
    radial_distance_degrees: float
    cardinal_direction: str
    status: VisibilityStatus
    is_above_horizon: bool


def altitude_to_radial_distance(
    altitude_degrees: float,
) -> float:
    """Convert altitude into distance from the chart centre."""

    if not -90.0 <= altitude_degrees <= 90.0:
        raise ValueError("Altitude must be between -90 and 90 degrees.")

    return 90.0 - altitude_degrees


def calculate_sky_map_points(
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    timezone_name: str,
    local_date: date,
    local_time: time,
    minimum_altitude_degrees: float = 20.0,
    include_catalog_objects: bool = True,
    include_solar_system_objects: bool = True,
) -> tuple[SkyMapPoint, ...]:
    """Calculate local sky positions for all selected object groups."""

    points: list[SkyMapPoint] = []

    if include_catalog_objects:
        for object_key, preset in CELESTIAL_PRESETS.items():
            result = calculate_horizontal_coordinates(
                right_ascension=preset.right_ascension,
                declination=preset.declination,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            points.append(
                SkyMapPoint(
                    object_key=object_key,
                    category="catalog",
                    altitude_degrees=result.altitude_degrees,
                    azimuth_degrees=result.azimuth_degrees,
                    radial_distance_degrees=(altitude_to_radial_distance(result.altitude_degrees)),
                    cardinal_direction=(result.cardinal_direction),
                    status=result.status,
                    is_above_horizon=(result.is_above_horizon),
                )
            )

    if include_solar_system_objects:
        for body_key in SOLAR_SYSTEM_BODIES:
            result = calculate_solar_system_body(
                body=body_key,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                timezone_name=timezone_name,
                local_date=local_date,
                local_time=local_time,
                minimum_altitude_degrees=(minimum_altitude_degrees),
            )

            points.append(
                SkyMapPoint(
                    object_key=body_key,
                    category="solar_system",
                    altitude_degrees=result.altitude_degrees,
                    azimuth_degrees=result.azimuth_degrees,
                    radial_distance_degrees=(altitude_to_radial_distance(result.altitude_degrees)),
                    cardinal_direction=(result.cardinal_direction),
                    status=result.status,
                    is_above_horizon=(result.is_above_horizon),
                )
            )

    return tuple(points)
