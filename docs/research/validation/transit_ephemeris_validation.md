# Mission 35 — Exoplanet Transit Ephemeris Validation

## Starting point and predeclared protocol

Mission 34 was verified merged through PR #34 at
`7fdc96f4c9739969ae600bb3477ba394379197df` on 2026-10-15 at 16:44:47 UTC.
Mission 35 starts from that exact main commit. Phases 0 and 1 remain complete;
Phase 2 is active. This mission validates the existing transit ephemeris APIs;
no later phase or unrelated feature is authorized by this work.

The [acceptance policy](../../../validation/manifests/transit_ephemeris_policy_v1.json)
was committed as `d114753` before generation/comparison. Reference generation uses only
Python's standard library, 60-digit Decimal arithmetic and independently enumerated
cycles, with no production import. Published parameters are frozen historical
arithmetic inputs, not a current observing ephemeris or measured timing truth.

The comparison covers midpoint, symmetric first/fourth contacts, baselines,
independent symmetric uncertainty, positive/negative cycles, inclusive midpoint
selection, empty intervals and capacity/invalid-input contracts. Exact dyadic
boundaries are unambiguous; non-dyadic boundaries within 0.2 ms of a midpoint
are retained as numerically indeterminate and cannot inflate the topology pass rate.

Time-coordinate identity must be supplied externally: the core model has no
scale/reference-position field. The application constructs JD UTC ranges;
visibility and calendar exports interpret event JD as UTC without a barycentric
correction. Therefore arithmetic agreement cannot establish safe use of BJD TDB
or HJD catalog ephemerides in those downstream paths.

## Independent primary references

