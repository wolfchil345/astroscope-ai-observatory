# Mission 60 reference amendment — exact binary64 sky inputs

The original protocol/corpus freeze is `cb9ad18`. The full pilot result is
[retained](../../../validation/results/catalogue_quantities_pilot_v1.json),
including its dirty working-tree flag and source hashes. It reported 25 unmet
checks, including eight attributable to the harness/reference interface. It is
not the canonical scientific result.

Seven synthetic exoplanet CSVs omitted the required `discoverymethod` and
`tran_flag` header fields in the runner adapter. The parser correctly rejected
them. The runner now supplies neutral `synthetic`/`0` values. Numeric inputs,
expected results and application parsing are unchanged. These seven rejections
are not production defects.

For CQ0542, serialized RA spellings `179.89999999999998` and `359.9` differ by
`-180.00000000000002` in decimal arithmetic, but their exact binary64 values
differ by precisely `-180`. The v1 decimal oracle chose positive 180 after
wrapping, while the float API correctly chose negative 180. At the -85-degree
centre this creates an apparent sign reversal of 15.688 degrees. This was a
reference-interface error, not evidence of incorrect production wrapping.

The [amendment generator](../../../validation/reference_generation/catalogue_binary_inputs.py)
recalculates all 564 valid offset references from exact binary64 input values
using `Decimal.from_float`, 60-digit arithmetic and the same independent cosine.
Its [frozen record](../../../validation/fixtures/catalogue_binary_inputs_v2.json)
overrides only expected offset coordinates. Original inputs, spherical diagnostic
comparators, tolerance, cases, IDs and physical goals remain unchanged. The
original v1 files are retained unchanged and pinned by their original manifest.
The new v2 manifest additionally pins this amendment and its generator.

This amendment is made after observing the pilot and is explicitly not a
pre-pilot decision. It is committed before the corrected formal evaluation.
The pilot is retained to make that sequence reviewable. No newly discovered
production failure is removed by this correction. Independent wrap/sign controls
and a test of this exact binary-input distinction accompany the final runner.
