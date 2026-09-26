"""Reproduce the committed IERS observations; this does not generate sky coordinates."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from astropy.time import Time
from astropy.utils import iers

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "validation/fixtures/celestial_eop_v1.json"
SOURCE_SHA256 = "6c1e052b7822ba84e793e28aa14080552f53d5c66b739cd0e67cb4b46d0e7815"


def main() -> None:
    source = Path(iers.IERS_B_FILE)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Install the pinned astropy-iers-data version before extraction")
    table = iers.IERS_B.open(str(source))
    rows = []
    for day in ["2024-03-20", "2024-06-21", "2024-09-22", "2024-12-21"]:
        mjd = Time(day).mjd
        for row in table[(table["MJD"].value >= mjd - 1) & (table["MJD"].value <= mjd + 2)]:
            rows.append({k: float(row[k].value) for k in ["MJD", "UT1_UTC", "PM_x", "PM_y"]})
    payload = {
        "source": "https://hpiers.obspm.fr/iers/eop/eopc04/eopc04.1962-now",
        "source_filename": source.name,
        "source_sha256": digest,
        "distribution": importlib.metadata.version("astropy-iers-data"),
        "units": {"MJD": "day", "UT1_UTC": "second", "PM_x": "arcsecond", "PM_y": "arcsecond"},
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
