"""Mission 61 independent, pre-correction references; standard library only.

The old corpus is immutable. This explicit successor changes the unit convention
and supported domains, retaining every original input and its identifier.
"""

import copy
import itertools
import json
import math
from decimal import Decimal as D
from decimal import localcontext

from validation.reference_generation.catalogue_quantities import (
    AU,
    EARTH_EQUATOR,
    PI,
    ROOT,
    SUN,
    cosine,
    sky_case,
)


def binary(value):
    return None if value is None else D.from_float(float(value))


def representable(value):
    if value is None:
        return None
    f = float(value)
    return str(value) if math.isfinite(f) and (value == 0 or f != 0) else None


def scalar(family, args):
    q = [binary(x) for x in args]
    if any(x is None or not x.is_finite() or x <= 0 for x in q):
        return None
    if family == "density":
        mass = D("3.986004e14") / D("6.67430e-11") * q[0]
        return representable(3 * mass / (4 * PI * (EARTH_EQUATOR * q[1]) ** 3) / 1000)
    if family == "depth":
        r = q[0] * EARTH_EQUATOR / (q[1] * SUN)
        return None if r > 1 else representable(1000000 * r * r)
    if family == "probability":
        r = (q[0] * SUN + q[1] * EARTH_EQUATOR) / (q[2] * AU)
        return None if r >= 1 else representable(100 * r)
    raise ValueError(family)


def offset_reference(args):
    ra, dec, cra, cdec = map(binary, args)
    if not all(x.is_finite() for x in (ra, dec, cra, cdec)):
        return None
    if not (0 <= ra < 360 and 0 <= cra < 360 and abs(dec) <= 90 and abs(cdec) <= 60):
        return None
    da = ra - cra
    while da < -180:
        da += 360
    while da >= 180:
        da -= 360
    # Independent spherical dot product; production uses a haversine distance.
    d, c, a = [x * PI / 180 for x in (dec, cdec, da)]
    dot = cosine(PI / 2 - d) * cosine(PI / 2 - c) + cosine(d) * cosine(c) * cosine(a)
    if dot < cosine(D("0.2500000001") * PI / 180):
        return None
    return [str(da * cosine(c)), str(dec - cdec)]


def flux_reference(q):
    # Decimal normalized clipped ramp is independent of production Fraction contacts.
    with localcontext() as ctx:
        ctx.prec = 1600
        depth, duration, ingress = [binary(q[k]) for k in ("depth", "duration", "ingress")]
        return [
            str(
                1
                - depth
                / 1000000
                * max(D(0), min(D(1), (D("0.5") - abs(binary(t) / duration)) / ingress))
            )
            for t in q["times"]
        ]


