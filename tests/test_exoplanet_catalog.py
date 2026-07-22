"""Tests for exoplanet catalogue queries and calculations."""

from email.message import Message
from urllib.parse import parse_qs, urlparse

import pytest

from astroscope.exoplanet_catalog import (
    ExoplanetCatalogError,
    ExoplanetSearchRequest,
    ExoplanetServiceError,
    build_exoplanet_adql,
    calculate_planet_density_g_cm3,
    calculate_transit_depth_ppm,
    calculate_transit_probability_percent,
    classify_temperate_candidate,
    fetch_exoplanets,
    parse_exoplanet_csv,
    summarize_exoplanets,
)

SAMPLE_CSV = (
    "pl_name,hostname,discoverymethod,disc_year,"
    "tran_flag,pl_orbper,pl_orbsmax,pl_rade,"
    "pl_bmasse,pl_eqt,pl_insol,pl_orbeccen,"
    "st_teff,st_rad,st_mass,sy_dist,sy_pnum,"
    "ra,dec\n"
    "Kepler-442 b,Kepler-442,Transit,2015,"
    "1,112.3053,0.409,1.34,2.36,233,0.70,"
    "0.04,4402,0.60,0.61,365,1,285.3,39.2\n"
    "HD 209458 b,HD 209458,Transit,1999,"
    "1,3.5247,0.047,15.4,219,1450,480,"
    "0.01,6071,1.20,1.15,48.2,1,"
    "330.8,18.9\n"
)


class FakeResponse:
    """Minimal context-managed HTTP response."""

    def __init__(
        self,
        body: str,
        *,
        content_type: str = "text/csv",
        status: int = 200,
    ) -> None:
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(
        self,
        *args: object,
    ) -> None:
        del args
        return None


def test_request_accepts_typical_values() -> None:
    request = ExoplanetSearchRequest(
        row_limit=100,
        transiting_only=True,
        maximum_distance_pc=100.0,
    )

    assert request.row_limit == 100
    assert request.transiting_only is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("row_limit", 0),
        ("row_limit", 5001),
        ("maximum_distance_pc", 0.0),
        ("maximum_planet_radius_earth", -1.0),
        ("timeout_seconds", 0.0),
        ("timeout_seconds", 121.0),
    ],
)
def test_invalid_request_values_raise(
    field: str,
    value: float | int,
) -> None:
    values = {
        "row_limit": 200,
        "maximum_distance_pc": 100.0,
        "timeout_seconds": 30.0,
    }

    values[field] = value

    with pytest.raises(ExoplanetCatalogError):
        ExoplanetSearchRequest(**values)


def test_temperature_order_is_validated() -> None:
    with pytest.raises(
        ExoplanetCatalogError,
        match="cannot exceed",
    ):
        ExoplanetSearchRequest(
            minimum_equilibrium_temperature_k=310.0,
            maximum_equilibrium_temperature_k=180.0,
        )


def test_adql_contains_selected_filters() -> None:
    query = build_exoplanet_adql(
        ExoplanetSearchRequest(
            row_limit=50,
            transiting_only=True,
            discovery_method="Transit",
            maximum_distance_pc=100.0,
            maximum_planet_radius_earth=2.0,
            minimum_equilibrium_temperature_k=180.0,
            maximum_equilibrium_temperature_k=310.0,
        )
    )

    assert "SELECT TOP 50" in query
    assert "FROM pscomppars" in query
    assert "tran_flag = 1" in query
    assert "discoverymethod = 'Transit'" in query
    assert "sy_dist <= 100" in query
    assert "pl_rade <= 2" in query
    assert "pl_eqt >= 180" in query
    assert "pl_eqt <= 310" in query


def test_earth_density_reference() -> None:
    density = calculate_planet_density_g_cm3(
        1.0,
        1.0,
    )

    assert density == pytest.approx(5.514)


def test_earth_sun_transit_depth() -> None:
    depth = calculate_transit_depth_ppm(
        1.0,
        1.0,
    )

    assert depth == pytest.approx(
        83.86,
        rel=1e-3,
    )


def test_earth_sun_transit_probability() -> None:
    probability = calculate_transit_probability_percent(
        1.0,
        1.0,
        1.0,
    )

    assert probability == pytest.approx(
        0.4693,
        rel=1e-3,
    )


def test_temperate_candidate_classification() -> None:
    assert (
        classify_temperate_candidate(
            1.2,
            250.0,
            1.0,
        )
        == "temperate_terrestrial_candidate"
    )

    assert (
        classify_temperate_candidate(
            8.0,
            250.0,
            1.0,
        )
        == "temperate_non_terrestrial"
    )

    assert (
        classify_temperate_candidate(
            1.0,
            1000.0,
            100.0,
        )
        == "outside_temperate_range"
    )

    assert (
        classify_temperate_candidate(
            1.0,
            None,
            None,
        )
        == "insufficient_data"
    )


def test_parse_csv_calculates_derived_values() -> None:
    planets = parse_exoplanet_csv(SAMPLE_CSV)

    assert len(planets) == 2

    temperate_planet = next(planet for planet in planets if planet.planet_name == "Kepler-442 b")

    assert temperate_planet.is_transiting
    assert temperate_planet.density_g_cm3 is not None
    assert temperate_planet.transit_depth_ppm is not None

    assert temperate_planet.temperate_status == "temperate_terrestrial_candidate"


def test_summary_finds_catalogue_highlights() -> None:
    planets = parse_exoplanet_csv(SAMPLE_CSV)
    summary = summarize_exoplanets(planets)

    assert summary.planet_count == 2
    assert summary.transiting_count == 2
    assert summary.temperate_candidate_count == 1

    assert summary.nearest_planet is not None
    assert summary.nearest_planet.planet_name == "HD 209458 b"

    assert summary.smallest_planet is not None
    assert summary.smallest_planet.planet_name == "Kepler-442 b"

    assert summary.median_radius_earth == pytest.approx(8.37)


def test_fetch_builds_tap_request() -> None:
    captured: dict[str, object] = {}

    def fake_opener(
        request: object,
        *,
        timeout: float,
    ) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(SAMPLE_CSV)

    search_request = ExoplanetSearchRequest(
        row_limit=20,
        timeout_seconds=12.0,
    )

    result = fetch_exoplanets(
        search_request,
        opener=fake_opener,
    )

    http_request = captured["request"]
    full_url = http_request.full_url

    parameters = parse_qs(urlparse(full_url).query)

    assert parameters["format"] == ["csv"]
    assert "pscomppars" in parameters["query"][0]
    assert captured["timeout"] == 12.0
    assert result.summary.planet_count == 2


def test_fetch_rejects_error_document() -> None:
    def fake_opener(
        request: object,
        *,
        timeout: float,
    ) -> FakeResponse:
        del request, timeout

        return FakeResponse(
            ("<VOTABLE><INFO name='QUERY_STATUS' value='ERROR'/></VOTABLE>"),
            content_type="application/xml",
        )

    with pytest.raises(ExoplanetServiceError):
        fetch_exoplanets(
            ExoplanetSearchRequest(),
            opener=fake_opener,
        )


def test_missing_csv_columns_raise() -> None:
    with pytest.raises(
        ExoplanetCatalogError,
        match="missing required columns",
    ):
        parse_exoplanet_csv("pl_name,hostname\nPlanet A,Star A\n")
