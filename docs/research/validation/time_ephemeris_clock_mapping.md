# Mission 42 — Independent Time-Ephemeris Reference Acquisition and Clock Mapping

## Decision and baseline

An independently integrated **geocentric** clock model is now executable offline.
JPL DE440t was acquired, identified and evaluated without Astropy, ERFA, PINT or
Skyfield in the reference process. CSPICE and jplephem reproduce its interpolation
and TT-to-TDB mapping at all 14 predeclared epochs. This is new reference evidence,
**not a qualified site-clock or complete arrival-time reference**. Physical timing
bounds remain unknown and production observing eligibility remains false.

Mission 41 merged in [PR #41](https://github.com/wolfchil345/astroscope-ai-observatory/pull/41)
as `fc959a380a920c7798185f3991bc5ca5404382ad` on 2026-10-18 at 07:48:24 UTC.
Its [post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39109050918)
passed. The [Mission 42 protocol](../../../validation/manifests/time_ephemeris_policy_v1.json)
was committed as `2a5aaff` before the first time-segment polynomial evaluation or
numerical comparison. Only acquisition, metadata and primary-source inspection
preceded that freeze. No frozen thresholds, epochs or conventions were changed
after measurement. Phases 0 and 1 remain complete; Phase 2 remains active.

## Acquired reference and independence

The original [JPL SSD DE440t binary](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440t.bsp)
was acquired on 2026-10-18. It contains 152,747,008 bytes, with SHA-256
`4f003b4437a8b479aaca262716a779e3683413200adfd6353c4901aab5de800e`.
The provider's Last-Modified header was 2020-12-22 00:56:32 GMT. The kernel's
comment area is empty; explanatory comments have not been invented.

| Property | Interpretation enforced by the generator |
|---|---|
| Dedicated time segment | Center `1000000000`, target `1000000001`, Type 2, frame 1, source `DE-0440LE-0440` |
| Quantity | First component is **TT minus TDB**, in **seconds**, not a position in kilometres |
| Independent variable | TDB, not TT or UTC; CSPICE receives TDB seconds from J2000 |
| Spatial scope | Geocentre; no observing-site arguments or site transformation in this segment |
| File coverage | JD TDB 2287184.5–2688976.5; coverage is not an accuracy claim |
| Primary reader | SpiceyPy 8.3.0 / CSPICE N0067, raw `spksfs` and `spkpvn` |
| Cross-check reader | jplephem 2.24, two-part JD Type 2 evaluation; derivative converted from per-day to per-second |

The time identifiers and seconds convention are supported by the official
[CALCEPH identifier documentation](https://calceph.imcce.fr/docs/latest/html/python/calceph.naifid.html)
and [evaluation documentation](https://calceph.imcce.fr/docs/latest/html/python/calceph.multiple.pythonusage.html).
CALCEPH itself was not executed. [CSPICE's segment evaluator](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpvn_c.html)
documents the TDB epoch argument. Generic SPK position units must not be applied
to this special coordinate-time segment.

Both readers share the **same kernel coefficients**, numerical integration,
constants and astronomical theory. Their agreement checks reader/solver
implementations, not two independent physical realizations. DE440t is independent
of the candidate's ERFA/FB90 clock backend, but backend independence alone does
not establish its uncertainty or site compatibility.

The raw kernel is retained in the local untracked project reference cache, not in Git.
Neither it nor raw coefficient excerpts are republished. The
[SSD FAQ](https://ssd.jpl.nasa.gov/faq.html) favors direct links and directs
publication-permission questions to JPL; NAIF's redistribution rules for its own
distribution are not assumed to cover this SSD download. This project publishes
its derived numerical research results, acquisition identity and code, without
claiming a blanket redistribution license for the source binary.

## Clock mapping, rate and normalization

Let `D(b)` denote the kernel's geocentric `TT−TDB` at TDB coordinate `b`, in
seconds from J2000. For a supplied TT coordinate `a`, solve for a small offset:

$$\delta + D(a+\delta)=0,\qquad \delta=\mathrm{TDB}-\mathrm{TT}.$$

CSPICE uses fixed-point iteration; jplephem uses Newton iteration with its
analytic polynomial derivative. Both start at zero and allow at most eight
evaluations, stopping at an equation residual of 1 femtosecond. The frozen
reader-offset agreement threshold is 1 picosecond, and derivative agreement is
`1e-15` seconds/second. These are numerical engineering criteria only. The audit
also checks every archived update, sign, TDB argument and stopping decision;
17-digit binary64 display roundoff is allowed at `1e-18` seconds in trace algebra.

Historical input TT is constructed independently using integer Gregorian calendar
arithmetic and the frozen 2024 `TAI−UTC=37 s`, then `TT−TAI=32.184 s`. It is not
copied from candidate output. All 12 Mission 38 dates × hours are used, followed
by explicit TT probes at JD 2451545.0 and 2443144.5003725. Four sites and six
targets do not multiply the number of independent geocentric samples. Archived
Mission 41 TT parts agree within the frozen 1 ns serialization check.

[Park et al. (2021), section 2.3](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf)
gives the integrated transformation and its normalization: `LB=1.550519768e-8`,
`LG=6.969290134e-10`, `T0=2443144.5003725` JD, and `TDB0=−65.5 µs`.
These are descriptive constants, **not additional corrections** to the delivered
kernel. Neither a fitted bias nor a forced zero is applied. The TT epoch probes
are retained as diagnostics, not used to calibrate or center the reference.

The small offset is kept separate from the large epoch coordinate throughout.
Maximum recorded argument quantization is **49.8505 ns for CSPICE double ET**
and **4.3542 ps for jplephem's split JD** across all solver evaluations. Those
argument errors are not hidden by the much smaller difference in clock
corrections: the time correction varies slowly. This experiment does not claim
picosecond absolute timestamp precision.

## Results and claim limits

All 28 solves converge: three evaluations for each CSPICE solve and two for each
jplephem solve. The signed comparisons are retained without exclusions or tuning.

| Diagnostic | Samples | Minimum | Maximum | Meaning |
|---|---:|---:|---:|---|
| Astropy minus DE440t, historical geocentre | 12 | −26.6511 ns | −23.3503 ns | Model difference; no physical accuracy threshold |
| Astropy minus DE440t, TT epoch probes | 2 | −17.0832 ns | −3.4166 ns | Normalization diagnostics, no fitted offset |
| jplephem minus CSPICE mapped offset | 14 | −1.3120e-17 s | +1.6426e-17 s | Same-kernel numerical agreement only |

The IAU TT epoch probe gives DE440t `TDB−TT=−0.000065500000000017747 s`;
J2000 TT gives `−0.000099290115743742695 s`. These are recorded model evaluations,
not new normalization definitions. The live local Astropy 8.0.1 candidate agrees
with all 12 archived Mission 41 geocentric values at their 17-digit precision.

No continuous-domain error envelope, physical reference bound or empirical
uncertainty follows from 14 samples or reader agreement. The audit can pass even
if a different candidate gives a large model discrepancy: it verifies the stated
experiment, not an unestablished physical accuracy requirement. All residuals
remain visible and no observing gate can be opened by passing this audit.

## Geocentre-to-site mapping: explicit remaining boundary

The selected arrival convention remains `astroscope-tdb-solar-au-v1` from
Missions 40–41, including Astropy's existing approximate site contribution and
its UTC-fraction approximation to UT1. It has not been replaced by DE440t.

Park et al.'s equation (3) contains a leading station term
`v_E · (r_S−r_E) / c²`, and a higher-order station term at `c^-4`. A future
site mapping must specify compatible coordinate scaling, frames, velocity units,
station position, Earth orientation, and the TDB argument at which they are
evaluated. A rotated WGS84/GCRS site vector is not automatically the complete
barycentric station difference required by that expression. An approximation
needs its own justified remainder and input-uncertainty bounds.

Conceptually, a site reference would solve
`delta_site + D(TT + delta_site) − site_term(TT + delta_site, site) = 0`.
That is a dependency statement, **not an implemented or qualified formula** here.
The geocentric offset cannot simply be relabeled a site offset; nor can a new
Einstein term be added on top of Astropy's already site-inclusive clock.

The audit retains mappings for all **48 site instants**, each blocked pending
site mapping and uncertainty. All **288 combined arrival cases remain blocked**:
240 are solar-component eligible and 48 retain their solar-domain exclusions.
Their full identities, reasons and null outputs remain in the checksum-pinned
[Mission 41 inventory](../../../validation/results/clock_reference_reference_run.json),
referenced instead of copied into a new apparently independent experiment.
Physical geocentric, site-clock and arrival bounds remain null. Production
conversion, observation scheduling, eligibility and scientific source code are
unchanged.

## Offline reproduction and quality evidence

The isolated [reference lock](../../../validation/reference_generation/time-ephemeris-requirements.txt)
contains only jplephem 2.24, NumPy 2.5.4 and SpiceyPy 8.3.0 (Python 3.12.14).
The [generator](../../../validation/reference_generation/time_ephemeris.py)
verifies the original kernel checksum, descriptor, package versions and frozen
inputs before evaluation. It blocks socket connections and rejects candidate
library imports. No LSK, `unitim`, `str2et`, online tables or approximate fallback
is used. The first implementation attempt mis-unpacked `spkuds` metadata and
stopped before polynomial evaluation; its tuple order was corrected. No data,
tolerance or sample selection was changed in response.

The [derived fixture](../../../validation/fixtures/time_ephemeris_v1.json)
regenerated **byte-for-byte identically offline**. The
[manifest](../../../validation/manifests/time_ephemeris_v1.json) pins it, its
generator, environment lock, protocol and all ten frozen historical inputs.
Normal tests and CI require neither the original binary nor the reference-reader
packages; the [audit](../../../validation/time_ephemeris.py) uses the archived
fixture and the live Astropy candidate, with network connections blocked.
Kernel regeneration requires one-time provisioning; offline reproducibility
does not mean a missing 153 MB binary can be recreated from these 14 samples.

```sh
# Explicit one-time setup (network allowed here only).
python3.12 -m venv work/mission42/reference-env
work/mission42/reference-env/bin/python -m pip install \
  -r validation/reference_generation/time-ephemeris-requirements.txt
curl -fL https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440t.bsp \
  -o work/mission42/de440t.bsp

# Offline regeneration; wrong or missing original binary is fatal.
work/mission42/reference-env/bin/python -m validation.reference_generation.time_ephemeris \
  --kernel work/mission42/de440t.bsp --output work/mission42/reproduced.json
cmp validation/fixtures/time_ephemeris_v1.json work/mission42/reproduced.json

# Ordinary project environment, no kernel/SpiceyPy/jplephem dependency.
python -m validation.time_ephemeris --output work/mission42/audit.json
python -m pytest -q tests/validation/test_time_ephemeris.py
python -m pytest -q
python -m ruff check .
```

The 46 new tests cover units, sign, time argument, solver trace, quantization,
finite numbers, inventory/context tampering, checksums, candidate/reference
isolation, Decimal precision isolation, live candidate evaluation, and false
qualification from both zero and large candidate differences. The new eleventh
CI artifact is `time-ephemeris-clock-mapping-record`; all ten prior records remain.
The full local suite passed **3,153 tests in 123.05 seconds**; Ruff, compilation,
all ten frozen historical-input checksums and 29 relative documentation links
also passed before the evidence commit. Local candidate packages were Python
3.12.14, Astropy 8.0.1, PyERFA 2.0.1.5 and NumPy 2.5.3; the full-suite environment
used Streamlit 1.66.0. The [canonical audit record](../../../validation/results/time_ephemeris_reference_run.json)
was generated from clean implementation
`99145db6da914e849e8cce7842b42036c9837882`, separately from the later documentation
and result-retention commit. Its `working_tree_dirty` field is false.
Delivery is tracked in [PR #42](https://github.com/wolfchil345/astroscope-ai-observatory/pull/42).
Published-head CI and artifact evidence must be verified and recorded in that PR
before merge. The original kernel must be reacquired and checksum-verified if
the local cache is lost; normal CI remains self-contained without that binary.

## Next gate

Proposed **Mission 43 — Independent Site-Clock Mapping and Uncertainty
Qualification** should establish the site mapping and a defensible uncertainty
budget, including geocentric reference uncertainty, before freezing any combined
arrival comparison. Any change from the selected clock convention must be
explicit and versioned. Mission 43 has not started; it requires Mission 42 review
and merge. No later roadmap phase is opened by this result.
