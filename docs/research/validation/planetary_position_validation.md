# Mission 53 — Planetary Position Validation

Review: [PR #53](https://github.com/wolfchil345/astroscope-ai-observatory/pull/53).

## Scope

This is W02 / P2-04 from the [Mission 51 audit](../phase_2_coverage_audit.md):
validate the seven planets already enabled by `calculate_solar_system_body`.
Mission 52 merged at `2e22f2319c4afa681b8dfd219a5f920916db14f0`, and its
[post-merge Quality Gate 39797889297](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39797889297)
passed. Phases 0 and 1 remain complete; Phase 2 stays active; Phases 3–8 are planned.
The Sun/Moon benchmark, observation-window sampling and native event APIs are not
restarted or expanded here.

## Reference and conventions

The [manifest](../../../validation/manifests/planetary_positions_v1.json),
[policy](../../../validation/manifests/planetary_positions_policy_v1.json) and
[fixture](../../../validation/fixtures/planetary_positions_v1.json) were frozen
before production residuals were examined. The
[generator](../../../validation/reference_generation/planetary_positions.py) uses
Skyfield 1.55 and the locally pinned DE421 kernel from Missions 33/34. It imports
neither AstroScope, Astropy nor ERFA. The implementation under test keeps Astropy's
`builtin` ephemeris; using Astropy with a JPL kernel as both implementation and
oracle would not establish the same implementation independence.

Sources reviewed 2026-10-22:

- [ERFA PLAN94](https://github.com/liberfa/erfa/blob/master/src/plan94.c), source
  revision 2023 May 5: approximate heliocentric planetary states on J2000 axes,
  with historical comparisons against earlier JPL ephemerides. Those error tables
  are neither topocentric confidence intervals nor an accuracy certification for
  every date accepted by this application.
- [Astropy get_body](https://docs.astropy.org/en/stable/api/astropy.coordinates.get_body.html):
  apparent GCRS positions for the supplied terrestrial observer, including light time.
- [Skyfield positions](https://rhodesmill.org/skyfield/positions.html): separate
  light-time, aberration and gravitational-deflection stages, with vectors
  oriented along ICRS axes. Reference RA/Dec uses `.apparent().radec()` without
  an epoch argument. Equinox-of-date RA/Dec is not silently substituted.
- [JPL DE421 kernel](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp):
  existing pinned local data; its SHA-256 is recorded and matched to Mission 34.
  No kernel was downloaded anew or added to the repository.

| Quantity | Convention and limit |
|---|---|
| Targets | DE421 system barycentres 1, 2, 4, 5, 6, 7, 8. No resolved giant-planet disk-centre qualification. |
| Observer | WGS84 geodetic latitude, east-positive longitude, ellipsoidal elevation in metres. |
| Time | UTC in 2024, TAI−UTC = 37 s, TT−TAI = 32.184 s; each engine's TDB conversion. No physical arrival-time conversion claim. |
| Earth orientation | Unmodified Mission 34 daily IERS snapshot, linear DUT1 and polar motion interpolation, with bracketing rows required. |
| RA/Dec | Apparent topocentric direction on non-precessed ICRS-aligned axes, compared by great-circle distance and separately by components. |
| AltAz | Unrefracted geometry, north-zero/east-positive azimuth; no limb, terrain, horizon dip or atmospheric accuracy claim. |
| Distance | Observer-to-retarded-target astrometric range in AU and km; exact AU = 149597870.7 km. |
| Separations | Apparent planet–Sun and planet–Moon angular separations; existing Sun/Moon allowances are inherited. |

Implementation and reference share measured EOP, WGS84 and astronomical conventions;
they are not independent observations of nature. Cross-model agreement supplies
bounded software evidence, not planetary covariance or a universal physical bound.
Skyfield's packaged `finals2000A.all` emits an expiry warning in this environment;
that file is not used. Both pipelines explicitly install the frozen Mission 34
EOP observations for the historical 2024 domain.

## Corpus and thresholds

| Category | Cases | Selection |
|---|---:|---|
| Seasonal site grid | 504 | 7 planets × 6 sites × 4 dates × 3 UTC times |
| Monthly samples | 84 | 7 planets × 12 months at Tokyo |
| Elongation extremes | 14 | Minimum/maximum from a reference-only daily 2024 grid at the equator |
| Zenith | 7 | Reference-derived geographic sites under each apparent direction |
| Altitude boundaries | 14 | Reference-only snapshots near 0° and 20°, one of each per planet |
| Total | 623 | 89 cases for every planet; no random sampling |

Sites are Tokyo, equator at 30° E, Paranal, Greenwich, Arctic and Antarctic.
Seasonal dates are March 20, June 21, September 22 and December 21; times are
00:00, 12:00 and 23:59:59.5 UTC. Monthly samples use day 15 at 06:00 UTC.
Daily-grid extrema are not claimed to be continuous-time conjunction/opposition
solutions. Boundary bisection selects challenging reference snapshots only;
it does not validate a production event finder or begin W03.

| Planet | Direction / altitude goal (arcsec) | Range goal (km) |
|---|---:|---:|
| Mercury | 30 | 5,000 |
| Venus | 30 | 10,000 |
| Mars | 90 | 50,000 |
| Jupiter | 120 | 500,000 |
| Saturn | 180 | 1,500,000 |
| Uranus | 180 | 3,000,000 |
| Neptune | 60 | 1,000,000 |

These are fixed planner-scale regression goals, informed by PLAN94's approximate
model and the amplification from heliocentric to observer geometry. Range budgets
allow transverse as well as radial contributions; copying the source's radial
error column alone would not justify a topocentric range bound. These thresholds
were not fitted to observed residuals. Passing them supports this corpus only,
not milliarcsecond astrometry, occultations, spacecraft navigation or other dates.

Solar separation allows the planet's direction goal plus 5 arcsec; Moon separation
allows plus 60 arcsec, using Mission 34's budgets. Azimuth allows 12 times the
planetary direction goal below |altitude| = 85°, while full horizontal direction
remains checked at zenith/nadir. RA's component bound accounts for cos(declination),
with a pole exclusion above |declination| = 85°; the full direction still applies.

Within 3° of the Sun, angular residuals are retained but excluded from qualification
because deflection and occultation conventions are not fully matched. Distance,
identity, units, finiteness, output formatting and internal classification
contracts remain checked. Excluded metrics do not increase the eligible count.

Reference classification is `boundary_indeterminate` within the direction goal
of altitude 0° or 20°; cardinal labels guard their sector boundaries using the
azimuth allowance. Raw agreements and disagreements are retained. Classifier
consistency with the actual returned angles is always enforced. The `observable`
label is an altitude policy, not a Sun-safety or general observing-eligibility claim.
Moon illumination is checked only as a finite [0,1] return contract here; its
numerical and physical-model evidence remains Mission 34.

## Retained initial harness failure

The pre-evaluation freeze is commit `a7ea32a`. The first run recorded 623 failures
because the harness expected abbreviated cardinal strings (`N`, `NE`, etc.) while
the existing API returns full keys (`north`, `northeast`, etc.). All numerical
metrics were within their unchanged thresholds. The
[initial failed record](../../../validation/results/planetary_positions_initial_label_failure.json)
is retained, including 591 reference-cardinal disagreements and all 623 internal
cardinal-contract failures. It truthfully records `git_dirty=true`: only CI and
research documentation were being assembled during that exploratory run. Its
source hashes identify the frozen harness and unchanged production code.

Commit `825715f` corrects only the harness's label vocabulary and adds explicit
API-key regression tests. No production code, reference values, exclusions or
acceptance thresholds change. The failed run is not claimed as a production
ephemeris defect or as clean canonical evidence.

## Results and reproducibility

The corrected clean run passes all 623 cases under the declared eligibility rules.
It was executed at implementation commit
`b4586a5d9e044324375a231948f0e45df3ff7713` with `git_dirty=false`.
Execution evidence is recorded in the
[canonical result](../../../validation/results/planetary_positions_reference_run.json).
It includes each actual/reference value, metric allowance, exclusion, classification,
per-planet and overall summaries with denominators, commit identity, dependency
versions, platform and source/input hashes. No new production feature is required.

The numerical comparison has 606 angular-eligible cases and 17 solar-excluded
cases; azimuth has 599 eligible cases and 24 exclusions (17 solar plus seven
zenith). All 623 ranges are eligible. These denominators, rather than a blanket
623-case angular-accuracy claim, define the result.

| Planet | Maximum eligible equatorial direction error (arcsec) | Maximum range error (km) |
|---|---:|---:|
| Mercury | 0.535552 | 467.553 |
| Venus | 1.250698 | 1468.755 |
| Mars | 19.123394 | 6209.753 |
| Jupiter | 17.487067 | 40151.226 |
| Saturn | 33.391532 | 46129.157 |
| Uranus | 6.163883 | 220517.487 |
| Neptune | 2.617481 | 90343.987 |

These maxima describe only the sampled 2024 corpus. They are not statistical
confidence limits or maximum error guarantees between samples. No production
correction is indicated by this comparison at the predeclared goals.

Reference generation used Python 3.12.14 on Linux x86_64 (glibc 2.39), with the
pinned package versions recorded in the fixture. A second generation with sockets
disabled and production/Astropy/ERFA imports blocked was byte-identical, including
its provenance. Local replay used one BLAS/OpenMP thread; this changes neither
case selection nor policy. Numerical reproducibility is distinct from platform
and execution-time metadata.


The [tests](../../../tests/validation/test_planetary_positions.py) replay the full
corpus in a subprocess with sockets disabled and Skyfield imports blocked. They
check reference provenance, all seven body inventories, dates/EOP coverage,
checksum tampering, duplicate/nonfinite inputs, frame/unit/format/separation
mutations, and preservation of checks at solar and zenith exclusions. All
previous scientific audits remain in CI; a twenty-first artifact is added:
`planetary-position-validation-record`.

With the project's development/validation environment installed, replay offline:

```bash
python -m validation.planetary_positions --output /tmp/planetary_positions_run.json
python -m pytest -q tests/validation/test_planetary_positions.py tests/test_solar_system.py
python -m ruff check .
```

Reference regeneration uses the separate pinned Skyfield environment described by
[reference-requirements.txt](../../../validation/reference_generation/reference-requirements.txt),
with its existing local `skyfield-data` DE421 installation:

```bash
python -m validation.reference_generation.planetary_positions --output /tmp/planetary_fixture.json
cmp validation/fixtures/planetary_positions_v1.json /tmp/planetary_fixture.json
```

Installing dependencies is separate from offline replay. Numerical records are
compared independently of execution timestamps and host provenance. The focused run passed 692 tests (672 Mission 53 tests and 20 existing Solar
System tests) in 144.02 seconds; Ruff passed. Full-suite
acceptance belongs to the exact final PR-head Quality Gate; its result and artifact
verification are recorded in the PR before handoff.

## Remaining limits

This is bounded W02 evidence for the supported 2024 comparison domain. It does not
validate planetary disk centres, all historical/future dates, physical refraction,
native rise/set APIs, planetary-fit covariance or a universal accuracy bound.
W03–W07 remain as scoped by Mission 51; Phase 2 exit is not approved.

X01 remains unchanged: 18 receipt gaps, six unresolved physical components,
48 unqualified site clocks and 288 blocked arrivals. Physical bounds stay null,
physical covariance remains unqualified, and `observing_eligible=false` stays
in force for unresolved arrival predictions. No provider contact or private-data
access is part of this mission.
