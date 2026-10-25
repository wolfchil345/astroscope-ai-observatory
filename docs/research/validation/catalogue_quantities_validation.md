# Mission 60 — Catalogue-Derived Quantity and Educational-Model Validation

## Decision

**The bounded validation dossier is delivered, but scientific acceptance is not
complete: 894 of 911 cases meet the fixed goals and 17 do not. G59-01 remains
open.** No production calculation is changed in this mission. CI reproduces the
complete observed baseline and retains the 17 strict expected failures. A green
reproduction audit does not convert these failures into scientific acceptance.

The baseline is Mission 59 merge `9303287a591026b63921844630e90b772bfa0226`.
[Post-merge Quality Gate 40213548200](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/40213548200)
passed 6,120 tests with nine historical expected failures in 346.19 seconds.
Its 26 artifact identities and expiry states were checked. No baseline archives
were downloaded in this mission; Mission 59's separate four-archive verification
remains in that PR. The original Phase 2 roadmap, all historical research results,
strict transit restrictions and X01 unknowns are preserved.

The [findings ledger](../evidence/catalogue_quantities_findings_v1.json) maps all
17 case IDs to their dispositions. The
[canonical result](../../../validation/results/catalogue_quantities_reference_run.json)
records a clean implementation commit `105a7ace4e423966bf95365a8f235cddd56df21f`,
OS/architecture, Python and numerical package versions, source/input hashes and
all results. Final PR CI verifies the final published head separately.

## Protocol, independent references and audit trail

1. `cb9ad18` froze the [protocol](catalogue_quantities_protocol.md), 911-case
   corpus, tolerances, domains, independent generator and source register before
   production evaluation. This was source-informed, not blinded.
2. The first pilot found 25 unmet checks. Its full
   [record](../../../validation/results/catalogue_quantities_pilot_v1.json) and
   original runner were retained in `4062f45`. The pilot truthfully records a
   dirty working tree and is not the canonical result.
3. Seven CSV failures were harness omissions of required nonnumeric headers.
   One sky-offset failure arose from comparing decimal coordinate spellings to a
   binary64 API at the exact RA-wrap boundary. The
   [explicit amendment](catalogue_reference_amendment.md), frozen at `fc10164`
   before formal evaluation, corrects these interface errors. It preserves all
   original files, numeric inputs, IDs, tolerances and scientific goals.
4. Formal evaluation at the clean amended commit found 17 acceptance failures.
   The full observed baseline, tests and CI audit were committed, then the clean
   canonical run above reproduced all results. No production failure was removed
   by the reference amendment.

References use 60-digit Decimal arithmetic, exact Fraction ramps and independently
constructed spherical vectors. Regeneration imports neither AstroScope nor its
numerical/plotting dependencies. This establishes independent numerical checks
of stated formulas, not independent observations or astrophysical calibration.
The original and amended generators regenerate their frozen files byte-for-byte
in the tested environment. Frozen replay is the CI path; numerical libraries and
libm may differ on untested platforms, so universal bitwise portability is not
claimed.

The [source register](../../../validation/manifests/catalogue_quantities_sources_v1.json)
contains URLs, factual constants, retrieval limitations and original summaries:

