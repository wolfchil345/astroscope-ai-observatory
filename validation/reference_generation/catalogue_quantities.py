"""Mission 60 references: stdlib Decimal/Fraction and independent spherical vectors.

No production, NumPy, Astropy or Plotly imports; no catalogue/network access.
This is a source-informed, pre-evaluation protocol, not a blinded experiment.
"""

import itertools
import json
import math
from decimal import Decimal as D
from decimal import localcontext
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PI = D("3.141592653589793238462643383279502884197169399375105820974944592")
AU = D("149597870700")
SUN = D("695700000")
EARTH_MEAN = D("6371000")
EARTH_EQUATOR = D("6378100")


def number(value):
    if value is None:
        return None
    q = D(str(value))
    return q if q.is_finite() else None


def cosine(x):
    """Taylor cosine with 60-digit Decimal arithmetic for |x| <= pi/2."""
    term = total = D(1)
    for n in range(1, 100):
        term *= -x * x / ((2 * n - 1) * (2 * n))
        total += term
        if abs(term) < D("1e-65"):
            break
    return total


def scalar(family, args):
    q = [number(x) for x in args]
    if family == "distance":
        return None if q[0] is None or q[0] <= 0 else str(1000 / q[0])
    if family == "absolute_g":
        if q[0] is None or q[1] is None or q[1] <= 0:
            return None
        # Distance modulus in distance space, rather than production's parallax formula.
        return str(q[0] - 5 * ((1000 / q[1]) / 10).log10())
    if any(x is None or x <= 0 for x in q):
        return None
    if family == "density":
        return str(D("5.514") * q[0] / q[1] ** 3)
    if family == "depth":
        # Deliberately frozen legacy conversion for arithmetic; coherence checked separately.
        return str(D(1000000) * (q[0] * D("0.0091577")) ** 2 / q[1] ** 2)
    if family == "probability":
        return str(min(D(100), 100 * (q[0] * D("0.00465047") + q[1] * D("0.0000426352")) / q[2]))
    raise ValueError(family)


def screen(args):
    r, t, s = map(number, args)
    if r is None or r <= 0:
        return "insufficient_data"
    available = [v for v in (t, s) if v is not None and v > 0]
    if not available:
        return "insufficient_data"
    accepted = (t is not None and D(180) <= t <= D(310)) or (
        s is not None and D("0.25") <= s <= D(2)
    )
    if not accepted:
        return "outside_temperate_range"
    return "temperate_terrestrial_candidate" if D("0.5") <= r <= 2 else "temperate_non_terrestrial"


def trapezoid(times, depth, duration, ingress):
    """Exact rational clipped ramp; independent of production's branch ordering."""
    d, total, fraction = map(F, (depth, duration, ingress))
    return [
        str(float(1 - d / 1000000 * max(F(0), min(F(1), (F(1, 2) - abs(F(t) / total)) / fraction))))
        for t in times
    ]


def gaia_expected(row):
    p, e = number(row.get("parallax")), number(row.get("parallax_error"))
    snr = number(row.get("parallax_over_error"))
    if snr is None and p is not None and e is not None and e > 0:
        snr = p / e
    bp, rp = number(row.get("phot_bp_mean_mag")), number(row.get("phot_rp_mean_mag"))
    colour = number(row.get("bp_rp"))
    if colour is None and bp is not None and rp is not None:
        colour = bp - rp
    a, b = number(row.get("pmra")), number(row.get("pmdec"))
    motion = None if a is None or b is None else (a * a + b * b).sqrt()
    return {
        "naive_distance_parsecs": scalar("distance", [row.get("parallax")]),
        "absolute_g_magnitude": scalar(
            "absolute_g", [row.get("phot_g_mean_mag"), row.get("parallax")]
        ),
        "parallax_snr": None if snr is None else str(snr),
        "bp_rp_mag": None if colour is None else str(colour),
        "proper_motion_total_mas_per_year": None if motion is None else str(motion),
    }


