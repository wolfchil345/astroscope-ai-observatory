"""Plotly visualizations for exoplanet catalogue records."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite, sqrt

import plotly.graph_objects as go

from astroscope.exoplanet_catalog import (
    ExoplanetRecord,
    TemperateStatus,
)


@dataclass(frozen=True, slots=True)
class ExoplanetChartLabels:
    """Translated labels used by exoplanet charts."""

    radius_period_title: str
    mass_radius_title: str
    climate_title: str
    transit_title: str
    orbital_period: str
    radius: str
    mass: str
    equilibrium_temperature: str
    insolation: str
    transit_time: str
    relative_flux: str
    planet_name: str
    host_name: str
    discovery_method: str
    temperate_status: str
    simulated_transit: str
    no_data: str


STATUS_ORDER: tuple[TemperateStatus, ...] = (
    "temperate_terrestrial_candidate",
    "temperate_non_terrestrial",
    "outside_temperate_range",
    "insufficient_data",
)


def _display_number(
    value: float | None,
    *,
    digits: int,
    suffix: str = "",
) -> str:
    """Format one optional value for Plotly hover text."""

    if value is None:
        return "N/A"

    return f"{value:.{digits}f}{suffix}"


def _marker_size(
    planet: ExoplanetRecord,
) -> float:
    """Calculate a bounded marker size from planet radius."""

    radius = planet.radius_earth

    if radius is None or radius <= 0.0:
        return 8.0

    size = 7.0 + 3.0 * sqrt(radius)

    return max(7.0, min(26.0, size))


def _source_customdata(
    planet: ExoplanetRecord,
) -> list[object]:
    """Build common Plotly hover information."""

    return [
        planet.planet_name,
        planet.hostname,
        planet.discovery_method or "N/A",
        planet.temperate_status,
        _display_number(
            planet.orbital_period_days,
            digits=4,
            suffix=" d",
        ),
        _display_number(
            planet.radius_earth,
            digits=3,
            suffix=" R⊕",
        ),
        _display_number(
            planet.mass_earth,
            digits=3,
            suffix=" M⊕",
        ),
        _display_number(
            planet.equilibrium_temperature_k,
            digits=1,
            suffix=" K",
        ),
        _display_number(
            planet.insolation_earth,
            digits=3,
            suffix=" S⊕",
        ),
    ]


def _hover_template(
    labels: ExoplanetChartLabels,
) -> str:
    """Return shared hover text for population plots."""

    return (
        "<b>%{customdata[0]}</b><br>"
        f"{labels.host_name}: "
        "%{customdata[1]}<br>"
        f"{labels.discovery_method}: "
        "%{customdata[2]}<br>"
        f"{labels.temperate_status}: "
        "%{customdata[3]}<br>"
        f"{labels.orbital_period}: "
        "%{customdata[4]}<br>"
        f"{labels.radius}: "
        "%{customdata[5]}<br>"
        f"{labels.mass}: "
        "%{customdata[6]}<br>"
        f"{labels.equilibrium_temperature}: "
        "%{customdata[7]}<br>"
        f"{labels.insolation}: "
        "%{customdata[8]}"
        "<extra></extra>"
    )


def _empty_figure(
    *,
    title: str,
    message: str,
) -> go.Figure:
    """Create an explanatory empty Plotly figure."""

    figure = go.Figure()

    figure.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=message,
        showarrow=False,
    )

    figure.update_layout(
        title=title,
        height=560,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={
            "l": 45,
            "r": 45,
            "t": 80,
            "b": 45,
        },
    )

    return figure


def _group_by_status(
    planets: Sequence[ExoplanetRecord],
) -> dict[TemperateStatus, tuple[ExoplanetRecord, ...]]:
    """Group planets using a deterministic status order."""

    return {
        status: tuple(planet for planet in planets if planet.temperate_status == status)
        for status in STATUS_ORDER
    }


def create_radius_period_figure(
    planets: Sequence[ExoplanetRecord],
    *,
    labels: ExoplanetChartLabels,
    status_names: dict[TemperateStatus, str],
) -> go.Figure:
    """Create a planet-radius versus orbital-period diagram."""

    valid_planets = tuple(
        planet
        for planet in planets
        if (
            planet.orbital_period_days is not None
            and planet.orbital_period_days > 0.0
            and planet.radius_earth is not None
            and planet.radius_earth > 0.0
        )
    )

    if not valid_planets:
        return _empty_figure(
            title=labels.radius_period_title,
            message=labels.no_data,
        )

    figure = go.Figure()

    for status, group in _group_by_status(valid_planets).items():
        if not group:
            continue

        figure.add_trace(
            go.Scatter(
                x=[planet.orbital_period_days for planet in group],
                y=[planet.radius_earth for planet in group],
                mode="markers",
                name=status_names[status],
                marker={
                    "size": [_marker_size(planet) for planet in group],
                    "opacity": 0.82,
                },
                customdata=[_source_customdata(planet) for planet in group],
                hovertemplate=_hover_template(labels),
            )
        )

    figure.update_layout(
        title=labels.radius_period_title,
        height=650,
        xaxis={
            "title": labels.orbital_period,
            "type": "log",
        },
        yaxis={
            "title": labels.radius,
            "type": "log",
        },
        margin={
            "l": 60,
            "r": 45,
            "t": 85,
            "b": 60,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
        },
    )

    return figure


def create_mass_radius_figure(
    planets: Sequence[ExoplanetRecord],
    *,
    labels: ExoplanetChartLabels,
    status_names: dict[TemperateStatus, str],
) -> go.Figure:
    """Create a planet-mass versus planet-radius diagram."""

    valid_planets = tuple(
        planet
        for planet in planets
        if (
            planet.mass_earth is not None
            and planet.mass_earth > 0.0
            and planet.radius_earth is not None
            and planet.radius_earth > 0.0
        )
    )

    if not valid_planets:
        return _empty_figure(
            title=labels.mass_radius_title,
            message=labels.no_data,
        )

    figure = go.Figure()

    for status, group in _group_by_status(valid_planets).items():
        if not group:
            continue

        figure.add_trace(
            go.Scatter(
                x=[planet.radius_earth for planet in group],
                y=[planet.mass_earth for planet in group],
                mode="markers",
                name=status_names[status],
                marker={
                    "size": [_marker_size(planet) for planet in group],
                    "opacity": 0.82,
                },
                customdata=[_source_customdata(planet) for planet in group],
                hovertemplate=_hover_template(labels),
            )
        )

    figure.update_layout(
        title=labels.mass_radius_title,
        height=650,
        xaxis={
            "title": labels.radius,
            "type": "log",
        },
        yaxis={
            "title": labels.mass,
            "type": "log",
        },
        margin={
            "l": 60,
            "r": 45,
            "t": 85,
            "b": 60,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
        },
    )

    return figure


def create_climate_figure(
    planets: Sequence[ExoplanetRecord],
    *,
    labels: ExoplanetChartLabels,
    status_names: dict[TemperateStatus, str],
) -> go.Figure:
    """Create an insolation versus equilibrium-temperature plot."""

    valid_planets = tuple(
        planet
        for planet in planets
        if (
            planet.insolation_earth is not None
            and planet.insolation_earth > 0.0
            and planet.equilibrium_temperature_k is not None
            and planet.equilibrium_temperature_k > 0.0
        )
    )

    if not valid_planets:
        return _empty_figure(
            title=labels.climate_title,
            message=labels.no_data,
        )

    figure = go.Figure()

    for status, group in _group_by_status(valid_planets).items():
        if not group:
            continue

        figure.add_trace(
            go.Scatter(
                x=[planet.insolation_earth for planet in group],
                y=[planet.equilibrium_temperature_k for planet in group],
                mode="markers",
                name=status_names[status],
                marker={
                    "size": [_marker_size(planet) for planet in group],
                    "opacity": 0.82,
                },
                customdata=[_source_customdata(planet) for planet in group],
                hovertemplate=_hover_template(labels),
            )
        )

    figure.update_layout(
        title=labels.climate_title,
        height=650,
        xaxis={
            "title": labels.insolation,
            "type": "log",
        },
        yaxis={
            "title": labels.equilibrium_temperature,
        },
        margin={
            "l": 60,
            "r": 45,
            "t": 85,
            "b": 60,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
        },
    )

    return figure


def calculate_trapezoid_transit_flux(
    time_hours: Sequence[float],
    *,
    depth_ppm: float,
    duration_hours: float,
    ingress_fraction: float = 0.15,
) -> tuple[float, ...]:
    """Calculate a simple symmetric trapezoidal transit model."""

    if not isfinite(depth_ppm) or depth_ppm <= 0.0:
        raise ValueError("Transit depth must be a positive finite value.")

    if not isfinite(duration_hours) or duration_hours <= 0.0:
        raise ValueError("Transit duration must be a positive finite value.")

    if not isfinite(ingress_fraction) or not 0.0 < ingress_fraction < 0.5:
        raise ValueError("Ingress fraction must be greater than 0 and below 0.5.")

    half_duration = duration_hours / 2.0
    ingress_duration = duration_hours * ingress_fraction

    flat_half_duration = half_duration - ingress_duration

    fractional_depth = depth_ppm / 1_000_000.0
    flux_values: list[float] = []

    for time_value in time_hours:
        if not isfinite(time_value):
            raise ValueError("Transit times must be finite.")

        absolute_time = abs(time_value)

        if absolute_time >= half_duration:
            depth_scale = 0.0
        elif absolute_time <= flat_half_duration:
            depth_scale = 1.0
        else:
            depth_scale = (half_duration - absolute_time) / ingress_duration

        flux_values.append(1.0 - fractional_depth * depth_scale)

    return tuple(flux_values)


def create_transit_simulation_figure(
    *,
    depth_ppm: float,
    duration_hours: float,
    ingress_fraction: float,
    labels: ExoplanetChartLabels,
    sample_count: int = 301,
) -> go.Figure:
    """Create an educational trapezoidal transit light curve."""

    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not 51 <= sample_count <= 5001
    ):
        raise ValueError("Transit sample count must be between 51 and 5001.")

    display_half_width = duration_hours * 0.9
    interval_count = sample_count - 1

    time_values = tuple(
        -display_half_width + (2.0 * display_half_width * index / interval_count)
        for index in range(sample_count)
    )

    flux_values = calculate_trapezoid_transit_flux(
        time_values,
        depth_ppm=depth_ppm,
        duration_hours=duration_hours,
        ingress_fraction=ingress_fraction,
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=time_values,
            y=flux_values,
            mode="lines",
            name=labels.simulated_transit,
            hovertemplate=(
                f"{labels.transit_time}: "
                "%{x:.3f} h<br>"
                f"{labels.relative_flux}: "
                "%{y:.7f}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title=labels.transit_title,
        height=520,
        xaxis={
            "title": labels.transit_time,
            "zeroline": True,
        },
        yaxis={
            "title": labels.relative_flux,
        },
        margin={
            "l": 70,
            "r": 45,
            "t": 85,
            "b": 60,
        },
        showlegend=False,
    )

    return figure
