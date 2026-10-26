"""Current acceptance, offline independence and application boundaries for Mission 61."""

import csv
import json
import math
import subprocess
import sys
from dataclasses import replace
from io import StringIO

import pytest
from streamlit.testing.v1 import AppTest

from astroscope import exoplanet_catalog as exo
from astroscope import gaia_catalog as gaia
from astroscope.exoplanet_dashboard import _chart_labels
from astroscope.exoplanet_export import exoplanets_to_csv
from astroscope.exoplanet_visuals import create_transit_simulation_figure
from astroscope.i18n import translate
from validation import catalogue_correction as current
from validation import catalogue_quantities as historical

POLICY, FIXTURE = current.load_inputs()


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["id"])
def test_current_independent_acceptance(case):
    row = current.evaluate(case, POLICY)
    assert row["passed"], row
    if case["family"] in {"density", "depth", "probability"} and case["expected"] is not None:
        assert row["actual"] > 0


def test_original_inputs_and_historical_discrepancies_remain_traceable():
    _, old = historical.load_inputs()
    baseline = json.loads((historical.ROOT / historical.OBSERVATIONS).read_text())
    for a, b in zip(old["cases"], FIXTURE["cases"][:911], strict=True):
        assert a["id"] == b["original_case_id"] == b["id"]
        assert a["inputs"] == b["inputs"]
        assert a["family"] == b["family"]
    assert historical.verify_retained_sources(baseline["production_source_sha256"])
    for case in FIXTURE["cases"]:
        if case["id"] in baseline["observations"]["failed_case_ids"]:
            assert current.evaluate(case, POLICY)["passed"]
    result = historical.run_benchmark()
    assert result["failed_cases"] == 17 and historical.audit_observations(result)["passed"]
    assert result["execution_target"].startswith("isolated historical")


def test_offline_regeneration_without_production_or_external_numerics():
    code = r"""
import json, socket, sys
from pathlib import Path
def deny(*a, **k): raise AssertionError("Network forbidden")
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
for name in ["astroscope", "astropy", "numpy", "plotly", "erfa"]: sys.modules[name] = None
from validation.reference_generation.catalogue_correction import generate
assert json.dumps(generate(), indent=2, sort_keys=True, allow_nan=False) + "\n" == Path(
    "validation/fixtures/catalogue_correction_v1.json").read_text()
"""
    subprocess.run([sys.executable, "-c", code], cwd=current.ROOT, check=True, timeout=30)


def test_offline_current_cli_is_acceptance_not_reproduction(tmp_path):
    code = r"""
import socket, sys
def deny(*a, **k): raise AssertionError("Network forbidden")
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
sys.modules["validation.reference_generation.catalogue_correction"] = None
from validation.catalogue_correction import main
raise SystemExit(main())
"""
    path = tmp_path / "result.json"
    subprocess.run(
        [sys.executable, "-c", code, "--output", str(path)],
        cwd=current.ROOT,
        check=True,
        timeout=30,
    )
    result = json.loads(path.read_text())
    assert result["case_count"] == 1252 and result["failed_cases"] == 0
    assert result["overall_passed"] and result["execution_target"] == "current production"
    assert not result["physical_arrival_qualification_changed"]
    assert not result["observational_calibration_established"]
    assert not result["phase_2_exit_approved"]
    assert 0 < float(result["analytic_projection_bound_arcsec"]) < 10
    assert result["maximum_sampled_accepted_projection_error_arcsec"] < 10
    assert result["projection_accepted_cases"] + result["projection_rejected_cases"] == 892


@pytest.mark.parametrize(
    "fault",
    [
        "legacy_depth",
        "legacy_density",
        "embedded_orbit",
        "nonfinite_screen",
        "invalid_source",
        "tiny_duration",
    ],
)
def test_comparator_rejects_reintroduced_faults(monkeypatch, fault):
    _, old = historical.load_inputs()
    ids = dict(
        legacy_depth="CQ0895",
        legacy_density=None,
        embedded_orbit=None,
        nonfinite_screen="CQ0759",
        invalid_source="CQ0752",
        tiny_duration="CQ0904",
    )
    if fault == "legacy_density":
        case = next(
            c for c in FIXTURE["cases"] if c["family"] == "density" and c["inputs"] == ["1", "1"]
        )
        monkeypatch.setattr(exo, "calculate_planet_density_g_cm3", lambda *x: 5.514)
    elif fault == "embedded_orbit":
        case = next(
            c
            for c in FIXTURE["cases"]
            if c["family"] == "probability" and c["inputs"] == ["1", "1", "0.001"]
        )
        monkeypatch.setattr(exo, "calculate_transit_probability_percent", lambda *x: 100.0)
    else:
        case = next(c for c in FIXTURE["cases"] if c["id"] == ids[fault])
        if fault == "legacy_depth":
            monkeypatch.setattr(exo, "EARTH_RADIUS_IN_AU", historical.exo.EARTH_RADIUS_IN_AU)
        elif fault == "nonfinite_screen":
            monkeypatch.setattr(
                exo, "classify_temperate_candidate", historical.exo.classify_temperate_candidate
            )
        elif fault == "invalid_source":
            monkeypatch.setattr(
                current, "calculate_local_offsets_deg", historical.calculate_local_offsets_deg
            )
        else:
            monkeypatch.setattr(
                current,
                "calculate_trapezoid_transit_flux",
                historical.calculate_trapezoid_transit_flux,
            )
    assert not current.evaluate(case, POLICY)["passed"]


@pytest.mark.parametrize("ra,dec", [(360, 0), (-1, 0), (0, 91), (0, -91), ("nan", 0)])
def test_required_csv_coordinates_reject(ra, dec):
    with pytest.raises(gaia.GaiaCatalogError):
        gaia.parse_gaia_csv(
            current.csv_text(dict(source_id=1, ra=ra, dec=dec, angular_distance_deg=0))
        )


