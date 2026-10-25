"""Independent Mission 60 arithmetic, conventions, domains and retained discrepancies."""

import copy
import json
import math
import socket
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction

import pytest

from astroscope import exoplanet_catalog as exo
from astroscope import gaia_catalog as gaia
from astroscope.exoplanet_visuals import calculate_trapezoid_transit_flux
from validation import catalogue_quantities as campaign

POLICY, FIXTURE = campaign.load_inputs()
BASELINE = json.loads((campaign.ROOT / campaign.OBSERVATIONS).read_text())
KNOWN_FAILURES = set(BASELINE["observations"]["failed_case_ids"])


@pytest.mark.parametrize(
    "case", [c for c in FIXTURE["cases"] if c["id"] not in KNOWN_FAILURES], ids=lambda c: c["id"]
)
def test_independent_catalogue_reference(case):
    assert campaign.evaluate(case, POLICY)["passed"]


@pytest.mark.parametrize(
    "case", [c for c in FIXTURE["cases"] if c["id"] in KNOWN_FAILURES], ids=lambda c: c["id"]
)
@pytest.mark.xfail(
    strict=True, reason="Mission 60 retained acceptance discrepancy; G59-01 stays open"
)
def test_retained_catalogue_scientific_failure(case):
    assert campaign.evaluate(case, POLICY)["passed"]


def test_reference_regeneration_independent_and_offline():
    code = r"""
import json, socket, sys
from pathlib import Path
def deny(*args, **kwargs): raise AssertionError('Network forbidden')
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
for name in ['astroscope', 'astropy', 'numpy', 'plotly', 'erfa']:
    sys.modules[name] = None
from validation.reference_generation.catalogue_quantities import generate
from validation.reference_generation.catalogue_binary_inputs import generate_amendment
for make, path in [(generate, 'validation/fixtures/catalogue_quantities_v1.json'),
                   (generate_amendment, 'validation/fixtures/catalogue_binary_inputs_v2.json')]:
    result = json.dumps(make(), indent=2, sort_keys=True, allow_nan=False) + '\n'
    assert result == Path(path).read_text(), path
"""
    subprocess.run([sys.executable, "-c", code], cwd=campaign.ROOT, check=True, timeout=30)


@pytest.fixture(scope="module")
def current_result():
    return campaign.run_benchmark()


def test_full_observation_audit_and_scientific_status_remain_distinct(current_result):
    assert current_result["case_count"] == 911
    assert current_result["failed_cases"] == 17
    assert not current_result["overall_passed"]
    assert campaign.audit_observations(current_result)["passed"]
    assert current_result["capped_non_exterior_probability_cases"] == 9
    assert not current_result["phase_2_exit_approved"]
    assert not current_result["physical_arrival_qualification_changed"]
    assert not current_result["observational_calibration_established"]


@pytest.mark.parametrize(
    "change", ["drop_case", "new_failure", "unexpected_improvement", "numeric_shift"]
)
def test_reproduction_audit_rejects_changed_evidence(current_result, change):
    altered = copy.deepcopy(current_result)
    if change == "drop_case":
        altered["results"].pop()
    elif change == "new_failure":
        altered["results"][0]["passed"] = False
    elif change == "unexpected_improvement":
        next(r for r in altered["results"] if not r["passed"])["passed"] = True
    else:
        altered["results"][0]["actual"] *= 1.01
    assert not campaign.audit_observations(altered)["passed"]


@pytest.mark.parametrize("audit", [False, True])
def test_offline_cli_exit_meaning(tmp_path, audit):
    output = tmp_path / "result.json"
    code = r"""
import socket, sys
def deny(*args, **kwargs): raise AssertionError('Network forbidden')
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
sys.modules['validation.reference_generation.catalogue_quantities'] = None
sys.modules['validation.reference_generation.catalogue_binary_inputs'] = None
from validation.catalogue_quantities import main
raise SystemExit(main())
"""
    args = [sys.executable, "-c", code, "--output", str(output)]
    if audit:
        args.append("--audit-known-discrepancies")
    process = subprocess.run(args, cwd=campaign.ROOT, timeout=60, capture_output=True, text=True)
    assert process.returncode == (0 if audit else 1), process.stderr
    result = json.loads(output.read_text())
    assert not result["overall_passed"] and result["failed_cases"] == 17
    assert ("observation_audit" in result) == audit


