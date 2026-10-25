# Mission 58 — BLS Physical-Membership Correction and Validation

## Decision and scope

The corrected production BLS search passes all **252 frozen Mission 56 trials**,
including all **ten required period recoveries** and all **nine previously failed
numerical checks**. The acceptance policy, synthetic inputs, published-data
selection and independent physical upper-bound reference are unchanged. These
results support the bounded W05 correction; W05 closure awaits review and merge.
Phase 2 remains active, with W06 reconciliation and W07 exit review outstanding.

Mission 57 was verified merged at `e2caf52d42ff1f053b05557be0ce045f251ef8bb`;
post-merge Quality Gate **40204219013** passed. Its
[mechanism study](bls_discrepancy_investigation.md) remains historical evidence.
This mission changes the production search, without patching the installed
Astropy package or introducing an upstream-fast fallback.

## Search contract

The [physical-search policy](../../../validation/manifests/physical_bls_policy_v1.json)
was committed at `971f795` before the first full corrected campaign evaluation.
It was designed after Mission 57's mechanism investigation: this is a targeted
repair and frozen-corpus regression, not a blind discovery experiment.

Astropy's `autoperiod` supplies the existing outer period grid. At every period,
the new engine evaluates every supplied duration and phase center
`j * min(durations) / oversample < period`. Centers are relative to the minimum
observation time. They are converted to representable absolute times before
evaluation, so the fit uses the epoch that will actually be returned. Durations
are the supplied physical durations, without legacy rounding to bin counts.

Each circular window is half-open, `[center-duration/2, center+duration/2)`.
The engine sorts observation phases, duplicates one period for wrapping, and
uses prefix sums to evaluate each window. No wrap-padding bin can replace a
real observation. For each partition, inverse-variance weights give inside and
outside means, depth `outside - inside`, and uncertainty
`sqrt(1/Win + 1/Wout)`. Nonnegative dimming fits are eligible. `snr` optimizes
depth divided by that uncertainty. `likelihood` retains the existing convention
`0.5 * Win * depth**2`: an improvement holding the fitted outside level fixed,
not a general likelihood-ratio or false-alarm calibration.

Every period is recomputed and ranked using the new objective. Refitting only
the old winning candidate would not establish a corrected period ranking.
Selected partitions are refitted with direct weighted means before reporting,
reducing accumulated-sum cancellation. Exact computed ties retain the first
ascending duration and phase, followed by the existing stable candidate ranking.
Floating arithmetic can distinguish mathematically equal fits; independent
tests accept any exact mathematical optimum. Candidate separation, result
models, input checks and typed production errors remain in place.

This is a finite period/phase/duration search. It does not establish a continuous
global optimum or arbitrary-precision behavior. Extremely ill-conditioned
weights, phase endpoints and large epochs remain floating-point limitations;
nonfinite weights/sums are rejected. More than one million phases at a single
period raises a typed production error before phase-grid allocation. That is a
resource guard, not a changed scientific acceptance threshold. Total work still
depends on period count, sample count and the supplied durations.

## Independent validation

The unchanged [Mission 56 reference](../../../validation/light_curve_references.py)
enumerates attainable circular-window memberships independently of the search.
Its numerical goals and all recovery requirements are reused byte-for-byte.
The new [Fraction oracle](../../../validation/physical_bls_reference.py) separately
enumerates every finite-grid window and calculates weighted means and objective
values with rational arithmetic. It imports neither Astropy nor production code
and does not use the production prefix-sum algorithm.

There are **106 new engine controls**, including 96 combinations of rational
fixtures, three periods, weighted/unweighted data and both objectives. They
compare scores and selected-fit quantities with absolute tolerance `1e-8`
(relative tolerance disabled). Other controls cover duplicate phases, wraparound,
half-open endpoints, multiple durations, affine flux/error changes, absolute
epoch offsets, all period samples, full production ranking and the phase cap.
A test forbids production calls to Astropy `power` or `autopower`.

The Mission 57 six-point counterexample now gives SNR `sqrt(75) = 8.66025404`,
consistent with the independent physical maximum, instead of the legacy
`sqrt(150) = 12.24744871`. A 24-point extension exercises the production minimum
sample count and confirms the newly computed best periodogram value is selected.
The first focused run had 102 passes and one test failure: the test excluded an
`autoperiod` endpoint represented as `0.8999999999999999`. The test was corrected
to respect the already-existing endpoint tolerance; production and science
thresholds were not changed for that failure. Further controls were then added.

