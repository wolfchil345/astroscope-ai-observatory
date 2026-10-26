"""NASA Exoplanet Archive queries and educational calculations."""

import csv
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from io import StringIO
from math import isfinite
from statistics import median
from typing import Any, Final, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EXOPLANET_TAP_SYNC_URL: Final[str] = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

EXOPLANET_TABLE: Final[str] = "pscomppars"

DEFAULT_USER_AGENT: Final[str] = "AstroScope-AI-Observatory/1.0"

EARTH_DENSITY_G_CM3: Final[float] = 5.514
EARTH_RADIUS_IN_SOLAR_RADII: Final[float] = 0.0091577
EARTH_RADIUS_IN_AU: Final[float] = 4.26352e-5
SOLAR_RADIUS_IN_AU: Final[float] = 0.00465047

TemperateStatus = Literal[
    "temperate_terrestrial_candidate",
    "temperate_non_terrestrial",
    "outside_temperate_range",
    "insufficient_data",
]


class ExoplanetCatalogError(ValueError):
    """Raised when catalogue input or returned data is invalid."""


class ExoplanetServiceError(RuntimeError):
    """Raised when the NASA Exoplanet Archive cannot return data."""


def _validate_finite(
    value: float,
    label: str,
) -> None:
    """Require a finite number."""

    if not isfinite(value):
        raise ExoplanetCatalogError(f"{label} must be finite.")


def _validate_positive_optional(
    value: float | None,
    label: str,
) -> None:
    """Validate an optional positive finite number."""

    if value is None:
        return

    _validate_finite(value, label)

    if value <= 0.0:
        raise ExoplanetCatalogError(f"{label} must be greater than zero.")


def _format_adql_number(value: float) -> str:
    """Format one validated number for ADQL."""

    if value == 0.0:
        return "0"

    return format(value, ".12g")


def _quote_adql_string(value: str) -> str:
    """Escape and quote one ADQL string literal."""

    escaped = value.replace("'", "''")
    return f"'{escaped}'"


@dataclass(frozen=True, slots=True)
class ExoplanetSearchRequest:
    """Validated filters for one exoplanet catalogue query."""

    row_limit: int = 200
    transiting_only: bool = False
    discovery_method: str | None = None
    maximum_distance_pc: float | None = None
    maximum_planet_radius_earth: float | None = None
    minimum_equilibrium_temperature_k: float | None = None
    maximum_equilibrium_temperature_k: float | None = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.row_limit, bool)
            or not isinstance(self.row_limit, int)
            or not 1 <= self.row_limit <= 5000
        ):
            raise ExoplanetCatalogError("Row limit must be an integer between 1 and 5000.")

        if not isinstance(self.transiting_only, bool):
            raise ExoplanetCatalogError("Transiting-only must be a Boolean value.")

        if self.discovery_method is not None:
            method = self.discovery_method.strip()

            if not method:
                raise ExoplanetCatalogError("Discovery method cannot be empty.")

            if len(method) > 100:
                raise ExoplanetCatalogError("Discovery method is too long.")

        _validate_positive_optional(
            self.maximum_distance_pc,
            "Maximum distance",
        )

        _validate_positive_optional(
            self.maximum_planet_radius_earth,
            "Maximum planet radius",
        )

        _validate_positive_optional(
            self.minimum_equilibrium_temperature_k,
            "Minimum equilibrium temperature",
        )

        _validate_positive_optional(
            self.maximum_equilibrium_temperature_k,
            "Maximum equilibrium temperature",
        )

        minimum_temperature = self.minimum_equilibrium_temperature_k

        maximum_temperature = self.maximum_equilibrium_temperature_k

        if (
            minimum_temperature is not None
            and maximum_temperature is not None
            and minimum_temperature > maximum_temperature
        ):
            raise ExoplanetCatalogError(
                "Minimum equilibrium temperature cannot exceed the maximum."
            )

        _validate_finite(
            self.timeout_seconds,
            "Timeout",
        )

        if not 0.0 < self.timeout_seconds <= 120.0:
            raise ExoplanetCatalogError("Timeout must be greater than 0 and at most 120 seconds.")


@dataclass(frozen=True, slots=True)
class ExoplanetRecord:
    """One confirmed planet and selected host-star parameters."""

    planet_name: str
    hostname: str
    discovery_method: str
    discovery_year: int | None
    is_transiting: bool
    orbital_period_days: float | None
    semi_major_axis_au: float | None
    radius_earth: float | None
    mass_earth: float | None
    equilibrium_temperature_k: float | None
    insolation_earth: float | None
    eccentricity: float | None
    stellar_temperature_k: float | None
    stellar_radius_solar: float | None
    stellar_mass_solar: float | None
    distance_pc: float | None
    system_planet_count: int | None
    ra_deg: float | None
    dec_deg: float | None
    density_g_cm3: float | None
    transit_depth_ppm: float | None
    transit_probability_percent: float | None
    temperate_status: TemperateStatus


