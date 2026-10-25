# Mission 57 — BLS Numerical Discrepancy Investigation

## Decision

The nine Mission 56 BLS discrepancies are explained by a source-traced phase-bin
membership defect in the inspected Astropy 8.0.2 fast implementation. They are
**not resolved in production**. W05 and Phase 2 remain active. This mission adds
causal evidence, an analytic counterexample and an offline sensitivity record;
it changes neither production code nor Mission 56 inputs, scientific goals,
observations or expected-failure tests.

Mission 56 was verified merged at `0ef98f5ca1f2f104c87c26baf306def8f8cc9f13`.
Post-merge Quality Gate **40200543887** completed successfully. Its original
[light-curve dossier](light_curve_validation.md) remains the baseline.

## Evidence design and independence

The [investigation policy](../../../validation/manifests/bls_discrepancy_policy_v1.json)
was committed with the diagnostic at `9321614` after exploratory source inspection
and a six-point probe, before the complete 95-measurement sweep. This is a
post-exploration mechanism study, not a blind preregistered discovery experiment.
Selection is deliberately failure-enriched: all nine failed trials plus ten
normalized/detrended BLS controls (four uniform synthetic signals and Kepler-8).
At each original best period, fast BLS is evaluated with the **original complete
three-duration grid** and oversampling 5, 10, 20, 50 and 100. The returned duration
can change; the independent bound is recomputed at that returned duration.
This does not repeat the full period search or establish a population failure rate.

Three distinct kinds of evidence are kept separate:

1. **Source-derived diagnostic:** the bin-to-observation trace reconstructs the
   inspected upstream algorithm. Agreement with Astropy checks the trace; it is
   not an independent scientific reference.
2. **Independent physical bound:** Mission 56's exhaustive circular-window
   membership oracle, unchanged, gives the maximum attainable positive weighted
   depth SNR at the reported period and duration. The existing 1e-5 upper slack
   remains unchanged. The trace agreement goal is separately 1e-8 absolute SNR.
3. **Analytic counterexample:** six rationally specified observations permit
   direct weighted-mean/Fraction calculations independent of Astropy.

