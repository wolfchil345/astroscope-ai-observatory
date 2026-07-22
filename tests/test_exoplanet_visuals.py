"""Tests for exoplanet exports and scientific plots."""

import csv
from io import StringIO

import pytest

from astroscope.exoplanet_catalog import (
    ExoplanetRecord,
    TemperateStatus,
)
from astroscope.exoplanet_export import (
    exoplanets_to_csv,
)
from astroscope.exoplanet_visuals import (
    ExoplanetChartLabels,
    calculate_trapezoid_transit_flux,
    create_climate_figure,
    create_mass_radius_figure,
    create_radius_period_figure,
    create_transit_simulation_figure,
)


def create_labels() -> ExoplanetChartLabels:
    """Create deterministic English chart labels."""

    return ExoplanetChartLabels(
        radius_period_title="Radius and period",
        mass_radius_title="Mass and radius",
        climate_title="Temperature and insolation",
        transit_title="Transit simulation",
        orbital_period="Orbital period",
        radius="Planet radius",
        mass="Planet mass",
        equilibrium_temperature=("Equilibrium temperature"),
        insolation="Insolation",
        transit_time="Time",
        relative_flux="Relative flux",
        planet_name="Planet",
        host_name="Host",
        discovery_method="Discovery method",
        temperate_status="Temperate status",
        simulated_transit="Simulated transit",
        no_data="No valid data.",
    )


def status_names() -> dict[TemperateStatus, str]:
    """Create deterministic status labels."""

    return {
        "temperate_terrestrial_candidate": ("Temperate terrestrial candidate"),
        "temperate_non_terrestrial": ("Temperate non-terrestrial"),
        "outside_temperate_range": ("Outside temperate range"),
        "insufficient_data": "Insufficient data",
    }


def create_planet(
    *,
    planet_name: str,
    radius_earth: float | None = 1.2,
    mass_earth: float | None = 2.0,
    orbital_period_days: float | None = 100.0,
    equilibrium_temperature_k: float | None = 250.0,
    insolation_earth: float | None = 1.0,
    status: TemperateStatus = ("temperate_terrestrial_candidate"),
) -> ExoplanetRecord:
    """Create one deterministic planet record."""

    return ExoplanetRecord(
        planet_name=planet_name,
        hostname=f"{planet_name} host",
        discovery_method="Transit",
        discovery_year=2020,
        is_transiting=True,
        orbital_period_days=orbital_period_days,
        semi_major_axis_au=0.5,
        radius_earth=radius_earth,
        mass_earth=mass_earth,
        equilibrium_temperature_k=(equilibrium_temperature_k),
        insolation_earth=insolation_earth,
        eccentricity=0.05,
        stellar_temperature_k=5000.0,
        stellar_radius_solar=0.8,
        stellar_mass_solar=0.8,
        distance_pc=50.0,
        system_planet_count=2,
        ra_deg=100.0,
        dec_deg=20.0,
        density_g_cm3=4.0,
        transit_depth_ppm=200.0,
        transit_probability_percent=2.0,
        temperate_status=status,
    )


def test_csv_export_contains_planet() -> None:
    planet = create_planet(planet_name="Test Planet b")

    csv_text = exoplanets_to_csv((planet,))

    rows = list(csv.DictReader(StringIO(csv_text)))

    assert len(rows) == 1

    assert rows[0]["planet_name"] == "Test Planet b"

    assert rows[0]["radius_earth"] == "1.2"

    assert rows[0]["temperate_status"] == "temperate_terrestrial_candidate"


def test_radius_period_figure_uses_log_axes() -> None:
    figure = create_radius_period_figure(
        (create_planet(planet_name="Planet A"),),
        labels=create_labels(),
        status_names=status_names(),
    )

    assert len(figure.data) == 1
    assert figure.layout.xaxis.type == "log"
    assert figure.layout.yaxis.type == "log"


def test_mass_radius_figure_filters_missing_mass() -> None:
    valid_planet = create_planet(planet_name="Planet A")

    incomplete_planet = create_planet(
        planet_name="Planet B",
        mass_earth=None,
    )

    figure = create_mass_radius_figure(
        (
            valid_planet,
            incomplete_planet,
        ),
        labels=create_labels(),
        status_names=status_names(),
    )

    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 1


def test_climate_figure_filters_missing_values() -> None:
    valid_planet = create_planet(planet_name="Planet A")

    incomplete_planet = create_planet(
        planet_name="Planet B",
        insolation_earth=None,
    )

    figure = create_climate_figure(
        (
            valid_planet,
            incomplete_planet,
        ),
        labels=create_labels(),
        status_names=status_names(),
    )

    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 1
    assert figure.layout.xaxis.type == "log"


def test_empty_population_figures_explain_missing_data() -> None:
    labels = create_labels()
    names = status_names()

    radius_period = create_radius_period_figure(
        (),
        labels=labels,
        status_names=names,
    )

    mass_radius = create_mass_radius_figure(
        (),
        labels=labels,
        status_names=names,
    )

    climate = create_climate_figure(
        (),
        labels=labels,
        status_names=names,
    )

    assert len(radius_period.layout.annotations) == 1

    assert len(mass_radius.layout.annotations) == 1

    assert len(climate.layout.annotations) == 1


def test_trapezoid_transit_flux() -> None:
    flux_values = calculate_trapezoid_transit_flux(
        (-2.0, -1.0, 0.0, 1.0, 2.0),
        depth_ppm=1000.0,
        duration_hours=2.0,
        ingress_fraction=0.2,
    )

    assert flux_values[0] == pytest.approx(1.0)
    assert flux_values[2] == pytest.approx(0.999)
    assert flux_values[-1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("depth_ppm", 0.0),
        ("duration_hours", 0.0),
        ("ingress_fraction", 0.0),
        ("ingress_fraction", 0.5),
    ],
)
def test_invalid_transit_values_raise(
    field: str,
    value: float,
) -> None:
    arguments = {
        "depth_ppm": 1000.0,
        "duration_hours": 2.0,
        "ingress_fraction": 0.2,
    }

    arguments[field] = value

    with pytest.raises(ValueError):
        calculate_trapezoid_transit_flux(
            (0.0,),
            **arguments,
        )


def test_transit_figure_contains_light_curve() -> None:
    figure = create_transit_simulation_figure(
        depth_ppm=500.0,
        duration_hours=3.0,
        ingress_fraction=0.15,
        labels=create_labels(),
    )

    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 301

    minimum_flux = min(figure.data[0].y)

    assert minimum_flux == pytest.approx(0.9995)