@dataclass(frozen=True, slots=True)
class ExoplanetCatalogSummary:
    """Highlights calculated from returned exoplanets."""

    planet_count: int
    transiting_count: int
    temperate_candidate_count: int
    nearest_planet: ExoplanetRecord | None
    smallest_planet: ExoplanetRecord | None
    median_radius_earth: float | None


@dataclass(frozen=True, slots=True)
class ExoplanetSearchResult:
    """Completed query and parsed catalogue records."""

    request: ExoplanetSearchRequest
    adql_query: str
    planets: tuple[ExoplanetRecord, ...]
    summary: ExoplanetCatalogSummary


def calculate_planet_density_g_cm3(
    mass_earth: float | None,
    radius_earth: float | None,
) -> float | None:
    """Estimate bulk density from Earth-relative mass and radius."""

    if (
        mass_earth is None
        or radius_earth is None
        or not isfinite(mass_earth)
        or not isfinite(radius_earth)
        or mass_earth <= 0.0
        or radius_earth <= 0.0
    ):
        return None

    return EARTH_DENSITY_G_CM3 * mass_earth / radius_earth**3


def calculate_transit_depth_ppm(
    radius_earth: float | None,
    stellar_radius_solar: float | None,
) -> float | None:
    """Estimate transit depth from planet and stellar radii."""

    if (
        radius_earth is None
        or stellar_radius_solar is None
        or not isfinite(radius_earth)
        or not isfinite(stellar_radius_solar)
        or radius_earth <= 0.0
        or stellar_radius_solar <= 0.0
    ):
        return None

    radius_ratio = radius_earth * EARTH_RADIUS_IN_SOLAR_RADII / stellar_radius_solar

    return radius_ratio**2 * 1_000_000.0


def calculate_transit_probability_percent(
    stellar_radius_solar: float | None,
    planet_radius_earth: float | None,
    semi_major_axis_au: float | None,
) -> float | None:
    """Estimate geometric transit probability for a circular orbit."""

    if (
        stellar_radius_solar is None
        or planet_radius_earth is None
        or semi_major_axis_au is None
        or not isfinite(stellar_radius_solar)
        or not isfinite(planet_radius_earth)
        or not isfinite(semi_major_axis_au)
        or stellar_radius_solar <= 0.0
        or planet_radius_earth <= 0.0
        or semi_major_axis_au <= 0.0
    ):
        return None

    stellar_radius_au = stellar_radius_solar * SOLAR_RADIUS_IN_AU

    planet_radius_au = planet_radius_earth * EARTH_RADIUS_IN_AU

    probability = (stellar_radius_au + planet_radius_au) / semi_major_axis_au

    return min(100.0, probability * 100.0)


def classify_temperate_candidate(
    radius_earth: float | None,
    equilibrium_temperature_k: float | None,
    insolation_earth: float | None,
) -> TemperateStatus:
    """Apply a transparent educational temperate-world screen."""

    if radius_earth is None or radius_earth <= 0.0:
        return "insufficient_data"

    temperature_available = (
        equilibrium_temperature_k is not None
        and isfinite(equilibrium_temperature_k)
        and equilibrium_temperature_k > 0.0
    )

    insolation_available = (
        insolation_earth is not None and isfinite(insolation_earth) and insolation_earth > 0.0
    )

    if not temperature_available and not insolation_available:
        return "insufficient_data"

    temperature_is_temperate = (
        temperature_available
        and equilibrium_temperature_k is not None
        and 180.0 <= equilibrium_temperature_k <= 310.0
    )

    insolation_is_temperate = (
        insolation_available and insolation_earth is not None and 0.25 <= insolation_earth <= 2.0
    )

    is_temperate = temperature_is_temperate or insolation_is_temperate

    if not is_temperate:
        return "outside_temperate_range"

    if 0.5 <= radius_earth <= 2.0:
        return "temperate_terrestrial_candidate"

    return "temperate_non_terrestrial"


