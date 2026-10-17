# Mission 37 — Strict Transit Timing Metadata and Eligibility Boundary

## Baseline and claim

Mission 36 was verified merged through [PR #36](https://github.com/wolfchil345/astroscope-ai-observatory/pull/36)
as `e5a3c70e8aca77ed0132091d3b088eb73e2f1fcf` on 2026-10-17 at
15:18:20 UTC. Its [post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39044453868)
passed. Phases 0 and 1 remain complete; Phase 2 remains active.

The [implementation policy](../../../validation/manifests/transit_timing_boundary_policy_v1.json)
was committed as `6cd2aac` before implementation and testing. Mission 37 implements
the metadata, nominal arithmetic, uncertainty and eligibility portion of the
[Mission 36 contract](transit_time_coordinate_contract.md). It does not enable an
observer-arrival resolver, strict observing-range selection, calibrated ranking,
or new observational timing claims.

**All strict coordinate predictions are ineligible for observing, ranking and
UTC/calendar export.** This includes observer-TAI predictions until a separately
validated adapter exists. Declaring a scale is not a substitute for resolution.
The old numeric scheduler remains available only as explicitly unvalidated legacy
behavior; preserving it does not certify its timestamps.

## Implemented boundary

`src/astroscope/transit_timing.py` is a standard-library-only domain module.
It defines immutable coordinate, provenance, optional observer-context,
uncertainty and ephemeris records, plus unresolved coordinate predictions.

| Object/API | Meaning and constraints |
|---|---|
| `TimeCoordinate` | Representation (JD/MJD/explicit offset), scale, reference position and original label remain distinct. Normalization changes the zero point only |
| `EphemerisProvenance` | Nonempty source, parameter-set, epoch/period references, version/retrieval evidence and explicit joint-fit declaration. Caller attribution is not authenticated evidence |
| `ObserverTimingContext` | Optional WGS84 site and ICRS target metadata, coordinate epoch and motion assumption. Validated structure/bounds, not sky accuracy; presence never grants observing eligibility |
| `UncertaintyComponent` | A decimal value or `None`, source and error interpretation. Asymmetric/limit/unknown-confidence inputs retain their original description and remain unsupported for standard propagation |
| `EphemerisUncertainty` | Epoch/period components, covariance in days squared or an explicit zero-covariance assumption. Finite/PSD checks; no silent repair |
| `StrictTransitEphemeris` | Original numeric strings, metadata, duration basis and uncertainty, optional cycle-validity limits. Missing validity is labelled unknown |
| `predict_coordinate_transit` | One signed-cycle nominal midpoint and symmetric T14 contacts; no baselines, UTC fields, observing window or range selection |
| `propagate_uncertainty` | Known symmetric errors with signed covariance; missing contributing inputs remain unknown with reasons |
| `require_quantified_padding` | Rejects a nonzero requested sigma multiplier when timing uncertainty is unknown. This check does not create an observing window |
| `require_observing_eligibility` | Always raises `arrival_resolution_unavailable` for this mission's unresolved predictions |
| `legacy_arithmetic_ephemeris` | Explicit acknowledged construction of the old numeric model. It does not convert a strict record or make a timing claim |

All domain errors use `TransitTimingError`, a `ValueError` with a stable `.code`.
Numeric source inputs must be decimal strings, not floats or booleans. They have
at most 24 significant digits and magnitude bounds stated in the policy; zero is
allowed only where meaningful. Normalized epochs are in JD [2400000,2500000],
periods in [0.125,365.25] days, cycles in [-10000,10000], and nominal T14 duration
in (0,24] hours. These are bounded implementation inputs, not physical validity
limits or claims of uncertainty accuracy.

Barycentric TDB arithmetic requires `ephemeris_coordinate` duration basis;
observer TAI arithmetic requires `observer_elapsed`. UTC, HJD, unknown or other
coordinate combinations may be represented in metadata but cannot be predicted
through the strict nominal API. No BJD-to-UTC scale relabelling occurs. Optional
observer metadata can be absent in a nominal preview because no observing
operation is enabled; it will be mandatory for a future arrival adapter.

An isolated 80-digit Decimal context protects arithmetic from a caller's decimal
precision setting. Bounded midpoint addition/multiplication is exact; division
for contacts and the square root for uncertainty can round at that precision.
The predeclared analytic test bound is 1e-70 days. This is an arithmetic contract
check, not an end-to-end timing tolerance or a physical accuracy claim. Original
input precision is retained and never represented as improved measurement precision.

## Unknown uncertainty and covariance

The implementation uses the linear-model propagation law

\[
\sigma_T^2(n)=\sigma_{T_0}^2+n^2\sigma_P^2+2n\operatorname{Cov}(T_0,P).
\]

The general law and the restriction on omitting covariance are supported by
[NIST's uncertainty guidance](https://physics.nist.gov/cuu/Uncertainty/combination.html).
The zero-covariance assumption must be supplied explicitly and remains in output.
The source record preserves both marginal uncertainties even when the output
cannot supply a total.

At cycle zero, only epoch uncertainty contributes. At nonzero cycles, missing
marginals/covariance, unsupported error semantics or a declaration that parameters
are not from a joint fit produce an unknown total. A known zero requires source
or assumption text and remains distinguishable from missing data. Non-PSD
covariance rejects, including just-outside-bound cases; negative variance is not
clamped. A standard deviation or a small numerical residual does not establish
confidence coverage, absence of TTV/decay, or the validity of extrapolation.

The time-coordinate distinction follows the primary sources already reviewed in
[Mission 36](transit_time_coordinate_contract.md#independent-references-and-project-decisions):
Eastman et al. (2010), Astropy Time documentation, and NASA archive column
metadata. No live catalogue data are fetched and no new independent conversion
reference is asserted in this mission.

## Downstream rejection and legacy compatibility

Strict records deliberately have no legacy `mid_transit_jd` property. Explicit
guards additionally reject strict objects at schedule generation, visibility
analysis/sampling, timing scores, ranking, UTC formatting, CSV/JSON/calendar
export, timelines, altitude/score figures and dashboard export/display helpers.
The tests include strict predictions nested inside legacy-shaped containers, so
these guards are not only checks on the outermost object.

The guards prevent implicit use of strict objects. They are not a security
boundary against a caller manually extracting a number and constructing a
legacy object. Raw-number APIs remain legacy compatibility paths and cannot
supply scientific provenance or validate the original coordinate. The original
`transit_scheduler.py` scalar implementation, its `None` handling and its inclusive
cycle selection are unchanged, preserving Mission 35's measured arithmetic.

Legacy JSON keeps schema version 1 and adds `timing_status: legacy_unvalidated`
at the top level and per event. Legacy CSV appends a `timing_status` column.
Calendar exports add `X-ASTROSCOPE-TIMING-STATUS:LEGACY-UNVALIDATED` and explanatory
event text. Strict consumers must not promote old files lacking this label or
source provenance. CSV consumers that require an exact old column count must
adapt to the appended field; existing field order and values are preserved.
The legacy timing-score helper now rejects `None` explicitly rather than
allowing it to be interpreted as zero; old finite numeric inputs are unchanged.

## Dashboard and nominal serialization

The English, Japanese, Korean and Thai dashboard now defaults to a
source-coordinate preview. Source identifier, parameter set and reference/version
are required before a prediction can be created. Uncertainty checkboxes default
to unknown; entering a number alone does not declare it known. The UI's
zero-covariance checkbox records an explicit user assumption. Asymmetric and
nonzero covariance metadata are available through the API, not this initial form.

Legacy scheduling requires selecting the legacy workflow and acknowledging its
UTC and uncertainty assumptions. Mode changes or acknowledgement revocation clear
old legacy results. A failed preview clears its prior downloadable result; failed
legacy generation also clears the previous schedule. Unsubmitted form edits do
not replace a previously submitted prediction.

`coordinate_prediction_to_json` uses schema version 2 with record kind
`unresolved_coordinate_prediction`, `observing_eligible: false`, source records,
output representation JD, uncertainty status and `null` for unknown values.
This is a nominal-prediction schema, not a schema-v2 observing schedule or an
import/migration implementation. No UTC fields or calendar export are offered.
The preview's stored model-validity status is unknown; the API additionally
accepts explicit bounded cycle-validity intervals and rejects predictions outside
them. Duration uncertainty is retained but no contact uncertainty is propagated.

## Coverage and verification

The separate [coverage record](../../../validation/manifests/transit_timing_boundary_coverage_v1.json)
maps all 26 Mission 36 scenario IDs to implemented boundary behavior, partial
coverage or deferred work. The original prospective manifest is unchanged.
In particular, converted query membership, numerical conversion accuracy, solver
failure handling, leap-second observing margins and resolved-event round trips
remain deferred. Passing CI does not execute those future scenarios.

Mission 37 adds **100 tests**. Independent rational arithmetic checks exact
dyadic midpoints/contacts and bounds repeating contact division. Perfect-square
variance cases check positive and negative covariance at signed cycles. Further
checks exercise unknown/zero distinctions, invalid/unsupported metadata, source
zero points, covariance just outside PSD bounds, foreign Decimal contexts,
serialization, direct consumer bypasses, explicit legacy compatibility, and UI
state across all four languages. A subprocess blocks network connections and
imports of Astropy, NumPy, Skyfield, Streamlit and Plotly while executing a strict
nominal prediction. Regression assertions would fail on unknown-to-zero or
covariance-sign changes; no conversion mutation experiment is claimed.

The 663 pre-existing transit/ephemeris tests passed during implementation.
The complete local suite passed **2,887 tests**, including all 100 new checks,
with Python 3.12.14, Streamlit 1.66.0, Astropy 8.0.1 and NumPy 2.5.3.
Ruff and compilation passed. The new UI tests were executed with Streamlit's
form-submission behavior from 1.66.0, as used by the preceding CI runs.
The complete quality gate and final published-head results are recorded in the
PR checks and retained six benchmark artifacts. Existing numerical fixtures,
reference generators and canonical benchmark records are unchanged. Mission 36's
historical audit remains tied to its original source hashes, not the modified
current consumers.

Reproduce locally after installing the project and its development dependencies:

```sh
python -m pytest -q tests/test_transit_timing.py tests/test_transit_timing_dashboard.py
python -m pytest -q
python -m ruff check .
python -m validation.transit_ephemeris --output work/transit-ephemeris-current.json
```

Use the existing workflow's environment and commands for all six benchmarks.
Installation may require package access; strict domain execution and benchmark
fixtures require no online source retrieval. The original Mission 35 environment
remains documented in its requirements file; CI also tests current allowed
versions. The PR records which versions and commit were actually exercised.

## Remaining gate and next mission

Delivery: [PR #37](https://github.com/wolfchil345/astroscope-ai-observatory/pull/37).
Its checks and PR description record the final published-head CI evidence.

Mission 37 merged through PR #37 on 2026-10-17 at 15:56:41 UTC as
`809b0bc89aa0e4b96de2e8f35d81c417b1609650`; post-merge CI passed.
The next scoped task, now active in
[Mission 38](observer_arrival_validation.md), is **Observer-Arrival Reference
Protocol and Conversion Validation**: define
independent reference data, coordinate/observer coverage, time-data provenance,
error budget, frozen tolerances and adapter acceptance before enabling observing
use. It must cover observer TAI/UTC representation and the separate barycentric
light-time problem rather than treating scale conversion as the entire operation.
Its exact implementation scope depends on reference feasibility. Mission 38 records research-only conversion evidence separately; production
observing eligibility remains disabled and later phases remain unstarted.
