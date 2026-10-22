"""Independent stdlib Decimal/Fraction optical reference; never imports AstroScope."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal as D
from decimal import localcontext
from fractions import Fraction as Q
from itertools import product
from pathlib import Path


def atan(x):
    """Half-angle reduction followed by alternating series (no binary trig)."""
    multiplier = 1
    while abs(x) > D("0.1"):
        x = x / (1 + (1 + x * x).sqrt())
        multiplier *= 2
    term = total = x
    for n in range(1, 200):
        term *= -x * x
        addition = term / (2 * n + 1)
        total += addition
        if abs(addition) < D("1e-85"):
            break
    return multiplier * total


def field(size, focal, pi):
    return 360 * atan(size / (2 * focal)) / pi


def make_fixture():
    with localcontext() as ctx:
        ctx.prec = 90
        pi = 16 * atan(D(1) / 5) - 4 * atan(D(1) / 239)
        telescopes = [
            ("70", "700"),
            ("100", "900"),
            ("130", "650"),
            ("200", "1000"),
            ("203", "2032"),
        ]
        accessories = [("1", "1"), ("2", "1"), ("1", "0.63"), ("2.5", "0.8")]
        eyes = [("32", "50"), ("25", "50"), ("24", "68"), ("10", "50"), ("6", "60")]
        cameras = [
            (1936, 1096, "2.90"),
            (3008, 3008, "3.76"),
            (4144, 2822, "4.63"),
            (6248, 4176, "3.76"),
            (9576, 6388, "3.76"),
        ]
        rows = []

        def add(kind, inputs, expected, digits):
            rows.append(
                {
                    "id": f"{kind}-{sum(r['kind'] == kind for r in rows):03}",
                    "kind": kind,
                    "inputs": inputs,
                    "expected": {k: str(v) for k, v in expected.items()},
                    "digits": digits,
                }
            )

        for (a, f), (e, af), (b, r) in product(telescopes, eyes, accessories):
            aperture, focal, eye, apparent, barlow, reducer = map(D, (a, f, e, af, b, r))
            effective = focal * barlow * reducer
            expected = dict(
                native_focal_ratio=focal / aperture,
                effective_focal_length_mm=effective,
                effective_focal_ratio=effective / aperture,
                magnification=effective / eye,
                exit_pupil_mm=aperture * eye / effective,
                true_field_degrees=apparent * eye / effective,
                dawes_resolution_arcseconds=116 / aperture,
                rayleigh_resolution_arcseconds=138 / aperture,
                minimum_useful_magnification=aperture / 7,
                maximum_useful_magnification=2 * aperture,
            )
            digits = {
                k: 4
                if k
                in (
                    "true_field_degrees",
                    "dawes_resolution_arcseconds",
                    "rayleigh_resolution_arcseconds",
                )
                else 3
                for k in expected
            }
            add(
                "optical",
                dict(aperture=a, focal=f, eye=e, apparent=af, barlow=b, reducer=r),
                expected,
                digits,
            )

        setups = list(product(telescopes, cameras, accessories))
        setups += [(("50", f), (6000, 4000, "6"), ("1", "1")) for f in ("20", "50", "100")]
        setups += [
            (("50", "20"), (4000, 6000, "6"), ("1", "1")),
            (("50", "100000"), (1, 1, "1"), ("1", "1")),
        ]
        for (a, f), (w, h, p), (b, r) in setups:
            aperture, focal, pixel, barlow, reducer = map(D, (a, f, p, b, r))
            effective = focal * barlow * reducer
            width, height = w * pixel / 1000, h * pixel / 1000
            scale = D("206.265") * pixel / effective
            expected = dict(
                effective_focal_length_mm=effective,
                effective_focal_ratio=effective / aperture,
                sensor_width_mm=width,
                sensor_height_mm=height,
                megapixels=D(w * h) / 1000000,
                image_scale_arcsec_per_pixel=scale,
                field_width_degrees=field(width, effective, pi),
                field_height_degrees=field(height, effective, pi),
                field_diagonal_degrees=field(
                    (width * width + height * height).sqrt(), effective, pi
                ),
                seeing_disk_pixels=2 / scale,
                dawes_resolution_arcseconds=116 / aperture,
                dawes_resolution_pixels=116 / aperture / scale,
                ideal_scale_min_arcsec_per_pixel=D(2) / 3,
                ideal_scale_max_arcsec_per_pixel=D(1),
            )
            three = (
                "effective_focal_length_mm",
                "effective_focal_ratio",
                "sensor_width_mm",
                "sensor_height_mm",
                "megapixels",
                "seeing_disk_pixels",
                "dawes_resolution_pixels",
            )
            add(
                "imaging",
                dict(aperture=a, focal=f, width=w, height=h, pixel=p, barlow=b, reducer=r),
                expected,
                {k: 3 if k in three else 4 for k in expected},
            )

        for size, focal in [
            ("1", "100000"),
            ("24", "650"),
            ("50", "200"),
            ("2", "1"),
            ("200", "1"),
            ("0.001", "10000"),
        ]:
            add(
                "field",
                dict(size=size, focal=focal),
                {"field_degrees": field(D(size), D(focal), pi)},
                {"field_degrees": None},
            )

        # Independent tiling oracle enumerates coverage until sufficient, no ceil formula.
        for fw, fh, overlap, tw, th in product(
            ["1", "2"], ["1", "0.5"], ["0", "25", "50"], ["0.5", "1", "1.75", "2.5"], ["0.5", "1.5"]
        ):
            fwq, fhq, oq, twq, thq = map(Q, (fw, fh, overlap, tw, th))
            step_fraction = 1 - oq / 100

            def cover(field_size, target, step_fraction):
                n, coverage = 1, field_size
                while coverage < target:
                    n += 1
                    coverage += field_size * step_fraction
                return n, coverage

            nx, cx = cover(fwq, twq, step_fraction)
            ny, cy = cover(fhq, thq, step_fraction)
            expected = dict(
                panels_horizontal=nx,
                panels_vertical=ny,
                total_panels=nx * ny,
                covered_width_degrees=D(cx.numerator) / D(cx.denominator),
                covered_height_degrees=D(cy.numerator) / D(cy.denominator),
                width_fill_percent=D(tw) / D(fw) * 100,
                height_fill_percent=D(th) / D(fh) * 100,
            )
            digits = {
                k: 0
                if k.startswith("panels") or k == "total_panels"
                else 2
                if k.endswith("percent")
                else 4
                for k in expected
            }
            add(
                "mosaic",
                dict(width=fw, height=fh, overlap=overlap, target_width=tw, target_height=th),
                expected,
                digits,
            )
        return {
            "schema_version": "1.0",
            "precision": 90,
            "reference": "Decimal analytic geometry; Fraction enumerated planar tiling",
            "pi": str(pi),
            "exact_plate_scale_constant": str(D(648) / pi),
            "cases": rows,
        }


def encoded_fixture():
    return json.dumps(make_fixture(), indent=2, sort_keys=True, allow_nan=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(encoded_fixture(), encoding="utf-8")


if __name__ == "__main__":
    main()