- [Gaia DR3 field definitions](https://irsa.ipac.caltech.edu/data/Gaia/dr3/gaia_dr3_source_colDescriptions.html)
  establish units and field meanings. The official ESA full datamodel page
  returned 503 during this review; its indexed norm definition and accessible
  IRSA schema are distinguished in the register.
- [Bailer-Jones (2015), v2](https://arxiv.org/abs/1507.02105v2) motivates keeping
  reciprocal parallax separate from noisy-distance inference.
- [IAU 2015 Resolution B3](https://arxiv.org/html/1510.07674v1),
  [JPL parameters](https://ssd.jpl.nasa.gov/astro_par.html) and the
  [NASA Earth fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html)
  supply the nominal radii, astronomical unit and mean-radius comparison.
- [Exoplanet Archive calculation notes](https://exoplanetarchive.ipac.caltech.edu/docs/pscp_calc.html)
  supply spherical density and the warning that composite parameters can combine
  references. [Winn (2010), v5](https://arxiv.org/html/1001.2010v5) supplies the
  transit-geometry context. Neither source calibrates the product's temperate
  thresholds or its piecewise-linear illustration.

No live catalogue query, real source selection, raw binary download or external
paper redistribution is required. Synthetic fixtures are authored repository
material. External sources retain their own rights; no blanket licence is implied.

## Coverage and results

| Family | Cases | Unmet goals | Interpretation |
|---|---:|---:|---|
| Naive Gaia distance | 14 | 1 | Positive-parallax reciprocal, invalid/missing fields and overflow |
| Absolute G magnitude | 34 | 0 | Distance-modulus arithmetic; no extinction or zero-point correction |
| Gaia CSV derived fields | 14 | 0 | Colour, SNR, proper-motion norm, supplied-field precedence and missing values |
| Local-sky offsets | 572 | 6 | 560 spherical probes, four arithmetic controls, eight invalid-coordinate checks |
| Planet density | 45 | 2 | Declared approximate Earth normalization, invalid inputs and extreme magnitudes |
| Radius-ratio depth | 30 | 2 | Uniform-disk arithmetic, invalid inputs and greater-than-unit depth |
| Circular geometric probability | 54 | 0 | Includes nine capped non-exterior-orbit cases, without physical validity |
| Temperate screen | 82 | 2 | Closed thresholds, OR conflicts, missing and nonfinite inputs |
| Trapezoidal illustration | 55 | 2 | 36 multitime curves, empty input, invalid parameters and degenerate duration |
| Individual conversion constants | 3 | 1 | Independent mean/equatorial/Sun/au comparisons at stated rounding precision |
| Common-radius coherence | 1 | 1 | Same Earth-radius label must not silently imply two SI radii |
| Exoplanet CSV derived fields | 7 | 0 | Missing fields, recalculation precedence and ignored eccentricity |
| **Total** | **911** | **17** | **894 meet the goals; no aggregate scientific acceptance** |

The catalogue parser sanitizes nonfinite optional fields before calculation.
Consequently the two radius-screen failures are direct-function cases; the tested
CSV path maps those fields to unknown. Finite extreme values can still reach
derived calculations. Supplied finite Gaia colour and SNR values override
recomputed fallbacks even when inconsistent. Passing these cases documents
precedence; it does not certify catalogue consistency.

Exoplanet density/depth are recalculated rather than taken from `pl_dens` or
`pl_trandep`. The circular probability does not use the stored eccentricity.
Mass provenance (including minimum-mass interpretations), limit flags, parameter
references and joint-fit covariance are not represented by the compact record.
No strict transit ephemeris adapter or uncertainty provenance is created here.

## Retained failures and required dispositions

| Finding | Failed cases | Evidence and next action |
|---|---|---|
| G60-01 Conversion conventions | CQ0895, CQ0897 | Earth/AU differs from the chosen IAU nominal equatorial reference beyond its final-digit rounding interval; depth and probability imply Earth radii differing by 7.123 km. Choose and document a consistent input-unit convention before correction |
| G60-02 Source-coordinate domain | CQ0750–CQ0755 | Nonfinite/out-of-range source RA or Dec is not rejected by the offset helper. Define and enforce source-domain handling; centre-domain rejection already passes |
| G60-03 Screen invalid radius | CQ0759–CQ0760 | NaN or positive-infinite radius yields `temperate_non_terrestrial` instead of insufficient data in the direct function. Add finite-radius enforcement |
| G60-04 Greater-than-unit depth | CQ0881, CQ0903 | A 1,000,001 ppm trapezoid gives negative flux; radius ratio greater than one yields depth above 1,000,000 ppm. Reject unsupported domains or adopt a separately validated physical model |
| G60-05 Extreme arithmetic | CQ0898, CQ0900–CQ0902 | Reciprocal/density/depth can return infinity; underflow of radius cubed can cause division by zero. Require safe finite evaluation or explicit unknown/rejection |
| G60-06 Degenerate duration | CQ0904 | Smallest positive binary64 duration underflows at half duration; midpoint flux becomes 1 instead of 0.999. Reject unresolved duration or evaluate a validated normalized form |

These findings are not authorization to silently change constants, clamp physical
depth, relax tolerances or relabel unknowns as zero. Some requirements are the
explicit Mission 60 qualification goals rather than pre-existing enforced API
contracts. Future fixes must preserve this baseline and distinguish successful
correction from mere reproduction.

For G60-01, the old depth conversion implies **6,371,013.89 m**, while the old
Earth/AU conversion implies **6,378,137.13686864 m**. Their **7,123.24686864 m**
separation exceeds the combined **42.264893535 m** rounding allowance. The depth
constant agrees with the chosen 6,371,000 m mean-radius comparison, while the
probability conversion is near the physical equatorial radius, rather than the
6,378,100 m IAU nominal value. These comparisons do not prove that every catalogue
row uses one convention; they show why that convention must be explicit.

The independently calculated mean-radius Earth/Sun depth is 83.863156 ppm, versus
84.050179 ppm using the nominal equatorial radius. The legacy density is 5.514
g/cm³; the independently evaluated mean-sphere value from the rounded mass/radius
inputs is 5.513443 g/cm³. These are definition-sensitivity diagnostics, not
measurement accuracy, uncertainty intervals or grounds for treating rounded
physical inputs as exact.

## Local-sky projection limits — G60-07

The display formula passes all valid arithmetic references after correcting the
binary-input interface. Its difference from a spherical geodesic log map is
substantial near poles and at large fields. Maximum sampled vector differences
are shown in **arcseconds**, grouped by cone radius and absolute centre
declination; each cell combines both RA centres and applicable bearings/signs.

| Cone radius | 0° centre | 60° centre | 85° centre | 90° centre |
|---:|---:|---:|---:|---:|
| 0.01° | 0.000000145 | 0.006085 | 0.040189 | 72 |
| 0.25° | 0.002258 | 3.819482 | 25.747437 | 1,800 |
| 1° | 0.144498 | 61.942429 | 443.617389 | 7,200 |
| 5° | 18.077399 | 1,661.766830 | 56,476.921300 | 36,000 |
| 10° | 144.997533 | 7,204.470971 | 66,974.940385 | 72,000 |

These are sampled differences between two explicitly defined coordinate maps,
not astrometric source errors or continuous worst-case bounds. At an exact pole,
RA is a coordinate convention and the planar east component collapses; near a
pole, a cone can cross a coordinate singularity. G60-07 therefore requires an
explicit display-domain/approximation disposition. A future domain restriction
or projection replacement needs separate validation; this mission adds neither.

## Tests, reproducibility and scientific status

The new test module has **946 passes and 17 strict expected failures**. The four
existing catalogue/visual modules pass their 49 tests unchanged. Tests cover:

- All 911 independent-reference/requirement cases; each known failure remains a
  separate strict xfail. Unexpected improvement is an XPASS failure requiring review.
- Exact rational trapezoid area, symmetry, range and contact behavior for 36
  curves, independently of branch-by-branch production code.
- Offline reference regeneration with application/numerical imports blocked;
  offline CLI replay with generators blocked; no network calls are permitted.
- Four deliberate faults: ppm/percent confusion, an extra cosine on Gaia proper
  motion, probability unit conversion and reversed sky-offset sign. All detected.
- Full-record audit rejection for missing cases, a new failure, an unexpected
  improvement or numeric drift; checksum rejection for altered inputs.
- Explicit v1/v2 reference scope and exact binary-input wrap-boundary checks.

Ruff and whitespace checks pass. The CI workflow preserves all 26 old artifacts
and adds `catalogue-quantities-validation-record`, for **27** total. The new
artifact retains `overall_passed: false`, all 17 failed IDs, full results and the
separate `observation_audit` result. Final PR checks and artifact verification are
recorded in [PR #60](https://github.com/wolfchil345/astroscope-ai-observatory/pull/60)
before handoff. Old nine BLS xfails remain historical; the
17 catalogue failures are current unmet goals and must not be described as fixed.

Replay after installing `.[dev,validation]`:

```bash
# Scientific/contract acceptance: intentionally exits 1 while 17 goals are unmet.
python -m validation.catalogue_quantities --output /tmp/catalogue-scientific.json

# Complete observed-baseline reproduction: exits 0 only when unchanged.
python -m validation.catalogue_quantities --audit-known-discrepancies \
  --output /tmp/catalogue-reproduction.json

python -m pytest -q tests/validation/test_catalogue_quantities.py
```

The [v1 manifest](../../../validation/manifests/catalogue_quantities_v1.json) and
[v2 manifest](../../../validation/manifests/catalogue_quantities_v2.json) pin
the complete reference chain. Canonical environment metadata is never replaced
with CI metadata. The pilot and formal implementation commits are in this PR's
commit history; if squash merged, their original refs/source hashes remain
necessary for historical reconstruction, as already disclosed in G59-02.

## Roadmap disposition

Mission 59 is merged, confirming bounded W05 closure and W06's documentary
dispositions. Mission 60 delivers the remaining catalogue/model dossier, but
G59-01 is **not closed** because G60-01–G60-06 retain acceptance failures and
G60-07 needs a display-scope decision. C01/C04/C08 mutable ingestion/static-input
limits remain G59-03; this work does not qualify live data or every preset.

The proposed next mission is **Mission 61 — Catalogue Numerical-Domain and
Convention Correction**. It should resolve the recorded input/convention
contracts, preserve this baseline, freeze correction criteria before evaluation,
then demonstrate improvement without weakening the original physical goals.
The projection disposition must be explicit. Mission 61 is proposed, not started.

W07 formal Phase 2 exit remains pending, along with G59-02/G59-03 provenance/scope
disposition. X01 still has 18 unestablished covariance requirements, six unknown
physical components, 48 unqualified site clocks and 288 blocked combined arrival
candidates (240 solar-eligible, 48 excluded). Physical geocentric-clock, site-clock
and arrival bounds remain null; covariance is neither acquired nor propagated;
strict observing/ranking/UTC/calendar eligibility remains false. Phases 0–1 are
complete, Phase 2 is active, and Phases 3–8 remain planned.
