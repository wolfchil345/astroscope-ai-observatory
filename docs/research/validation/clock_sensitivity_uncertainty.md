# Geocentric Time-Ephemeris Sensitivity and Uncertainty Propagation

Mission 48, Phase 2 scientific validation. Mission 47 was merged through
[PR #47](https://github.com/wolfchil345/astroscope-ai-observatory/pull/47) at
`d1c2d0d39ea5e50da761a220004e65fc25bf5062`; its post-merge
[Quality Gate 39650383938](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39650383938)
passed before this work began. Phases 0 and 1 remain complete.

## Result and claim boundary

The supplied-input sensitivity audit passes: 516 rate partials at 12 archived
geocentric states, 28 implicit clock mappings, and nine synthetic uncertainty
controls. Two different numerical implementations check each rate partial.
These results qualify local algebra for the declared equations and inputs.
They do not establish the uncertainty of DE440t, INPOP21a, a site clock or an
observer-arrival time. No physical covariance was propagated.

All three physical timing bounds remain **unknown** (`null`). All six unresolved
components remain, 48 site clocks are unqualified, and all 288 combined arrival
cases remain blocked (240 solar-eligible candidates, 48 solar-excluded). The
selected convention remains `astroscope-tdb-solar-au-v1`; observing eligibility
is false. Production code and historical fixtures are unchanged.

## Frozen method and independence

The [protocol](clock_sensitivity_protocol.md) and
[policy](../../../validation/manifests/clock_sensitivity_policy_v1.json) were
committed as `3fe2829` before new sensitivity or covariance evaluations.
The protocol contains the derivation, units, source applicability, sample
selection and predeclared tolerances. No tolerance was changed after evaluation.

The rate calculation covers the kinetic and ten-body monopole term, including
the declared scaling prefactor, at the final archived Mission 45 geocentric
arguments. It does not reconstruct either full integrated time ephemeris. Its
partial derivatives hold other instantaneous inputs fixed; a fitted parameter
change would also alter trajectories. The implicit mapping uses actual archived
clock derivatives from each ephemeris, rather than substituting the truncated
rate into the full clock solution.

| Reference | Audit implementation | What the agreement checks |
|---|---|---|
| 100-digit Decimal analytic partials | NumPy analytic gradient and complex-step scalar differentiation | Signs, SI scaling and local derivatives of the declared rate |
| Exact Fraction implicit gains, serialized at 100 digits | 70-digit Decimal implicit gains | Offset and absolute-time sensitivity distinguished |
| Exact Fraction expanded covariance cross terms | 70-digit Decimal quadratic form with exact rational PSD validation | Correlations, singular covariance, missing covariance and separate box assumptions |

The reference generator uses only Python's standard library and runs with
`python -S`. It does not import the audit, astronomy packages or old calculated
reference coefficients. Nominal archived states, constants and mathematical
definitions are shared. This is independent numerical implementation, not
statistically independent physical evidence. Both ephemeris derivative archives
retain their original reader provenance and limitations.

## Numerical results

| Check | Count | Largest error / limit |
|---|---:|---|
| Declared kinetic/monopole rate | 12 | 3.142 × 10^-24 s/s, limit 10^-22 s/s |
| Analytic and complex-step partials | 1,032 checks of 516 partials | 0.001187 of the per-partial tolerance |
| Implicit mappings | 28, three gains each | 4.898 × 10^-70, absolute limit 10^-60 |
| Synthetic uncertainty controls | 9 | All pass; seven known covariances and two unknown |

The partial limit is `1e-45 + 5e-13 * abs(reference)`, expressed in each
partial's SI derivative units. These are engineering comparison limits, not
timing uncertainties or physical error certificates. The mapping denominator
condition is checked only at the sampled arguments, not over an interval.

| Synthetic control | Linearized variance (s²) | Separately assumed linearized box bound (s) |
|---|---:|---:|
| Independent inputs | 13 | 5 |
| Positive correlation | 19 | 5 |
| Negative correlation | 7 | 5 |
| Perfect correlated cancellation | 0 | 4 |
| One uncertain rate over intervals of 2 s and 3 s | 100 | 10 |
| Anchor/rate correlation | 9 | 7 |
| Zero covariance | 0 | 0 |
| No covariance or box inputs | Unknown | Unknown |
| Missing cross covariance, separate complete box inputs | Unknown | 5 |

These arbitrary synthetic numbers are not estimated astronomy uncertainties.
The constant-rate example preserves correlation between time intervals; treating
those intervals as independent would incorrectly give 52 s². Perfect covariance
cancellation does not cancel independently assumed deterministic box bounds.
Unknown cross entries are never silently replaced by zero.

## Physical evidence still needed

The [evidence ledger](../evidence/clock_sensitivity_evidence_v1.json) records five
primary sources and seven input-availability categories. The review establishes
nominal archived states/GMs and clock derivatives. It does not establish a
complete source-matched fitted covariance, joint cross-epoch state covariance,
parameter-to-trajectory Jacobians, a model-discrepancy bound, or a nonlinear
remainder bound. This is a finding about the reviewed material, not proof that
such products do not exist elsewhere.

The integrated sensitivity contract requires the parameter response along the
whole trajectory and any relevant anchor cross covariance. Twelve sparse
instantaneous states do not supply that path. Mission 47 inter-model differences
remain diagnostics; reader agreement and solver residuals also cannot replace
physical uncertainty inputs. First-order covariance and a linearized box bound
do not certify physical accuracy outside a justified linearization domain.
The current JCGM nonlinearity amendment is included in the frozen source review.

## Reproducibility and retained development failure

The [independent generator](../../../validation/reference_generation/clock_sensitivity.py),
[fixture](../../../validation/fixtures/clock_sensitivity_v1.json),
[integrity manifest](../../../validation/manifests/clock_sensitivity_v1.json),
[audit](../../../validation/clock_sensitivity.py) and
[tests](../../../tests/validation/test_clock_sensitivity.py) require no external
ephemeris download or live network access for replay. The manifest pins the
protocol, policy, generator, fixture, evidence ledger and prior inputs. The audit
pins the manifest digest. Both entry points disable network connections.

```bash
python -S -m validation.reference_generation.clock_sensitivity \
  --output /tmp/clock_sensitivity_reproduced.json
cmp validation/fixtures/clock_sensitivity_v1.json /tmp/clock_sensitivity_reproduced.json
python -m validation.clock_sensitivity --output /tmp/clock_sensitivity_audit.json
python -m pytest -q tests/validation/test_clock_sensitivity.py
python -m ruff check .
python -m pytest -q
```

The [initial development failure](../../../validation/results/clock_sensitivity_development_failure.json)
is retained. A clock-only numeric parser rejected outer-planet positions above
10^12 metres before numerical comparison began. A separate SI input parser
repairs that unit-domain mismatch; frozen acceptance thresholds and reference
values did not change. The original clock parser remains unchanged.

The [canonical record](../../../validation/results/clock_sensitivity_reference_run.json)
was generated from clean implementation commit
`c28a4629633169d77f1a62005ded3122c76d3481` (`working_tree_dirty=false`).
Its SHA-256 is `f1129ef041735564da72f240d530e32d04f35d86f8829945a1a3edd9f79f54bb`.
Runtime: Python 3.12.14, NumPy 2.5.3, Astropy 8.0.1 and PyERFA 2.0.1.5;
the latter two are environment provenance, not sensitivity reference providers.
The full local suite passed all 3537 tests in 681.57 seconds. Six additional
portability regression controls bring the Mission 48 test inventory to 68;
the final CI suite therefore contains 3543 tests. Exact offline reference
regeneration is preserved.
CI adds a seventeenth retained artifact,
`clock-sensitivity-uncertainty-record`. Final-head CI and downloaded artifact
verification are recorded in [PR #48](https://github.com/wolfchil345/astroscope-ai-observatory/pull/48)
before handoff.

The [initial CI portability failure](../../../validation/results/clock_sensitivity_ci_portability_failure.json)
is also retained, including all 32 differing analytic residuals. Run 39656208517
passed 3536 tests but failed the new canonical test because it demanded identical
binary64 residual strings between environments. Both records passed every frozen
numerical comparison, and their other 23 top-level fields were identical.
The corrected [record comparator](../../../validation/clock_sensitivity_records.py)
checks independent reference values, conventions, exact-arithmetic results and
qualification gates exactly, and validates both sets of floating-point diagnostics
against the original frozen limits. It also checks their summary consistency;
regression tests reject altered references, limits, eligibility or excess errors.
The original canonical bytes and their checksum are retained. A CI artifact may
therefore have different last-bit residuals while satisfying the same scientific
contract; raw diagnostics and both runtime environments remain available.

## Next research gate

Proposed Mission 49: **Ephemeris Covariance Provenance and Applicability
Qualification**. Seek and inspect primary, source-matched covariance products
and their parameter basis, units, fit, correlations and validity interval. Only
an applicable, reproducible input contract can support subsequent integrated
propagation. If the required inputs cannot be established, preserve unknown
physical uncertainty rather than constructing a surrogate from model agreement.
Mission 49 is not started and is contingent on Mission 48 review and merge.
