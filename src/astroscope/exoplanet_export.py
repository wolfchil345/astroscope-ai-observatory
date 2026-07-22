"""CSV export helpers for exoplanet catalogue records."""

import csv
from collections.abc import Iterable
from io import StringIO
from typing import Final

from astroscope.exoplanet_catalog import ExoplanetRecord

EXOPLANET_CSV_FIELDS: Final[tuple[str, ...]] = (
    "planet_name",
    "hostname",
    "discovery_method",
    "discovery_year",
    "is_transiting",
    "orbital_period_days",
    "semi_major_axis_au",
    "radius_earth",
    "mass_earth",
    "equilibrium_temperature_k",
    "insolation_earth",
    "eccentricity",
    "stellar_temperature_k",
    "stellar_radius_solar",
    "stellar_mass_solar",
    "distance_pc",
    "system_planet_count",
    "ra_deg",
    "dec_deg",
    "density_g_cm3",
    "transit_depth_ppm",
    "transit_probability_percent",
    "temperate_status",
)


def _csv_value(value: object | None) -> object:
    """Convert optional values into CSV-compatible values."""

    if value is None:
        return ""

    return value


def exoplanets_to_csv(
    planets: Iterable[ExoplanetRecord],
) -> str:
    """Export exoplanet records as UTF-8 CSV text."""

    output = StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=EXOPLANET_CSV_FIELDS,
        lineterminator="\n",
    )

    writer.writeheader()

    for planet in planets:
        writer.writerow(
            {
                "planet_name": planet.planet_name,
                "hostname": planet.hostname,
                "discovery_method": planet.discovery_method,
                "discovery_year": _csv_value(planet.discovery_year),
                "is_transiting": planet.is_transiting,
                "orbital_period_days": _csv_value(planet.orbital_period_days),
                "semi_major_axis_au": _csv_value(planet.semi_major_axis_au),
                "radius_earth": _csv_value(planet.radius_earth),
                "mass_earth": _csv_value(planet.mass_earth),
                "equilibrium_temperature_k": _csv_value(planet.equilibrium_temperature_k),
                "insolation_earth": _csv_value(planet.insolation_earth),
                "eccentricity": _csv_value(planet.eccentricity),
                "stellar_temperature_k": _csv_value(planet.stellar_temperature_k),
                "stellar_radius_solar": _csv_value(planet.stellar_radius_solar),
                "stellar_mass_solar": _csv_value(planet.stellar_mass_solar),
                "distance_pc": _csv_value(planet.distance_pc),
                "system_planet_count": _csv_value(planet.system_planet_count),
                "ra_deg": _csv_value(planet.ra_deg),
                "dec_deg": _csv_value(planet.dec_deg),
                "density_g_cm3": _csv_value(planet.density_g_cm3),
                "transit_depth_ppm": _csv_value(planet.transit_depth_ppm),
                "transit_probability_percent": _csv_value(planet.transit_probability_percent),
                "temperate_status": planet.temperate_status,
            }
        )

    return output.getvalue()
