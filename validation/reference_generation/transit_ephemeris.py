"""Stage A: independent Decimal reference; standard library only, no production imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = "validation/manifests/transit_ephemeris_policy_v1.json"
SOURCES = "validation/fixtures/transit_ephemeris_sources_v1.json"
GENERATOR = "validation/reference_generation/transit_ephemeris.py"
FIXTURE = "validation/fixtures/transit_ephemeris_v1.json"
MANIFEST = "validation/manifests/transit_ephemeris_v1.json"
D = Decimal


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ephemerides() -> list[dict]:
    published = json.loads((ROOT / SOURCES).read_text(encoding="utf-8"))["published_ephemeris"]
    values = []
    specifications = [
        ("dyadic", "2450000.25", "2", "3", "0.001", "0.0001"),
        ("short", "2460000.5", "0.125", "0.75", "0.002", "0.00001"),
        ("fractional", "2460000.1234567", "3.14159265", "2.7", "0.0003", "0.000002"),
        ("long", "2400000.5", "365.25", "12", "0.02", "0.001"),
        ("unknown", "2450000.25", "2.5", "2", None, None),
        ("epoch_only", "2450000.25", "2.5", "2", "0.01", None),
        ("period_only", "2450000.25", "2.5", "2", None, "0.0001"),
        ("explicit_zero", "2450000.25", "2.5", "2", "0", "0"),
        (
            published["id"],
            published["reference_mid_transit_jd"],
            published["orbital_period_days"],
            "3",
            published["reference_epoch_uncertainty_days"],
            published["period_uncertainty_days"],
        ),
    ]
    for name, epoch, period, duration, sigma_epoch, sigma_period in specifications:
        values.append(
            {
                "id": name,
                "planet_name": name,
                "reference_mid_transit_jd": epoch,
                "orbital_period_days": period,
                "transit_duration_hours": duration,
                "reference_epoch_uncertainty_days": sigma_epoch,
                "period_uncertainty_days": sigma_period,
                "time_coordinate": "BJD_TDB" if name == published["id"] else "synthetic_uniform_JD",
                "input_origin": "published_coefficients_synthetic_duration"
                if name == published["id"]
                else "synthetic_analytic",
                "uncertainty_status": "unknown_component"
                if None in (sigma_epoch, sigma_period)
                else "explicit_zero"
                if sigma_epoch == sigma_period == "0"
                else "supplied",
            }
        )
    return values


def reference_event(e: dict, n: int, options: dict) -> dict:
    """Evaluate real-valued model with decimal coefficients and variance addition."""
    midpoint = D(e["reference_mid_transit_jd"]) + D(n) * D(e["orbital_period_days"])
    half = D(e["transit_duration_hours"]) / D(48)
    variance = D(e["reference_epoch_uncertainty_days"] or "0") ** 2
    variance += D(n) ** 2 * D(e["period_uncertainty_days"] or "0") ** 2
    sigma = variance.sqrt()
    margin = D(options["uncertainty_sigma_multiplier"]) * sigma
    start = midpoint - half - D(options["baseline_before_hours"]) / 24 - margin
    end = midpoint + half + D(options["baseline_after_hours"]) / 24 + margin
    return {
        k: str(v)
        for k, v in {
            "mid_transit_jd": midpoint,
            "ingress_jd": midpoint - half,
            "egress_jd": midpoint + half,
            "observation_start_jd": start,
            "observation_end_jd": end,
            "timing_uncertainty_days": sigma,
            "timing_uncertainty_hours": sigma * 24,
            "observation_window_hours": (end - start) * 24,
        }.items()
    }


def build_fixture() -> dict:
    """Enumerate cycles rather than reproducing production's ceil/floor selector."""
    with localcontext() as context:
        context.prec = 60
        ephs = ephemerides()
        events, ranges, covariance = [], [], []
        options_list = [
            {
                "baseline_before_hours": "0",
                "baseline_after_hours": "0",
                "uncertainty_sigma_multiplier": "0",
            },
            {
                "baseline_before_hours": "1",
                "baseline_after_hours": "2",
                "uncertainty_sigma_multiplier": "1",
            },
            {
                "baseline_before_hours": "0.25",
                "baseline_after_hours": "0.75",
                "uncertainty_sigma_multiplier": "3",
            },
        ]
        for e in ephs:
            for n in [-10000, -100, -1, 0, 1, 100, 10000]:
                for j, options in enumerate(options_list):
                    events.append(
                        {
                            "id": f"{e['id']}:event:{n}:{j}",
                            "ephemeris_id": e["id"],
                            "cycle": n,
                            "options": options,
                            "expected": reference_event(e, n, options),
                        }
                    )
            epoch, period = D(e["reference_mid_transit_jd"]), D(e["orbital_period_days"])
            dyadic = all(D.from_float(float(v)) == D(v) for v in (epoch, period))
            for n in [-100, 0, 100]:
                mid = epoch + n * period
                one_second = D(1) / 86400
                nominal = float(mid)
                scenarios = [
                    ("inclusive_three", mid, mid + 2 * period),
                    ("point", mid, mid),
                    ("exclude_left", mid + one_second, mid + period - one_second),
                    ("include_one", mid - one_second, mid + one_second),
                    (
                        "negative_to_positive" if n == 0 else "wide",
                        mid - period / 2,
                        mid + period * D("2.5"),
                    ),
                    (
                        "ulp_below",
                        D.from_float(math.nextafter(nominal, -math.inf)),
                        D.from_float(math.nextafter(nominal, -math.inf)),
                    ),
                    (
                        "ulp_above",
                        D.from_float(math.nextafter(nominal, math.inf)),
                        D.from_float(math.nextafter(nominal, math.inf)),
                    ),
                ]
                for label, start, end in scenarios:
                    # Persist exact float input values; reference comparison uses their exact reals.
                    start_float, end_float = float(start), float(end)
                    lo, hi = D.from_float(start_float), D.from_float(end_float)
                    candidates = [(k, epoch + k * period) for k in range(n - 4, n + 6)]
                    guard = D("0.0002") / 86400
                    certain = [k for k, t in candidates if lo + guard < t < hi - guard]
                    possible = [k for k, t in candidates if lo - guard <= t <= hi + guard]
                    near = any(min(abs(t - lo), abs(t - hi)) <= guard for _, t in candidates)
                    eligible = dyadic or not near
                    expected = [k for k, t in candidates if lo <= t <= hi]
                    ranges.append(
                        {
                            "id": f"{e['id']}:range:{n}:{label}",
                            "ephemeris_id": e["id"],
                            "start_jd": repr(start_float),
                            "end_jd": repr(end_float),
                            "expected_cycles": expected,
                            "expected_after": next(k for k, t in candidates if t >= lo),
                            "expected_before": next(k for k, t in reversed(candidates) if t <= hi),
                            "eligible": eligible,
                            "certain_cycles": certain,
                            "possible_cycles": possible,
                            "boundary_guard_seconds": "0.0002",
                            "enumeration_domain": [n - 4, n + 5],
                        }
                    )
            if e["uncertainty_status"] == "supplied":
                a = D(e["reference_epoch_uncertainty_days"])
                b = D(e["period_uncertainty_days"])
                for n in [-1000, 1000]:
                    for rho in [D("-0.5"), D("0.5")]:
                        independent = (a * a + n * n * b * b).sqrt()
                        correlated = (a * a + n * n * b * b + 2 * n * rho * a * b).sqrt()
                        covariance.append(
                            {
                                "ephemeris_id": e["id"],
                                "cycle": n,
                                "rho": str(rho),
                                "independent_sigma_days": str(independent),
                                "correlated_sigma_days": str(correlated),
                                "status": "unsupported_model_diagnostic",
                            }
                        )
        return {
            "schema_version": "1.0",
            "precision_decimal_digits": 60,
            "ephemerides": ephs,
            "events": events,
            "ranges": ranges,
            "covariance_diagnostics": covariance,
            "independence": "stdlib Decimal; no production imports or runtime oracle",
        }


def generate(output_root: Path) -> None:
    fixture = build_fixture()
    destination = output_root / FIXTURE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded(fixture))
    manifest = {
        "schema_version": "1.0",
        "mission": 35,
        "files": {p: sha(ROOT / p) for p in [POLICY, SOURCES, GENERATOR]},
        "counts": {
            k: len(fixture[k])
            for k in ["ephemerides", "events", "ranges", "covariance_diagnostics"]
        },
    }
    manifest["files"][FIXTURE] = sha(destination)
    path = output_root / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    generate(parser.parse_args().output_root)