def build_exoplanet_adql(
    request: ExoplanetSearchRequest,
) -> str:
    """Build a bounded PSCompPars query."""

    conditions = [
        "pl_name IS NOT NULL",
        "hostname IS NOT NULL",
    ]

    if request.transiting_only:
        conditions.append("tran_flag = 1")

    if request.discovery_method is not None:
        method = _quote_adql_string(request.discovery_method.strip())

        conditions.append(f"discoverymethod = {method}")

    if request.maximum_distance_pc is not None:
        maximum_distance = _format_adql_number(request.maximum_distance_pc)

        conditions.extend(
            [
                "sy_dist IS NOT NULL",
                f"sy_dist <= {maximum_distance}",
            ]
        )

    if request.maximum_planet_radius_earth is not None:
        maximum_radius = _format_adql_number(request.maximum_planet_radius_earth)

        conditions.extend(
            [
                "pl_rade IS NOT NULL",
                f"pl_rade <= {maximum_radius}",
            ]
        )

    minimum_temperature = request.minimum_equilibrium_temperature_k

    if minimum_temperature is not None:
        formatted_minimum = _format_adql_number(minimum_temperature)

        conditions.extend(
            [
                "pl_eqt IS NOT NULL",
                f"pl_eqt >= {formatted_minimum}",
            ]
        )

    maximum_temperature = request.maximum_equilibrium_temperature_k

    if maximum_temperature is not None:
        formatted_maximum = _format_adql_number(maximum_temperature)

        conditions.extend(
            [
                "pl_eqt IS NOT NULL",
                f"pl_eqt <= {formatted_maximum}",
            ]
        )

    where_clause = "\n    AND ".join(conditions)

    return f"""SELECT TOP {request.row_limit}
    pl_name,
    hostname,
    discoverymethod,
    disc_year,
    tran_flag,
    pl_orbper,
    pl_orbsmax,
    pl_rade,
    pl_bmasse,
    pl_eqt,
    pl_insol,
    pl_orbeccen,
    st_teff,
    st_rad,
    st_mass,
    sy_dist,
    sy_pnum,
    ra,
    dec
FROM {EXOPLANET_TABLE}
WHERE {where_clause}
ORDER BY pl_name ASC"""


def _parse_optional_float(
    value: object,
) -> float | None:
    """Parse one optional finite float."""

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


def _parse_optional_int(
    value: object,
) -> int | None:
    """Parse one optional integer-like value."""

    parsed = _parse_optional_float(value)

    if parsed is None or not parsed.is_integer():
        return None

    return int(parsed)


def _required_text(
    row: Mapping[str, str],
    field_name: str,
) -> str:
    """Read one required non-empty text field."""

    value = row.get(field_name, "").strip()

    if not value:
        raise ExoplanetCatalogError(f"Exoplanet response is missing a valid {field_name!r} value.")

    return value


def _record_from_row(
    row: Mapping[str, str],
) -> ExoplanetRecord:
    """Convert one normalized CSV row into a planet record."""

    radius_earth = _parse_optional_float(row.get("pl_rade"))

    mass_earth = _parse_optional_float(row.get("pl_bmasse"))

    equilibrium_temperature = _parse_optional_float(row.get("pl_eqt"))

    insolation = _parse_optional_float(row.get("pl_insol"))

    stellar_radius = _parse_optional_float(row.get("st_rad"))

    semi_major_axis = _parse_optional_float(row.get("pl_orbsmax"))

    transit_flag = _parse_optional_int(row.get("tran_flag"))

    return ExoplanetRecord(
        planet_name=_required_text(
            row,
            "pl_name",
        ),
        hostname=_required_text(
            row,
            "hostname",
        ),
        discovery_method=row.get(
            "discoverymethod",
            "",
        ).strip(),
        discovery_year=_parse_optional_int(row.get("disc_year")),
        is_transiting=transit_flag == 1,
        orbital_period_days=_parse_optional_float(row.get("pl_orbper")),
        semi_major_axis_au=semi_major_axis,
        radius_earth=radius_earth,
        mass_earth=mass_earth,
        equilibrium_temperature_k=(equilibrium_temperature),
        insolation_earth=insolation,
        eccentricity=_parse_optional_float(row.get("pl_orbeccen")),
        stellar_temperature_k=_parse_optional_float(row.get("st_teff")),
        stellar_radius_solar=stellar_radius,
        stellar_mass_solar=_parse_optional_float(row.get("st_mass")),
        distance_pc=_parse_optional_float(row.get("sy_dist")),
        system_planet_count=_parse_optional_int(row.get("sy_pnum")),
        ra_deg=_parse_optional_float(row.get("ra")),
        dec_deg=_parse_optional_float(row.get("dec")),
        density_g_cm3=calculate_planet_density_g_cm3(
            mass_earth,
            radius_earth,
        ),
        transit_depth_ppm=calculate_transit_depth_ppm(
            radius_earth,
            stellar_radius,
        ),
        transit_probability_percent=(
            calculate_transit_probability_percent(
                stellar_radius,
                radius_earth,
                semi_major_axis,
            )
        ),
        temperate_status=classify_temperate_candidate(
            radius_earth,
            equilibrium_temperature,
            insolation,
        ),
    )