def test_derived_csv_extremes_stay_unknown_and_export_convention_is_explicit():
    row = dict(
        source_id=1,
        ra=0,
        dec=0,
        angular_distance_deg=0,
        parallax="1e308",
        parallax_error="5e-324",
        pmra="1.7e308",
        pmdec="1.7e308",
        phot_bp_mean_mag="1e308",
        phot_rp_mean_mag="-1e308",
    )
    star = gaia.parse_gaia_csv(current.csv_text(row))[0]
    assert star.parallax_snr is None and star.bp_rp_mag is None
    assert star.proper_motion_total_mas_per_year is None
    planet = exo.parse_exoplanet_csv(
        current.csv_text(
            dict(
                pl_name="synthetic b",
                hostname="synthetic",
                discoverymethod="",
                tran_flag=0,
                pl_rade="1e-110",
                pl_bmasse="1e-320",
                st_rad="",
                pl_orbsmax="",
            )
        )
    )[0]
    assert planet.density_g_cm3 == pytest.approx(5.494960690480628e10, rel=2e-12)
    assert planet.transit_depth_ppm is None and planet.transit_probability_percent is None
    exported = list(csv.DictReader(StringIO(exoplanets_to_csv([planet]))))[0]
    assert exported["transit_depth_ppm"] == "" and exported["transit_probability_percent"] == ""
    assert exported["calculation_convention"] == "nominal_spherical_v1"
    legacy = replace(planet, calculation_convention=None)
    assert (
        list(csv.DictReader(StringIO(exoplanets_to_csv([legacy]))))[0]["calculation_convention"]
        == ""
    )


@pytest.mark.parametrize("duration", [2, 1e308])
def test_model_figure_has_finite_ordered_grid_and_bounded_flux(duration):
    figure = create_transit_simulation_figure(
        depth_ppm=1e6, duration_hours=duration, ingress_fraction=0.15, labels=_chart_labels("en")
    )
    x, y = figure.data[0].x, figure.data[0].y
    assert all(math.isfinite(t) for t in x)
    assert all(a < b for a, b in zip(x[:-1], x[1:], strict=True))
    assert all(0 <= v <= 1 for v in y)
    assert y[150] == 0


def test_unresolved_plot_grid_rejects():
    with pytest.raises(ValueError, match="resolved plotting grid"):
        create_transit_simulation_figure(
            depth_ppm=1000, duration_hours=5e-324, ingress_fraction=0.15, labels=_chart_labels("en")
        )


@pytest.mark.parametrize("language", ["en", "ja", "ko", "th"])
@pytest.mark.parametrize("dec,separation", [(0, 0.1), (0, 1), (85, 0)])
def test_gaia_dashboard_retains_tables_when_projection_is_unsupported(language, dec, separation):
    code = f"""
from astroscope.gaia_catalog import (
    GaiaConeSearchRequest, GaiaSearchResult, parse_gaia_csv, summarize_gaia_sources)
from astroscope.gaia_dashboard import _display_search_result
sources = parse_gaia_csv(
    "source_id,ra,dec,angular_distance_deg\\n1,{separation},{dec},{separation}\\n")
result = GaiaSearchResult(
    GaiaConeSearchRequest(0, {dec}, 2), "synthetic", sources, summarize_gaia_sources(sources))
_display_search_result(result, language={language!r})
"""
    app = AppTest.from_string(code).run(timeout=20)
    assert not app.exception
    assert len(app.dataframe) == 1
    assert len(app.get("plotly_chart")) == (3 if dec == 0 and separation == 0.1 else 2)
    notices = app.caption if dec == 0 and separation == 0.1 else app.info
    assert translate("gaia_projection_domain", language) in [x.value for x in notices]


@pytest.mark.parametrize("depth", [None, 1e-20, float("inf"), 1e7])
def test_simulator_default_handles_unknown_or_outside_widget_range(depth):
    # Exercise the rendered widget, including manually constructed legacy records.
    value = repr(depth) if depth != float("inf") else 'float("inf")'
    code = f"""
from dataclasses import replace
from astroscope.exoplanet_catalog import parse_exoplanet_csv
from astroscope.exoplanet_dashboard import _render_transit_simulator
planet = parse_exoplanet_csv("pl_name,hostname,discoverymethod,tran_flag\\np,h,,0\\n")[0]
_render_transit_simulator([replace(planet, transit_depth_ppm={value})], language="en")
"""
    app = AppTest.from_string(code).run(timeout=20)
    assert not app.exception
    assert app.number_input[0].value == 1000


def test_new_notes_have_all_four_languages():
    for key in ["gaia_projection_domain", "exoplanet_convention_note"]:
        assert len({translate(key, lang) for lang in ["en", "ja", "ko", "th"]}) == 4


@pytest.mark.parametrize(
    "radius,star", [(695700000.0, 6378100.0), (695700000.0 * 2, 6378100.0 * 2)]
)
def test_equal_physical_radii_stay_at_unit_depth(radius, star):
    assert exo.calculate_transit_depth_ppm(radius, star) == pytest.approx(1e6, abs=2e-9)
    assert exo.calculate_transit_depth_ppm(radius, star) <= 1e6
    assert exo.calculate_transit_depth_ppm(math.nextafter(radius, math.inf), star) is None


def test_manifest_rejects_tampered_current_reference(tmp_path, monkeypatch):
    manifest = json.loads((current.ROOT / current.MANIFEST).read_text())
    for path in [current.MANIFEST, *manifest["files"]]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((current.ROOT / path).read_bytes())
    (tmp_path / current.FIXTURE).write_text("{}")
    monkeypatch.setattr(current, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        current.load_inputs()
