"""Independent frozen Skyfield/DE421 reference generation; no production imports."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from skyfield.api import Star, load, load_file, wgs84
from skyfield.searchlib import find_discrete, find_maxima, find_minima
from skyfield.timelib import Timescale
from skyfield_data import get_skyfield_data_path

ROOT = Path(__file__).resolve().parents[2]
EOP = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
POLICY = ROOT / "validation/manifests/solar_lunar_twilight_policy_v1.json"
FIXTURE = ROOT / "validation/fixtures/solar_lunar_twilight_v1.json"
MANIFEST = ROOT / "validation/manifests/solar_lunar_twilight_v1.json"
SITES = [
    ("tokyo", 35.6762, 139.6503, 40),
    ("equator", 0.0, 30.0, 0),
    ("paranal", -24.6272, -70.4042, 2635),
    ("greenwich", 51.4769, 0.0005, 46),
    ("arctic", 78.2232, 15.6469, 20),
    ("antarctic", -75.1, 123.35, 3233),
]
SEASONS = ["2024-03-20", "2024-06-21", "2024-09-22", "2024-12-21"]
PHASE_DATES = ["2024-03-10", "2024-03-17", "2024-03-25", "2024-04-02"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate() -> None:
    rows = json.loads(EOP.read_text())["rows"]
    daily_tt = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in rows])
    delta = np.array([69.184 - r["UT1_UTC"] for r in rows])
    base = load.timescale(builtin=True)
    ts = Timescale(lambda tt: np.interp(tt, daily_tt, delta), base.leap_dates, base.leap_offsets)
    ts.polar_motion_table = (
        daily_tt,
        np.array([r["PM_x"] for r in rows]),
        np.array([r["PM_y"] for r in rows]),
    )
    kernel = Path(get_skyfield_data_path()) / "de421.bsp"
    eph = load_file(str(kernel))
    cases: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    target = Star(ra_hours=6.0, dec_degrees=20.0)
    for name, lat, lon, height in SITES:
        site = {"name": name, "latitude_deg": lat, "longitude_deg": lon, "elevation_m": height}
        observer = eph["earth"] + wgs84.latlon(lat, lon, elevation_m=height)

        def snapshot(dt: datetime, category: str, observer=observer, site=site) -> None:
            t = ts.from_datetime(dt)
            seen = observer.at(t)
            sun = seen.observe(eph["sun"]).apparent()
            moon = seen.observe(eph["moon"]).apparent()
            star = seen.observe(target).apparent()
            sa, sz, _ = sun.altaz()
            ma, mz, _ = moon.altaz()
            ta, _, _ = star.altaz()
            separation = float(sun.separation_from(moon).degrees)
            physical = float(moon.fraction_illuminated(eph["sun"]))
            cases.append(
                {
                    "id": f"{site['name']}_{len(cases):04}",
                    "site": site,
                    "utc": dt.isoformat(),
                    "category": category,
                    "reference": {
                        "sun_altitude": float(sa.degrees),
                        "sun_azimuth": float(sz.degrees),
                        "moon_altitude": float(ma.degrees),
                        "moon_azimuth": float(mz.degrees),
                        "sun_moon_separation": separation,
                        "illumination_model": (1 - math.cos(math.radians(separation))) / 2,
                        "illumination_physical": physical,
                        "target_altitude": float(ta.degrees),
                    },
                }
            )

        for day in SEASONS + PHASE_DATES:
            for clock in ["00:00:00", "06:00:00", "12:00:00", "23:59:59.500000"]:
                snapshot(
                    datetime.fromisoformat(day + "T" + clock + "+00:00"),
                    "season" if day in SEASONS else "lunar_phase_region",
                )
        for day in SEASONS:
            start = datetime.fromisoformat(day + "T12:00:00+00:00")
            end = start + timedelta(days=1)
            t0, t1 = ts.from_datetime(start), ts.from_datetime(end)
            for body in ["sun", "moon"]:

                def altitude(t, body=body, observer=observer):
                    return observer.at(t).observe(eph[body]).apparent().altaz()[0].degrees

                altitude.step_days = 1 / 24
                maxima_t, maxima = find_maxima(t0, t1, altitude, epsilon=0.001 / 86400)
                minima_t, minima = find_minima(t0, t1, altitude, epsilon=0.001 / 86400)
                endpoints = [float(altitude(t0)), float(altitude(t1))]
                minimum = float(min([*endpoints, *minima]))
                maximum = float(max([*endpoints, *maxima]))
                for threshold in [0.0, -6.0, -12.0, -18.0] if body == "sun" else [0.0]:

                    def above(t, threshold=threshold, altitude=altitude):
                        return altitude(t) > threshold

                    above.step_days = 300 / 86400
                    roots, flags = find_discrete(t0, t1, above, epsilon=0.001 / 86400)
                    events = []
                    for t, rising in zip(roots, flags, strict=True):
                        seconds = float((t.tt - t0.tt) * 86400)
                        if seconds >= 86400:
                            continue
                        slope = float(
                            (
                                altitude(ts.tt_jd(t.tt + 1 / 86400))
                                - altitude(ts.tt_jd(t.tt - 1 / 86400))
                            )
                            * 1800
                        )
                        events.append(
                            {
                                "seconds": seconds,
                                "direction": "rising" if rising else "setting",
                                "slope_arcsec_per_second": slope,
                                "utc": t.utc_datetime().isoformat(),
                            }
                        )
                        # Fixed classifications just before/at/after crossings, all archived.
                        if name in ["tokyo", "arctic"]:
                            for offset in [-120, 0, 120]:
                                snapshot(
                                    t.utc_datetime() + timedelta(seconds=offset),
                                    f"{body}_threshold_{threshold}_{offset:+d}s",
                                )
                    state = (
                        "crossings"
                        if events
                        else "always_above"
                        if minimum > threshold
                        else "always_below"
                        if maximum < threshold
                        else "grazing_indeterminate"
                    )
                    windows.append(
                        {
                            "id": f"{name}_{day}_{body}_{threshold}",
                            "site": site,
                            "start_utc": start.isoformat(),
                            "end_utc": end.isoformat(),
                            "body": body,
                            "threshold": threshold,
                            "reference": {
                                "events": events,
                                "state": state,
                                "minimum_altitude": minimum,
                                "maximum_altitude": maximum,
                                "extrema_utc": [
                                    t.utc_datetime().isoformat() for t in [*minima_t, *maxima_t]
                                ],
                            },
                        }
                    )
        print(name, len(cases), len(windows), flush=True)
    fixture = {
        "schema_version": "1.0",
        "reference": {
            "engine": "Skyfield",
            "versions": {
                p: importlib.metadata.version(p)
                for p in ["skyfield", "skyfield-data", "numpy", "jplephem", "sgp4"]
            },
            "kernel": "de421.bsp",
            "kernel_sha256": sha(kernel),
            "kernel_source": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
            "generator_sha256": sha(Path(__file__)),
            "eop_sha256": sha(EOP),
            "policy_sha256": sha(POLICY),
            "precision": "float64; UTC microseconds; 0.001s event searches",
            "conventions": json.loads(POLICY.read_text())["conventions"],
            "event_reference": "Skyfield find_discrete (300s grid) and find_minima/find_maxima",
            "independence": "No AstroScope/Astropy/ERFA imports; shared frozen IERS measurements",
        },
        "cases": cases,
        "windows": windows,
    }
    FIXTURE.write_text(json.dumps(fixture, indent=2, allow_nan=False) + "\n")
    manifest = {
        "schema_version": "1.0",
        "benchmark_id": "solar-lunar-twilight-v1",
        "case_count": len(cases),
        "window_count": len(windows),
        "files": {str(p.relative_to(ROOT)): sha(p) for p in [FIXTURE, EOP, POLICY]},
        "generator_sha256": sha(Path(__file__)),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(cases)} snapshots and {len(windows)} event windows")


if __name__ == "__main__":
    generate()
