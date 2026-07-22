"""Interactive visualizations for Gaia catalogue sources."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import cos, isfinite, radians

import plotly.graph_objects as go

from astroscope.gaia_catalog import GaiaSource


@dataclass(frozen=True, slots=True)
class GaiaChartLabels:
    """Translated labels used by Gaia charts."""

    local_sky_title: str
    hr_diagram_title: str
    proper_motion_title: str
    ra_offset: str
    dec_offset: str
    color_index: str
    absolute_g: str
    pmra: str
    pmdec: str
    designation: str
    source_id: str
    g_magnitude: str
    angular_distance: str
    naive_distance: str
    catalog_sources: str
    missing_color: str
    no_data: str


def _validate_center(
    center_ra_deg: float,
    center_dec_deg: float,
) -> None:
    """Validate a chart centre."""

    if not isfinite(center_ra_deg) or not 0.0 <= center_ra_deg < 360.0:
        raise ValueError("Chart right ascension must be at least 0 and below 360 degrees.")

    if not isfinite(center_dec_deg) or not -90.0 <= center_dec_deg <= 90.0:
        raise ValueError("Chart declination must be between -90 and 90 degrees.")


def calculate_local_offsets_deg(
    source: GaiaSource,
    *,
    center_ra_deg: float,
    center_dec_deg: float,
) -> tuple[float, float]:
    """Calculate small-field RA and Dec offsets."""

    _validate_center(
        center_ra_deg,
        center_dec_deg,
    )

    delta_ra = ((source.ra_deg - center_ra_deg + 180.0) % 360.0) - 180.0

    ra_offset = delta_ra * cos(radians(center_dec_deg))

    dec_offset = source.dec_deg - center_dec_deg

    return ra_offset, dec_offset


def _marker_size(
    source: GaiaSource,
) -> float:
    """Return a display marker size from G magnitude."""

    magnitude = source.phot_g_mean_mag

    if magnitude is None:
        return 6.0

    size = 24.0 - 1.2 * (magnitude - 5.0)

    return max(
        6.0,
        min(24.0, size),
    )


def _display_number(
    value: float | None,
    *,
    digits: int,
    suffix: str = "",
) -> str:
    """Format one optional chart value."""

    if value is None:
        return "N/A"

    return f"{value:.{digits}f}{suffix}"


def _source_customdata(
    source: GaiaSource,
) -> list[object]:
    """Create shared Plotly hover data."""

    return [
        source.designation,
        source.source_id,
        _display_number(
            source.phot_g_mean_mag,
            digits=3,
        ),
        _display_number(
            source.bp_rp_mag,
            digits=3,
        ),
        _display_number(
            source.angular_distance_deg * 60.0,
            digits=3,
            suffix=" arcmin",
        ),
        _display_number(
            source.naive_distance_parsecs,
            digits=2,
            suffix=" pc",
        ),
    ]


def _hover_template(
    labels: GaiaChartLabels,
) -> str:
    """Return shared source hover text."""

    return (
        "<b>%{customdata[0]}</b><br>"
        f"{labels.source_id}: "
        "%{customdata[1]}<br>"
        f"{labels.g_magnitude}: "
        "%{customdata[2]}<br>"
        f"{labels.color_index}: "
        "%{customdata[3]}<br>"
        f"{labels.angular_distance}: "
        "%{customdata[4]}<br>"
        f"{labels.naive_distance}: "
        "%{customdata[5]}"
        "<extra></extra>"
    )


def _empty_figure(
    *,
    title: str,
    message: str,
) -> go.Figure:
    """Create an empty chart with an explanation."""

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
        height=550,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={
            "l": 40,
            "r": 40,
            "t": 80,
            "b": 40,
        },
    )

    return figure


def _add_local_sky_trace(
    figure: go.Figure,
    *,
    sources: Sequence[GaiaSource],
    center_ra_deg: float,
    center_dec_deg: float,
    labels: GaiaChartLabels,
    use_color_scale: bool,
) -> None:
    """Add one collection of sky markers."""

    x_values: list[float] = []
    y_values: list[float] = []

    for source in sources:
        x_value, y_value = calculate_local_offsets_deg(
            source,
            center_ra_deg=center_ra_deg,
            center_dec_deg=center_dec_deg,
        )

        x_values.append(x_value)
        y_values.append(y_value)

    marker: dict[str, object] = {
        "size": [_marker_size(source) for source in sources],
        "opacity": 0.85,
        "line": {
            "width": 0.5,
        },
    }

    trace_name = labels.missing_color

    if use_color_scale:
        marker.update(
            {
                "color": [source.bp_rp_mag for source in sources],
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {
                    "title": labels.color_index,
                },
            }
        )

        trace_name = labels.catalog_sources

    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers",
            name=trace_name,
            marker=marker,
            customdata=[_source_customdata(source) for source in sources],
            hovertemplate=_hover_template(labels),
        )
    )


def create_local_sky_figure(
    sources: Sequence[GaiaSource],
    *,
    center_ra_deg: float,
    center_dec_deg: float,
    labels: GaiaChartLabels,
) -> go.Figure:
    """Create a small-field Gaia sky chart."""

    _validate_center(
        center_ra_deg,
        center_dec_deg,
    )

    if not sources:
        return _empty_figure(
            title=labels.local_sky_title,
            message=labels.no_data,
        )

    sources_with_color = tuple(source for source in sources if source.bp_rp_mag is not None)

    sources_without_color = tuple(source for source in sources if source.bp_rp_mag is None)

    figure = go.Figure()

    if sources_with_color:
        _add_local_sky_trace(
            figure,
            sources=sources_with_color,
            center_ra_deg=center_ra_deg,
            center_dec_deg=center_dec_deg,
            labels=labels,
            use_color_scale=True,
        )

    if sources_without_color:
        _add_local_sky_trace(
            figure,
            sources=sources_without_color,
            center_ra_deg=center_ra_deg,
            center_dec_deg=center_dec_deg,
            labels=labels,
            use_color_scale=False,
        )

    figure.update_layout(
        title=labels.local_sky_title,
        height=650,
        xaxis={
            "title": labels.ra_offset,
            "autorange": "reversed",
            "zeroline": True,
        },
        yaxis={
            "title": labels.dec_offset,
            "scaleanchor": "x",
            "scaleratio": 1,
            "zeroline": True,
        },
        margin={
            "l": 55,
            "r": 55,
            "t": 85,
            "b": 55,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
        },
    )

    return figure


def create_hr_diagram(
    sources: Sequence[GaiaSource],
    *,
    labels: GaiaChartLabels,
) -> go.Figure:
    """Create a Gaia colour–magnitude diagram."""

    valid_sources = tuple(
        source
        for source in sources
        if (source.bp_rp_mag is not None and source.absolute_g_magnitude is not None)
    )

    if not valid_sources:
        return _empty_figure(
            title=labels.hr_diagram_title,
            message=labels.no_data,
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=[source.bp_rp_mag for source in valid_sources],
            y=[source.absolute_g_magnitude for source in valid_sources],
            mode="markers",
            name=labels.catalog_sources,
            marker={
                "size": [_marker_size(source) for source in valid_sources],
                "color": [source.bp_rp_mag for source in valid_sources],
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {
                    "title": labels.color_index,
                },
                "opacity": 0.85,
            },
            customdata=[_source_customdata(source) for source in valid_sources],
            hovertemplate=_hover_template(labels),
        )
    )

    figure.update_layout(
        title=labels.hr_diagram_title,
        height=650,
        xaxis={
            "title": labels.color_index,
            "zeroline": True,
        },
        yaxis={
            "title": labels.absolute_g,
            "autorange": "reversed",
            "zeroline": True,
        },
        margin={
            "l": 60,
            "r": 55,
            "t": 85,
            "b": 55,
        },
        showlegend=False,
    )

    return figure


def create_proper_motion_figure(
    sources: Sequence[GaiaSource],
    *,
    labels: GaiaChartLabels,
    maximum_sources: int = 100,
) -> go.Figure:
    """Create a proper-motion vector diagram."""

    if (
        isinstance(maximum_sources, bool)
        or not isinstance(maximum_sources, int)
        or not 1 <= maximum_sources <= 500
    ):
        raise ValueError("Maximum proper-motion source count must be between 1 and 500.")

    valid_sources = tuple(
        source
        for source in sources
        if (source.pmra_mas_per_year is not None and source.pmdec_mas_per_year is not None)
    )

    selected_sources = tuple(
        sorted(
            valid_sources,
            key=lambda source: source.proper_motion_total_mas_per_year or 0.0,
            reverse=True,
        )[:maximum_sources]
    )

    if not selected_sources:
        return _empty_figure(
            title=labels.proper_motion_title,
            message=labels.no_data,
        )

    line_x: list[float | None] = []
    line_y: list[float | None] = []

    for source in selected_sources:
        line_x.extend(
            [
                0.0,
                source.pmra_mas_per_year,
                None,
            ]
        )

        line_y.extend(
            [
                0.0,
                source.pmdec_mas_per_year,
                None,
            ]
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            name=labels.proper_motion_title,
            hoverinfo="skip",
            showlegend=False,
        )
    )

    figure.add_trace(
        go.Scatter(
            x=[source.pmra_mas_per_year for source in selected_sources],
            y=[source.pmdec_mas_per_year for source in selected_sources],
            mode="markers",
            name=labels.catalog_sources,
            marker={
                "size": [_marker_size(source) for source in selected_sources],
                "opacity": 0.85,
            },
            customdata=[
                [
                    source.designation,
                    source.source_id,
                    _display_number(
                        source.proper_motion_total_mas_per_year,
                        digits=3,
                        suffix=" mas/yr",
                    ),
                ]
                for source in selected_sources
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                f"{labels.source_id}: "
                "%{customdata[1]}<br>"
                f"{labels.proper_motion_title}: "
                "%{customdata[2]}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title=labels.proper_motion_title,
        height=650,
        xaxis={
            "title": labels.pmra,
            "zeroline": True,
        },
        yaxis={
            "title": labels.pmdec,
            "zeroline": True,
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        margin={
            "l": 60,
            "r": 55,
            "t": 85,
            "b": 55,
        },
        showlegend=False,
    )

    return figure
