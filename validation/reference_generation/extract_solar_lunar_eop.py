"""Extract frozen 2024 IERS observations; not a celestial-reference generator."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from astropy.utils import iers

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA256 = "6c1e052b7822ba84e793e28aa14080552f53d5c66b739cd0e67cb4b46d0e7815"


def main() -> None:
    source = Path(iers.IERS_B_FILE)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Wrong IERS source: install the constrained data package")
    table = iers.IERS_B.open(str(source))
    rows = [
        {k: float(r[k].value) for k in ["MJD", "UT1_UTC", "PM_x", "PM_y"]}
        for r in table[(table["MJD"].value >= 60300) & (table["MJD"].value <= 60700)]
    ]
    payload = {
        "source": "https://hpiers.obspm.fr/iers/eop/eopc04/eopc04.1962-now",
        "source_sha256": digest,
        "source_filename": source.name,
        "distribution": importlib.metadata.version("astropy-iers-data"),
        "units": {"MJD": "day", "UT1_UTC": "second", "PM_x": "arcsecond", "PM_y": "arcsecond"},
        "rows": rows,
    }
    (ROOT / "validation/fixtures/solar_lunar_eop_v1.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