def sky_case(ra, dec, radius, bearing):
    """Create points by a 3-D great-circle rotation; return a spherical log map."""
    a, d, rho, theta = map(math.radians, (ra, dec, radius, bearing))
    center = (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))
    east = (-math.sin(a), math.cos(a), 0)
    north = (-math.sin(d) * math.cos(a), -math.sin(d) * math.sin(a), math.cos(d))
    v = tuple(
        math.cos(rho) * c + math.sin(rho) * (math.sin(theta) * e + math.cos(theta) * n)
        for c, e, n in zip(center, east, north, strict=True)
    )
    source_ra = math.degrees(math.atan2(v[1], v[0])) % 360
    source_dec = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))
    da = D(str(source_ra)) - D(str(ra))
    # Fraction/Decimal remainder has different negative semantics; reduce explicitly.
    while da < -180:
        da += 360
    while da >= 180:
        da -= 360
    planar = [str(da * cosine(D(str(dec)) * PI / 180)), str(D(str(source_dec)) - D(str(dec)))]
    return {
        "inputs": [repr(source_ra), repr(source_dec), str(ra), str(dec)],
        "expected": planar,
        "diagnostic": {
            "radius_deg": radius,
            "bearing_deg": bearing,
            "center_dec_deg": dec,
            "spherical_log_map_deg": [radius * math.sin(theta), radius * math.cos(theta)],
            "meaning": "geodesic east/north offsets; diagnostic, not a chosen projection contract",
        },
    }


