# Mission 34 — Solar, Lunar, and Twilight Validation

## Scope and verified starting point

This mission continues Phase 2 from Mission 33, merged as PR #33 at
`4c673bab7d0c940327b5d623d6fbd51bdba8d00b`. Local `main` was fast-forwarded to
that exact commit before branch `research/mission-34-solar-lunar-twilight` was
created. The Phase 0–8 roadmap and production scientific behavior are preserved.

**354 snapshots**, **120 event windows** and **188 matched crossings** compare
existing production APIs against frozen independent references. The
[canonical record](../../../validation/results/solar_lunar_twilight_reference_run.json)
retains numerical values, statistics, exclusions, classification guards, no-event
states, source hashes and environment provenance. No scientific defect was found
within the explicitly bounded validation domain.

## API audit and event claim boundary

The existing `calculate_solar_system_body` returns Sun/Moon apparent topocentric
altitude and azimuth, Sun–Moon separation, solar elongation, approximate lunar
illumination and visibility status. `sample_transit_visibility` supplies solar and
lunar altitude, illumination, a configurable solar darkness threshold and target
observability. `calculate_darkness_score` maps solar altitude to a 0–15 score.

**There is no existing native sunrise, sunset, moonrise, moonset or twilight-time
API.** Event times here are **validation-derived roots of the existing altitude
API**, not verification of an existing event-time algorithm and not a newly added
production feature. The record explicitly marks native event APIs unsupported.
The configurable transit visibility thresholds allow civil, nautical and
astronomical darkness classification checks without adding UI or scientific APIs.

All horizon events use **unrefracted apparent topocentric body-centre altitude
0°**. Both implementations use the same convention. No upper limb, solar/lunar
angular radius, atmospheric refraction, terrain mask or elevation-dependent
horizon dip is added. Observer elevation affects WGS84 position only. These events
must not be compared directly to published refracted upper-limb sunrise/sunset
or conventional −0.8333° solar-centre almanac events. Civil, nautical and
astronomical twilight boundaries use Sun-centre altitudes −6°, −12° and −18°.

## Frozen independent reference

The coordinate/event generator imports Skyfield, NumPy and Python utilities;
it does not import AstroScope, Astropy or ERFA. Reference versions are Skyfield
1.55, skyfield-data 7.0.0, NumPy 2.5.3, jplephem 2.24 and sgp4 2.27. Its separate
environment has no production package. JPL **DE421** is obtained from the pinned
skyfield-data distribution. Kernel name, source URL and SHA-256 are stored in the
fixture, alongside the generator checksum and reference versions.

The 401-row daily IERS B snapshot spans MJD 60300–60700. It records the source
URL, filename, full source-file checksum and astropy-iers-data distribution
`0.2026.9.21.0.56.25`. The extractor reads these observations with Astropy but
performs no reference sky calculations; it refuses a different source-file hash.
Every observing instant and event window lies inside the snapshot, with
consecutive bracketing daily rows. Both paths linearly interpolate DUT1 and
polar motion. The common IERS observations are shared measurement inputs, not
independent measurements of the sky.

All dates are in 2024, with TAI−UTC = 37 s and TT−UTC = 69.184 s. The reference
uses TT−UT1 = 69.184 − DUT1. Leap-second boundaries are not covered; Python
`datetime` does not represent 23:59:60. UTC instants have microsecond storage,
calculations use float64, and astronomical JD conversion can round by tens of
microseconds. Reference events are refined to 0.001 s; validation-side events to
0.02 s. Sub-millisecond residuals are numerical agreement, not an observational
accuracy claim.

Directions are apparent and topocentric (including light-time/aberration), with
**refraction disabled**. Azimuth is eastward from geographic north. Angular
residuals wrap at 360°. Production uses its built-in ephemeris, independently of
the reference DE421 path. The validation context pins the otherwise configurable
transit API to `builtin` and restores all ephemeris/IERS settings on exit.

## Coverage and event search

Sites include Tokyo, an equatorial location, Paranal, Greenwich, Arctic latitude
78.2232°N and Antarctic latitude 75.1°S. Site/elevation values are fixed inputs,
not surveyed observatory metadata. Seasonal dates are March 20, June 21,
September 22 and December 21, 2024. Additional March 10, March 17, March 25 and
April 2 dates sample new, first-quarter, full and last-quarter Moon regions;
they are not claimed to be the exact phase instants.

The base 192 snapshots use four UTC times per site/date, including 23:59:59.5.
Another 162 snapshots lie 120 s before, at, and 120 s after reference Sun/Moon
horizon or twilight crossings at Tokyo and the Arctic site. Each event window
runs from 12:00 UTC to 12:00 the following day, crossing midnight. The start is
inclusive and the end exclusive.