def parse_exoplanet_csv(
    csv_text: str,
) -> tuple[ExoplanetRecord, ...]:
    """Parse a NASA Exoplanet Archive CSV response."""

    reader = csv.DictReader(StringIO(csv_text))

    if reader.fieldnames is None:
        raise ExoplanetCatalogError("Exoplanet response has no CSV header.")

    normalized_fields = {field.strip().lower() for field in reader.fieldnames if field is not None}

    required_fields = {
        "pl_name",
        "hostname",
        "discoverymethod",
        "tran_flag",
    }

    missing_fields = required_fields - normalized_fields

    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))

        raise ExoplanetCatalogError(
            f"Exoplanet response is missing required columns: {missing_text}."
        )

    planets: list[ExoplanetRecord] = []

    for raw_row in reader:
        normalized_row = {
            str(key).strip().lower(): ("" if value is None else value)
            for key, value in raw_row.items()
            if key is not None
        }

        planets.append(_record_from_row(normalized_row))

    return tuple(
        sorted(
            planets,
            key=lambda planet: planet.planet_name,
        )
    )


def summarize_exoplanets(
    planets: Iterable[ExoplanetRecord],
) -> ExoplanetCatalogSummary:
    """Calculate catalogue highlights."""

    planet_tuple = tuple(planets)

    planets_with_distance = tuple(
        planet for planet in planet_tuple if planet.distance_pc is not None
    )

    nearest_planet = min(
        planets_with_distance,
        key=lambda planet: planet.distance_pc,
        default=None,
    )

    planets_with_radius = tuple(
        planet for planet in planet_tuple if planet.radius_earth is not None
    )

    smallest_planet = min(
        planets_with_radius,
        key=lambda planet: planet.radius_earth,
        default=None,
    )

    if planets_with_radius:
        median_radius = median(
            planet.radius_earth for planet in planets_with_radius if planet.radius_earth is not None
        )
    else:
        median_radius = None

    return ExoplanetCatalogSummary(
        planet_count=len(planet_tuple),
        transiting_count=sum(planet.is_transiting for planet in planet_tuple),
        temperate_candidate_count=sum(
            planet.temperate_status == "temperate_terrestrial_candidate" for planet in planet_tuple
        ),
        nearest_planet=nearest_planet,
        smallest_planet=smallest_planet,
        median_radius_earth=median_radius,
    )


def _response_content_type(
    response: Any,
) -> str:
    """Read an HTTP response content type safely."""

    headers = getattr(response, "headers", None)

    if headers is None:
        return ""

    get_content_type = getattr(
        headers,
        "get_content_type",
        None,
    )

    if callable(get_content_type):
        return str(get_content_type()).lower()

    get_header = getattr(headers, "get", None)

    if callable(get_header):
        return str(get_header("Content-Type", "")).lower()

    return ""


def fetch_exoplanets(
    request: ExoplanetSearchRequest,
    *,
    opener: Callable[..., Any] = urlopen,
) -> ExoplanetSearchResult:
    """Execute a public NASA Exoplanet Archive TAP query."""

    adql_query = build_exoplanet_adql(request)

    query_string = urlencode(
        {
            "query": adql_query,
            "format": "csv",
        }
    )

    http_request = Request(
        f"{EXOPLANET_TAP_SYNC_URL}?{query_string}",
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="GET",
    )

    try:
        with opener(
            http_request,
            timeout=request.timeout_seconds,
        ) as response:
            status = getattr(response, "status", 200)

            if status >= 400:
                raise ExoplanetServiceError(
                    f"NASA Exoplanet Archive returned HTTP status {status}."
                )

            raw_data = response.read()
            content_type = _response_content_type(response)

    except ExoplanetServiceError:
        raise

    except HTTPError as error:
        raise ExoplanetServiceError(
            f"NASA Exoplanet Archive returned HTTP status {error.code}."
        ) from error

    except (
        URLError,
        TimeoutError,
        OSError,
    ) as error:
        raise ExoplanetServiceError("NASA Exoplanet Archive could not be reached.") from error

    try:
        response_text = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ExoplanetServiceError("The exoplanet response was not valid UTF-8.") from error

    response_prefix = response_text[:4000].lower()

    if "xml" in content_type or "<votable" in response_prefix or "query_status" in response_prefix:
        raise ExoplanetServiceError("The archive returned an error document instead of CSV data.")

    planets = parse_exoplanet_csv(response_text)

    return ExoplanetSearchResult(
        request=request,
        adql_query=adql_query,
        planets=planets,
        summary=summarize_exoplanets(planets),
    )
