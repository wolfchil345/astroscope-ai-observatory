"""Freeze independent injected signals and a deterministic Kepler archive selection."""

import hashlib
import json
import math
import random
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = "validation/fixtures/published/kplr006922244-2010078095331_llc.fits"
URL = (
    "https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:Kepler/url/missions/kepler/"
    "lightcurves/0069/006922244/kplr006922244-2010078095331_llc.fits"
)


def synthetic():
    cases = []
    for kind in ["sine", "box", "white_null", "red_null", "constant"]:
        regimes = (
            ["uniform", "gap", "daily", "trend", "outlier"]
            if kind in ["sine", "box"]
            else ["uniform"]
        )
        seeds = range(2) if kind in ["sine", "box"] else range(10) if kind != "constant" else [0]
        for regime in regimes:
            for seed in seeds:
                rng = random.Random(56000 + seed)
                times = [round(i * 0.06 + 0.003 * rng.random(), 12) for i in range(500)]
                if regime == "gap":
                    times = [t for t in times if not 8 < t < 19]
                if regime == "daily":
                    times = [t for t in times if t % 1 < 0.25]
                period = 2.7
                values = []
                errors = []
                red = 0.0
                for i, t in enumerate(times):
                    sigma = 0.001 * (1 + (i % 3) / 2)
                    z = rng.gauss(0, 1)
                    red = 0.9 * red + math.sqrt(1 - 0.9**2) * sigma * z
                    noise = red if kind == "red_null" else sigma * z
                    signal = (
                        0.015 * math.sin(2 * math.pi * t / period)
                        if kind == "sine"
                        else (
                            -0.015
                            if kind == "box"
                            and abs((t - 0.4 + period / 2) % period - period / 2) < 0.09
                            else 0
                        )
                    )
                    value = 1 + signal + (0 if kind == "constant" else noise)
                    if regime == "trend":
                        value *= 1 + 0.02 * t
                    if regime == "outlier" and i % 41 == 0:
                        value += 0.1
                    values.append(round(value, 14))
                    errors.append(sigma)
                cases.append(
                    {
                        "id": f"{kind}-{regime}-{seed}",
                        "kind": kind,
                        "regime": regime,
                        "seed": 56000 + seed,
                        "time_standard": "synthetic_elapsed_days; no absolute time coordinate",
                        "times": times,
                        "values": values,
                        "uncertainties": errors,
                        "injected_period": period if kind in ["sine", "box"] else None,
                        "injected_depth": 0.015 if kind == "box" else None,
                        "injected_duration": 0.18 if kind == "box" else None,
                        "injected_epoch": 0.4 if kind == "box" else None,
                    }
                )
    return cases


def published():
    # FITS decoding only: no period-search or production API is called here.
    from astropy.io import fits

    raw = (ROOT / RAW).read_bytes()
    integrity = []
    with fits.open(ROOT / RAW) as hdus:
        for hdu in hdus:
            info = hdu.fileinfo()
            start, end = info["hdrLoc"], info["datLoc"] + info["datSpan"]
            total = sum(x[0] for x in struct.iter_unpack(">I", raw[start:end]))
            while total >> 32:
                total = (total & 0xFFFFFFFF) + (total >> 32)
            assert total == 0xFFFFFFFF, "Raw HDU checksum failed"
            integrity.append(
                {"name": hdu.name, "start": start, "end": end, "raw_ones_complement": total}
            )
        data = hdus[1].data
        hdr = hdus[1].header
        assert hdr["TIMESYS"] == "TDB" and hdr["TIMEREF"] == "SOLARSYSTEM"
        assert hdr["BJDREFI"] == 2454833 and hdr["BJDREFF"] == 0 and hdr["TIMEUNIT"] == "d"
        origin = min(float(x) for x in data["TIME"] if math.isfinite(x))
        rows = []
        counts = {
            "total_rows": len(data),
            "outside_first_30_days": 0,
            "nonfinite_or_nonpositive_error": 0,
            "nonzero_quality": 0,
            "retained": 0,
        }
        for index, row in enumerate(data):
            t, y, e = map(float, [row["TIME"], row["PDCSAP_FLUX"], row["PDCSAP_FLUX_ERR"]])
            if not all(map(math.isfinite, [t, y, e])) or e <= 0:
                counts["nonfinite_or_nonpositive_error"] += 1
            elif not origin <= t < origin + 30:
                counts["outside_first_30_days"] += 1
            elif row["SAP_QUALITY"] != 0:
                counts["nonzero_quality"] += 1
            else:
                rows.append((index, t, y, e))
        counts["retained"] = len(rows)
        provenance = {
            "source_url": URL,
            "hdu_integrity": integrity,
            "initial_astropy_8_0_2_checksum_results": [1, 0, 0],
            "datasum_present": False,
            "mirror_byte_identity": (
                "MAST API, archive missions URL and STScI public S3 URL yielded identical SHA256"
            ),
            "raw_sha256": hashlib.sha256((ROOT / RAW).read_bytes()).hexdigest(),
            "retrieved_date_utc": "2026-10-25",
            "object": hdus[0].header["OBJECT"],
            "quarter": hdus[0].header["QUARTER"],
            "data_release": hdus[0].header["DATA_REL"],
            "processing_version": hdus[0].header["PROCVER"],
            "time_header": {
                k: hdr[k] for k in ["TIMESYS", "TIMEREF", "BJDREFI", "BJDREFF", "TIMEUNIT"]
            },
            "flux_unit": hdus[1].columns["PDCSAP_FLUX"].unit,
            "first_finite_bkjd": origin,
            "row_counts_exclusive_in_filter_order": counts,
            "retained_zero_based_rows": [r[0] for r in rows],
            "rights": (
                "Public Kepler mission archive data; MAST data-use policy; "
                "not relicensed as repository code"
            ),
            "rights_url": "https://archive.stsci.edu/publishing/data-use",
            "reference": (
                "Jenkins et al. 2010, arXiv:1001.0416v1 abstract; rounded period 3.523 days"
            ),
            "reference_url": "https://arxiv.org/pdf/1001.0416v1",
        }
    return {
        "id": "kepler8-q4-first30days",
        "kind": "published_transit",
        "regime": "archive",
        "seed": None,
        "time_standard": "BKJD_TDB = BJD_TDB - 2454833; days; archive-supplied, not converted",
        "times": [r[1] for r in rows],
        "values": [r[2] for r in rows],
        "uncertainties": [r[3] for r in rows],
        "injected_period": None,
        "published_period": 3.523,
        "provenance": provenance,
    }


if __name__ == "__main__":
    out = ROOT / "validation/fixtures/light_curve_campaign_v1.json"
    out.write_text(
        json.dumps(
            {"mission": 56, "cases": synthetic() + [published()]},
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
