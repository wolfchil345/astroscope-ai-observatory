"""Independent Skyfield/DE421 observing windows; no production-engine imports."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from skyfield.api import Star, load, load_file, wgs84
from skyfield.timelib import Timescale
from skyfield_data import get_skyfield_data_path

ROOT = Path(__file__).resolve().parents[2]


def generate():
    eop = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
    rows = json.loads(eop.read_text())["rows"]
    tt = np.array([r["MJD"] + 2400000.5 + 69.184 / 86400 for r in rows])
    base = load.timescale(builtin=True)
    ts = Timescale(
        lambda t: np.interp(t, tt, [69.184 - r["UT1_UTC"] for r in rows]),
        base.leap_dates,
        base.leap_offsets,
    )
    ts.polar_motion_table = (
        tt,
        np.array([r["PM_x"] for r in rows]),
        np.array([r["PM_y"] for r in rows]),
    )
    kernel = Path(get_skyfield_data_path()) / "de421.bsp"
    eph = load_file(str(kernel))
    windows = []
    sites = [
        ("equator", 0, 30, 0),
        ("greenwich", 51.4769, 0, 46),
        ("arctic", 78.2232, 15.6469, 20),
        ("paranal", -24.6272, -70.4042, 2635),
    ]
    for site in sites:
        for season, month, day in [("equinox", 3, 20), ("solstice", 6, 21)]:
            for target_name, ra, dec in [("equatorial", 180, 0), ("northern", 37.95, 89.26)]:
                start = datetime(2024, month, day, 16, tzinfo=UTC)
                jd0 = 2440587.5 + start.timestamp() / 86400
                # Explicit UTC instants, twelve-hour window, off-centre four-hour event.
                jd1 = jd0 + 0.5
                observer = eph["earth"] + wgs84.latlon(site[1], site[2], elevation_m=site[3])
                star = Star(ra_hours=ra / 15, dec_degrees=dec)
                grids = {}
                for count in (3, 9, 25, 241):
                    jds = [jd0 + (jd1 - jd0) * i / (count - 1) for i in range(count)]
                    dates = [
                        datetime(1970, 1, 1, tzinfo=UTC)
                        + timedelta(seconds=(jd - 2440587.5) * 86400)
                        for jd in jds
                    ]
                    seen = observer.at(ts.from_datetimes(dates))
                    apparent = seen.observe(star).apparent()
                    sun = seen.observe(eph["sun"]).apparent()
                    moon = seen.observe(eph["moon"]).apparent()
                    grids[str(count)] = {
                        "jd": jds,
                        "target_altitude_degrees": apparent.altaz()[0].degrees.tolist(),
                        "sun_altitude_degrees": sun.altaz()[0].degrees.tolist(),
                        "moon_separation_degrees": apparent.separation_from(moon).degrees.tolist(),
                    }
                windows.append(
                    {
                        "id": f"{site[0]}-{season}-{target_name}",
                        "site": dict(
                            zip(
                                (
                                    "name",
                                    "latitude_degrees",
                                    "longitude_degrees",
                                    "elevation_meters",
                                ),
                                site,
                                strict=True,
                            )
                        ),
                        "target": {
                            "name": target_name,
                            "right_ascension_degrees": ra,
                            "declination_degrees": dec,
                        },
                        "event": {
                            "planet_name": "supplied UTC example",
                            "transit_number": 0,
                            "observation_start_jd": jd0,
                            "observation_end_jd": jd1,
                            "ingress_jd": jd0 + 2 / 24,
                            "mid_transit_jd": jd0 + 4 / 24,
                            "egress_jd": jd0 + 6 / 24,
                            "timing_uncertainty_days": 0.0,
                        },
                        "grids": grids,
                    }
                )
    return {
        "mission": 54,
        "reference": "Skyfield 1.55 / DE421; WGS84; unrefracted",
        "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
        "eop_sha256": hashlib.sha256(eop.read_bytes()).hexdigest(),
        "windows": windows,
    }


if __name__ == "__main__":
    path = ROOT / "validation/fixtures/visibility_sampling_v1.json"
    path.write_text(json.dumps(generate(), indent=2, sort_keys=True, allow_nan=False) + "\n")
