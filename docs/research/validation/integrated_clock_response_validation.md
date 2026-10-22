# Mission 50 — Integrated Geocentric Clock Parameter-Response Validation

## Outcome and scope

The integrated parameter-response machinery passes its manufactured-solution
validation: eight synthetic cases, 120 endpoint parameter partials, 40 implicit
parameter responses and 24 covariance scenarios. The oscillator cases show
fourth-order refinement on all three grid doublings. This qualifies numerical
machinery for the geocentric clock research pipeline; it does not qualify a
physical clock, real ephemeris covariance or observer-arrival conversion.

Mission 49 merged as `3ba8af17232286d12f6f3d174ce6076c97da7614`. Its
post-merge [Quality Gate 39664651386](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39664651386)
passed before the [protocol](integrated_clock_response_protocol.md) and
[policy](../../../validation/manifests/integrated_clock_response_policy_v1.json)
were frozen in commit `17bd0e8`. No completed mission was restarted.

## What was missing

Mission 48 validated instantaneous rate derivatives. Mission 49 established
that neither archived nominal ephemeris had a complete applicable physical
covariance receipt. An integrated clock needs the parameter response of the
whole trajectory, including its initial conditions and clock anchor:

\[
S'=f_xS+f_p,\qquad G'=F_xS+F_p,\qquad
G(b_*)=\frac{\partial D_*}{\partial p}.
\]

The reference anchor is held fixed while differentiating. The numerical tests
exercise both transport through the trajectory and explicit parameter terms.
At fixed TT-like input \(t\), the implicit equation and parameter response are

\[
b+D(b,p)-t=0,\qquad \frac{\partial b}{\partial p}
=-\frac{G}{1+F}.
\]

The final expression is also the offset response at fixed t. Solver closure
and integration accuracy are checked separately. Neither is a physical bound.

## Manufactured models and independent reference

