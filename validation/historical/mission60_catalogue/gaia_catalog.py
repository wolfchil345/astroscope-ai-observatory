"""Gaia DR3 cone-search queries and catalogue calculations."""

import csv
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from io import StringIO
from math import hypot, isfinite, log10
from statistics import median
from typing import Any, Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GAIA_TAP_SYNC_URL: Final[str] = "https://gea.esac.esa.int/tap-server/tap/sync"
GAIA_SOURCE_TABLE: Final[str] = "gaiadr3.gaia_source"
DEFAULT_USER_AGENT: Final[str] = "AstroScope-AI-Observatory/1.0"


class GaiaCatalogError(ValueError):
    """Raised when catalogue input or returned data is invalid."""


class GaiaServiceError(RuntimeError):
    """Raised when the Gaia TAP service cannot return a query."""


def _validate_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite floating-point value."""

    if not isfinite(value):
        raise GaiaCatalogError(f"{label} must be finite.")


def _format_adql_number(value: float) -> str:
    """Format a validated number for an ADQL expression."""

    if value == 0.0:
        return "0"

    return format(value, ".12g")


@dataclass(frozen=True, slots=True)
class GaiaConeSearchRequest:
    """Validated parameters for one Gaia DR3 cone search."""

    center_ra_deg: float
    center_dec_deg: float
    radius_deg: float
    row_limit: int = 200
    maximum_g_magnitude: float | None = 16.0
    minimum_parallax_snr: float | None = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        _validate_finite(
            self.center_ra_deg,
            "Right ascension",
        )

        _validate_finite(
            self.center_dec_deg,
            "Declination",
        )

        _validate_finite(
            self.radius_deg,
            "Search radius",
        )

        _validate_finite(
            self.timeout_seconds,
            "Timeout",
        )

        if not 0.0 <= self.center_ra_deg < 360.0:
            raise GaiaCatalogError("Right ascension must be at least 0 and below 360 degrees.")

        if not -90.0 <= self.center_dec_deg <= 90.0:
            raise GaiaCatalogError("Declination must be between -90 and 90 degrees.")

        if not 0.0 < self.radius_deg <= 10.0:
            raise GaiaCatalogError("Search radius must be greater than 0 and at most 10 degrees.")

        if (
            isinstance(self.row_limit, bool)
            or not isinstance(self.row_limit, int)
            or not 1 <= self.row_limit <= 5000
        ):
            raise GaiaCatalogError("Row limit must be an integer between 1 and 5000.")

        if self.maximum_g_magnitude is not None:
            _validate_finite(
                self.maximum_g_magnitude,
                "Maximum G magnitude",
            )

        if self.minimum_parallax_snr is not None:
            _validate_finite(
                self.minimum_parallax_snr,
                ("Minimum parallax signal-to-noise ratio"),
            )

            if self.minimum_parallax_snr < 0.0:
                raise GaiaCatalogError("Minimum parallax signal-to-noise ratio cannot be negative.")

        if not 0.0 < self.timeout_seconds <= 120.0:
            raise GaiaCatalogError("Timeout must be greater than 0 and at most 120 seconds.")


@dataclass(frozen=True, slots=True)
class GaiaSource:
    """A compact application-friendly Gaia source."""

    source_id: int
    designation: str
    ra_deg: float
    dec_deg: float
    angular_distance_deg: float
    parallax_mas: float | None
    parallax_error_mas: float | None
    parallax_snr: float | None
    pmra_mas_per_year: float | None
    pmdec_mas_per_year: float | None
    proper_motion_total_mas_per_year: float | None
    phot_g_mean_mag: float | None
    phot_bp_mean_mag: float | None
    phot_rp_mean_mag: float | None
    bp_rp_mag: float | None
    radial_velocity_km_per_s: float | None
    effective_temperature_k: float | None
    naive_distance_parsecs: float | None
    absolute_g_magnitude: float | None


@dataclass(frozen=True, slots=True)
class GaiaCatalogSummary:
    """Useful highlights from returned Gaia sources."""

    source_count: int
    nearest_source: GaiaSource | None
    brightest_source: GaiaSource | None
    highest_proper_motion_source: GaiaSource | None
    median_g_magnitude: float | None


@dataclass(frozen=True, slots=True)
class GaiaSearchResult:
    """Gaia query, parsed sources, and summary."""

    request: GaiaConeSearchRequest
    adql_query: str
    sources: tuple[GaiaSource, ...]
    summary: GaiaCatalogSummary


def estimate_naive_distance_parsecs(
    parallax_mas: float | None,
) -> float | None:
    """Estimate distance using positive-parallax inversion."""

    if parallax_mas is None or not isfinite(parallax_mas) or parallax_mas <= 0.0:
        return None

    return 1000.0 / parallax_mas


def calculate_absolute_g_magnitude(
    apparent_g_magnitude: float | None,
    parallax_mas: float | None,
) -> float | None:
    """Calculate absolute G magnitude from positive parallax."""

    if apparent_g_magnitude is None or not isfinite(apparent_g_magnitude):
        return None

    if parallax_mas is None or not isfinite(parallax_mas) or parallax_mas <= 0.0:
        return None

    return apparent_g_magnitude + 5.0 * log10(parallax_mas) - 10.0


def build_gaia_adql(
    request: GaiaConeSearchRequest,
) -> str:
    """Build a bounded Gaia DR3 cone-search query."""

    ra = _format_adql_number(request.center_ra_deg)

    dec = _format_adql_number(request.center_dec_deg)

    radius = _format_adql_number(request.radius_deg)

    conditions = [
        (f"1 = CONTAINS(POINT('ICRS', gs.ra, gs.dec), CIRCLE('ICRS', {ra}, {dec}, {radius}))")
    ]

    if request.maximum_g_magnitude is not None:
        maximum_g = _format_adql_number(request.maximum_g_magnitude)

        conditions.append(f"gs.phot_g_mean_mag <= {maximum_g}")

    if request.minimum_parallax_snr is not None:
        minimum_snr = _format_adql_number(request.minimum_parallax_snr)

        conditions.extend(
            [
                "gs.parallax IS NOT NULL",
                "gs.parallax_error > 0",
                (f"gs.parallax_over_error >= {minimum_snr}"),
            ]
        )

    where_clause = "\n    AND ".join(conditions)

    return f"""SELECT TOP {request.row_limit}
    gs.source_id,
    gs.designation,
    gs.ra,
    gs.dec,
    gs.parallax,
    gs.parallax_error,
    gs.parallax_over_error,
    gs.pmra,
    gs.pmdec,
    gs.phot_g_mean_mag,
    gs.phot_bp_mean_mag,
    gs.phot_rp_mean_mag,
    gs.bp_rp,
    gs.radial_velocity,
    gs.teff_gspphot,
    DISTANCE(
        POINT('ICRS', gs.ra, gs.dec),
        POINT('ICRS', {ra}, {dec})
    ) AS angular_distance_deg