Skyfield searches crossings from a 300-second grid with `find_discrete`, and
independently searches extrema with `find_minima`/`find_maxima`. The validation
harness searches the production altitude API with an hourly grid, bounded
extremum refinement and Brent roots. Extrema are inserted into the root brackets
so two crossings between grid points can be detected. Tests cover this situation,
a tangent touch, exact roots, missing events and continuous above/below states.
These are bounded daily solar/lunar searches, not proof of root-search completeness
for arbitrary functions or untested grazing geometries.

All **120/120 window topologies agree**, including **25 no-event windows**:
15 solar always-above-threshold, four solar always-below-threshold, three lunar
always-above-horizon and three lunar always-below-horizon windows. The solar counts
include the three twilight thresholds as well as 0°. No astronomical twilight,
polar day/night, and continuous lunar visibility/nonvisibility are explicitly
preserved for the tested 24-hour windows; they do not imply indefinite visibility.

## Predeclared tolerances and conditioning

The [acceptance policy](../../../validation/manifests/solar_lunar_twilight_policy_v1.json)
was committed in `e7de6c1` **before examining production residuals**. The bounds
were not adjusted after comparison.

| Quantity | Maximum allowed error | Rationale |
|---|---:|---|
| Sun altitude / sky direction | 5 arcsec | Planner bound allowing independent ephemeris models |
| Moon altitude / sky direction | 60 arcsec | One-arcminute planner bound for builtin lunar ephemeris |
| Sun / Moon azimuth | 60 / 720 arcsec | Coordinate projection allowance below absolute altitude 85° |
| Sun–Moon separation / lunar solar elongation | 65 arcsec | Sum of the two directional bounds |
| Illumination, same elongation model | 0.0003 absolute fraction | Propagated angular-error allowance |
| Illumination, spherical phase-angle model | 0.01 absolute fraction | Bound on the documented approximation |
| Darkness score | 0.002 score points | Solar angular bound through the score slope |
| Solar horizon/twilight crossing time | 10 seconds | 5 arcsec / minimum admitted slope 0.5 arcsec/s |
| Lunar horizon crossing time | 120 seconds | 60 arcsec / minimum admitted slope 0.5 arcsec/s |

Above absolute altitude 85°, the azimuth-component gate is explicitly excluded,
while great-circle direction remains gated. This fixture has **zero such azimuth
exclusions**. The rule is preserved for future versioned additions, not used to
hide difficult results. Reference crossing slopes below 0.5 arcsec/s are labelled
ill-conditioned; their residuals remain visible but are excluded from timing
limits. There are **zero ill-conditioned timing exclusions** in this fixture;
a synthetic failure-sensitivity test verifies the exclusion mechanism.

A horizon or observing/darkness classification within the corresponding angular
error bound is marked `boundary_indeterminate`. The numerical coordinates and
internal boolean/status consistency still must pass; other cases require
independent reference classification agreement. The canonical run retains 32
indeterminate classification checks and 1,738 reference-compared checks. Exact reference-root snapshots
are retained rather than perturbed away or counted as certain horizon signs.

Production illumination uses `(1 − cos(elongation))/2`. It is compared separately
with the same formula using reference topocentric elongation and Skyfield's
spherical Sun–Moon–observer phase-angle fraction. The second comparison measures
approximation error as well as numerical error. Relative error is diagnostic
only and is excluded for reference illuminated fraction <0.01: **24 near-new
cases** are explicitly null, with the absolute error still gated. The remaining
330 relative errors have a maximum of approximately 0.003132 (0.3132%).

Canonical implementation: `8099a86e534e47dad4a0f9992f3146462c018557`, recorded from a clean checkout
in a fresh execution environment without Skyfield.

## Executed results

All **354/354 snapshots**, **120/120 event windows**, and **188/188 matched event
timings** pass the frozen criteria. Every event matches both direction and count;
missing or extra events cause failure independently of timing statistics.

Angular errors (arcseconds):

| Quantity | MAE | Median | RMS | Maximum | Pass rate |
|---|---:|---:|---:|---:|---:|
| Sun altitude | 0.00437276 | 0.00346444 | 0.00556931 | 0.0137805 | 354/354 |
| Sun azimuth | 0.00585626 | 0.00561979 | 0.00706351 | 0.0297917 | 354/354 |
| Moon altitude | 1.18446 | 1.09327 | 1.38918 | 4.35746 | 354/354 |
| Moon azimuth | 1.51424 | 1.40728 | 1.89984 | 8.01687 | 354/354 |

Sun–Moon separation and lunar solar elongation have MAE 1.28699 arcsec and maximum
4.27621 arcsec, with 100% pass rates. The record contains their median/RMS and
worst-case details, plus independent transit-API altitude/illumination metrics.

