"""Independent Skyfield/DE421 planetary corpus; no AstroScope/Astropy/ERFA imports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from skyfield.api import load, load_file, wgs84
from skyfield.timelib import Timescale
from skyfield_data import get_skyfield_data_path

ROOT = Path(__file__).resolve().parents[2]
EOP = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
POLICY = ROOT / "validation/manifests/planetary_positions_policy_v1.json"
TARGETS = {
    "mercury": 1,
    "venus": 2,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
    "uranus": 7,
    "neptune": 8,
}
SITES = [
    ("tokyo", 35.6762, 139.6503, 40),
    ("equator", 0, 30, 0),
    ("paranal", -24.6272, -70.4042, 2635),
    ("greenwich", 51.4769, 0.0005, 46),
    ("arctic", 78.2232, 15.6469, 20),
    ("antarctic", -75.1, 123.35, 3233),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate():
    rows = json.loads(EOP.read_text())["rows"]
    tt = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in rows])
    delta = np.array([69.184 - r["UT1_UTC"] for r in rows])
    base = load.timescale(builtin=True)
    ts = Timescale(lambda t: np.interp(t, tt, delta), base.leap_dates, base.leap_offsets)
    ts.polar_motion_table = (
        tt,
        np.array([r["PM_x"] for r in rows]),
        np.array([r["PM_y"] for r in rows]),
    )
    kernel = Path(get_skyfield_data_path()) / "de421.bsp"
    eph = load_file(str(kernel))
    cases = []

    def add(body, site, dt, category):
        name, lat, lon, height = site
        observer = eph["earth"] + wgs84.latlon(lat, lon, elevation_m=height)
        t = ts.from_datetime(dt)
        seen = observer.at(t)
        astrometric = seen.observe(eph[TARGETS[body]])
        apparent = astrometric.apparent()
        sun = seen.observe(eph["sun"]).apparent()
        moon = seen.observe(eph["moon"]).apparent()
        ra, dec, _ = apparent.radec()
        alt, az, _ = apparent.altaz()
        cases.append(
            {
                "id": f"{body}-{sum(c['body'] == body for c in cases):03}",
                "body": body,
                "target_id": TARGETS[body],
                "category": category,
                "utc": dt.isoformat(),
                "site": {
                    "name": name,
                    "latitude_deg": lat,
                    "longitude_deg": lon,
                    "elevation_m": height,
                },
                "reference": {
                    "ra_degrees": float(ra.hours * 15),
                    "dec_degrees": float(dec.degrees),
                    "distance_au": float(astrometric.distance().au),
                    "distance_km": float(astrometric.distance().km),
                    "altitude_degrees": float(alt.degrees),
                    "azimuth_degrees": float(az.degrees),
                    "solar_elongation_degrees": float(apparent.separation_from(sun).degrees),
                    "moon_separation_degrees": float(apparent.separation_from(moon).degrees),
                },
            }
        )

    for body in TARGETS:
        for site in SITES:
            for day in ("2024-03-20", "2024-06-21", "2024-09-22", "2024-12-21"):
                for clock in ("00:00:00", "12:00:00", "23:59:59.500000"):
                    add(
                        body,
                        site,
                        datetime.fromisoformat(day + "T" + clock + "+00:00"),
                        "season_grid",
                    )
        for month in range(1, 13):
            add(body, SITES[0], datetime(2024, month, 15, 6, tzinfo=UTC), "monthly")
        dates = [datetime(2024, 1, 1, 12, tzinfo=UTC) + timedelta(days=i) for i in range(366)]
        t = ts.from_datetimes(dates)
        seen = (eph["earth"] + wgs84.latlon(0, 30)).at(t)
        elong = (
            seen.observe(eph[TARGETS[body]])
            .apparent()
            .separation_from(seen.observe(eph["sun"]).apparent())
            .degrees
        )
        for tag, index in [
            ("daily_min_elongation", np.argmin(elong)),
            ("daily_max_elongation", np.argmax(elong)),
        ]:
            add(body, SITES[1], dates[int(index)], tag)
        # A constructed physical location under the geocentric apparent direction.
        dt = datetime(2024, 3, 20, 12, tzinfo=UTC)
        t = ts.from_datetime(dt)
        ra, dec, _ = eph["earth"].at(t).observe(eph[TARGETS[body]]).apparent().radec(epoch=t)
        longitude = (ra.hours * 15 - t.gast * 15 + 180) % 360 - 180
        add(body, (f"zenith_{body}", float(dec.degrees), float(longitude), 0), dt, "zenith")
        # Select reference-only threshold snapshots; not a production event API benchmark.
        observer = eph["earth"] + wgs84.latlon(0, 30)

        def altitude(seconds, observer=observer, body=body, dt=dt):
            at = ts.from_datetime(dt + timedelta(seconds=seconds))
            return float(observer.at(at).observe(eph[TARGETS[body]]).apparent().altaz()[0].degrees)

        for threshold in (0, 20):
            grid = list(range(0, 86401, 3600))
            values = [altitude(s) - threshold for s in grid]
            bracket = next(
                (a, b)
                for a, b, x, y in zip(grid[:-1], grid[1:], values[:-1], values[1:], strict=True)
                if x * y < 0
            )
            left, right = bracket
            sign = altitude(left) - threshold
            for _ in range(36):
                mid = (left + right) / 2
                if (altitude(mid) - threshold) * sign > 0:
                    left = mid
                else:
                    right = mid
            add(
                body,
                SITES[1],
                dt + timedelta(seconds=(left + right) / 2),
                f"altitude_boundary_{threshold}",
            )
    fixture = {
        "schema_version": "1.0",
        "reference": {
            "engine": "Skyfield",
            "versions": {
                p: importlib.metadata.version(p)
                for p in ("skyfield", "skyfield-data", "numpy", "jplephem", "sgp4")
            },
            "kernel": "de421.bsp",
            "kernel_sha256": sha(kernel),
            "kernel_source": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
            "eop_sha256": sha(EOP),
            "policy_sha256": sha(POLICY),
            "generator_sha256": sha(Path(__file__)),
            "independence": (
                "No production, Astropy or ERFA imports; shared measured EOP and WGS84 conventions"
            ),
            "conventions": json.loads(POLICY.read_text())["conventions"],
            "randomness": "none",
            "precision": "float64; UTC datetime microseconds",
            "licensing": (
                "Original computed reference values under repository MIT; "
                "kernel not redistributed; Skyfield MIT, bundled DE421 provenance "
                "inherited from Missions 33/34"
            ),
        },
        "cases": cases,
    }
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = generate()
    args.output.write_text(json.dumps(fixture, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(dict(Counter(c["body"] for c in fixture["cases"])))


if __name__ == "__main__":
    main()
