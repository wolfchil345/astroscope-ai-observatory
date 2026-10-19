# Mission 47 — Independent Time-Ephemeris Cross-Model Qualification

## Baseline and scope

Mission 46 was merged in [PR #46](https://github.com/wolfchil345/astroscope-ai-observatory/pull/46)
at `72534fbdfe15d18d789c883d7356df5ac17cb05b`; its post-merge
[Quality Gate 39253030570](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39253030570)
passed. Phases 0 and 1 remain complete; Phase 2 scientific validation continues.
This mission follows the [Mission 46 next boundary](time_ephemeris_normalization.md).

The [protocol](../../../validation/manifests/cross_model_time_policy_v1.json) is
committed before the first INPOP time-polynomial evaluation or new clock comparison.
Source inspection, archive acquisition and segment metadata inspection precede
that freeze, committed as `118baf1eba0e69b2ce480fec4db3ece219c7fb15`.
Failed checks must be retained, with no fitted bias, recentering,
threshold adjustment or silent replacement of the selected reference.

The sample set remains the 12 unique historical geocentric instants, J2000 TT,
and the 1977 IAU origin: **14 instants**, not 48 sites or 288 target/site events.
No production converter, site model or unrelated roadmap feature is introduced.

## Reference acquisition and conventions

INPOP21a supplies the second integrated ephemeris family. The provider's
[release page][1] identifies a TDB SPICE distribution containing the time
transformation. The ordinary JPL-compatible planetary binary omits it. We select
the 100-year-before/after-J2000 SPICE archive; the release is chosen for this
bounded comparison and is not asserted to be the latest INPOP release.

The protocol pins the archive and extracted kernel bytes, SHA-256 hashes, URL,
segment descriptor and coverage. Only the explicitly named BSP member is
extracted. The original archive, kernel and publication PDFs remain local inputs;
this repository retains attributed, limited derived research values and
acquisition instructions. The provider's [usage conditions][7] are linked;
no blanket raw-data redistribution permission is inferred.

The completed archive is 24,194,181 bytes; the selected member is
`inpop21a_TDB_m100_p100_spice_time.bsp`, 5,694,464 bytes. Its unique Type 2
segment has identifier `TT-TDB`, frame 1 and coverage JD(TDB) 2414105–2488985.
Hashes are locally computed acquisition pins, not provider-published checksums.
The initial download timed out and was resumed; only the completed archive was
hashed for the protocol and extracted. No partial-download hash was accepted.

| Property | Contract |
|---|---|
| Quantity | First component, TT−TDB in seconds |
| Argument | TDB coordinate; geocentre |
| SPK identifiers | Target 1000000001, center 1000000000 |
| Input epochs | TT seconds from J2000 noon; calendar construction independent of Astropy |
| Primary evaluation | CSPICE raw `spksfs` / `spkpvn`, fixed-point iteration |
| Reader crosscheck | jplephem two-part JD, Newton iteration; derivative divided by 86400 |
| Excluded operations | Approximate `unitim`/LSK conversion, aberration, distance scaling, fitted offset |

The [INPOP family paper][2], §2.4, describes joint time/dynamics integration
through c⁻⁴ and normalization before Chebyshev construction. Its J2000 internal
zero is not a zero in the delivered transformation. The IAU origin requires
TDB−TT = −65.5 µs; this mission adds no second normalization correction.
The older paper's body inventory is not silently assigned to INPOP21a.
The [2021 release note][3] supplies release-specific dynamical and observation
context. CALCEPH's [identifiers][4] and [usage documentation][5] establish the
special time-segment interpretation; CALCEPH itself is not run.

Let D(b) denote delivered TT−TDB. For a specified TT epoch t, solve

\[
\delta + D(t+\delta)=0,\qquad \delta=\mathrm{TDB}-\mathrm{TT}.
\]

The generator retains every iteration, derivative, actual input representation
and argument quantization. Both readers use the same INPOP coefficients.
The numerical reader/solver design is adapted from Mission 42; this shared
infrastructure is explicitly recorded. Independent integrated models do not
mean independent software paths for every operation.

## Frozen checks and interpretation

| Check | Limit | Meaning |
|---|---:|---|
| Solver iterations | 8 maximum | Deterministic termination |
| Final equation residual | 10⁻¹⁵ s | Implicit mapping arithmetic |
| Reader offset agreement | 10⁻¹² s | Common-kernel interpolation |
| Reader derivative agreement | 10⁻¹⁵ s/s | Unit/derivative consistency |
| Trace algebra replay | 10⁻¹⁸ s | Independent Decimal audit |
| Historical candidate replay | 10⁻¹² s | Continuity with Mission 42 |
| IAU-origin closure | 10⁻¹² s | Delivered normalization check |
| Comparison triangle closure | 10⁻¹² s | Signs and historical-edge consistency |
| Cross-model or candidate difference | No accuracy threshold | Diagnostic only |

These are engineering checks, not physical uncertainty bounds. Binary64 absolute
TDB arguments can have much larger quantization than the correction checks;
the record exposes that quantization rather than claiming picosecond timestamps.

For each epoch the audit retains INPOP21a−DE440t, live Astropy−INPOP21a,
and the archived Astropy−DE440t edge, all using TDB−TT offsets. Their signed
triangle closes within the frozen replay limit. Historical and epoch-probe
summaries stay separate. No offset fit, drift fit or uncertainty estimate is
computed from these 14 samples. Coverage of a kernel does not validate every
time in that coverage.

## Physical uncertainty and independence

The [evidence ledger](../evidence/cross_model_time_evidence_v1.json) separates
distribution contracts, family methods, older model comparisons, release-specific
orbit evidence, implementation conventions and project inference. The old
INPOP08/TE405 comparison is not promoted into an INPOP21a/DE440t bound.
The 2021 release's orbit comparisons and parameter uncertainties do not provide
a complete clock certificate for these epochs.

INPOP and DE440t are distinct integrated families, independent of the candidate's
FB90 series. Their errors are not established to be statistically independent.
As a project inference, common definitions, theory, observations and reader
software can leave common errors invisible. If two models equal truth plus the
same unknown error, their difference vanishes while that error remains unknown.
Thus even zero discrepancy cannot establish physical accuracy.

All six uncertainty components remain open: geocentric time ephemeris, Earth
state, station coordinates, Earth orientation, omitted physics/coefficient
model and higher-order remainder. Geocentric, site-clock and arrival physical
bounds remain null. All 48 site clocks remain unqualified; combined inventory
remains **288 candidates, 0 executed, 288 blocked** (240 solar-eligible,
48 solar-excluded). Observing eligibility remains false and the selected
`astroscope-tdb-solar-au-v1` convention is preserved.

## Reproduction and quality evidence

Acquire the exact archive URL in the protocol and verify its checksum before
extracting only the named BSP. Verify the extracted checksum and size too.
Use Python 3.12.14 for byte-identical reference provenance and an isolated environment from the pinned
[reference requirements](../../../validation/reference_generation/time-ephemeris-requirements.txt),
then run:

```sh
python -m validation.reference_generation.cross_model_time \
  --kernel inpop21a_TDB_m100_p100_spice_time.bsp \
  --output /tmp/cross_model_time_v1.json
cmp validation/fixtures/cross_model_time_v1.json /tmp/cross_model_time_v1.json
python -m validation.cross_model_time --output /tmp/cross_model_time_reference_run.json
python -m pytest -q tests/validation/test_cross_model_time.py
```

Reference generation imports neither Astropy/ERFA nor production timing code.
The normal audit needs no raw kernel, jplephem, SpiceyPy or network. It reuses
the checksum-pinned Mission 42 Decimal trace auditor and live candidate adapter.
Both executables block network connections. The manifest pins the new fixture,
generator, ledger, protocol, requirements and historical inputs.
CI retains all prior artifacts and adds `cross-model-time-ephemeris-record`.

## Results

All 28 reader/solver runs converged and all 14 numerical cases passed on the
first evaluation under the frozen protocol. Regeneration in the pinned reference
environment is byte-identical. Maximum reader offset difference is
1.6426×10⁻¹⁷ s; maximum derivative difference is 3.697×10⁻²⁴ s/s.
The INPOP IAU-origin closure residual is −1.6446×10⁻¹⁷ s. These small residuals
describe arithmetic on delivered polynomials, not physical clock accuracy.

Maximum actual-argument quantization is 5.22243984×10⁻⁸ s for CSPICE ET and
4.41970330×10⁻¹² s for jplephem's two-part JD. All live-candidate replay and
comparison-triangle residuals are zero at retained serialization precision.

| Samples | INPOP21a−DE440t, ns | Astropy−INPOP21a, ns |
|---|---:|---:|
| 12 historical epochs | +2.45044157464 to +2.52478422885 | −29.17592099459 to −25.80073596735 |
| J2000 TT | +1.185011512176 | −18.268211563946 |
| IAU-origin TT | +0.000000001301 | −3.416552090299 |

The [fixture](../../../validation/fixtures/cross_model_time_v1.json) retains the
full traces. The [manifest](../../../validation/manifests/cross_model_time_v1.json)
pins all inputs. Source review establishes no applicable complete physical
uncertainty bound; the numerical qualification is explicitly limited to sampled
geocentric cross-model diagnostics. It does not rank either model by truth.

All **50 new regression tests pass**: convention and trace corruption, checksum
and provenance rejection, triangle signs, delivered normalization, historical
continuity, independence claims, missing evidence, and closed eligibility with
both zero and large cross-model differences. The full local suite passed
**3475 tests in 144.76 seconds**. Ruff lint, new-file formatting, compilation,
all 17 manifest input hashes and the report's relative links passed. No
scientific evaluation failed; no protocol threshold or input selection changed.
The [canonical record](../../../validation/results/cross_model_time_reference_run.json)
was generated from clean implementation commit
`9d8f18aa34a35870374a481db612adaf04007ae8`, using Python 3.12.14,
Astropy 8.0.1, PyERFA 2.0.1.5 and NumPy 2.5.3. Final-head GitHub CI and
artifact verification will be tracked in the Mission 47 pull request.

## Next research boundary

Proposed **Mission 48 — Geocentric Time-Ephemeris Sensitivity and Uncertainty
Propagation** should derive a source-matched sensitivity contract for integrated
clock dependence on ephemeris inputs, distinguish correlated input errors from
numerical checks, and identify which required uncertainty inputs are available.
Missing input bounds must stay unknown. These cross-model differences remain
diagnostics and cannot enable combined arrival execution. Mission 48 is not
started and requires Mission 47 review and merge.

## Primary references

[1]: https://www.imcce.fr/recherche/equipes/asd/inpop/download21a
[2]: https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop08_preprint.pdf
[3]: https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop21a.pdf
[4]: https://calceph.imcce.fr/docs/latest/html/python/calceph.naifid.html
[5]: https://calceph.imcce.fr/docs/latest/html/python/calceph.multiple.pythonusage.html
[6]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpvn_c.html
[7]: https://www.imcce.fr/mentions-legales

Primary sources inspected on 2026-10-19 UTC. The family paper is the author's
2009-06-10 preprint, not a claim to have inspected an inaccessible publisher PDF.
The [raw CSPICE segment API][6] defines TDB seconds from J2000.
