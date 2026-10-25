# Mission 61 — Catalogue Numerical-Domain and Convention Correction

**Current production passes all 1,252 frozen acceptance cases.** This supports
bounded closure of G60-01–G60-07 and G59-01 upon review and merge. Phase 2 remains
active; formal exit, composite-input provenance and physical arrival qualification
are not approved. Mission 60's 911-case baseline and all 17 failures remain
reproducible against isolated historical source.

## Baseline and experiment chronology

Mission 60 PR #60 merged at `e94271adfaf90c22c986fe2433f91b2a0b844489`.
[Post-merge Quality Gate 40217057624](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/40217057624)
passed 7,066 tests with 26 historical expected failures in 397.11 seconds. All
27 artifact names, head identities and expiry states were checked; those baseline
archives were inventoried, not downloaded again in Mission 61.

1. `f86c85e` freezes the correction protocol, independent generator, fixture,
   policy, source register and retained Mission 60 source before production edits.
2. `260e4fc` corrects a prose counting error: **320**, not 640, added projection
   cases. No reference, input, domain or tolerance changes. Both commits precede
   the first corrected evaluation.
3. `ce0cc2983939dc1e1a84eec175a07abfabf07ae8` contains the implementation, tests,
   historical adapter and CI. The clean canonical run uses this commit.

The first corrected evaluation already passed all 1,252 cases. Subsequent
integration checks added a final-rounding cap at unit depth after the exact
radius-domain check; no frozen expected values or tolerances changed. Original
Mission 60 corpus, binary-input amendment, pilot, observations and canonical result
are unchanged. The historical source manifest verifies exact original bytes after
reversing only two import-prefix changes.

## Corrections and evidence

| Finding | Current behavior | Evidence and scope |
|---|---|---|
| G60-01 unit conventions | One IAU nominal Earth/Sun radius convention; explicit spherical density normalization | Independent SI references; tighter constant/coherence checks; record and CSV convention marker |
| G60-02 source coordinates | Reject nonfinite/out-of-range source RA/Dec | Original six failures plus CSV boundary tests |
| G60-03 radius screen | Nonfinite radius yields insufficient data | Original NaN/Inf cases; other heuristic thresholds unchanged |
| G60-04 excessive depth | Rp > Rstar returns unknown; model depth >1000000 ppm rejects | Original two failures; exact equality/next-float boundary tests |
| G60-05 arithmetic range | Scaled density/depth products, exact probability ratios, finite Gaia derivations | Extreme finite and subnormal controls; missing values survive CSV export |
| G60-06 duration underflow | Rational contact arithmetic resolves finite positive durations | Independent 1600-digit Decimal flux reference; unresolved figure grids reject explicitly |
| G60-07 chart distortion | Enforce center abs(Dec) <=60 degrees and source separation <=0.25 degrees | 1e-10 degree numerical boundary allowance; analytic bound 7.728691 arcsec; translated notice keeps other views usable |

See the [protocol](catalogue_correction_protocol.md) for the derivative-bound proof.
This is a domain restriction on the existing planar chart, not a new spherical
projection. Unsupported charts reject as a whole; sources are not silently
filtered. Query/table coverage is unchanged.

## Convention and physical interpretation

The assumed calculation convention `nominal_spherical_v1` uses IAU 2015 B3
equatorial Earth radius 6378100 m, solar radius 695700000 m, Earth GM
3.986004e14 m3/s2, au 149597870700 m and CODATA 2018 G=6.67430e-11.
Spherical planet density uses `(GM/G)/(4*pi*R^3/3)`, giving a normalization of
**5.495021865555211 g/cm3**. This is not measured terrestrial density and not
the IAU nominal ellipsoidal Earth volume. G's uncertainty is not propagated here.
Unit radius Earth/Sun area depth is **84.05017877225195 ppm**.

NASA composite catalogue fields may mix references. The new marker identifies
our **assumed calculation units**, not verification of each archive entry's
convention, mass provenance or covariance. Parsed records/export carry the marker;
legacy/manual records default to unknown. Four-language interface notes explain
the assumptions. The [source register](../../../validation/manifests/catalogue_correction_sources_v1.json)
links the primary standards and archive documentation.

