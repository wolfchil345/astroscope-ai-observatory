# Mission 56 — Light-Curve Recovery and Validation Baseline

## Decision and scope

W05 remains **active**. The frozen campaign executes 252 trials on 42 datasets.
All 10 required period recoveries pass, but **nine independent BLS numerical
checks fail**. Reproduction of these observations is a software audit, not a
scientific pass. This mission supplies the protocol, published input, independent
controls and retained evaluation; it does not close W05 or approve Phase 2 exit.
No production code or pre-evaluation acceptance threshold changed.

Mission 55 was verified merged at `a6b5d8bedfdd32f374d4632b4af5656f29014466`;
post-merge Quality Gate **40191044692** succeeded. This work follows the
[W05 scope and split-deliverable allowance](../phase_2_coverage_audit.md).

## Frozen design

The [policy](../../../validation/manifests/light_curve_campaign_policy_v1.json),
[inputs](../../../validation/fixtures/light_curve_campaign_v1.json) and their
[hash manifest](../../../validation/manifests/light_curve_campaign_v1.json) were
committed at `41a7885` before evaluation. Synthetic generation uses standard-library
math and seeded randomness, independently of AstroScope and Astropy periodograms.
There are two seeds for each sine/box × uniform/gap/daily/trend/outlier combination
(20 curves), ten white-noise and ten AR(1) nulls, one constant curve and one
published Kepler curve. Fixed seeds are a small designed corpus, not a population
sample; stages and signal kinds sharing seeds are paired, not independent repeats.

Synthetic times are elapsed days without an absolute coordinate. Nominal cadence
is 0.06 day with small jitter, 500 points and about 30 days' span. The signal period
is 2.7 days; sine amplitude and box depth are 0.015, box duration 0.18 day. Noise
has known heteroscedastic sigma cycling through 0.001, 0.0015 and 0.002. AR(1)
coefficient is 0.9; initialization is zero, not an independently equilibrated
stationary draw. The gap removes days 8–19; daily sampling keeps phase <0.25;
trend multiplies flux by 1+0.02t without rescaling supplied errors; outliers add
0.1 every 41 samples. Trend cases therefore deliberately include misspecified
uncertainties. They do not establish an astrophysical noise model.

Each curve independently enters median normalization, normalized linear detrending,
and normalized 5-sigma clipping: these are three branches, not sequential steps.
Search bounds are 1–6 days; LS uses 10 samples per peak; BLS uses durations
0.12/0.18/0.24 day, oversample 10, frequency factor 3 and SNR objective. All top-five
candidates, warning messages, rejections, sample counts, removed points, period
classes and injected-depth ratios are retained. Depth ratios after preprocessing
are descriptive, not unbiased depth recovery claims.

Required recovery is within 1% only for matching sine/LS and box/BLS uniform
cases, and published BLS, on normalized and detrended stages: ten trials. Other
recoveries remain diagnostics, including half/double-period and daily aliases.
LS compares returned power with independently solved weighted sine/cosine/intercept
regression at the returned frequency (absolute allowance 0.01 for fast-grid
approximation). BLS enumerates every circular-window membership at returned period
and duration using weighted inside/outside means. Its maximum positive depth SNR
is a one-sided upper bound (slack 1e-5), not an independent global period search
or a validation of underestimation. Analytic weighted examples and 81 exhaustive
small-grid value combinations test this oracle, including both entry and exit
transitions. Constant input permits typed rejection or finite output; near-zero
roundoff after detrending is not assigned a detection or LS reference power.

## Published input and independent period