- NASA Exoplanet Archive, [Transit Algorithms](https://exoplanetarchive.ipac.caltech.edu/docs/transit/transit_algorithms.html), accessed 2026-10-15: linear midpoint prediction and distinction between contacts and padded windows. This mission does not claim equivalence to the archive's full uncertainty/window model or service output.
- NIST, [Combining uncertainty components](https://physics.nist.gov/cuu/Uncertainty/combination.html), accessed 2026-10-15: variance propagation including covariance; the zero-covariance restriction is explicit here.
- Maciejewski et al. (2011), [High-precision photometry of WASP-12 b transits](https://arxiv.org/abs/1102.2421v1), DOI 10.1051/0004-6361/201016268: historical BJD TDB coefficients in the abstract. No observed timings are reproduced or claimed as ground truth.
- Eastman, Siverd & Gaudi (2010), [Achieving better than 1 minute accuracy in the Heliocentric and Barycentric Julian Dates](https://arxiv.org/abs/1005.4415): time scale and reference position must accompany timestamps.

## Model and claim boundary

For integer cycle n, the validated model is:

```text
T(n) = T0 + n P
sigma(n)^2 = sigma(T0)^2 + n^2 sigma(P)^2
T1 = T(n) - T14 / 48               [T14 in hours; T1 in days]
T4 = T(n) + T14 / 48
start = T1 - baseline_before / 24 - k sigma(n)
end   = T4 + baseline_after / 24 + k sigma(n)
```

The general propagated variance includes `2 n Cov(T0, P)`. Its omission is valid
only under the declared zero-covariance assumption. Twenty separate diagnostic
examples with correlation ±0.5 and cycles ±1000 retain both variance models; they
are labelled **unsupported model diagnostics**, not failures of the implemented
zero-covariance arithmetic or validation of real confidence coverage. No
covariance is inferred for the historical published coefficients.

`None` uncertainties become numerical zero in production. The record labels each
input as supplied, explicitly zero, or containing an unknown component. A zero
output from missing data is not evidence of precise timing. Baseline duration,
T14, and k are deterministic experiment inputs. Contacts assume a symmetric,
constant-duration transit. Duration uncertainty and contact asymmetry are absent.

An event is selected by its **midpoint inside a closed range**. The observing
window may extend outside that range; a transit overlapping the range whose
midpoint is outside it is not selected. This is different from scheduling
occupancy/overlap semantics validated in previous missions.

## Frozen reference and reproducibility boundary

The [source record](../../../validation/fixtures/transit_ephemeris_sources_v1.json)
contains manually transcribed historical coefficients, citation, versioned source
URL, access date, time coordinate, and acquisition method. It is not a downloaded
NASA service response or an observed-transit dataset. The eight synthetic
families and one historical coefficient family deliberately separate arithmetic
from empirical astrophysics. Published duration/baseline values are not claimed:
those fields are synthetic even for the historical family.

[Stage A](../../../validation/reference_generation/transit_ephemeris.py) uses
60-digit Decimal arithmetic and exhaustive local cycle enumeration. It does not
reuse production ceil/floor selection, float hypot, or production constants.
Expected decimal strings retain their precision. Range endpoints are materialized
as binary64 inputs and then interpreted exactly via `Decimal.from_float` for the
reference comparison. Midpoints retain the original decimal coefficients.

The small enumeration domain surrounds every constructed query; its endpoints
and possible/certain cycles are retained. It is not an arbitrary-query oracle.
Normal tests and CI read the frozen fixture and never regenerate expected values.
The generator was separately executed under isolated Python in a fresh standard-
library environment with no AstroScope or astronomy dependencies. Fixture and
manifest regeneration were byte-identical. Manual one-cycle historical midpoint
anchors additionally check coefficient transcription/arithmetic.

The [manifest](../../../validation/manifests/transit_ephemeris_v1.json) records
SHA-256 hashes of the fixture, generator, source record and acceptance policy.
Stage B pins the manifest digest and rejects alteration of every input. The
[execution lock](../../../validation/requirements-transit.txt) records the actual
fresh validation environment. Scalar calculations need no IERS, ephemeris kernel,
network, Astropy or reference generator. A subprocess test blocks sockets and
imports of the reference generator, Skyfield and Astropy while running the full
benchmark CLI.

## Corpus and acceptance

| Evidence group | Coverage | Count |
|---|---|---:|
| Scalar event cases | 9 families × 7 signed cycles × 3 baseline/padding configurations | 189 |
| Range cases | 9 families × 3 signed cycle centres × 7 endpoint scenarios | 189 |
| Unambiguous range/index comparisons | Exact dyadic or >0.2 ms from non-dyadic boundaries | 165 |
| Indeterminate range/index comparisons | Retained near non-dyadic boundaries | 24 |
| Input contracts | Nonfinite/negative/zero parameters, invalid cycles/capacity, reversed intervals | 49 |
| Covariance diagnostics | Five supplied-uncertainty families, two cycle signs, two correlations | 20 |

Reference epochs span JD 2400000.5–2460000.5; periods span 0.125–365.25 days;
cycles are −10000, −100, −1, 0, 1, 100, 10000. Large cycle offsets are numerical
stress tests, not claims of a stable physical ephemeris across millennia. Range
scenarios include exact points, ULP-adjacent points, inclusive multi-event ranges,
empty ranges, ±1-second brackets and negative-to-positive cycle crossings.

The maximum scalar timestamp error allowed is **0.0002 s**, and the maximum
window-duration error is **0.0004 s**. Binary64 spacing at ordinary astronomical
JD is about 40 microseconds, with additional rounding through sums/subtractions.
Uncertainty error must be no larger than the greater of **1e-8 s** and **1e-12
relative**. These limits were frozen before the first measured residual and
have not been adjusted. They are numerical acceptance limits, not physical
transit prediction accuracy.

## Measured results

All 189 scalar events, 165 unambiguous range/index cases and 49 rejection
contracts pass. All 24 indeterminate cases satisfy the guard against gross
cycle errors, missing certain events, duplicates, unordered events, and events
outside the guarded range. Those 24 are **excluded from the independent topology
pass denominator**. There are no unexpected failures.

| Quantity | Maximum absolute error (seconds) | Bound |
|---|---:|---:|
| `egress_jd` | 4.5626564e-05 | 0.0002 s |
| `ingress_jd` | 2.95333099e-05 | 0.0002 s |
| `mid_transit_jd` | 3.7579937e-05 | 0.0002 s |
| `observation_end_jd` | 5.49765737e-05 | 0.0002 s |
| `observation_start_jd` | 4.61339951e-05 | 0.0002 s |
| `observation_window_hours` | 7.56382942e-05 | 0.0004 s |
| `timing_uncertainty_days` | 6.90171016e-11 | max(1e-8 s, 1e-12 relative) |
| `timing_uncertainty_hours` | 1.78580247e-11 | max(1e-8 s, 1e-12 relative) |

Each metric has 189/189 passing values. The canonical JSON also retains MAE,
median, RMS, finite counts, worst-case IDs, each reference decimal, actual float,
residual and threshold.

Four of the 24 indeterminate cases disagree with exact-decimal range/index
selection. These are disclosed results, not hidden by a relative JD comparison:

| Case | Exact-decimal cycles | Production cycles | Difference |
|---|---|---|---|
| fractional, n=−100, inclusive range | −100, −99 | −99, −98 | Both boundary memberships change |
| fractional, n=−100, point | empty | empty | First/last cycle indices differ |
| fractional, n=0, point | empty | 0 | Rounded epoch is selected |
| historical WASP-12, n=0, point | empty | 0 | Rounded epoch is selected |

The inputs contain the rounded floating endpoints while the oracle retains
exact decimal coefficients. Membership is ill-conditioned at that resolution.
This mission establishes neither exact real-arithmetic endpoint selection for
all non-dyadic values nor a new rounding policy. A future explicit time-coordinate
and boundary contract is needed before a stronger claim can be made.

## Scientific limitations and required follow-up

- No observed-transit O−C validation, current catalog freshness, TTV detection,
  orbital decay or validity of long-term linear extrapolation is established.
- BJD TDB is a barycentric timestamp; JD UTC in this workflow is interpreted as
  an observing instant. Relabelling the same number does not convert between
  them. No site/target-dependent light-time inversion or time-scale conversion
  exists in the ephemeris model. Downstream observatory timing is **unsupported
  for unconverted BJD/HJD inputs** despite passing scalar arithmetic.
- Correlated/asymmetric errors and duration uncertainty are unsupported. A k-sigma
  padded window has no empirically established probability coverage here.
- Unknown uncertainties remain scientifically unknown even when output is zero.
- Leap-second elapsed intervals, extreme overflow/sub-ULP periods, type coercion
  outside the tested numeric contracts, visibility, ranking and observing success
  are not validated by this corpus.

These limits are recorded for Phase 2 follow-up; this mission does not implement
new time types, conversions, UI controls, catalog retrieval or later-phase work.
Production Python under `src/` is unchanged.

## Reproduce

Execution (Python 3.12; installation requires package access):

```sh
python -m venv .venv-validation
.venv-validation/bin/python -m pip install -c validation/requirements-transit.txt -e '.[dev,validation]'
.venv-validation/bin/python -m validation.transit_ephemeris --output work/transit-run.json
.venv-validation/bin/python -m pytest -q
.venv-validation/bin/python -m ruff check .
```

Independent Stage A (no pip packages required):

```sh
python -m venv .venv-reference
.venv-reference/bin/python -I validation/reference_generation/transit_ephemeris.py --output-root work/reference-regenerated
cmp validation/fixtures/transit_ephemeris_v1.json work/reference-regenerated/validation/fixtures/transit_ephemeris_v1.json
cmp validation/manifests/transit_ephemeris_v1.json work/reference-regenerated/validation/manifests/transit_ephemeris_v1.json
```

The [canonical record](../../../validation/results/transit_ephemeris_reference_run.json)
is generated from a clean committed implementation, then committed separately to
avoid a self-referential Git hash. Its provenance includes implementation and
checkout commits, source/input hashes, dependency versions, environment, policy,
and execution timestamp. The runner exits nonzero on unexpected failure; CI
retains its JSON artifact even when the benchmark fails.

## Quality gate and baseline repair

Before Mission 35 changes, the baseline suite produced 2,299 passes and two
failures in `test_planner_preserves_new_york_repeated_hour_fold`. The bundled
IERS_Auto predictions had aged beyond the 30-day freshness rule. These two tests
assert civil-time identity, not Earth-orientation accuracy. They now use an
explicit installed IERS_A table in a restoring context. This makes their fold
assertions independent of wall-clock cache age; it does not relax production
freshness checks or alter Mission 33/34 frozen Earth-orientation evidence.

Mission 35 adds **486 tests**. The final full suite passes **2,787 tests**.
Ruff, compilation, independent byte-identical regeneration, and existing
observer-time, civil-time, schedule-interval, weather-provider, celestial-coordinate
and solar/lunar/twilight benchmarks pass. The three civil-time benchmarks are
run with `PYTHONTZPATH=''`, as required by their existing pinned-IANA protocol.
New tests include corrupted evidence, one-second and nonfinite output mutations,
missing/extra/duplicate events, gross cycle-index errors, offline subprocess
execution, canonical model limitations and the CLI failure exit code.

Canonical evidence is recorded in a separate commit after the implementation;
the commit recorded in the JSON is the source of truth for the measured code.
The canonical implementation is `8a1891f38963c2f81abd3c2c1a8f4b5b4ead32da`,
with `git_dirty: false` and no Skyfield installed in the execution environment.

Phase 2 remains active. Mission 35 remains active until review and merge; a
passing arithmetic benchmark does not close the outstanding scientific limits.

## Delivery status

The validated implementation and canonical evidence are committed on local branch
`research/mission-35-transit-ephemeris`. Publishing was attempted after validation:
terminal Git had no push credentials, and the connected GitHub integration rejected
Git tree creation with HTTP 403, `Resource not accessible by integration`. No
remote branch or pull request was created. The unchanged upstream main remains
Mission 34 merge `7fdc96f4c9739969ae600bb3477ba394379197df`.

The delivery bundle preserves all local commits, including the pre-measurement
policy commit and clean canonical implementation. Repository write access is
required to publish this branch. Mission 35 stays active pending PR review and
merge; no new mission has started.
