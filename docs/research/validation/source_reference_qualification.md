# Mission 40 — Observer-Arrival Source Convention and Reference-Domain Qualification

## Decision and baseline

Mission 39 merged in [PR #39](https://github.com/wolfchil345/astroscope-ai-observatory/pull/39)
on 2026-10-18 at 05:56:33 UTC as
`eaf3e22b8fb819ef37e0f803595de5330d21e0c7`. Its
[post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39102278645)
passed. Phases 0 and 1 remain complete; Phase 2 remains active.

Mission 40 selects **`astroscope-tdb-solar-au-v1`**, an explicit intended research
source convention. It qualifies a **supplied-input solar Shapiro component
reference** and records the membership of a finite historical sample set in that
component's declared domain. It does not qualify a full barycentric converter,
an observed transit, a catalogue source or a continuous astronomical domain.

The [protocol](../../../validation/manifests/source_reference_policy_v1.json)
was frozen in `827cf8f` before reference outputs, candidate code or numerical
tests. The PINT input-type investigation was recorded in `4abaf70` and `a948519`
before the first successful fixture. No threshold was adjusted after measurement.
All previous scientific tolerances, canonical records and production gates are
preserved. There are no changes under `src/`.

| Question | Mission 40 result | Limit |
|---|---|---|
| Which coordinate is intended? | A named formula, sign, normalization, clock path and omission inventory are selected | A real source must independently demonstrate compatibility |
| Is the solar component reference usable? | Pinned PINT component output agrees with an independent Decimal implementation on 285 eligible inputs | Numerical component comparison only; physical reference uncertainty unknown |
| Which historical samples are eligible? | 240 of 288 meet the declared component guards; 48 retained exclusions | Not continuous-time, all-sky or observing-window coverage |
| Is the full arrival-time reference qualified? | **No** | Clock/reference uncertainty, physical budget and integration remain incomplete |

## Selected source convention

Let `n` be a fixed ICRS unit direction at infinity, `r` the simultaneous geometric
SSB-to-observer vector, `s` the simultaneous observer-to-Sun vector, `R=|s|`,
and `mu=s.n/R`. The selected source coordinate is

\[
 B=JD_{\mathrm{TDB,site}}+
 \frac{\boldsymbol r\cdot\boldsymbol n/c+S_\odot}{86400},\qquad
 S_\odot=\frac{2GM_\odot}{c^3}
 \ln\!\left[\frac{R}{\mathrm{au}}(1-\mu)\right].
\]

The `JD_TDB,site` notation denotes the stated **algorithmic** clock path:
TT(TAI) converted through location-aware ERFA `dtdb` via Astropy. Its approximate
topocentric contribution is included once. A separate `r_site.v_earth/c²` term
must not be added. The retained
[Mission 39 clock audit](../evidence/arrival_clock_inclusion_audit_v1.json)
establishes inclusion, not physical clock accuracy. Mission 40 does not execute
this full formula or a clock conversion; it executes only `S_sun`.

The normalization has zero solar correction at `R=1 au, mu=0`. It is chosen
explicitly to match the sign-adjusted PINT component. The term is added to the
source coordinate; PINT returns a propagation delay that its barycentric TOA
method subtracts. No fitted offset or mean subtraction is allowed.

This is a first-order, solar-only, static-direction research convention.
Planetary Shapiro, higher-order/moving-body gravity, finite distance, target
motion, atmospheric/instrument delays, exposure integration, target-system
propagation, TT(BIPM) realization and uncertainty transport are omitted. No claim
that these omissions are negligible is made. Simultaneous geometric vectors
are required; apparent positions and an `observe()` light-time solution would
change the input convention.

`c=299792458 m/s` and `au=149597870700 m` retain the exact definitions used in
Mission 39. `GM_sun=132712440018000000000 m³/s²` is a **fixed model constant**
matching PINT 1.1.7, not an exact physical measurement. A chosen constant value
does not establish its physical uncertainty or compatibility with a kernel fit.

### Why normalization must be explicit

Eastman et al. equation 5 supplies an angular-only expression. The selected
distance-normalized expression differs from that expression by

\[
 S_{\rm selected}-S_{\rm angular}
 =\frac{2GM_\odot}{c^3}\ln(R/\mathrm{au}).
\]

This is a project algebraic comparison of two stated formulas, not a claim that
their full timing pipelines are interchangeable. The difference varies with
distance, so a constant epoch offset generally cannot remove it. Over the
declared `0.9 <= R/au <= 1.1`, the analytic maximum absolute difference evaluates
to approximately **1.037904532 microseconds**. This number describes a convention
difference under the fixed model constant; it is not a physical error budget.

The research descriptor checks scale, SSB reference position, clock path,
single inclusion of the topocentric clock contribution, solar normalization,
target model and unresolved source state, plus source/algorithm/data provenance.
A generic `BJD_TDB` label is insufficient. Matching declarations return only
`compatible_declarations_for_study_only`; they do not authenticate their own
provenance or grant observing eligibility. This helper is not wired into the
production timing boundary or a catalogue importer.

## Reference selection and independence

| Route | Evidence used | Qualification decision |
|---|---|---|
| PINT 1.1.7 `SolarSystemShapiro.ss_obj_shapiro_delay` | Execute the installed vector component with pinned inputs and constants | Qualified for the supplied-input component comparison only |
| Skyfield 1.55 / DE421 | Generate simultaneous Sun-minus-observer vectors for the historical census | Input construction; geometry accuracy is not independently revalidated here |
| Mission 38 Skyfield/Astropy comparison | Existing geometric and leap evidence, retained unchanged | Does not contain the selected solar correction or certify the selected full clock model |
| Astropy/ERFA clock path | Retained inclusion audit and explicit prospective selection | Inclusion known; independent matched clock accuracy reference still missing |

The reference calls PINT; it does not copy or monkeypatch its formula. The
candidate uses standard-library Decimal scalar arithmetic at 70 digits. It
imports no PINT, NumPy, Astropy, ERFA, Skyfield or production AstroScope module.
Reference and candidate share the mathematical convention, model constants and
supplied historical scalar inputs. That shared basis is disclosed: this is not
independent ephemeris, site, Earth-orientation or clock validation.

PINT's own call chain supplies a length-bearing Astropy `Column` and a
dimensionless `Quantity` direction. Two initial type combinations raised unit
errors and produced no fixture. The
[input audit](../evidence/pint_reference_input_audit_v1.json) records those setup
failures and hashes of the upstream column/direction construction methods.
The final generator matches both input types. PINT's code, constants and the
1 ps threshold were unchanged.

The manifest pins the generator, full reference dependency lock, policy,
input audit, fixture and relevant historical inputs. It also checks hashes of
the executed PINT component, barycentric-delay subtraction method and upstream
input construction methods during regeneration. A method hash establishes
identity, not scientific accuracy. PINT's **full TOA pipeline was not executed**.

## Domain, sample design and results

The component accepts `0.9 <= R/au <= 1.1` and `-1 <= mu <= 0.8`, inclusive.
The angular guard corresponds to geometric solar elongation at least
`acos(0.8)` (about 36.87 degrees). It is a research-domain exclusion, **not an
instruction or safety criterion for solar observing**. Decimal comparisons do
not expand this domain with epsilon or clamp invalid values.

The synthetic grid contains three radii, five cosine/sine pairs and three axis
orientations: 45 cases. The historical census uses all 288 inputs from Mission
38's predeclared four dates, four WGS84 sites, six fixed directions and three
hours. Every candidate is retained, including excluded cases with null reference
corrections and explicit reasons. Sites/targets here are study inputs, not
certified site surveys or measured stellar astrometry.

| Cohort | Total | Compared | Excluded | Failed | Maximum absolute arithmetic difference |
|---|---:|---:|---:|---:|---:|
| Synthetic component grid | 45 | 45 | 0 | 0 | 6.424 × 10⁻²¹ s (rounded upward for display) |
| Historical census | 288 | 240 | 48 | 0 | 4.171 × 10⁻²¹ s (rounded upward for display) |

All 48 exclusions fail the solar-elongation guard. No row was excluded for
numerical disagreement. These maxima are finite-sample numerical differences;
they do not establish accuracy at that scale. The **predeclared 1 ps threshold**
is an engineering test of component arithmetic and serialization, not an
estimate of PINT's physical reference uncertainty. No residual is turned into
a physical bound. The reference uncertainty and total physical arrival bound
remain null.

| Deliberate fault | Detected | Undetected | Compared denominator | Explanation |
|---|---:|---:|---:|---|
| Reverse the additive correction's sign | 282 | 3 | 285 | Three zero-correction synthetic cases are insensitive |
| Omit `R/au` from the logarithm | 270 | 15 | 285 | Fifteen synthetic cases at exactly 1 au are insensitive |

All undetected IDs are retained in the audit result. Excluded cases are not
counted as fault detections. This separates fault sensitivity from a domain
rejection and keeps the complete denominator visible.

## Reproducibility and verification

The committed fixture is
[source_reference_v1.json](../../../validation/fixtures/source_reference_v1.json).
Reference generation uses Python 3.12.14, PINT 1.1.7, Astropy 8.0.2, NumPy 2.5.4,
Skyfield 1.55 and the complete pinned package list below. The DE421 payload is
the same checksum already used by Mission 38. Skyfield's packaged
`finals2000A.all` may issue an expiry warning when locating the package data;
that file is **not used**. The generator constructs its timescale and polar-motion
tables from the checksum-pinned historical EOP/leap fixtures.

After installing dependencies, all generation and evaluation runs block socket
connections. The fixture regenerated byte-for-byte identically in the pinned
reference environment. There is no catalogue lookup or online data refresh.

```sh
# Separate reference environment, only needed to regenerate the fixture.
python -m venv .venv-source-reference
.venv-source-reference/bin/python -m pip install \
  -r validation/reference_generation/source-reference-requirements.txt
.venv-source-reference/bin/python -m validation.reference_generation.source_reference \
  --output work/source_reference_regenerated.json
cmp validation/fixtures/source_reference_v1.json work/source_reference_regenerated.json

# Ordinary project environment; CI consumes the archived fixture, not PINT.
python -m validation.source_reference --output work/source_reference_run.json
python -m pytest -q tests/validation/test_source_reference.py
python -m pytest -q
python -m ruff check .
```

The 57 new tests cover an independent `ln(2)` series oracle, zero/sign and radial
normalization identities, Decimal context isolation, exact domain endpoints and
sub-float outside cases, convention/clock mismatches, provenance requirements,
input corruption, missing/duplicate/context-altered samples, hidden exclusions,
invalid vectors, biased reference output, full denominators, offline import
isolation and CLI provenance. Test counts are not physical validation counts.

The full local suite passed **3,061 tests in 119.45 seconds**. Ruff, compilation,
all eight policy-pinned historical file hashes and 30 relative documentation
links passed. The test environment used Python 3.12.14, Astropy 8.0.1, NumPy
2.5.3 and Streamlit 1.66.0; the separate pinned reference environment above used
Astropy 8.0.2 and NumPy 2.5.4. The executable qualification audit itself requires
only the Python standard library and committed inputs.

The [canonical qualification record](../../../validation/results/source_reference_reference_run.json)
was generated from clean implementation
`37ce0ea036727b1c280ba4c95af06c38a6e18716`. It retains all 333 candidate rows,
all exclusions and mutation denominators, source/manifest hashes, the null
physical bounds and the explicit unqualified full-reference status.

Delivery is tracked in [PR #40](https://github.com/wolfchil345/astroscope-ai-observatory/pull/40).
The PR description records the final published-head CI run and nine retained
artifacts after verification. Those checks must pass before merge; the clean
canonical implementation record is retained separately from later documentation.

The seven existing scientific benchmark steps and Mission 39 budget audit
remain intact. A ninth CI artifact retains this component/reference-domain
qualification record. Production timing, ranking and export gates stay closed.

## Sources and remaining gate

Primary sources inspected on 2026-10-18 UTC:

- [Eastman, Siverd & Gaudi (2010), equations 1, 2, 5 and 6](https://arxiv.org/html/1005.4415v3): term taxonomy and the angular-only comparison expression; no borrowed accuracy claim.
- [PINT solar-system Shapiro source documentation](https://nanograv-pint.readthedocs.io/en/stable/_modules/pint/models/solar_system_shapiro.html): vector direction, negative propagation-delay sign and au normalization. Installed PINT 1.1.7 source hashes are authoritative because online `stable` documentation can change.
- [PINT timing-model documentation](https://nanograv-pint.readthedocs.io/en/stable/_autosummary/pint.models.timing_model.TimingModel.html): component organization; installed `get_barycentric_toas` confirms delay subtraction. Tag `1.1.7` resolves to `df54870102b5f4417ba06441ecaca1c6a1d33e05`.
- [Skyfield vector API](https://rhodesmill.org/skyfield/api-position.html) and [geographic-location API](https://rhodesmill.org/skyfield/api-topos.html): input construction along ICRF axes and WGS84 site semantics.

The formula selection resolves ambiguity for **this intended research source**,
not for arbitrary published ephemerides. Physical reference uncertainty,
independent matched clock evidence, real-source provenance, the Mission 39
physical budget, continuous mapping/root certificates and production integration
remain open. No aggregate physical accuracy has been demonstrated.

Proposed **Mission 41 — Matched-Convention Observer-Arrival Reference Validation**
should first establish a compatible independent clock/reference path, then
evaluate the combined selected convention with frozen assumptions and tolerances.
It must retain any unsuccessful qualification outcome explicitly. Mission 41
is not started; Mission 40 awaits review and merge.