The upstream [Astropy v8.0.2 source](https://github.com/astropy/astropy/blob/v8.0.2/astropy/timeseries/periodograms/bls/bls.c)
was retrieved and byte-hashed against the installed source; both SHA256 values are
`c278224544ab517de9089183779de5dec7e6e3137ad7d68ac1744be1cb3fda56`.
The source is BSD-3-Clause licensed; the diagnostic credits it explicitly.
Runtime refuses an unreviewed Astropy version or source digest. This bounded
source qualification is intentional: a new upstream implementation needs review.
[Astropy's API documentation](https://docs.astropy.org/en/stable/api/astropy.timeseries.BoxLeastSquares.html)
describes fast versus slow methods and oversampling. Same-library slow results
from Mission 56 remain diagnostics, not an independent reference.

## Mechanism

Let the bin width be b = min(duration grid)/oversample and L = ceil(period/b).
The implementation assigns real observations to one-based bins 1 through L.
Its wraparound copy begins at **L**, replacing that real final bin with bin 1,
then copies subsequent early bins. Consequently, a candidate may use early-phase
observations in place of actual late-phase observations. The weighted mean
arithmetic can be internally consistent while describing a different set of
observations from the reported physical box.

The trace records original row indices, the overwritten bin, selected start bin,
legacy members, physical members and both signed two-level fits. It also performs
one controlled intervention: preserve bin L, copy padding after it and allocate
padding for the longest requested duration. It evaluates the **same selected bin
window**, isolating membership changes. This intervention does not rerank periods
or search for a corrected global optimum.

For the eight trending failures at oversample 10, start bin 80, L=90 and duration
10 bins select the corrupted wrap boundary. Nine observation memberships differ
from the reported physical box. For the detrended red null, start bin 282, L=294
and duration 20 bins produce two differences. Reconstructed SNRs match all nine
retained production values within 1e-8 (maximum error over all 95 measurements:
9.10e-13). The same-window padding intervention drops the original failing SNRs
below their independent upper bounds; physical candidate refits also respect
the bounds. Original SNRs, replacement fits and every membership are retained.

This establishes the mechanism for these selected failures. It does **not** prove
that changing one C index is a sufficient general repair. A partial final bin
still affects quantized wrap geometry, and the legacy padding length depends on
the shortest duration although a longer duration can win. Any repair must address
physical membership and phase coverage together, rather than assuming a uniformly
quantized circle has exactly the requested period.

## Analytic witness and endpoint limitation

Use period 1, duration 0.2, oversample 2, unit uncertainties, times
[0, 0.02, 0.82, 0.92, 0.5, 0.6] and values [0, 0, 0, 10, 10, 10]. These six
observations exercise the upstream numerical method directly; AstroScope's
production minimum of 20 observations is not bypassed or modified.

The corrupted winning window contains rows [0,1,2], three zero values. Its reported
SNR squared is 10²/(1/3+1/3) = **150**, hence SNR **12.24744871**. No physical
0.2-wide circular box can contain all three zeros without admitting the high
point at time 0.92. The optimal physical box contains the first two zeros;
the outside mean is 30/4 and SNR squared is (30/4)²/(1/2+1/4) = **75**, hence
**8.66025404**. The independent oracle reproduces this analytic maximum.

The padding intervention selects rows [2,3] and yields zero depth. At the reported
center 0.9, time zero is exactly a mathematical open endpoint: floating modulo
may include it, producing physical-fit rows [0,2,3] and SNR 4.08248 instead of
zero. Both are explicitly allowed as endpoint diagnostic outcomes and both remain
below the unchanged analytic bound. The first witness test wrongly assumed that
endpoint would always be excluded (107 passed, one failed); it was corrected to
check both explicit memberships. No fixture, science threshold or upstream result
was changed to address that test assumption.

## Sensitivity results

All **95 source traces** pass and all physical refits satisfy their independent
bounds. The original nine violations reproduce. There are **22 fast-bound
violations out of 95 selected measurements**; the analytic witness is additional.
The denominator includes paired stages and repeated curves/settings and must not
be treated as 95 independent astrophysical realizations.

Oversampling is non-monotonic: the trending sine cases pass the bound at 5,
fail at 10 and 20, then pass at 50 and 100. Box trend seed 0 also fails at 50.
The red-null case passes at 5 but still fails at 100. A single higher oversampling
setting is therefore not qualified as a remedy.

The original Mission 56 slow/fast diagnostic passed only the returned duration
into its rerun. For a winning duration 0.24, that makes the phase bin twice as
wide as the original search whose minimum duration was 0.12. Mission 57 retains
that historical diagnostic but uses the full original duration grid throughout;
otherwise a change in discretization can be mistaken for a pure resolution test.

## Reproduction and tests

Install the project with `.[dev,validation]`; no network is needed afterward:

```bash
python -m pytest -q tests/validation/test_bls_discrepancy.py tests/validation/test_light_curve_campaign.py
python -m validation.bls_discrepancy --output /tmp/bls_discrepancy_reference_run.json
```

Recorded environment: Python 3.12, Astropy 8.0.2, NumPy 2.5.4, SciPy 1.18.1.
The canonical run uses `OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1`; the
original-kernel run is also tested. Machine, requested core type, dependency
versions, input/source hashes and clean implementation identity are recorded.
Tests block socket access, cover all 95 traces, reproduce the analytic witness,
check signed fits and affine flux invariance, reject duplicated membership and
unreviewed upstream source, and preserve the distinction between a successful
mechanism audit and unresolved production science. Focused validation: **500
passed, nine strict expected failures**, including 108 new passing tests.

[Canonical investigation record](../../../validation/results/bls_discrepancy_reference_run.json),
executed cleanly at `010ea438b310c76cb73404d62691fd822c4cb446`.
CI adds artifact 25, `bls-discrepancy-investigation-record`, preserving the previous
24. Exit zero means the mechanism checks passed; the record explicitly keeps
`production_scientific_failures_resolved=false`. Final-head CI and downloaded
artifact verification will be recorded in the PR before handoff.

## Next bounded work

A production remedy needs a separately reviewed physical-membership contract,
corrected search/ranking strategy, boundary and multi-duration counterexamples,
and full frozen Mission 56 recovery replay with unchanged scientific goals.
Refitting only the old best candidate cannot prove that the corrected best period
has been found. Until those checks pass, keep all nine expected failures and
retain W05 as active. This mission neither patches the installed dependency nor
files an external upstream issue.

X01 is unchanged: 48 site clocks unqualified, 18 covariance requirements
unestablished, six physical components unknown and all 288 arrival candidates
blocked (240 solar-eligible, 48 excluded). No physical covariance was acquired or
propagated; physical bounds remain null and observing eligibility false. W06
reconciliation and W07 formal review remain pending; Phases 3–8 remain planned.
