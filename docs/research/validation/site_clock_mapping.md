# Mission 43 — Independent Site-Clock Mapping and Uncertainty Qualification

## Outcome and baseline

An independent **leading-order site-clock surrogate** now runs offline for all
48 historical site instants, with 12 separate geocentric controls. All numerical
checks pass. The physical qualification outcome is **incomplete evidence
retained**, not a validated observing clock: six required uncertainty components
remain unknown, and all 288 combined arrival cases remain blocked.

Mission 42 merged in [PR #42](https://github.com/wolfchil345/astroscope-ai-observatory/pull/42)
as `7d1e6557929f873389be369612b6855ae4db22cc` on 2026-10-18 at 08:21:50 UTC.
Its [post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39111153623)
passed before tracked changes. The [Mission 43 protocol](../../../validation/manifests/site_clock_policy_v1.json)
and isolated environment lock were committed as `7b80a95` before site-model
values, target-date formal-error extraction or residual measurement. Source and
implementation inspection preceded that freeze; thresholds, inputs and sample
selection were not tuned afterwards. Phases 0 and 1 remain complete; Phase 2 is active.

## Model and convention boundary

The new research model is `de440t-skyfield-gcrs-c2-site-surrogate-v1`. For supplied
TT seconds `a` from J2000, it solves

$$\delta+D(a+\delta)-\frac{\mathbf v_E(a+\delta)\cdot
\mathbf r_{\mathrm{GCRS}}(a,\mathrm{UT1},x_p,y_p;\delta)}{c^2}=0.$$

`D` is the DE440t geocentric **TT minus TDB**, in seconds. The station term has
the positive sign in `TDB−TT`; it is not a propagation delay added to an already
site-inclusive candidate. The speed of light is exactly 299,792,458 m/s.

| Quantity | Implemented source and limitations |
|---|---|
| Geocentric clock | Mission 42 checksum-pinned DE440t; raw CSPICE time segment, no re-normalization or fitted bias |
| Earth velocity | CSPICE `spkez(399, et, "J2000", "NONE", 0)`, geometric barycentric velocity; km/s converted to m/s |
| Station position | Skyfield WGS84 ITRS-to-GCRS rotation at supplied TT, frozen UT1 and polar motion; metres |
| Orientation | Model precession/nutation; observed celestial-pole offsets dX,dY are retained as evidence but not applied |
| TDB argument | Integrated trial delta explicitly injected into Skyfield `tdb_fraction`; its approximate `tdb_minus_tt` raises if invoked |
| Frame/scale boundary | GCRS vector is a leading-order surrogate, **not** the exact scaled BCRS station difference |

[Park et al. (2021), section 2.3, equation (3)](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf)
provides the leading station dot product and a displayed higher-order station
term. This experiment does not implement its complete relativistic mapping.
[IERS Conventions 2010, chapter 10](https://iers-conventions.obspm.fr/content/chapter10/tn36_c10.pdf)
distinguishes coordinate-time transformations, normalization and proper-clock
realization. Its estimates for particular older time ephemerides cannot simply
be assigned to this DE440t site surrogate.
[Klioner (2008)](https://arxiv.org/abs/astro-ph/0508292) explains why relativistic
scaling concerns coordinate quantities, not interchangeable units. Naming both
vectors in metres does not establish frame/scale compatibility.

The selected arrival convention remains **`astroscope-tdb-solar-au-v1`**, including
the existing Astropy/ERFA site clock and UTC-fraction approximation to UT1. The
surrogate is a separately named research comparison, not a silent replacement.
No production scientific code, eligibility boundary or scheduling behavior changes.

## Independence and numerical protocol

The isolated reference process imports Skyfield, SpiceyPy and jplephem, but no
Astropy, ERFA, PINT, AstroScope or candidate validation code. It uses the same
published physical inputs, so this is implementation independence, not independence
of astronomical theory or observations. CSPICE and jplephem read the **same**
kernel; their velocity agreement is an implementation cross-check only.

All four dates × four sites × three hours from Mission 38 are retained. The six
target directions do not multiply the 48 unique clock inputs. Twelve distinct
zero-site controls reproduce Mission 42. TT inputs come from its independently
constructed historical coordinates, not from the candidate clock.

Fixed-point solves start at zero, allow eight evaluations, and stop at an equation
residual of `1e-15 s`. Every iteration, signed residual, actual binary64 ET,
velocity, station vector and failed outcome is retained. The audit replays signs,
updates, arguments and stopping decisions. Supplied-vector dot products are
recomputed with 70-digit Decimal arithmetic. Frozen engineering limits are
`1e-15 s` for vector arithmetic, `1e-6 m/s` for the velocity readers, and `1e-12 s`
for geocentric and archived-candidate reproduction. These limits are not physical
accuracy requirements. Large-epoch ET quantization is separately reported and
must not be confused with the precision of the slowly varying clock correction.
The maximum recorded ET argument quantization is **59.5921 ns** across these
site solves; all 48 converge in three evaluations.

Two variants change only the site term at the final nominal velocity: UTC used
as UT1, and polar motion omitted. These are component diagnostics, not alternate
full solves or uncertainty estimates. No residual-based exclusions are made.

## Retained uncertainty evidence

The original IERS ASCII file already pinned by Mission 34 includes formal errors
that its slim EOP fixture omitted. This mission extracts the eight daily records
bracketing the four dates and retains `xp`, `yp`, `UT1−UTC`, `dX`, `dY` and all five
formal errors. Nominal xp, yp and UT1 values must exactly match the historical
fixture; no refreshed EOP inputs are substituted.

The source is `eopc04.1962-now` in `astropy-iers-data 0.2026.9.21.0.56.25`, SHA-256
`6c1e052b7822ba84e793e28aa14080552f53d5c66b739cd0e67cb4b46d0e7815`.
It is parsed as data with the standard library, not imported through Astropy.
The [IERS C04 format description](https://datacenter.iers.org/versionMetadata.php?filename=latestVersionMeta%2F234_EOP_C04_20.62-NOW234.txt)
identifies these formal-error fields. They are not hard error bounds; covariance,
coverage probabilities, interpolation/model errors and missing CIP corrections
are not invented. [Skyfield's accuracy documentation](https://rhodesmill.org/skyfield/accuracy-efficiency.html)
also makes explicit the need to supply polar-motion information.

| Required physical component | Why its hard bound remains null |
|---|---|
| Geocentric time ephemeris | No applicable domain-wide DE440t clock bound established |
| Earth velocity | Same-kernel reader agreement is not ephemeris uncertainty |
| Station coordinates | Nominal WGS84 inputs are not survey error bounds |
| Earth orientation | Formal errors do not bound all orientation/interpolation errors |
| Frame/scale mapping | GCRS-to-scaled-BCRS mapping and its error are not qualified |
| Higher-order remainder | Bounding one displayed term does not bound the complete remainder |

For **hypothetical**, compatible-coordinate bounds `|v|≤V`, `|r|≤R`,
`|Δr|≤dr`, `|Δv|≤dv`, the triangle inequality gives
`|Δ(v·r)/c²| ≤ (V dr + R dv + dv dr)/c²`, without a statistical independence
assumption. The displayed Park station term has conditional envelope
`(3U+V²/2) V R/c⁴` when its potential and coordinate assumptions hold.
The frozen example `V=40,000 m/s`, `R=7,000,000 m`, `dr=1 m`, `dv=0.001 m/s`,
`U=2e9 m²/s²` evaluates to approximately **0.523 ps** and **0.236 ps** respectively.
These are finite-precision evaluations of analytical inequalities under invented
example inputs, not observed uncertainty, outward-certified complete bounds or a
sum that qualifies this reference. Even zero hypothetical errors leave the real
physical total unknown. Proper-clock realization error is separately outside the
supplied ideal TT(TAI) coordinate assumption.

## Results and claim limits

All 48 site solves and 12 geocentric controls converge and pass their numerical
checks. The live candidate reproduces Mission 41's 48 archived site/geocentric
pairs within the frozen tolerance. Every signed comparison is retained.

| Diagnostic | Samples | Minimum | Maximum |
|---|---:|---:|---:|
| Astropy site clock minus surrogate | 48 | −27.0662 ns | −22.9410 ns |
| Site-increment difference after removing geocentric model difference | 48 | −0.604208 ns | +0.953600 ns |
| UTC-as-UT1 minus nominal site term | 48 | −6.42623 ps | +8.00551 ps |
| No-polar-motion minus nominal site term | 48 | −3.58237 ps | +4.66386 ps |

Maximum velocity-reader discrepancy is `8.03145e-12 m/s`; maximum absolute
Decimal/supplied-vector discrepancy is `5.46748e-22 s`. These tiny numerical
differences do not resolve the six missing physical bounds. Subtracting the
geocentric model difference exposes the site increment; it does not calibrate,
correct or re-center the selected candidate.

`audit_passed=true` means the stated experiment and evidence checks passed.
`site_reference_status=unqualified` means physical qualification did not pass.
Both statements are intentional. All 288 combined cases remain unexecuted and
blocked: 240 retain solar-component eligibility and 48 retain solar exclusions.
Their identities, reasons and null combined outputs remain in the checksum-pinned
[Mission 41 inventory](../../../validation/results/clock_reference_reference_run.json).
There is no physical site-clock or arrival bound, no continuous-domain accuracy
claim and no production observing eligibility.

## Offline reproduction and verification

The [reference lock](../../../validation/reference_generation/site-clock-requirements.txt)
pins Python-package versions (executed with Python 3.12.14). The
[generator](../../../validation/reference_generation/site_clock.py) checks the
kernel, original IERS source, versions and eleven historical input checksums. It
blocks socket connections, disables the approximate Skyfield clock and rejects
candidate imports. The [derived fixture](../../../validation/fixtures/site_clock_v1.json)
was regenerated byte-for-byte offline. Its [manifest](../../../validation/manifests/site_clock_v1.json)
also pins the generator, lock and frozen protocol.

```sh
# One-time environment provisioning; reuse the verified Mission 42 kernel.
python3.12 -m venv work/mission43/reference-env
work/mission43/reference-env/bin/python -m pip install \
  -r validation/reference_generation/site-clock-requirements.txt
# Supply eopc04.1962-now from the exact pinned astropy-iers-data distribution.
# The generator rejects any different hash, including a refreshed online file.
work/mission43/reference-env/bin/python -m validation.reference_generation.site_clock \
  --kernel work/mission42/de440t.bsp --eop-source /path/to/eopc04.1962-now \
  --output work/mission43/reproduced.json
cmp validation/fixtures/site_clock_v1.json work/mission43/reproduced.json

# Ordinary project environment; no kernel, Skyfield or CSPICE needed.
python -m validation.site_clock --output work/mission43/audit.json
python -m pytest -q tests/validation/test_site_clock.py
python -m pytest -q
python -m ruff check .
```

The original 152,747,008-byte DE440t SHA-256 remains
`4f003b4437a8b479aaca262716a779e3683413200adfd6353c4901aab5de800e`.
No raw binary is redistributed; see [Mission 42 acquisition and reuse notes](time_ephemeris_clock_mapping.md).
Original-source regeneration requires provisioned files; ordinary tests and CI
are self-contained and offline using the archived derived evidence.

The 79 new tests cover integrity, reference independence, finite values, context,
solver algebra/convergence, candidate regression, numerical failure retention,
Decimal isolation, conditional inequalities and false uncertainty promotion.
Omitted, reversed, doubled and kilometre-mis-scaled station vectors are each
detected in **48/48** cases. These are supplied-vector fault controls, not proof
that every coherent astronomical model error is detectable. CI retains the new
`site-clock-qualification-record` plus all eleven prior artifacts.
The full local suite passed **3,232 tests in 118.92 seconds**; Ruff, compilation,
all eleven historical input checksums and 30 relative documentation links passed.
The candidate environment used Python 3.12.14, Astropy 8.0.1, PyERFA 2.0.1.5 and
NumPy 2.5.3; the full suite used Streamlit 1.66.0. The
[canonical audit record](../../../validation/results/site_clock_reference_run.json)
was generated from clean implementation `d942a93165b702abadacb7b5244a4f3e3b4f7015`,
with `working_tree_dirty=false`, before this separate result-retention commit.
Published-head CI and all twelve artifacts must be verified before merge.

## Next gate

Proposed **Mission 44 — Relativistic Site-Frame Mapping and Error-Bound Evidence**
should resolve compatible scaled-coordinate station mapping and identify
applicable geocentric/reference uncertainty evidence before any combined-arrival
comparison is frozen. A bounded approximation requires an explicit remainder;
a source-convention change requires explicit versioning. Mission 44 is not
started and requires Mission 43 review and merge. No later phase is opened here.
