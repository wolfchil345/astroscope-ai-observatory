"""Tests for Gaia catalogue queries and calculations."""

from email.message import Message
from urllib.parse import parse_qs

import pytest

from astroscope.gaia_catalog import (
    GaiaCatalogError,
    GaiaConeSearchRequest,
    GaiaServiceError,
    build_gaia_adql,
    calculate_absolute_g_magnitude,
    estimate_naive_distance_parsecs,
    fetch_gaia_sources,
    parse_gaia_csv,
    summarize_gaia_sources,
)

SAMPLE_CSV = (
    "source_id,designation,ra,dec,parallax,"
    "parallax_error,parallax_over_error,"
    "pmra,pmdec,phot_g_mean_mag,"
    "phot_bp_mean_mag,phot_rp_mean_mag,"
    "bp_rp,radial_velocity,teff_gspphot,"
    "angular_distance_deg\n"
    "1002,Gaia DR3 1002,83.83,-5.39,"
    "2.0,0.2,10.0,3.0,4.0,12.5,"
    "13.0,12.0,1.0,20.0,5500,0.02\n"
    "1001,Gaia DR3 1001,83.82,-5.38,"
    "5.0,0.5,10.0,6.0,8.0,10.0,"
    "10.4,9.5,0.9,,6000,0.01\n"
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

    def __enter__(
        self,
    ) -> "FakeResponse":
        return self

    def __exit__(
        self,
        *args: object,
    ) -> None:
        del args
        return None


def test_request_accepts_typical_values() -> None:
    request = GaiaConeSearchRequest(
        center_ra_deg=83.822,
        center_dec_deg=-5.391,
        radius_deg=0.25,
    )

    assert request.row_limit == 200

    assert request.maximum_g_magnitude == 16.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("center_ra_deg", 360.0),
        ("center_dec_deg", 91.0),
        ("radius_deg", 0.0),
        ("row_limit", 0),
        ("timeout_seconds", 0.0),
    ],
)
def test_invalid_request_values_raise_error(
    field: str,
    value: float | int,
) -> None:
    values = {
        "center_ra_deg": 83.822,
        "center_dec_deg": -5.391,
        "radius_deg": 0.25,
        "row_limit": 200,
        "timeout_seconds": 30.0,
    }

    values[field] = value

    with pytest.raises(GaiaCatalogError):
        GaiaConeSearchRequest(**values)


def test_adql_contains_bounded_filters() -> None:
    query = build_gaia_adql(
        GaiaConeSearchRequest(
            center_ra_deg=83.822,
            center_dec_deg=-5.391,
            radius_deg=0.25,
            row_limit=50,
            maximum_g_magnitude=14.5,
            minimum_parallax_snr=5.0,
        )
    )

    assert "SELECT TOP 50" in query

    assert "FROM gaiadr3.gaia_source AS gs" in query

    assert "CIRCLE('ICRS', 83.822, -5.391, 0.25)" in query

    assert "gs.phot_g_mean_mag <= 14.5" in query

    assert "gs.parallax_over_error >= 5" in query

    assert "ORDER BY angular_distance_deg ASC" in query


def test_parse_csv_calculates_values() -> None:
    sources = parse_gaia_csv(SAMPLE_CSV)

    assert [source.source_id for source in sources] == [1001, 1002]

    assert sources[0].proper_motion_total_mas_per_year == pytest.approx(10.0)

    assert sources[0].naive_distance_parsecs == pytest.approx(200.0)

    assert sources[0].absolute_g_magnitude == pytest.approx(3.49485)


def test_distance_requires_positive_parallax() -> None:
    assert estimate_naive_distance_parsecs(None) is None

    assert estimate_naive_distance_parsecs(0.0) is None

    assert estimate_naive_distance_parsecs(-1.0) is None

    assert estimate_naive_distance_parsecs(10.0) == pytest.approx(100.0)


def test_absolute_magnitude_requires_parallax() -> None:
    assert (
        calculate_absolute_g_magnitude(
            10.0,
            None,
        )
        is None
    )

    assert (
        calculate_absolute_g_magnitude(
            10.0,
            -1.0,
        )
        is None
    )

    assert calculate_absolute_g_magnitude(
        10.0,
        10.0,
    ) == pytest.approx(5.0)


def test_summary_finds_highlights() -> None:
    sources = parse_gaia_csv(SAMPLE_CSV)

    summary = summarize_gaia_sources(sources)

    assert summary.source_count == 2

    assert summary.nearest_source is not None

    assert summary.nearest_source.source_id == 1001

    assert summary.brightest_source is not None

    assert summary.brightest_source.source_id == 1001

    assert summary.highest_proper_motion_source is not None

    assert summary.highest_proper_motion_source.source_id == 1001

    assert summary.median_g_magnitude == pytest.approx(11.25)


def test_fetch_posts_adql_and_parses() -> None:
    captured: dict[str, object] = {}

    def fake_opener(
        request: object,
        *,
        timeout: float,
    ) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(SAMPLE_CSV)

    search_request = GaiaConeSearchRequest(
        center_ra_deg=83.822,
        center_dec_deg=-5.391,
        radius_deg=0.25,
        timeout_seconds=12.0,
    )

    result = fetch_gaia_sources(
        search_request,
        opener=fake_opener,
    )

    http_request = captured["request"]

    assert http_request.method == "POST"

    assert captured["timeout"] == 12.0

    body = http_request.data.decode("utf-8")

    parameters = parse_qs(body)

    assert parameters["REQUEST"] == ["doQuery"]

    assert parameters["LANG"] == ["ADQL"]

    assert parameters["FORMAT"] == ["csv"]

    assert "gaiadr3.gaia_source" in parameters["QUERY"][0]

    assert result.summary.source_count == 2


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

    with pytest.raises(GaiaServiceError):
        fetch_gaia_sources(
            GaiaConeSearchRequest(
                center_ra_deg=83.822,
                center_dec_deg=-5.391,
                radius_deg=0.25,
            ),
            opener=fake_opener,
        )


def test_missing_csv_columns_raise_error() -> None:
    with pytest.raises(
        GaiaCatalogError,
        match="missing required columns",
    ):
        parse_gaia_csv("source_id,ra,dec\n1,10,20\n")