Primary context is the [Astropy BLS API](https://docs.astropy.org/en/stable/api/astropy.timeseries.BoxLeastSquares.html)
and the [v8.0.2 implementation](https://github.com/astropy/astropy/blob/v8.0.2/astropy/timeseries/periodograms/bls/bls.c).
They define the retained period-grid and scoring conventions, not independent
scientific validation. The frozen Kepler-8 selection and
[Jenkins et al. 2010 reference](https://arxiv.org/abs/1001.0416) retain the
[Mission 56 provenance and limitations](light_curve_validation.md).

## Campaign results

The [canonical record](../../../validation/results/physical_bls_reference_run.json)
was executed from clean implementation commit
`74e397b0093284a23ba1940d1cb3ae35b0b06b1c`, before adding this report and result.
It records source/input hashes, dependencies and execution identity.

| Check | Result |
|---|---|
| Frozen trials | 252 passed, zero failed |
| Required period recoveries | 10 / 10 |
| Previously failed BLS checks | 9 / 9 now pass |
| Period outcomes across both algorithms and all stages | 77 fundamental; 9 daily alias; 2 half-period; 38 other; 124 without periodic truth; 2 expected LS rejections |
| White-null threshold flags, each stage | LS 0/10; BLS 0/10 |
| Red-null threshold flags, each stage | LS 10/10; BLS 1/10 |
| Local complete campaign runtime | 69.41 seconds |

The two rejections are approved constant-curve LS outcomes, not hidden failures.
The initial corrected run at `971f795` also passed all 252 trials (66.34 seconds).
The later clean run adds explicit old/current failure correspondence and provenance.
The corrected campaign is more expensive than the historical binned search;
these timings characterize this corpus and machine, not a performance guarantee.

The trending-case SNRs fall from approximately 394–399 to 341–350; the detrended
red-null SNR changes from 5.57456 to 5.55467. All are below their independently
computed attainable maxima under the unchanged numerical goal. One aggregate
period outcome moves from `other` to `daily_alias`; all required recoveries
remain successful. Full candidate values and all paired stage outcomes are
retained, including unfavorable and alias outcomes.

The null samples are small and paired across preprocessing stages. Counts and
Wilson intervals are descriptive, not universal FAP calibration. Kepler data
remain the same 1,322 retained rows in the first 30 days, in BKJD_TDB, without
time-coordinate conversion; the reference period remains the rounded abstract
value 3.523 days. Period recovery does not qualify transit arrival times.

## Historical evidence and offline reproduction

The old wrapper is retained byte-for-byte in
[the historical validation directory](../../../validation/historical/README.md),
SHA256 `daa92537c91274c774379385de85dfce3862fda73ccd891c2001054ecd2fd55a`.
Mission 56's default runner now explicitly targets that historical wrapper;
its nine strict expected failures and original observation snapshots remain.
Mission 57's upstream mechanism runner also labels its target as historical.
Their frozen canonical files are not rewritten or relabelled as successes.
The new production runner has **253 campaign tests with no expected failures**.
Together with the engine controls, this adds 359 passing tests.

Install `.[dev,validation]`, then all following work runs offline:

```bash
python -m pytest -q tests/validation/test_physical_bls.py tests/validation/test_physical_bls_campaign.py
OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 python -m validation.physical_bls_campaign --output /tmp/physical_bls_reference_run.json
python -m validation.light_curve_campaign --audit-observed-baseline --output /tmp/historical_light_curve_reference_run.json
python -m validation.bls_discrepancy --output /tmp/historical_bls_discrepancy_reference_run.json
python -m ruff check .
python -m pytest -q
```

Canonical environment: Python 3.12.14, Astropy 8.0.2, NumPy 2.5.4, SciPy 1.18.1,
Haswell OpenBLAS selection with one thread. The full local suite on the native numerical kernel passed **6,120 tests with
nine historical strict expected failures** in 271.61 seconds. Ruff, new-file
formatting, source/input hashes and changed Markdown link targets passed. Campaign tests block socket connections.
CI adds artifact 26, `physical-bls-validation-record`, retaining all 25 prior
artifacts. Its exit status requires all frozen trials and all nine old failures
to pass on current production. Final-head CI and downloaded artifact verification
are recorded in [PR #58](https://github.com/wolfchil345/astroscope-ai-observatory/pull/58)
before handoff.

## Remaining research boundaries

The numerical BLS correction does not provide a population detection-efficiency
model, calibrated false-alarm probabilities, transit-parameter posterior,
astrophysical confirmation or physical timing uncertainty. W06 must reconcile
coverage/provenance and the deferred Mission 36 contracts; W07 must review the
formal E01–E08 exit gates. Neither is completed by this mission.

X01 is unchanged: 18 covariance requirements unestablished, six physical
components unknown, 48 site clocks unqualified, and all 288 arrival candidates
blocked (240 solar-eligible, 48 excluded). No applicable physical covariance was
acquired or propagated. Physical timing bounds remain null and observing
eligibility false. Phases 0–1 remain complete; Phases 3–8 remain planned.