The depth model supports only Rp <= Rstar. The probability now requires a
circular exterior orbit `a > Rstar + Rp`, so previously capped embedded/contact
orbits return unknown. This is a predeclared domain correction, not an eccentric
or dynamically qualified model. The temperate screen retains its educational
threshold policy and makes no composition, habitability or calibrated probability
claim. The trapezoid remains a symmetric illustration without limb darkening,
exposure integration, physical contacts or fitted transit parameters.

## Results and reproducibility

All 911 original inputs and identifiers are retained in an explicit successor
fixture; every changed convention/domain interpretation is labeled. Added controls
comprise 320 projection boundaries, nine extreme scalar cases and 12 extreme
duration/ingress cases. Independent references import no production, NumPy,
Astropy, Plotly or ERFA code and regenerate byte-for-byte with network blocked.
Scalar algebra and flux references validate computation, not observed accuracy.

| Quantity | Result |
|---|---:|
| Current acceptance cases | 1,252 passed; 0 failed |
| Requirement categories | 536 value, 714 rejection, 1 rejection-or-null, 1 value-or-rejection |
| Projection cases | 195 supported values, 697 explicit domain rejections |
| Maximum sampled supported projection error | 3.819482 arcsec |
| Conservative analytic projection bound | 7.728691 arcsec |
| Historical Mission 60 replay | 911 cases; 17 retained failures; complete observation audit passes |

The value-or-rejection case retains the original tiny-duration acceptance wording;
current production returns the correct flux, and the added extreme-duration cases
require actual values. Domain rejections and unknown results are not counted as
numerical accuracy measurements. No current-production test is marked xfail.

The canonical record is
`validation/results/catalogue_correction_reference_run.json`, SHA-256
`becd902ca1fb20a7f88249f83db0c85acc00ad02eb4b301398bc895ed7791404`.
It records a clean checkout, implementation identity, source/input hashes, Python,
platform and package versions. CI produces a fresh record with the PR's actual
head identity as the 28th artifact, `catalogue-correction-validation-record`;
it also continues the separate historical catalogue artifact.

```bash
python -m validation.reference_generation.catalogue_correction
python -m validation.catalogue_correction --output /tmp/catalogue-current.json
python -m validation.catalogue_quantities --audit-known-discrepancies \
  --output /tmp/catalogue-historical.json
python -m pytest -q
python -m ruff check .
```

The full local suite passed **8,356 tests with 26 historical strict expected
failures** in 267.51 seconds; Ruff passed. Mission 61 adds 1,290 passing tests.
The 26 xfails comprise nine historical BLS failures and 17 historical catalogue
failures, with no current-production expected failure.

Current CLI exit success means all current acceptance cases passed. Historical
audit success means the entire historical observation record was reproduced,
including failures. Omitting its audit option still exits nonzero on the original
17 failures. Six controlled faults test convention, embedded-orbit, screen,
coordinate and tiny-duration detection; checksum corruption also rejects.
Rendered dashboard tests cover English, Japanese, Korean and Thai, normal/wide/
polar fields, table retention and invalid simulator defaults.

Exact rational flux was measured locally at roughly 1.1 ms for 301 samples and
18.4 ms for 5,001 samples, averaged over ten runs; this is a local observation,
not a performance guarantee. The maximum plotting sample count is unchanged.

## Review disposition and retained limits

G59-01 has a bounded correction dossier ready for closure on review/merge.
G59-02 historical provenance and G59-03 mutable/static catalogue scope require
explicit disposition during W07 exit readiness. The next proposed mission is
**Mission 62 — Phase 2 Exit Readiness and Provenance Disposition**, not started.
It must inspect merged evidence and decide exit eligibility; no automatic exit
or Phase 3 work follows these passing tests.

X01 remains unchanged: 18 unestablished covariance requirements, six unknown
physical components, 48 unqualified site clocks, 288 blocked combined arrivals
(240 solar-eligible, 48 excluded), zero executed. Physical clock/arrival bounds
remain null, physical covariance is neither acquired nor propagated, and strict
observing, ranking, UTC and calendar consumers remain ineligible. W05's current
BLS acceptance and its nine historical failures remain separate and unchanged.

The [Mission 61 ledger](../evidence/catalogue_correction_findings_v1.json) records
the bounded disposition. Final-head CI counts, artifact inventory and downloaded
archive/payload verification are recorded in the PR before handoff.
