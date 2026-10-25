"""Stdlib-only Decimal score references and exhaustive schedule controls (Mission 55)."""

import itertools
import json
from decimal import Decimal as D
from decimal import localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def clip(x):
    return min(D(1), max(D(0), x))


def generate():
    cases = []

    def add(family, inputs, expected):
        cases.append(
            {
                "id": f"{family}-{len(cases):04}",
                "family": family,
                "inputs": inputs,
                "expected": expected,
            }
        )

    with localcontext() as ctx:
        ctx.prec = 60
        for x in [-90, -1, 0, 0.001, 20, 45, 74.999, 75, 75.001, 90]:
            add("planner_altitude", [x], str(45 * clip(D(str(x)) / 75)))
        for x in [None, 0.5, 1, 1.001, 2, 2.999, 3, 3.001, 10]:
            add("planner_airmass", [x], str(0 if x is None else 20 * clip((3 - D(str(x))) / 2)))
        for x in [-90, -18.001, -18, -17.999, -9, -0.001, 0, 0.001, 90]:
            add("planner_darkness", [x], str(15 * clip(-D(str(x)) / 18)))
        for minimum in [0, 30, 89.999, 90, 179.999, 180]:
            for sep in sorted({0, minimum, min(180, minimum + 0.001), 90, 180}):
                for moon in [False, True]:
                    ideal = D(90 if minimum < 90 else 180)
                    m, s = D(str(minimum)), D(str(sep))
                    value = (
                        D(20)
                        if moon or (s >= m and ideal == m)
                        else (D(0) if s < m else 20 * clip((s - m) / (ideal - m)))
                    )
                    add("planner_moon", [sep, minimum, moon], str(value))
        for family, values in [
            ("rank_altitude", [-90, 0, 0.001, 45, 89.999, 90, 100]),
            ("rank_moon", [0, 0.001, 45, 89.999, 90, 90.001, 180]),
            ("rank_depth", [0, 1, 100, 1000, 9999.999, 10000, 10000.001, 1e6]),
            ("rank_timing", [0, 0.001, 1, 2, 4, 20, 100, 2000]),
            ("rank_brightness", [-5, 4.999, 5, 5.001, 10.5, 15.999, 16, 16.001, 25]),
        ]:
            for x in values:
                q = D(str(x))
                value = {
                    "rank_altitude": lambda q=q: clip(q / 90),
                    "rank_moon": lambda q=q: clip(q / 90),
                    "rank_depth": lambda q=q: clip((1 + q).ln() / D(10001).ln()),
                    "rank_timing": lambda q=q: (-q / 2).exp(),
                    "rank_brightness": lambda q=q: clip((16 - q) / 11),
                }[family]()
                add(family, [x], str(value))
        base = dict(
            cloud_cover_percent=0,
            precipitation_probability_percent=0,
            precipitation_mm=0,
            visibility_m=20000,
            relative_humidity_percent=60,
            wind_speed_kmh=10,
            wind_gusts_kmh=0,
        )
        values = {
            "cloud_cover_percent": [0, 25, 50, 75, 100],
            "precipitation_probability_percent": [0, 25, 50, 75, 100],
            "precipitation_mm": [0, 0.499, 0.5, 0.501, 10],
            "visibility_m": [0, 10000, 19999.999, 20000, 20000.001, 1e6],
            "relative_humidity_percent": [0, 59.999, 60, 60.001, 80, 94.999, 95, 95.001, 100],
            "wind_speed_kmh": [0, 9.999, 10, 10.001, 25, 39.999, 40, 40.001, 100],
            "wind_gusts_kmh": [0, 59.999, 60, 60.001, 100],
        }
        weather = [dict(base, **{key: x}) for key, xs in values.items() for x in xs]
        weather += [
            dict(base, precipitation_mm=r, wind_gusts_kmh=g, cloud_cover_percent=c)
            for r, g, c in itertools.product([0, 0.5], [0, 60], [0, 100])
        ]
        for w in weather:
            q = {k: D(str(v)) for k, v in w.items()}
            score = (
                40 * (1 - q["cloud_cover_percent"] / 100)
                + 25 * (1 - q["precipitation_probability_percent"] / 100)
                + 15 * clip(q["visibility_m"] / 20000)
                + 10 * clip((95 - q["relative_humidity_percent"]) / 35)
                + 10 * clip((40 - q["wind_speed_kmh"]) / 30)
            )
            if q["precipitation_mm"] >= D("0.5"):
                score = min(score, D(25))
            if q["wind_gusts_kmh"] >= 60:
                score = min(score, D(20))
            add("weather", w, str(score.quantize(D("0.1"))))
        for family, cuts, labels in [
            (
                "planner_rating",
                [35, 50, 65, 80],
                ["poor", "fair", "good", "very_good", "excellent"],
            ),
            (
                "weather_rating",
                [30, 50, 65, 80],
                ["unsuitable", "poor", "fair", "good", "excellent"],
            ),
        ]:
            for x in [0, 100] + [c + offset for c in cuts for offset in [-0.001, 0, 0.001]]:
                add(family, [x], labels[sum(x >= c for c in cuts)])
        for spread, humidity in itertools.product(
            [0.999, 1, 1.001, 2.499, 2.5, 2.501, 4.999, 5, 5.001],
            [79.999, 80, 89.999, 90, 94.999, 95],
        ):
            severity = max(
                3 if spread <= 1 else 2 if spread <= 2.5 else 1 if spread <= 5 else 0,
                3 if humidity >= 95 else 2 if humidity >= 90 else 1 if humidity >= 80 else 0,
            )
            add("dew", [spread, 0, humidity], ["low", "moderate", "high", "critical"][severity])
    for missing, moon, status, threshold in itertools.product(
        [False, True],
        [False, True],
        ["observable", "low_altitude"],
        [44.5, 54.499, 54.5, 54.501, 64.5],
    ):
        total = D("54.5") - (10 if missing else 0) + (10 if moon else 0)
        add(
            "plan_entry",
            {"missing_airmass": missing, "moon": moon, "status": status, "threshold": threshold},
            {
                "total": str(total),
                "recommended": status == "observable" and total >= D(str(threshold)),
            },
        )
    rankings = []
    default = ["0.30", "0.15", "0.15", "0.10", "0.10", "0.10", "0.05", "0.05"]
    profiles = [default, [str(D(x) * 7) for x in default]]
    profiles += [[str(int(i == j)) for i in range(8)] for j in range(8)]
    profiles += [
        [str(D(x) * (D(2) if i == j else D(1))) for i, x in enumerate(default)] for j in range(8)
    ]
    for profile_index, weights in enumerate(profiles):
        for name, missing, high, full in [
            ("alpha", True, False, False),
            ("beta", False, False, False),
            ("gamma", False, True, True),
        ]:
            with localcontext() as ctx:
                ctx.prec = 60
                components = [
                    D("0.5"),
                    D("0.5"),
                    D(1),
                    D("0.5"),
                    D("0.5") if missing else D(int(high)),
                    D(-1).exp(),
                    D("0.5") if missing else D(int(high)),
                    D(int(full)),
                ]
                total = (
                    sum(c * D(w) for c, w in zip(components, weights, strict=True))
                    / sum(map(D, weights))
                    * 100
                )
            rankings.append(
                {
                    "id": f"profile{profile_index}-{name}",
                    "name": name,
                    "profile": profile_index,
                    "weights": weights,
                    "missing": missing,
                    "high": high,
                    "full": full,
                    "components": list(map(str, components)),
                    "expected_total": str(total),
                }
            )
    schedules = []
    for name, scores in [
        ("alternating", [[90, 89], [89, 90], [90, 89]]),
        ("constant", [[90, 80], [90, 80], [90, 80]]),
        ("exact_tie", [[70, 70], [70, 70], [70, 70]]),
    ]:
        for penalty in [0, 5, 20]:
            paths = list(itertools.product(range(2), repeat=len(scores)))
            utilities = [
                sum(scores[i][k] for i, k in enumerate(p))
                - penalty * sum(a != b for a, b in zip(p[:-1], p[1:], strict=True))
                for p in paths
            ]
            best = max(utilities)
            schedules.append(
                {
                    "id": f"{name}-cost{penalty}",
                    "scores": scores,
                    "switch_penalty": penalty,
                    "optimal_utility": best,
                    "optimal_paths": [
                        list(p) for p, u in zip(paths, utilities, strict=True) if u == best
                    ],
                }
            )
    return {
        "mission": 55,
        "reference": "Decimal precision 60; exhaustive 2^3 path enumeration",
        "cases": cases,
        "rankings": rankings,
        "schedules": schedules,
    }


if __name__ == "__main__":
    (ROOT / "validation/fixtures/heuristic_characterisation_v1.json").write_text(
        json.dumps(generate(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