FROM {GAIA_SOURCE_TABLE} AS gs
WHERE {where_clause}
ORDER BY angular_distance_deg ASC"""


def _parse_optional_float(
    value: object,
) -> float | None:
    """Parse a finite optional floating-point field."""

    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {"null", "none", "nan"}:
        return None

    try:
        parsed = float(text)
    except ValueError:
        return None

    if not isfinite(parsed):
        return None

    return parsed


def _required_float(
    row: Mapping[str, str],
    field_name: str,
) -> float:
    """Parse a required finite floating-point field."""

    parsed = _parse_optional_float(row.get(field_name))

    if parsed is None:
        raise GaiaCatalogError(f"Gaia response is missing a valid {field_name!r} value.")

    return parsed


def _source_from_row(
    row: Mapping[str, str],
) -> GaiaSource:
    """Convert one normalized CSV row into a Gaia source."""

    source_id_text = row.get(
        "source_id",
        "",
    ).strip()

    try:
        source_id = int(source_id_text)
    except ValueError as error:
        raise GaiaCatalogError("Gaia response contains an invalid source_id.") from error

    if source_id <= 0:
        raise GaiaCatalogError("Gaia response contains a non-positive source_id.")

    parallax = _parse_optional_float(row.get("parallax"))

    parallax_error = _parse_optional_float(row.get("parallax_error"))

    parallax_snr = _parse_optional_float(row.get("parallax_over_error"))

    if (
        parallax_snr is None
        and parallax is not None
        and parallax_error is not None
        and parallax_error > 0.0
    ):
        parallax_snr = parallax / parallax_error

    pmra = _parse_optional_float(row.get("pmra"))

    pmdec = _parse_optional_float(row.get("pmdec"))

    if pmra is not None and pmdec is not None:
        proper_motion_total = hypot(
            pmra,
            pmdec,
        )
    else:
        proper_motion_total = None

    g_magnitude = _parse_optional_float(row.get("phot_g_mean_mag"))

    bp_magnitude = _parse_optional_float(row.get("phot_bp_mean_mag"))

    rp_magnitude = _parse_optional_float(row.get("phot_rp_mean_mag"))

    bp_rp = _parse_optional_float(row.get("bp_rp"))

    if bp_rp is None and bp_magnitude is not None and rp_magnitude is not None:
        bp_rp = bp_magnitude - rp_magnitude

    designation = row.get(
        "designation",
        "",
    ).strip()

    if not designation:
        designation = f"Gaia DR3 {source_id}"

    return GaiaSource(
        source_id=source_id,
        designation=designation,
        ra_deg=_required_float(
            row,
            "ra",
        ),
        dec_deg=_required_float(
            row,
            "dec",
        ),
        angular_distance_deg=_required_float(
            row,
            "angular_distance_deg",
        ),
        parallax_mas=parallax,
        parallax_error_mas=parallax_error,
        parallax_snr=parallax_snr,
        pmra_mas_per_year=pmra,
        pmdec_mas_per_year=pmdec,
        proper_motion_total_mas_per_year=(proper_motion_total),
        phot_g_mean_mag=g_magnitude,
        phot_bp_mean_mag=bp_magnitude,
        phot_rp_mean_mag=rp_magnitude,
        bp_rp_mag=bp_rp,
        radial_velocity_km_per_s=(_parse_optional_float(row.get("radial_velocity"))),
        effective_temperature_k=(_parse_optional_float(row.get("teff_gspphot"))),
        naive_distance_parsecs=(estimate_naive_distance_parsecs(parallax)),
        absolute_g_magnitude=(
            calculate_absolute_g_magnitude(
                g_magnitude,
                parallax,
            )
        ),
    )


def parse_gaia_csv(
    csv_text: str,
) -> tuple[GaiaSource, ...]:
    """Parse a Gaia TAP CSV response."""

    reader = csv.DictReader(StringIO(csv_text))

    if reader.fieldnames is None:
        raise GaiaCatalogError("Gaia response does not contain a CSV header.")

    normalized_fields = {field.strip().lower() for field in reader.fieldnames if field is not None}

    required_fields = {
        "source_id",
        "ra",
        "dec",
        "angular_distance_deg",
    }

    missing_fields = required_fields - normalized_fields

    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))

        raise GaiaCatalogError(f"Gaia response is missing required columns: {missing_text}.")

    sources: list[GaiaSource] = []

    for raw_row in reader:
        normalized_row = {
            str(key).strip().lower(): ("" if value is None else value)
            for key, value in raw_row.items()
            if key is not None
        }

        sources.append(_source_from_row(normalized_row))

    return tuple(
        sorted(
            sources,
            key=lambda source: source.angular_distance_deg,
        )
    )


def summarize_gaia_sources(
    sources: Iterable[GaiaSource],
) -> GaiaCatalogSummary:
    """Calculate catalogue highlights for display."""

    source_tuple = tuple(sources)

    nearest_source = min(
        source_tuple,
        key=lambda source: source.angular_distance_deg,
        default=None,
    )

    sources_with_g = tuple(source for source in source_tuple if source.phot_g_mean_mag is not None)

    brightest_source = min(
        sources_with_g,
        key=lambda source: source.phot_g_mean_mag,
        default=None,
    )

    sources_with_motion = tuple(
        source for source in source_tuple if (source.proper_motion_total_mas_per_year is not None)
    )

    highest_proper_motion_source = max(
        sources_with_motion,
        key=lambda source: source.proper_motion_total_mas_per_year,
        default=None,
    )

    if sources_with_g:
        median_g = median(
            source.phot_g_mean_mag
            for source in sources_with_g
            if source.phot_g_mean_mag is not None
        )
    else:
        median_g = None

    return GaiaCatalogSummary(
        source_count=len(source_tuple),
        nearest_source=nearest_source,
        brightest_source=brightest_source,
        highest_proper_motion_source=(highest_proper_motion_source),
        median_g_magnitude=median_g,
    )


def _response_content_type(
    response: Any,
) -> str:
    """Read the response content type safely."""

    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers is None:
        return ""

    get_content_type = getattr(
        headers,
        "get_content_type",
        None,
    )

    if callable(get_content_type):
        return str(get_content_type()).lower()

    get_header = getattr(
        headers,
        "get",
        None,
    )

    if callable(get_header):
        return str(
            get_header(
                "Content-Type",
                "",
            )
        ).lower()

    return ""


def fetch_gaia_sources(
    request: GaiaConeSearchRequest,
    *,
    opener: Callable[..., Any] = urlopen,
) -> GaiaSearchResult:
    """Execute a public synchronous Gaia TAP query."""

    adql_query = build_gaia_adql(request)

    body = urlencode(
        {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "QUERY": adql_query,
        }
    ).encode("utf-8")

    http_request = Request(
        GAIA_TAP_SYNC_URL,
        data=body,
        headers={
            "Content-Type": ("application/x-www-form-urlencoded"),
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="POST",
    )

    try:
        with opener(
            http_request,
            timeout=request.timeout_seconds,
        ) as response:
            status = getattr(
                response,
                "status",
                200,
            )

            if status >= 400:
                raise GaiaServiceError(f"Gaia TAP returned HTTP status {status}.")

            raw_data = response.read()

            content_type = _response_content_type(response)

    except GaiaServiceError:
        raise

    except HTTPError as error:
        raise GaiaServiceError(f"Gaia TAP returned HTTP status {error.code}.") from error

    except (
        URLError,
        TimeoutError,
        OSError,
    ) as error:
        raise GaiaServiceError("The Gaia TAP service could not be reached.") from error

    try:
        response_text = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise GaiaServiceError("The Gaia TAP response was not valid UTF-8 text.") from error

    response_prefix = response_text[:4000].lower()

    if "xml" in content_type or "<votable" in response_prefix or "query_status" in response_prefix:
        raise GaiaServiceError("Gaia TAP returned an error document instead of CSV data.")

    sources = parse_gaia_csv(response_text)

    return GaiaSearchResult(
        request=request,
        adql_query=adql_query,
        sources=sources,
        summary=summarize_gaia_sources(sources),
    )