Both one-dimensional models use \(x'=v\) and the artificial clock functional
\(D'=\kappa+\lambda x+\beta v^2\). Constant acceleration uses \(v'=a\);
the forced oscillator uses \(v'=a-\omega^2x\). The five parameters are
\((x_0,v_0,a,\kappa,D_0)\). Coefficients and parameter covariances are invented
controls with declared units, not fitted astronomical quantities. The symbols
lambda/beta do not represent the physical INPOP rate functions.

| Implementation | Method | Independence boundary |
|---|---|---|
| Reference | Closed-form trajectories and clock antiderivatives; exact Fraction polynomial arithmetic, 100-digit Decimal oscillator with 80-term sine/cosine series | No candidate, numerical integrator or astronomy-package imports |
| Candidate | 60-digit Decimal classical RK4 of 3 state values and a 3×5 sensitivity matrix | Derivatives integrated from variational ODEs, not copied endpoint formulas |
| Implicit mapping | Newton iteration, reintegrating at every trial endpoint | Recovers a fixed nominal endpoint from an independently constructed TT-like coordinate |
| Covariance | Full joint parameter covariance with reused validated PSD checks | First-order synthetic variances only; no distribution or physical coverage claim |

Each family includes zero duration, forward integration, backward integration
and a shifted fixed anchor. Parameter perturbation tests hold t fixed; segment
composition tests carry sensitivities between segments. Resetting sensitivity
initial conditions at a segment boundary loses part of the response and is
explicitly detected. Tests also detect omitted acceleration, clock transport,
direct clock-rate and anchor terms.

## Numerical results

All 32 integrations use frozen grids of 16, 32, 64 and 128 steps. Polynomial
cases meet the 1e-45 rounding criterion at every grid. Zero-duration cases
retain their initial derivatives; no convergence ratio is assigned to zero
errors. The finest oscillator position errors and adjacent refinement ratios
are shown below. Values are numerical discrepancies for synthetic inputs.

| Oscillator case | Position error at 128 steps (m) | 16→32 error ratio | 32→64 | 64→128 |
|---|---:|---:|---:|---:|
| Forward | 6.196e-12 | 15.951 | 15.977 | 15.989 |
| Backward | 2.418e-12 | 17.007 | 16.522 | 16.266 |
| Shifted anchor | 1.754e-11 | 15.250 | 15.637 | 15.822 |

All ratios satisfy the predeclared interval 8–32. This is empirical convergence
on the frozen cases, not a universal integration error certificate.

| Finest-grid diagnostic | Maximum absolute discrepancy | Frozen limit |
|---|---:|---:|
| Position | 1.754e-11 m | 1e-7 m |
| Velocity | 1.497e-11 m/s | 1e-7 m/s |
| Accumulated clock | 2.398e-13 s | 1e-9 s |
| Recovered implicit argument | 2.378e-13 s | 1e-8 s |

Every derivative is checked in its corresponding state/parameter units. The
largest clock-partial error occupies approximately 0.000111 of its allowed
limit. All Newton solves satisfy the separate 1e-35 s residual criterion and
sampled denominator guard. That tiny residual does not erase the integration
discrepancy in the table. These synthetic magnitudes are not an accuracy claim
about actual astronomical time transformations.

## Correlations and unknowns

Each case evaluates three anchor modes: full correlated anchor covariance,
fixed conventional anchor with an explicitly zero D0 row/column, and unknown
anchor cross terms. There are 32 known linearized variance values and 16 null
values across the two output quantities. A complete parameter covariance keeps
correlations across the entire time path through shared parameters; independent
epoch errors are never assumed.

At zero duration, the correlated D variance is the supplied synthetic anchor
variance 0.000026 s²; the fixed-anchor D variance is zero. Unknown-cross mode
remains null under the frozen complete-input contract, including when a
particular zero-duration expression could be simplified. No partial-covariance
inference was introduced. Fixed anchor treatment changes an assumption; it
does not mean that real physical anchor uncertainty has been measured as zero.

The nonlinear clock term means first-order covariance is generally not an
exact propagated distribution. Model discrepancy, nonlinear remainder,
physical covariance and coverage remain unestablished.

## Retained failures and verification

The [development failure record](../../../validation/results/integrated_clock_response_development_failure.json)
retains three aborted audit attempts from the same exact-zero representation
issue: high-precision reference zeros, an internal zero integration span, and
zero sensitivities crossing the reused covariance parser. The parser accepts
only short exponent fields; values such as `0E-322` are exact zeros but failed
that syntax contract. Exact-zero normalization at serialization boundaries
repairs interoperability. The inherited parser, equations, nonzero values,
precision, inputs and acceptance limits were not changed. Regression tests
cover both model families and the covariance boundary. No numerical tolerance
was relaxed.

The initial targeted suite passed 70 cases, with the canonical-record comparison
deferred until its clean implementation commit. Two endpoint-coordinate guards
were then added. Final validation comprises 73 Mission 50 tests and 3690
repository tests, including the canonical comparison with no skip.
The [canonical record](../../../validation/results/integrated_clock_response_reference_run.json)
was generated from clean implementation commit
`209da4bcc9c406dc25bf9f555bd4ba10a5ae5530`. Its SHA-256 is
`930dccd98ac0f743f0606e8478aa77039376fae42004c661f69473aaa97770fe`.
Full-suite, final-head CI and downloaded artifact evidence are recorded in
[PR #50](https://github.com/wolfchil345/astroscope-ai-observatory/pull/50)
before handoff.

## Offline reproduction

```sh
python -S -m validation.reference_generation.integrated_clock_response --output /tmp/integrated_clock_response_fixture.json
cmp /tmp/integrated_clock_response_fixture.json validation/fixtures/integrated_clock_response_v1.json
python -m validation.integrated_clock_response --output /tmp/integrated_clock_response_run.json
python -m pytest -q tests/validation/test_integrated_clock_response.py
python -m ruff check .
python -m pytest -q
```

The [manifest](../../../validation/manifests/integrated_clock_response_v1.json)
pins the frozen policy, protocol, independent generator, fixture, evidence,
failure history and inherited scientific/production inputs. Reference and audit
paths deny network connections. The nineteenth CI artifact is
`integrated-clock-parameter-response-record`. Canonical generation requires a
clean implementation commit. All scientific record fields compare exactly
across environments; Python/Git runtime metadata are checked separately.

## Sources and remaining gate

The [source ledger](../evidence/integrated_clock_response_evidence_v1.json)
records the primary mathematical references and their limitations. CVODES
v7.1.1 documents forward sensitivity and quadrature equations; it is not used
as a solver here. INPOP08 motivates integrated clock/trajectory treatment, not
our manufactured equations. JCGM's correlated propagation guidance and 2026
nonlinearity amendment delimit the interpretation of the synthetic covariance.
The protocol provides direct links and detailed derivations.

All 18 unestablished Mission 49 receipt requirements and six unresolved physical
components remain. There are 48 unqualified site clocks, 288 blocked arrival
cases and zero executed cases; solar eligibility counts remain 240/48. Physical
clock/site/arrival bounds are null and `observing_eligible=false`.

Physical propagation still requires provider-supported, source-matched inputs
and applicable trajectory responses. This mission establishes a numerical test
harness for that future work, without claiming those missing inputs were acquired.
Phase 2 remains active. Mission 50 merged through PR #50 at
`4aae68b9035c6cbf7d4ad36d9c1f88ad358d33ed`; post-merge
[Quality Gate 39669626225](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39669626225)
passed. This status update preserves the original canonical evidence and limits.
