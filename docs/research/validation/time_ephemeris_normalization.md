# Mission 46 — Time-Ephemeris Normalization and Physical Uncertainty Evidence

## Decision and baseline

The IAU affine normalization is independently reproducible, and the archived
DE440t epoch value is consistent with its defining offset at the frozen numerical
tolerance. This establishes a convention check, **not physical clock accuracy**.
The eight reviewed evidence claims supply no applicable complete physical bound.
All six unresolved components and all 288 blocked arrival cases remain visible.

Mission 45 merged in [PR #45](https://github.com/wolfchil345/astroscope-ai-observatory/pull/45)
as `ee10e9e04f5422bb0416b87662de571e9d76d135`. Its
[post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39231240199)
passed before this mission began. The
[protocol](../../../validation/manifests/time_normalization_policy_v1.json) was
committed as `435f351` before new reference generation or numerical evaluation.
Previously published residuals and primary sources were inspected before that
freeze. Phases 0 and 1 remain complete; Phase 2 remains active.

## Definitions and independent arithmetic

Use seconds from J2000, with `a=TT`, `b=TDB`, `c=TCB`, `g=TCG`, and
`t0=(2443144.5003725−2451545)×86400` seconds. The defining constants are
`LB=1.550519768e−8`, `LG=6.969290134e−10`, and `d0=TDB0=−0.0000655 s`.
The adopted affine relations [1, 2] are

$$b=(1-L_B)c+L_Bt_0+d_0,\qquad a=(1-L_G)g+L_Gt_0.$$

At the geocentric origin, `a=g=c=t0`, but `b=t0+d0`. TDB is therefore
not synchronized with TT at that event. The inverse evaluated at numerical
`b=t0` describes a different event. The delivered DE440t correction already
contains its normalization [3]; adding `TDB0` again would double count it.

For each archived small offset `delta=b−a`, the
[reference generator](../../../validation/reference_generation/time_normalization.py)
uses exact rational arithmetic to recover

$$c=\frac{a+\delta-L_Bt_0-d_0}{1-L_B},\qquad
g=\frac{a-L_Gt_0}{1-L_G}.$$

It verifies `(b−c)+(c−g)+(g−a)=delta` exactly, then serializes at 90 decimal
digits. The live [audit](../../../validation/time_normalization.py) implements
these relations independently with 70-digit Decimal arithmetic and a shifted
origin. Its replay limit is `1e−50 s`, an algebra/serialization check only.
Recovering `c−g` from a supplied `delta` does **not** independently integrate the
physical TCB–TCG relation. The fixture explicitly records that distinction.

Nine controls span offsets from −100 to +1000 Julian years relative to the
origin, including zero, ±1 second, ±1 day and +1 year. Each independently tests
TCB→TDB, TDB→TCB, TCG→TT and TT→TCG. Live ERFA executes all 36 mappings
with split Julian dates. Output-minus-input offsets are compared at the actual
serialized input; input quantization is retained separately. The largest
library-versus-exact offset discrepancy is **8.171 ps**, below the frozen
40 ps engineering limit. The control span is an arithmetic domain, not an
ephemeris-accuracy claim.

The reference needs only Python 3.12's standard library and runs with `-S` to
exclude site packages. It imports no Astropy, ERFA, audit or production code.
The ERFA check is a candidate implementation comparison, not a second physical
reference. No raw kernel, external download or new ephemeris integration is
needed: all 14 historical inputs are reused, checksum-pinned Mission 42 results.

## Normalization findings without a fitted correction

All 9 controls and 14 archived cases pass. The 12 historical values are the
four frozen 2024 dates at 10, 12 and 14 UTC. The remaining two are the J2000
and IAU-origin TT probes. They are not 48 independent sites or 288 independent
arrival measurements. Live Astropy reproduces the archived candidate values.

| Diagnostic | Result | Interpretation |
|---|---:|---|
| DE440t epoch correction minus `TDB0` | −1.7747e−17 s | Passes the 1 ps normalization check |
| Candidate epoch correction minus `TDB0` | −3.416552107 ns | Model realization diagnostic |
| Candidate minus DE440t, 12 historical samples | −26.651136766 to −23.350272340 ns | Unchanged model differences |
| Range of those 12 differences | 3.300864426 ns | Sample variation, not uncertainty |
| Range over all 14 samples | 23.234584677 ns | Includes the two earlier epoch probes |

For any constant shift `k` and sample residuals `r_i`, the triangle inequality
on the largest and smallest residual gives

$$\max_i |r_i+k|\ \geq\ \frac{\max_i r_i-\min_i r_i}{2}.$$

This lower bound is **1.650432213 ns** for the 12 historical samples and
**11.617292338 ns** for all 14. No value of `k` is estimated, selected or
applied. The sample differences cannot all be eliminated by a constant shift;
this result does not identify their cause, measure secular drift, or supply a
continuous-domain error envelope. In particular, the DE405-relative 3 ns claim
below is not an acceptance criterion for these DE440t comparisons.

Fault checks reject omitted `TDB0` in all 9 controls. Reversing the `LB` sign
or using days as seconds is rejected in 8 of 9; both faults vanish at the
zero-offset control, and that denominator is retained explicitly.

## Physical-uncertainty evidence and source disagreement

The machine-readable [evidence ledger](../evidence/time_normalization_evidence_v1.json)
records source URLs, precise locations, categories, applicability and rejection
reasons. It preserves eight claims; every applicable physical bound is null.

| Evidence | What it supports | Why it does not close this budget |
|---|---|---|
| IAU defining constants [1, 2] | Exact normalization conventions | Definition is not physical realization accuracy |
| IAU 2006 note 2 [1] | Possible ephemeris-dependent drift, expected within 1 ns/year | Not a measured DE440t rate or hard absolute bound |
| ERFA `dtdb` note 5 [4] | A stated expectation of 1 ns/century | Differs from the IAU statement; neither is adopted as a bound |
| ERFA `dtdb` note 7 [4] | 3 ns relative to DE405-based time integration, 1950–2050 | Different comparator; no complete DE440t physical bound |
| IAU B1.5 note 1 [2] | Conditional 0.2 ps quasi-periodic formulation accuracy | Complete formulation and input-error conditions not demonstrated |
| Park §2.3 [3] | Integrated equations and normalization | No complete uncertainty for these archived values established |
| Mission 42 readers [5] | Agreement on common coefficients | Shared physical errors remain invisible |

The year-versus-century discrepancy is recorded as unresolved. This audit does
not correct upstream documentation or invent an explanation for the mismatch.
The IAU numerical constants remain authoritative definitions; their exactness
does not authorize treating an expected model drift as bounded uncertainty.
Likewise, the 0.2 ps statement is conditional and allows larger astronomical
input errors. It cannot be transferred to Mission 45's truncated ten-body model.

The remaining components are geocentric time ephemeris, Earth state, station
coordinates, Earth orientation, omitted physics/coefficient consistency, and
higher-order remainder. No root-sum-square, sum or fitted discrepancy is used
to replace these unknowns. Geocentric, site-clock and arrival physical bounds
remain null; observing eligibility is false. Combined inventory remains
**288 candidates, 0 executed, 288 blocked**, comprising 240 solar-eligible and
48 solar-excluded cases. Production timing and the selected
`astroscope-tdb-solar-au-v1` convention remain unchanged.

Primary sources were inspected on 2026-10-19 UTC. ERFA v2.0.1 was resolved to
commit `9915ba38c9365f8b0738269b8c2ac1fdd5f8dee3`. Source text and the IAU/Park
equations were inspected; the IERS Chapter 10 endpoint was inaccessible again,
so no fresh finding from that endpoint is claimed. The ledger contains our
paraphrases and links, not redistributed source PDFs or ephemeris coefficients.

## Reproduction, failures and quality evidence

```sh
python -S -m validation.reference_generation.time_normalization \
  --output /tmp/time_normalization_v1.json
cmp validation/fixtures/time_normalization_v1.json /tmp/time_normalization_v1.json
python -m validation.time_normalization \
  --output /tmp/time_normalization_reference_run.json
python -m pytest -q tests/validation/test_time_normalization.py
```

The [manifest](../../../validation/manifests/time_normalization_v1.json) pins the
reference generator, fixture, ledger, frozen protocol and historical inputs.
Reference regeneration is byte-identical. Both executables block network
connections. Normal CI needs only the project's existing validation dependencies.
The fifteenth artifact is `time-normalization-evidence-record`; earlier artifacts
are retained.

The [retained development exception](../../../validation/results/time_normalization_development_failure.json)
records an expected-ID transcription error: June 20 was written where the frozen
inputs specify June 21. The audit stopped before historical comparisons and
result serialization. Only the audit literal was corrected; inputs, selections,
thresholds and protocol remained frozen. A test-decorator syntax error was also
corrected before test execution; it produced no scientific result.

All **60 new tests pass**, including inverse identities, epoch distinction,
independent exact rational checks, constant-shift inequality, wrong-unit/sign
sensitivity, nonfinite/corrupted input rejection, reference isolation, byte-exact
regeneration, provenance, and false qualification even with zero discrepancies.
The full local suite passed **3425 tests in 131.38 seconds**. Ruff lint,
new-file formatting, compilation, 33 relative documentation links and all frozen
input hashes passed. The live library reports ERFA 2.0.1, matching the reviewed
source version. The [canonical record](../../../validation/results/time_normalization_reference_run.json)
was generated from clean implementation commit
`f6cc15bb7206e19d3f97fa16c35faa74ffc1c861` using Python 3.12.14,
Astropy 8.0.1, PyERFA 2.0.1.5 and NumPy 2.5.3. Final-head GitHub CI and
artifact verification will be recorded in the review PR.

## Next research boundary

Proposed **Mission 47 — Independent Time-Ephemeris Cross-Model Qualification**
should identify and acquire a second integrated time ephemeris, reconcile its
time/epoch conventions, and determine what uncertainty evidence is actually
available for the existing domain. Cross-model agreement must remain distinct
from a physical error bound. If evidence is unavailable, retain that limitation
explicitly. Mission 47 is not started and requires Mission 46 review and merge.

## Primary references

1. [IAU 2006 Resolution 3, p. 2](https://www.iers.org/fileadmin/SharedDocs/Publikationen/EN/IERS/resolutions/IAU/IAU2006_Resolution_B3.pdf), defining equation and notes 1, 2, 5.
2. [IAU 2000 resolutions](https://syrte.obspm.fr/IAU_resolutions/Resol-UAI.htm), B1.9 and B1.5 note 1.
3. [Park et al. (2021), DE440/DE441](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf), §2.3, equations 3–7.
4. [ERFA v2.0.1 `eraDtdb`](https://github.com/liberfa/erfa/blob/9915ba38c9365f8b0738269b8c2ac1fdd5f8dee3/src/dtdb.c), notes 5–8; source derived from SOFA.
5. [Mission 42 time-ephemeris mapping](time_ephemeris_clock_mapping.md), retained project evidence, not an independent external physical reference.
