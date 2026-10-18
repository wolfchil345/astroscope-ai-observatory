# Mission 41 — Matched-Convention Observer-Arrival Reference Validation

## Decision

**Clock qualification was unsuccessful for the four audited routes.** The
combined selected-convention arrival comparison therefore has **zero executed
cases**. All 288 proposed cases remain explicitly blocked. This is a retained
research result, not a successful independent timing validation.

Mission 40 merged in [PR #40](https://github.com/wolfchil345/astroscope-ai-observatory/pull/40)
as `176ba2a504e64464f6f69e642dddb4bb98a05efc` on 2026-10-18 at 07:07:19 UTC.
Its [post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39106487552)
passed before Mission 41 changes. No open follow-up PR existed at the baseline
check. Phases 0 and 1 stay complete; Phase 2 stays active.

The [protocol](../../../validation/manifests/clock_reference_policy_v1.json)
was frozen in `5b63ed2` before diagnostic values, fixture generation, evaluator
implementation or numerical tests. Source inspection preceded that freeze.
The Mission 40 roadmap explicitly requires compatible independent clock evidence
before combined validation and requires retaining an unsuccessful outcome.
No tolerance was changed after measurement; no production code was changed.

## Route evidence and qualification requirements

A usable independent reference must be executable, match the selected site-clock
convention, avoid the candidate clock backend, and have reference uncertainty
established for the study domain. A library name, identical output or checksum
alone meets none of those scientific requirements.

| Audited route | Evidence actually executed | Decision for the combined study |
|---|---|---|
| PINT 1.1.7 default | 48 calls through `Observatory.get_TDBs`; each traced to one ERFA `dtdb` call through Astropy | Selected algorithm reproduced, but the backend is shared |
| PINT 1.1.7 ephemeris method | One public dispatch with TT input and `ephem=DE421` | `NotImplementedError`; no result, fallback or time-kernel evaluation |
| Skyfield 1.55 clock | Geocentric `tdb_minus_tt` at 12 unique TT instants | Different approximation with no site arguments; not the selected site clock |
| Explicit ERFA call | 48 calls with the selected argument convention | Same backend; argument/dispatch reproduction only |

None has a physical reference uncertainty established here. This is a bounded
census of the stated installed routes, **not a claim that no independent clock
reference exists elsewhere**. No SOFA, TEMPO2, numerical time ephemeris, full PINT
TOA pipeline, TT(BIPM) correction or observed transit was executed.

Installed source identities are pinned in the protocol and checked during
fixture generation. `TopoObs._get_TDB_default` inherits the audited base method.
The PINT alternative method fails before consulting the requested ephemeris;
there is no claim that ordinary DE421 contains a TT–TDB time series. A custom
callable would require its own evidence and cannot make a route independent by
changing its name.

The [fixture](../../../validation/fixtures/clock_reference_v1.json) retains the
actual PINT-to-ERFA argument traces, the unsupported-method exception, the
method hashes, package versions and all diagnostic values. Its evidence kind
is explicitly `clock_route_diagnostics_not_independent_reference`.

## Exact clock convention and the UTC approximation

Mission 40 selected `astroscope-tdb-solar-au-v1`. Its intended full source formula
remains

\[
 B=JD_{\mathrm{TDB,site}}+
 \frac{\boldsymbol r\cdot\boldsymbol n/c+S_\odot}{86400}.
\]

**This formula is not evaluated as a combined converter in Mission 41.**
The existing clock selection means TT(TAI), with TT−TAI = 32.184 s, passed through
Astropy's location-aware ERFA calculation. The approximate site contribution is
included once. Adding another observer Einstein term would change the convention.

Source inspection makes an existing implementation detail explicit: Astropy
uses the UTC day fraction as an approximation to UT1 for `dtdb`, while ERFA's
parameter denotes UT1. This is a description of the pinned algorithm, not a
statement that UTC equals UT1. The date uses a two-part TT Julian date; site
inputs are WGS84 longitude, distance from the spin axis and height above the
equatorial plane in km. Astropy's signed day remainder and the explicit call's
fraction in [0, 1) represent the same periodic argument.

The audit separately evaluates the UT1 argument using the frozen historical
EOP table. It does not replace the selected UTC approximation, retune the
convention, or assign an uncertainty from that difference. The older Mission 39
inclusion audit and Mission 40 numerical record remain unchanged.

## Sample census and diagnostic results

The clock census is the Mission 38 four dates × four sites × three UTC hours:
**48 unique site instants**, containing **12 unique geocentric instants**. Target
direction does not affect these clock calls. The 288 target/role rows must not
be counted as independent clock samples. Geocentric values are checked for
consistency across the four sites and summarized with denominator 12.

For two clock corrections \(\Delta_A\) and \(\Delta_B\), the diagnostic is
\(d=\Delta_A-\Delta_B\) in seconds. This compares numeric coordinate corrections;
subtracting two Astropy `Time` objects representing the same instant in TT and
TDB would instead give zero elapsed time and would not measure TDB−TT.

| Difference | Unique comparisons | Maximum absolute difference | Interpretation |
|---|---:|---:|---|
| PINT default − Astropy site | 48 | 0 at archived precision | Shared-backend control |
| Explicit ERFA with UTC − Astropy site | 48 | 0 at archived precision | Shared-backend argument control |
| Skyfield − Astropy geocentre | 12 | 3.8915017365421 µs | Different geocentric approximations |
| Astropy site − Astropy geocentre | 48 | 2.0874106949681 µs | Site contribution in the chosen model |
| ERFA with UT1 − ERFA with UTC | 48 | 7.9827236 ps | Effect of the day-fraction substitution in this sample |

The two shared-backend controls meet the **predeclared 1 ps reproduction
threshold**. That threshold checks argument dispatch and serialization only.
The other three differences have **no accuracy acceptance threshold**. Their
signed extrema and every sample are retained; there is no fitting, centering or
residual-based exclusion. These finite-sample differences are neither absolute
physical errors nor continuous-domain bounds. In particular, picosecond-scale
differences between two calls to the same model do not establish picosecond
physical clock accuracy.

Skyfield provides a separately coded geocentric approximation, not an independent
realization of the entire selected site clock. Shared astronomical theory and
constants remain relevant. ERFA's documented accuracy relative to a historical
time ephemeris is not adopted as this project's calibrated uncertainty.

## Combined comparison gate

| Proposed combined cases | Executed | Blocked | Solar component within Mission 40 domain | Solar component excluded |
|---:|---:|---:|---:|---:|
| 288 | **0** | **288** | 240 | 48 |

Every combined row retains its target/site/time identity, associated clock case,
blocking reasons and null reference coordinate, candidate coordinate and residual.
The 48 solar-domain exclusions retain both the clock blocker and the solar
elongation reason. The 240 solar-eligible cases still lack a qualified clock
reference. No missing result is encoded as a zero residual or a passed comparison.

The executable report distinguishes:

- `audit_passed=true`: integrity, route classification, sample accounting and
  shared-backend reproduction checks passed;
- `clock_qualification_outcome=unsuccessful` and `qualified_route_count=0`;
- `full_reference_status=unqualified`;
- physical clock and arrival bounds are null; observing eligibility is false.

The evaluator is a closed audit of these pinned routes. It cannot accept a
self-declared newly qualified route. Changed upstream behavior, a replacement
reference or a revised convention requires a new reviewed protocol. This audit
is not connected to production eligibility, ranking, exports or source import.

## Reproduction, tests and provenance

The reference environment reuses the complete
[pinned Mission 40 dependency lock](../../../validation/reference_generation/source-reference-requirements.txt):
Python 3.12.14, PINT 1.1.7, Astropy 8.0.2, PyERFA 2.0.1.5 and Skyfield 1.55.
The [generator](../../../validation/reference_generation/clock_reference.py)
uses frozen EOP/leap tables, blocks socket connections and restores astronomy
tables on exit. It imports the audited libraries intentionally and is explicitly
not an independent oracle. It imports no AstroScope candidate or production code.
No new kernel, catalogue, online clock file or online table is fetched.

The fixture regenerated byte-for-byte identically offline. The
[manifest](../../../validation/manifests/clock_reference_v1.json) pins the
fixture, generator, protocol, dependency lock and historical inputs. The normal
[evaluator](../../../validation/clock_reference.py) uses only the Python standard
library and archived evidence. CI does not install PINT or Skyfield.

```sh
# Existing pinned Mission 40 reference environment, for explicit regeneration.
.venv-pint-reference/bin/python -m validation.reference_generation.clock_reference \
  --output work/clock_reference_regenerated.json
cmp validation/fixtures/clock_reference_v1.json work/clock_reference_regenerated.json

# Ordinary project environment; no reference packages needed.
python -m validation.clock_reference --output work/clock_reference_run.json
python -m pytest -q tests/validation/test_clock_reference.py
python -m pytest -q
python -m ruff check .
```

The **46 new tests** cover all route outcomes, rejection of invented independence,
unsupported-method fallback, zero residual and common-mode bias without promotion,
detectable wrapper faults, exact threshold boundaries, complete denominators,
signed diagnostics, Decimal context isolation, corrupted identity/context and
checksums, invalid numbers, retained solar exclusions, and offline import isolation.
A live Astropy regression reproduces all 48 archived site corrections within the
same 1 ps engineering threshold and checks the inspected method identity. This
regression also uses the same clock backend and is not independent accuracy evidence.

The full local suite passed **3,107 tests in 122.05 seconds**. The 46 affected
tests were rerun after the final fixture provenance update. Ruff, compilation,
14 frozen historical input hashes and 33 relative documentation links passed.
The local test environment used Python 3.12.14, Astropy 8.0.1, NumPy 2.5.3 and
Streamlit 1.66.0; the separate reference environment is listed above.
A clean canonical audit record is retained in the evidence commit following
the implementation commit.
The seven prior scientific benchmarks and both prior audits remain intact; a
new tenth CI artifact retains this unsuccessful qualification audit.

## Sources and next gate

Primary source inspection on 2026-10-18 UTC:

- [PINT 1.1.7 observatory source](https://nanograv-pint.readthedocs.io/en/stable/_modules/pint/observatory.html): dispatch, default delegation and unsupported alternative. Installed method hashes, not a mutable documentation label, pin the executed behavior.
- [Astropy time source](https://docs.astropy.org/en/stable/_modules/astropy/time/core.html): inspected `_get_delta_tdb_tt`, UTC approximation and site arguments; installed 8.0.1 and 8.0.2 method identities match.
- [Skyfield 1.55 time source](https://github.com/skyfielders/python-skyfield/blob/1.55/skyfield/timelib.py): installed method cites USNO Circular 179 equation 2.6 and accepts only date parts. The tagged raw web fetch was unavailable; the installed pinned source was inspected.
- [ERFA `dtdb` source](https://github.com/liberfa/erfa/blob/v2.0.1/src/dtdb.c): the installed wrapper documentation identifies the UT1 parameter, FB90 geocentric model, approximate topocentric term and SOFA lineage. The tagged raw web fetch was unavailable; installed documentation identity is retained.

Proposed **Mission 42 — Independent Time-Ephemeris Reference Acquisition and
Clock Mapping** should first acquire and archive an executable independently
integrated reference with documented timescale, rate, epoch, sign, domain and
uncertainty. It must reconcile geocentric and site conventions, including the UTC
approximation, before a new combined-comparison protocol is frozen. Availability,
license, reproducibility and compatibility must be established rather than assumed.
If the evidence requires changing the selected source convention, that change
must be explicit and versioned. Mission 42 has not started.
