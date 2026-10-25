"""Transparent Mission 60 amendment: evaluate sky references at exact binary64 inputs.

The v1 corpus, generator and preliminary result remain frozen. The production API
accepts floats, not the decimal spellings used to serialize them. No tolerance,
input, domain requirement or physical model changes here.
"""

import json
from decimal import Decimal as D
from decimal import localcontext

from validation.reference_generation.catalogue_quantities import PI, ROOT, cosine, generate


def generate_amendment():
    replacements = []
    with localcontext() as ctx:
        ctx.prec = 60
        for case in generate()["cases"]:
            if case["family"] != "offsets" or case["requirement"] != "value":
                continue
            ra, dec, cra, cdec = [D.from_float(float(x)) for x in case["inputs"]]
            delta = ra - cra
            while delta < -180:
                delta += 360
            while delta >= 180:
                delta -= 360
            replacements.append(
                {
                    "id": case["id"],
                    "expected": [str(delta * cosine(cdec * PI / 180)), str(dec - cdec)],
                }
            )
    return {
        "mission": 60,
        "version": 2,
        "reason": "Reference uses exact binary64 API inputs, not serialized decimal coordinates",
        "pilot_case": "CQ0542",
        "original_freeze_commit": "cb9ad18",
        "inputs_changed": False,
        "tolerances_changed": False,
        "production_changed": False,
        "replacements": replacements,
    }


if __name__ == "__main__":
    (ROOT / "validation/fixtures/catalogue_binary_inputs_v2.json").write_text(
        json.dumps(generate_amendment(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