@pytest.mark.parametrize(
    "case",
    [
        c
        for c in FIXTURE["cases"]
        if c["family"] == "trapezoid" and c["group"] == "educational" and c["inputs"]["times"]
    ],
    ids=lambda c: c["id"],
)
def test_trapezoid_exact_integral_symmetry_and_range(case):
    q = case["inputs"]
    times = list(map(float, q["times"]))
    flux = calculate_trapezoid_transit_flux(
        times,
        depth_ppm=float(q["depth"]),
        duration_hours=float(q["duration"]),
        ingress_fraction=float(q["ingress"]),
    )
    assert all(0 <= f <= 1 for f in flux)
    assert flux == pytest.approx(flux[::-1], abs=2e-12)
    area = math.fsum(
        (b - a) * ((1 - fa) + (1 - fb)) / 2
        for a, b, fa, fb in zip(times[:-1], times[1:], flux[:-1], flux[1:], strict=True)
    )
    exact = Fraction(q["depth"]) / 1000000 * Fraction(q["duration"]) * (1 - Fraction(q["ingress"]))
    assert area == pytest.approx(float(exact), rel=2e-9, abs=2e-14)


def test_binary_reference_amendment_is_narrow_and_preserves_inputs():
    original = json.loads((campaign.ROOT / campaign.FIXTURE).read_text())
    amendment = json.loads((campaign.ROOT / campaign.AMENDMENT).read_text())
    assert len(amendment["replacements"]) == 564
    assert len({x["id"] for x in amendment["replacements"]}) == 564
    for before, after in zip(original["cases"], FIXTURE["cases"], strict=True):
        assert {k: v for k, v in before.items() if k != "expected"} == {
            k: v for k, v in after.items() if k != "expected"
        }
        if before["family"] != "offsets" or before["requirement"] != "value":
            assert before == after
    case = next(c for c in FIXTURE["cases"] if c["id"] == "CQ0542")
    a, _, b, _ = case["inputs"]
    assert Decimal(a) - Decimal(b) < -180
    assert Decimal.from_float(float(a)) - Decimal.from_float(float(b)) == -180
    assert campaign.evaluate(case, POLICY)["passed"]


def test_all_references_and_recorded_unknowns_remain_finite_or_explicit():
    assert not campaign.matches(float("nan"), "0", atol=1, rtol=1)
    assert not campaign.matches(float("inf"), "Infinity", atol=1, rtol=1)
    assert not campaign.matches(0, None, atol=1, rtol=1)
    assert not campaign.matches(1, True, atol=1, rtol=1)
    assert campaign.matches(None, None, atol=0, rtol=0)


@pytest.mark.parametrize(
    "fault", ["depth_percent", "extra_pm_cosine", "probability_units", "offset_sign"]
)
def test_scientific_comparator_detects_controlled_faults(monkeypatch, fault):
    families = {
        "depth_percent": "depth",
        "extra_pm_cosine": "gaia_row",
        "probability_units": "probability",
        "offset_sign": "offsets",
    }
    case = next(
        c
        for c in FIXTURE["cases"]
        if c["family"] == families[fault]
        and c["id"] not in KNOWN_FAILURES
        and c["expected"] is not None
    )
    if fault == "depth_percent":
        original = exo.calculate_transit_depth_ppm
        monkeypatch.setattr(exo, "calculate_transit_depth_ppm", lambda *x: original(*x) / 10000)
    elif fault == "probability_units":
        original = exo.calculate_transit_probability_percent
        monkeypatch.setattr(
            exo, "calculate_transit_probability_percent", lambda *x: original(*x) / 100
        )
    elif fault == "extra_pm_cosine":
        original = gaia.hypot
        monkeypatch.setattr(gaia, "hypot", lambda a, b: original(a * 0.5, b))
    else:
        case = next(
            c
            for c in FIXTURE["cases"]
            if c["family"] == "offsets"
            and c["requirement"] == "value"
            and abs(float(c["expected"][0])) > 0.1
        )
        original = campaign.calculate_local_offsets_deg

        def reversed_offset(*args, **kwargs):
            x, y = original(*args, **kwargs)
            return -x, y

        monkeypatch.setattr(campaign, "calculate_local_offsets_deg", reversed_offset)
    assert not campaign.evaluate(case, POLICY)["passed"]


def test_manifest_detects_tampered_reference(tmp_path, monkeypatch):
    manifest = json.loads((campaign.ROOT / campaign.MANIFEST).read_text())
    for path in [campaign.MANIFEST, *manifest["files"]]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((campaign.ROOT / path).read_bytes())
    target = tmp_path / campaign.FIXTURE
    target.write_text(target.read_text() + " ")
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        campaign.load_inputs()


def test_gaia_csv_network_is_not_used(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny)
    for case in FIXTURE["cases"]:
        if case["family"] in {"gaia_row", "exoplanet_row"}:
            assert campaign.evaluate(case, POLICY)["passed"]