Timing errors (seconds; matching centre/threshold conventions):

| Event group | MAE | Median | RMS | Maximum | Pass rate |
|---|---:|---:|---:|---:|---:|
| Solar horizon and twilight crossings | 0.00127662 | 0.000859864 | 0.00183393 | 0.00759127 | 154/154 |
| Lunar horizon crossings | 0.141209 | 0.119690 | 0.173574 | 0.483742 | 34/34 |

The canonical JSON additionally separates solar 0°, −6°, −12°, −18° and lunar
0° event statistics. Each record retains direction, window, observer, UTC time,
reference slope and residual. The largest timing error is well within the
predeclared bounds; it does not account for atmospheric/horizon uncertainty.


Per-threshold timing statistics, also in seconds:

| Event | MAE | Median | RMS | Maximum | Passed |
|---|---:|---:|---:|---:|---:|
| Sun centre rise/set | 0.0010379375 | 0.00067578761 | 0.001499626 | 0.0046250782 | 40/40 |
| Civil twilight | 0.0013874644 | 0.0010768792 | 0.0018400384 | 0.0045734153 | 40/40 |
| Nautical twilight | 0.0012802209 | 0.00087218405 | 0.0019471123 | 0.0075912735 | 40/40 |
| Astronomical twilight | 0.0014227898 | 0.00096290059 | 0.0020358215 | 0.0050048733 | 34/34 |
| Moon centre rise/set | 0.1412091 | 0.11968974 | 0.17357403 | 0.4837423 | 34/34 |

Illumination model agreement has MAE 0.00000233147 and maximum 0.0000102240 in
fraction. Comparison with spherical phase-angle illumination has MAE 0.000783775
and maximum **0.00142076** (about **0.142 percentage points**), with 100% absolute
tolerance pass rate. This is documented approximation error, not an undisclosed
scientific correction. Maximum darkness-score error is 0.00000261572 points.

## Reproduce the benchmark and reference data

Execution environment (Python 3.12; installation alone requires package access):

```sh
python -m venv .venv-validation
.venv-validation/bin/python -m pip install -c validation/requirements-celestial.txt -e '.[dev,validation]'
.venv-validation/bin/python -m validation.solar_lunar_twilight --output work/solar-lunar-run.json
.venv-validation/bin/python -m pytest -q
.venv-validation/bin/python -m ruff check .
```

The constraints are the preserved Mission 33 environment. Skyfield, skyfield-data
and the JPL kernel are unnecessary for normal validation execution. A full CLI
subprocess test disables socket connections and blocks reference-engine imports.
The canonical result is generated in a fresh environment without Skyfield from
a clean committed implementation; its metadata identifies that commit and all
relevant input/source hashes. Evidence is committed separately to avoid a
self-referential Git hash.

Separate **reference-generation** environment:

```sh
python -m venv .venv-reference
.venv-reference/bin/python -m pip install -r validation/reference_generation/reference-requirements.txt
.venv-validation/bin/python -m validation.reference_generation.extract_solar_lunar_eop
.venv-reference/bin/python -m validation.reference_generation.solar_lunar_twilight
```

The extractor reads the pinned IERS observations; all reference astronomical
calculations occur in the separate Skyfield environment. EOP, fixture and manifest
regeneration are byte-for-byte checked. The runner pins the manifest hash; any
intentional fixture/policy change requires explicit review and updating that pin.
Ordinary tests and CI never rewrite expected values or contact data services.

## Quality gate and continuation

Mission 34 adds **493 tests**, including the full offline run, integrity/provenance,
wrapped angles, classifications, topology, tangent/hidden roots, missing events,
perturbed positions/illumination/darkness and state restoration. CI executes the
new benchmark and retains its JSON even when a step fails. Existing Phase 2
validation remains in the quality gate. The full fresh-environment suite passes
**2,301 tests**; Ruff and the observer-time, civil-time, schedule-interval and
Mission 33 celestial-coordinate benchmarks pass.

Phase 2 remains active. **Mission 35 — Exoplanet Transit Ephemeris Validation** is
proposed only and will not start without a new instruction. No scheduling, UI,
feature expansion, or later-phase work is included in this mission.

## Primary references

- [Astropy get_body: apparent observer-dependent GCRS coordinates](https://docs.astropy.org/en/stable/api/astropy.coordinates.get_body.html)
- [Skyfield positions and spherical illuminated fraction](https://rhodesmill.org/skyfield/api-position.html)
- [Skyfield almanac conventions](https://rhodesmill.org/skyfield/almanac.html)
- [Skyfield Earth orientation and polar motion](https://rhodesmill.org/skyfield/accuracy-efficiency.html)
- [JPL planetary ephemerides](https://ssd.jpl.nasa.gov/planets/eph_export.html)