The committed raw product is Kepler-8 / KIC 6922244 Quarter 4, DR25,
`kplr006922244-2010078095331_llc.fits` (469440 bytes), obtained from
[MAST](https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:Kepler/url/missions/kepler/lightcurves/0069/006922244/kplr006922244-2010078095331_llc.fits).
SHA256: `3dd9096da2753b01a1bbc2bd97b58da7526f4b98ea06c07b83c67d70abfe0224`.
MAST API, archive missions URL and STScI public S3 mirror returned identical bytes.
NASA's Kepler mission and MAST/STScI supplied these public mission data;
[MAST data-use terms](https://archive.stsci.edu/publishing/data-use) apply. The FITS
product is not relicensed as repository code.

Selection was fixed before searching: first 30 days from first finite TIME,
finite PDCSAP_FLUX/TIME/positive PDCSAP_FLUX_ERR, then SAP_QUALITY=0. Exclusive
filter counts are 4397 total, 289 nonfinite/invalid-error, 2659 outside the window,
127 nonzero-quality, **1322 retained**. No additional clipping selects the archive
sample. Original row indices, units, processing version and header conventions
are retained. PDC flux is already pipeline corrected; this campaign does not
validate that correction. See the [archive-product explanation](https://lightkurve.github.io/lightkurve/tutorials/1-getting-started/using-light-curve-file-products.html).

TIME is retained as **BKJD_TDB = BJD_TDB − 2454833**, with TIMESYS=TDB,
TIMEREF=SOLARSYSTEM, BJDREFF=0 and days. Metadata labels perform no time conversion.
The independent published period is the rounded **3.523 days** in the abstract of
[Jenkins et al. (2010), arXiv:1001.0416v1](https://arxiv.org/pdf/1001.0416v1).
This supports bounded period recovery, not precision ephemerides or transit timing.

### Retained checksum investigation

Astropy 8.0.2 initially returned CHECKSUM statuses [1,0,0]; DATASUM is absent in
all HDUs. No bytes were repaired. Independent big-endian 32-bit one's-complement
sums of each complete padded HDU equal 0xffffffff. The
[FITS checksum specification](https://fits.gsfc.nasa.gov/registry/checksum/checksum.pdf)
permits CHECKSUM without DATASUM; the missing-key behavior is consistent with
[Astropy issue 20595](https://github.com/astropy/astropy/issues/20595). A diagnostic
fitsio 1.4.2 check also rejected absent data checksums, so it is not claimed as
successful verification or required for replay. Integrity rests on raw whole-HDU
sums, sealed SHA256 and byte-identical downloads; checksums do not prove authenticity.

## Results, retained failures and limitations

The [initial clean run](../../../validation/results/light_curve_campaign_initial_failure.json)
retains 14 failures: 13 BLS comparisons and one LS constant-reference instability.
The initial BLS oracle missed some memberships caused by removal of a point.
The corrected oracle enumerates boundaries and intervening intervals; four BLS
failures disappear. Centering the LS reference and explicitly excluding constant
input resolve the degenerate comparison under the original constant policy.
The initial run is historical evidence, not a valid current oracle baseline.

Nine discrepancies remain: normalized and sigma-clipped `sine-trend-{0,1}` and
`box-trend-{0,1}`, plus detrended `red_null-uniform-2`. Trend SNR excesses are
118.89–125.90 (43–46% above the independent bound); the red-null excess is 0.23150
(4.33%). These include paired duplicate stages, not nine independent discoveries.
The [same-library diagnostic](../../../validation/light_curve_bls_diagnostic.py)
uses slow and fast modes at oversample 100 at each reported period/duration.
All nine slow results respect the independent bound; fast mode at 100 still
exceeds it on the red null. This implicates phase discretization/implementation
behavior, but does not establish a complete root cause or a generally safe new
oversampling setting. No production fix or new configuration is claimed.

At each stage LS flags 0/10 white nulls and 10/10 red nulls using FAP <0.01;
BLS flags 0/10 white and 1/10 red using SNR >=6. Wilson 95% intervals are recorded,
including [0,0.27753] for 0/10 and [0.72247,1] for 10/10. These small, paired,
fixed ensembles do not calibrate universal FAPs, detection probabilities or survey
false-positive rates. BLS SNR is not a calibrated false-alarm probability.
Clipping can remove transit information; detrending can alter periods and depths.
All diagnostic outcomes remain in the record rather than conditioning results
on successful recoveries. Kepler-8 BLS returns 3.524205 days on both normalized
and detrended branches (within the 1% goal); LS returns its half-period. Clipping
removes 57 points, after which neither algorithm recovers the fundamental. Across
all trials the retained classifications are 77 fundamentals, eight daily aliases,
two half-periods, 39 other periods, 124 without periodic truth and two rejections.

## Offline replay and CI meaning

After installing `.[dev,validation]` (recorded runtime: Python 3.12, Astropy 8.0.2,
NumPy 2.5.4, SciPy 1.18.1), no network is needed:

```bash
python -m validation.reference_generation.light_curve_campaign
python -m pytest -q tests/validation/test_light_curve_campaign.py tests/test_light_curve*.py
python -m validation.light_curve_campaign --output /tmp/light_curve_science.json
# Expected exit 1: overall_passed=false, nine scientific failures.
python -m validation.light_curve_campaign --audit-observed-baseline --output /tmp/light_curve_audit.json
# Expected exit 0 only when observed successes AND failures reproduce.
python -m validation.light_curve_bls_diagnostic --record /tmp/light_curve_audit.json --output /tmp/light_curve_diagnostic.json
```

The generator decodes the frozen FITS with Astropy; its numerical injection and
runtime reference regression do not call Astropy periodograms. Runtime evaluates
frozen JSON; tests deny socket connections and require byte-identical regeneration.
The post-evaluation [original observation baseline](../../../validation/fixtures/light_curve_observed_baseline_v1.json)
is explicitly a regression snapshot, not an independent reference or revised
acceptance policy. It compares every observation with float roundoff tolerances
1e-8 relative / 1e-9 absolute against one complete supported variant. Changed
failure identities, missing trials, degraded values, improved results or changed
metadata require review; they cannot silently pass. Mixing rows from variants
is rejected. Nine strict expected-failure tests expose unresolved scientific checks.
CLI tests verify default exit failure, explicit audit success and mutation rejection.

### Retained cross-platform audit failure

[CI run 40193626649](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/40193626649)
failed eight tests: six trial snapshots plus aggregate and CLI audit checks
(5644 passed, nine expected failures). All nine scientific failure identities,
required recoveries and null counts were unchanged. The audit steps were skipped
following the test failure, so uploads found no generated files; this was not
loss of previously committed evidence. The new light-curve step now runs even
after a test failure and writes both records while preserving its failure exit.

Local replay with `OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1` reproduced
the same six affected trial IDs and mismatch paths. Detrending roundoff changes
nearly tied BLS candidates on five curves and the meaningless LS candidates on
a constant curve. For daily-sampled sine seed 1, equally strong BLS peaks
(SNR 52.35211398) move from 1.58879745 to 1.58667179 days. Re-evaluating the
independent bound at the changed period gives 52.35211398 rather than 54.01604741;
both satisfy the original bound. No scientific threshold was loosened.

The [investigation record](../../../validation/results/light_curve_platform_investigation.json)
and [complete Haswell observation variant](../../../validation/fixtures/light_curve_observed_haswell_v1.json)
retain this evidence alongside the original snapshot. The audit requires the
entire campaign to match one variant; no row-wise mixing or selective omissions
are allowed. This is bounded reproducibility for two observed numerical-kernel
variants, not a claim of bitwise portability or unique candidate selection.
Unknown variants fail review. All raw candidate outputs remain in the records.
Requested OpenBLAS settings and machine architecture are recorded in new runs;
no specific numerical kernel is forced on the production application.

The [canonical record](../../../validation/results/light_curve_campaign_reference_run.json)
was first executed cleanly at `0f38a93be98112cf2163ff6b3254e4f46707b378`.
The current canonical replay includes both supported observation variants; its
observation audit passes while scientific acceptance remains false. The
[diagnostic record](../../../validation/results/light_curve_bls_diagnostic.json)
retains all nine comparisons. Initial focused tests: **662 passed, nine strict xfailed**. The platform fix
adds a whole-variant mixing rejection test (392 new passing tests and nine new
expected failures); updated validation is recorded below. Ruff lint passes.
Formatting checks pass for all new Python files; a repository-wide format check
reports 15 pre-existing files, left unchanged.
The canonical record identifies the clean implementation commit, source/input
hashes, package versions and all 252 outcomes. CI retains the previous 23 artifacts
and adds `light-curve-validation-record` with the campaign and diagnostic records.
A green CI run means reproducible baseline and passing software tests; it does
**not** change `overall_passed=false`. Local full suite: **5652 passed, nine strict xfailed** (194.13 seconds).
Final-head CI and artifact verification are recorded in
[PR #56](https://github.com/wolfchil345/astroscope-ai-observatory/pull/56).

## Follow-up and preserved restrictions

W05 needs qualification of the BLS discrepancy and a reviewed correction or
explicit bounded exclusion, with the same frozen inputs and unchanged scientific
goals. Do not claim W05 complete on the basis of required recovery alone. W06
reconciliation and W07 formal review remain pending. X01 remains blocked: all
48 site clocks unqualified, 18 covariance requirements unestablished, six physical
error components unknown, 288 combined arrival candidates blocked (240
solar-eligible/48 excluded), no applicable physical covariance acquired or
propagated, physical bounds null and observing eligibility false. Light-curve
period recovery does not alter arrival-time qualification. Phases 0–1 remain
complete, Phase 2 active and Phases 3–8 planned.
