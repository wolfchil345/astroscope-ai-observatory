"""Tests for Gaia catalogue visualizations and exports."""

import csv
from io import StringIO
from math import cos, radians

import pytest

from astroscope.gaia_catalog import GaiaSource
from astroscope.gaia_export import gaia_sources_to_csv
from astroscope.gaia_visuals import (
    GaiaChartLabels,
    calculate_local_offsets_deg,
    create_hr_diagram,
    create_local_sky_figure,
    create_proper_motion_figure,
)


def create_labels() -> GaiaChartLabels:
    """Create deterministic English chart labels."""

    return GaiaChartLabels(
        local_sky_title="Local sky",
        hr_diagram_title="Colour-magnitude diagram",
        proper_motion_title="Proper motion",
        ra_offset="RA offset",
        dec_offset="Dec offset",
        color_index="BP-RP",
        absolute_g="Absolute G",
        pmra="pmRA",
        pmdec="pmDec",
        designation="Designation",
        source_id="Source ID",
        g_magnitude="G magnitude",
        angular_distance="Angular distance",
        naive_distance="Naive distance",
        catalog_sources="Gaia sources",
        missing_color="Missing colour",
        no_data="No valid data.",
    )


def create_source(
    *,
    source_id: int,
    ra_deg: float,
    dec_deg: float,
    g_magnitude: float | None = 12.0,
    bp_rp: float | None = 1.0,
    pmra: float | None = 5.0,
    pmdec: float | None = 4.0,
    total_motion: float | None = 6.403,
    absolute_g: float | None = 5.0,
) -> GaiaSource:
    """Create one deterministic Gaia source."""

    return GaiaSource(
        source_id=source_id,
        designation=f"Gaia DR3 {source_id}",
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        angular_distance_deg=0.01,
        parallax_mas=5.0,
        parallax_error_mas=0.5,
        parallax_snr=10.0,
        pmra_mas_per_year=pmra,
        pmdec_mas_per_year=pmdec,
        proper_motion_total_mas_per_year=(total_motion),
        phot_g_mean_mag=g_magnitude,
        phot_bp_mean_mag=12.5,
        phot_rp_mean_mag=11.5,
        bp_rp_mag=bp_rp,
        radial_velocity_km_per_s=20.0,
        effective_temperature_k=5500.0,
        naive_distance_parsecs=200.0,
        absolute_g_magnitude=absolute_g,
    )


def test_local_offsets_handle_ra_wraparound() -> None:
    source = create_source(
        source_id=1,
        ra_deg=0.1,
        dec_deg=10.0,
    )

    ra_offset, dec_offset = calculate_local_offsets_deg(
        source,
        center_ra_deg=359.9,
        center_dec_deg=10.0,
    )

    expected_ra = 0.2 * cos(radians(10.0))

    assert ra_offset == pytest.approx(expected_ra)

    assert dec_offset == pytest.approx(0.0)


def test_local_sky_figure_reverses_ra_axis() -> None:
    source = create_source(
        source_id=1,
        ra_deg=83.82,
        dec_deg=-5.39,
    )

    figure = create_local_sky_figure(
        (source,),
        center_ra_deg=83.82,
        center_dec_deg=-5.39,
        labels=create_labels(),
    )

    assert len(figure.data) == 1
    assert figure.layout.xaxis.autorange == "reversed"
    assert figure.layout.yaxis.scaleanchor == "x"


def test_hr_diagram_filters_incomplete_sources() -> None:
    valid_source = create_source(
        source_id=1,
        ra_deg=83.82,
        dec_deg=-5.39,
    )

    invalid_source = create_source(
        source_id=2,
        ra_deg=83.83,
        dec_deg=-5.38,
        absolute_g=None,
    )

    figure = create_hr_diagram(
        (
            valid_source,
            invalid_source,
        ),
        labels=create_labels(),
    )

    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 1
    assert figure.layout.yaxis.autorange == "reversed"


def test_proper_motion_figure_contains_vectors() -> None:
    sources = (
        create_source(
            source_id=1,
            ra_deg=83.82,
            dec_deg=-5.39,
        ),
        create_source(
            source_id=2,
            ra_deg=83.83,
            dec_deg=-5.38,
            pmra=10.0,
            pmdec=8.0,
            total_motion=12.806,
        ),
    )

    figure = create_proper_motion_figure(
        sources,
        labels=create_labels(),
    )

    assert len(figure.data) == 2
    assert len(figure.data[1].x) == 2
    assert figure.layout.yaxis.scaleanchor == "x"


def test_gaia_csv_export_contains_sources() -> None:
    source = create_source(
        source_id=123,
        ra_deg=83.82,
        dec_deg=-5.39,
    )

    csv_text = gaia_sources_to_csv((source,))

    rows = list(csv.DictReader(StringIO(csv_text)))

    assert len(rows) == 1
    assert rows[0]["source_id"] == "123"

    assert rows[0]["designation"] == "Gaia DR3 123"


def test_empty_charts_contain_explanation() -> None:
    labels = create_labels()

    local_figure = create_local_sky_figure(
        (),
        center_ra_deg=83.82,
        center_dec_deg=-5.39,
        labels=labels,
    )

    hr_figure = create_hr_diagram(
        (),
        labels=labels,
    )

    motion_figure = create_proper_motion_figure(
        (),
        labels=labels,
    )

    assert len(local_figure.layout.annotations) == 1
    assert len(hr_figure.layout.annotations) == 1
    assert len(motion_figure.layout.annotations) == 1