def generate():
    cases = []

    def add(family, inputs, expected=None, *, requirement="value", group="arithmetic", **extra):
        cases.append(
            {
                "id": f"CQ{len(cases) + 1:04}",
                "family": family,
                "inputs": inputs,
                "requirement": requirement,
                "group": group,
                "expected": expected,
                **extra,
            }
        )

    with localcontext() as ctx:
        ctx.prec = 60
        valid = {
            "distance": [[p] for p in ["0.000001", "0.1", "1", "2.5", "10", "100", "1000"]],
            "absolute_g": list(
                itertools.product(
                    ["-5", "0", "10", "25"], ["0.001", "0.1", "1", "10", "100", "1000"]
                )
            ),
            "density": list(
                itertools.product(
                    ["0.01", "1", "5", "318", "30000"], ["0.1", "0.5", "1", "2", "10", "25"]
                )
            ),
            "depth": list(itertools.product(["0.1", "1", "2", "10"], ["0.1", "0.5", "1", "10"])),
            "probability": list(
                itertools.product(
                    ["0.1", "1", "10"], ["0.1", "1", "10"], ["0.001", "0.01", "1", "100"]
                )
            ),
        }
        for family, inputs in valid.items():
            for args in inputs:
                extra = {}
                if family == "probability":
                    star, planet, orbit = map(D, args)
                    extra["exterior_circular_orbit"] = (
                        orbit * AU > star * SUN + planet * EARTH_EQUATOR
                    )
                add(family, list(args), scalar(family, args), **extra)
        for family, seed in [
            ("distance", ["1"]),
            ("absolute_g", ["10", "1"]),
            ("density", ["1", "1"]),
            ("depth", ["1", "1"]),
            ("probability", ["1", "1", "1"]),
        ]:
            for i in range(len(seed)):
                for bad in [None, "NaN", "Infinity", "-Infinity", "0", "-1"]:
                    if family == "absolute_g" and i == 0 and bad in ["0", "-1"]:
                        continue
                    args = list(seed)
                    args[i] = bad
                    add(family, args, scalar(family, args), group="domain")
        base = dict(
            parallax="2",
            parallax_error="0.25",
            pmra="3",
            pmdec="-4",
            phot_g_mean_mag="12",
            phot_bp_mean_mag="13.25",
            phot_rp_mean_mag="12",
        )
        variants = [
            {},
            {"bp_rp": "9", "parallax_over_error": "-123"},
            {"bp_rp": "NaN", "parallax_over_error": "Infinity"},
            {"parallax": "-2"},
            {"parallax": "0"},
            {"parallax_error": "0"},
            {"parallax_error": "-1"},
            {"pmra": None},
            {"pmdec": "NaN"},
            {"phot_rp_mean_mag": None},
            {"phot_bp_mean_mag": "Infinity"},
            {"parallax": None},
            {"phot_g_mean_mag": None},
            {"pmra": "-6", "pmdec": "8"},
        ]
        for changes in variants:
            row = dict(base, **changes)
            add("gaia_row", row, gaia_expected(row), group="ingestion")
        for ra, dec, radius, bearing in itertools.product(
            [0, 359.9], [-90, -85, -60, 0, 60, 85, 90], [0.01, 0.25, 1, 5, 10], range(0, 360, 45)
        ):
            item = sky_case(ra, dec, radius, bearing)
            add("offsets", **item, group="projection")
        for args in [
            ["0", "0", "0", "0"],
            ["0.1", "0", "359.9", "0"],
            ["359.9", "0", "0.1", "0"],
            ["180", "0", "0", "0"],
        ]:
            a, d, a0, d0 = map(D, args)
            delta = a - a0
            if delta >= 180:
                delta -= 360
            if delta < -180:
                delta += 360
            add("offsets", args, [str(delta), str(d - d0)], group="arithmetic")
        for i, bad in [
            (0, "NaN"),
            (0, "Infinity"),
            (0, "360.1"),
            (0, "-1"),
            (1, "91"),
            (1, "-91"),
            (2, "360"),
            (3, "91"),
        ]:
            args = ["0", "0", "0", "0"]
            args[i] = bad
            add("offsets", args, requirement="reject", group="domain")
        thresholds = [
            (
                0,
                [
                    None,
                    "NaN",
                    "Infinity",
                    "-Infinity",
                    "-1",
                    "0",
                    "0.499999",
                    "0.5",
                    "0.500001",
                    "1.999999",
                    "2",
                    "2.000001",
                ],
            ),
            (
                1,
                [
                    None,
                    "NaN",
                    "Infinity",
                    "-1",
                    "0",
                    "179.999999",
                    "180",
                    "180.000001",
                    "309.999999",
                    "310",
                    "310.000001",
                ],
            ),
            (
                2,
                [
                    None,
                    "NaN",
                    "Infinity",
                    "-1",
                    "0",
                    "0.249999",
                    "0.25",
                    "0.250001",
                    "1.999999",
                    "2",
                    "2.000001",
                ],
            ),
        ]
        for i, values in thresholds:
            for value in values:
                args = ["1", "250", None] if i != 2 else ["1", None, "1"]
                args[i] = value
                add("screen", args, screen(args), group="heuristic")
        for args in itertools.product(
            ["0.5", "2", "3"], [None, "150", "250", "400"], [None, "0.1", "1", "3"]
        ):
            add("screen", list(args), screen(args), group="heuristic")
        for depth, duration, ingress in itertools.product(
            ["1", "1000", "1000000"], ["0.001", "0.5", "2", "24"], ["0.01", "0.15", "0.49"]
        ):
            f = D(ingress)
            phases = [
                -D("0.6"),
                -D("0.5"),
                -D("0.5") + f / 2,
                -D("0.5") + f,
                D(0),
                D("0.5") - f,
                D("0.5") - f / 2,
                D("0.5"),
                D("0.6"),
            ]
            times = [str(q * D(duration)) for q in phases]
            args = dict(times=times, depth=depth, duration=duration, ingress=ingress)
            add("trapezoid", args, trapezoid(times, depth, duration, ingress), group="educational")
        add(
            "trapezoid",
            dict(times=[], depth="1000", duration="2", ingress="0.15"),
            [],
            group="educational",
        )
        for key, values in [
            ("depth", ["0", "-1", "NaN", "Infinity", "1000001"]),
            ("duration", ["0", "-1", "NaN", "Infinity"]),
            ("ingress", ["0", "0.5", "-1", "NaN", "Infinity"]),
        ]:
            for value in values:
                args = dict(times=["0"], depth="1000", duration="2", ingress="0.15")
                args[key] = value
                add("trapezoid", args, requirement="reject", group="domain")
        for time in ["NaN", "Infinity", "-Infinity"]:
            add(
                "trapezoid",
                dict(times=[time], depth="1000", duration="2", ingress="0.15"),
                requirement="reject",
                group="domain",
            )
        # Independent SI/rounded-constant controls, and a common-radius consistency requirement.
        for name, reference, half_digit in [
            ("EARTH_RADIUS_IN_SOLAR_RADII", EARTH_MEAN / SUN, "0.00000005"),
            ("EARTH_RADIUS_IN_AU", EARTH_EQUATOR / AU, "0.00000000005"),
            ("SOLAR_RADIUS_IN_AU", SUN / AU, "0.000000005"),
        ]:
            add(
                "constant",
                [name],
                str(reference),
                group="convention",
                absolute_tolerance=half_digit,
            )
        add(
            "radius_coherence",
            [],
            "0",
            group="convention",
            absolute_tolerance=str(D("0.00000005") * SUN + D("0.00000000005") * AU),
        )
        for family, args in [
            ("distance", ["5e-324"]),
            ("density", ["1e300", "1e100"]),
            ("density", ["1e-320", "1e-110"]),
            ("density", ["1e308", "1"]),
            ("depth", ["1e200", "1e-200"]),
        ]:
            # References here use the exact binary64 inputs, including subnormal quantization.
            reference = scalar(family, [str(D.from_float(float(x))) for x in args])
            requirement = (
                "reject_or_null"
                if abs(D(reference)) > D.from_float(float.fromhex("0x1.fffffffffffffp+1023"))
                else "value_or_reject"
            )
            add(family, args, reference, requirement=requirement, group="extreme")
        add("depth", ["200", "1"], requirement="reject_or_null", group="physical_domain")
        add(
            "trapezoid",
            dict(times=["0"], depth="1000", duration="5e-324", ingress="0.15"),
            ["0.999"],
            requirement="value_or_reject",
            group="extreme",
        )
        # Synthetic CSV only. Limits and covariance are not synthesized.
        for values in [
            {},
            {"pl_rade": None},
            {"pl_bmasse": None},
            {"st_rad": None},
            {"pl_eqt": "NaN", "pl_insol": "1"},
            {"pl_orbeccen": "0.9"},
            {"pl_dens": "999", "pl_trandep": "99"},
        ]:
            row = dict(
                pl_rade="1",
                pl_bmasse="1",
                st_rad="1",
                pl_orbsmax="1",
                pl_eqt="250",
                pl_insol=None,
                pl_orbeccen="0",
            )
            row.update(values)
            expected = {
                "density_g_cm3": scalar("density", [row.get("pl_bmasse"), row.get("pl_rade")]),
                "transit_depth_ppm": scalar("depth", [row.get("pl_rade"), row.get("st_rad")]),
                "transit_probability_percent": scalar(
                    "probability", [row.get("st_rad"), row.get("pl_rade"), row.get("pl_orbsmax")]
                ),
                "temperate_status": screen(
                    [row.get("pl_rade"), row.get("pl_eqt"), row.get("pl_insol")]
                ),
            }
            add("exoplanet_row", row, expected, group="ingestion")
        diagnostics = {
            "earth_density_from_mass_and_mean_sphere_g_cm3": str(
                D("5.9722e24") / (4 * PI * EARTH_MEAN**3 / 3) / 1000
            ),
            "earth_sun_depth_mean_radius_ppm": str((EARTH_MEAN / SUN) ** 2 * 1000000),
            "earth_sun_depth_nominal_equatorial_radius_ppm": str(
                (EARTH_EQUATOR / SUN) ** 2 * 1000000
            ),
            "meaning": (
                "Definition sensitivity only; rounded Earth mass and radius have uncertainty; "
                "no physical error bound."
            ),
        }
    return {
        "mission": 60,
        "reference_precision": 60,
        "randomness": "none",
        "cases": cases,
        "independent_definition_diagnostics": diagnostics,
    }


if __name__ == "__main__":
    (ROOT / "validation/fixtures/catalogue_quantities_v1.json").write_text(
        json.dumps(generate(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