def generate():
    original = json.loads((ROOT / "validation/fixtures/catalogue_quantities_v1.json").read_text())
    amended = json.loads((ROOT / "validation/fixtures/catalogue_binary_inputs_v2.json").read_text())
    replacements = {c["id"]: c["expected"] for c in amended["replacements"]}
    cases = copy.deepcopy(original["cases"])
    with localcontext() as ctx:
        ctx.prec = 80
        constants = {
            "EARTH_RADIUS_IN_SOLAR_RADII": EARTH_EQUATOR / SUN,
            "EARTH_RADIUS_IN_AU": EARTH_EQUATOR / AU,
            "SOLAR_RADIUS_IN_AU": SUN / AU,
        }
        for case in cases:
            family, args = case["family"], case["inputs"]
            case["original_case_id"] = case["id"]
            case["disposition"] = "unchanged acceptance contract"
            if case["id"] in replacements:
                case["expected"] = replacements[case["id"]]
            if family in {"density", "depth", "probability"}:
                case["expected"] = scalar(family, args)
                case["requirement"] = "value"
                case["disposition"] = (
                    "nominal spherical convention; supported finite exterior geometry"
                )
                case.pop("exterior_circular_orbit", None)
            elif family == "constant":
                case["expected"] = str(constants[args[0]])
                case["absolute_tolerance"] = 2e-16
                case["disposition"] = "single nominal Earth radius convention"
            elif family == "radius_coherence":
                case["expected"] = "0"
                case["absolute_tolerance"] = 2e-9
                case["disposition"] = "single nominal Earth radius convention"
            elif family == "offsets":
                case["expected"] = offset_reference(args)
                case["requirement"] = "reject" if case["expected"] is None else "value"
                case["disposition"] = "enforced small-field domain"
            elif family == "trapezoid" and case["requirement"] != "reject":
                case["expected"] = flux_reference(args)
                case["disposition"] = (
                    "same model at exact binary64 inputs; independent Decimal oracle"
                )
            elif family == "exoplanet_row":
                for field, name, keys in [
                    ("density_g_cm3", "density", ["pl_bmasse", "pl_rade"]),
                    ("transit_depth_ppm", "depth", ["pl_rade", "st_rad"]),
                    (
                        "transit_probability_percent",
                        "probability",
                        ["st_rad", "pl_rade", "pl_orbsmax"],
                    ),
                ]:
                    if field in case["expected"]:
                        case["expected"][field] = scalar(name, [args.get(k) for k in keys])
                case["disposition"] = "nominal spherical convention with unknown propagation"

        def add(family, inputs, expected=None, requirement="value", **extra):
            cases.append(
                dict(
                    id=f"CC{len(cases) - 910:04}",
                    family=family,
                    inputs=inputs,
                    expected=expected,
                    requirement=requirement,
                    group="correction_extension",
                    disposition="new boundary or extreme control",
                    **extra,
                )
            )

        for ra, dec, rho, bearing in itertools.product(
            [0, 359.9],
            [-60.000001, -60, 0, 60, 60.000001],
            [0.249999, 0.25, 0.2500000002, 0.250001],
            range(0, 360, 45),
        ):
            q = sky_case(ra, dec, rho, bearing)
            expected = offset_reference(q["inputs"])
            add(
                "offsets",
                q["inputs"],
                expected,
                "reject" if expected is None else "value",
                diagnostic=q["diagnostic"],
            )
        for family, args in [
            ("density", ["1e-320", "1e-110"]),
            ("density", ["1e308", "1e103"]),
            ("density", ["1e308", "1"]),
            ("density", ["5e-324", "1e308"]),
            ("depth", ["1e308", "1e308"]),
            ("depth", ["1e-300", "1e100"]),
            ("probability", ["1e308", "1e308", "1e308"]),
            ("probability", ["5e-324", "5e-324", "5e-324"]),
            ("probability", ["1", "1", "0.001"]),
        ]:
            add(family, args, scalar(family, args))
        for duration, ingress in itertools.product(
            ["5e-324", "1e-300", "2", "1e308"], ["5e-324", ".15", ".49999999999999994"]
        ):
            q = dict(
                times=["-1e308", "-5e-324", "0", "5e-324", "1e308"],
                depth="1000000",
                duration=duration,
                ingress=ingress,
            )
            add("trapezoid", q, flux_reference(q))
        rho = D("0.2500000001") * PI / 180
        dmax = D(60) * PI / 180 + rho
        sec = 1 / cosine(dmax)
        tan = cosine(PI / 2 - dmax) * sec
        bound = rho * rho / 2 * tan * (sec * sec + 1).sqrt() * 180 / PI * 3600
    return dict(
        mission=61,
        version=1,
        original_case_count=911,
        cases=cases,
        analytic_projection_bound_arcsec=str(bound),
        projection_goal_arcsec=10,
        reference_kind="independent arithmetic/domain validation; no observed calibration",
    )


if __name__ == "__main__":
    (ROOT / "validation/fixtures/catalogue_correction_v1.json").write_text(
        json.dumps(generate(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
