"""CSV exports for Gaia catalogue search results."""

import csv
from collections.abc import Iterable
from io import StringIO
from typing import Final

from astroscope.gaia_catalog import GaiaSource

GAIA_CSV_FIELDS: Final[tuple[str, ...]] = (
    "source_id",
    "designation",
    "ra_deg",
    "dec_deg",
    "angular_distance_deg",
    "parallax_mas",
    "parallax_error_mas",
    "parallax_snr",
    "pmra_mas_per_year",
    "pmdec_mas_per_year",
    "proper_motion_total_mas_per_year",
    "phot_g_mean_mag",
    "phot_bp_mean_mag",
    "phot_rp_mean_mag",
    "bp_rp_mag",
    "radial_velocity_km_per_s",
    "effective_temperature_k",
    "naive_distance_parsecs",
    "absolute_g_magnitude",
)


def _csv_value(value: object | None) -> object:
    """Convert optional values into CSV-safe values."""

    if value is None:
        return ""

    return value


def gaia_sources_to_csv(
    sources: Iterable[GaiaSource],
) -> str:
    """Export Gaia sources as UTF-8 CSV text."""

    output = StringIO(newline="")

    writer = csv.DictWriter(
        output,
        fieldnames=GAIA_CSV_FIELDS,
        lineterminator="\n",
    )

    writer.writeheader()

    for source in sources:
        writer.writerow(
            {
                "source_id": source.source_id,
                "designation": source.designation,
                "ra_deg": source.ra_deg,
                "dec_deg": source.dec_deg,
                "angular_distance_deg": (source.angular_distance_deg),
                "parallax_mas": _csv_value(source.parallax_mas),
                "parallax_error_mas": _csv_value(source.parallax_error_mas),
                "parallax_snr": _csv_value(source.parallax_snr),
                "pmra_mas_per_year": _csv_value(source.pmra_mas_per_year),
                "pmdec_mas_per_year": _csv_value(source.pmdec_mas_per_year),
                "proper_motion_total_mas_per_year": (
                    _csv_value(source.proper_motion_total_mas_per_year)
                ),
                "phot_g_mean_mag": _csv_value(source.phot_g_mean_mag),
                "phot_bp_mean_mag": _csv_value(source.phot_bp_mean_mag),
                "phot_rp_mean_mag": _csv_value(source.phot_rp_mean_mag),
                "bp_rp_mag": _csv_value(source.bp_rp_mag),
                "radial_velocity_km_per_s": (_csv_value(source.radial_velocity_km_per_s)),
                "effective_temperature_k": (_csv_value(source.effective_temperature_k)),
                "naive_distance_parsecs": (_csv_value(source.naive_distance_parsecs)),
                "absolute_g_magnitude": (_csv_value(source.absolute_g_magnitude)),
            }
        )

    return output.getvalue()
