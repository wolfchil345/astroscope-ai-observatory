# Mission 39 — Observer-Arrival Error Budget and Resolved-Event Contract

## Scope and baseline

Mission 38 merged in [PR #38](https://github.com/wolfchil345/astroscope-ai-observatory/pull/38)
on 2026-10-18 at 05:23:07 UTC as
`9012c675b509f49df61a1ec83b7a330dd5efe99d`. Its
[post-merge Quality Gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39100364031)
passed. Phases 0 and 1 remain complete and Phase 2 remains active.

This mission supplies a **conditional mathematical error-budget audit and a
prospective resolved-event contract**. It does not qualify a physical timing
model, enable production resolution or change any scientific reference value.
The [policy](../../../validation/manifests/arrival_budget_policy_v1.json) was
committed as `2952633` before computing its illustrative results or running the
new tests. Mission 38's 1 ms comparison threshold is unchanged.

**The total physical observer-arrival error remains unknown.** The
[ledger](../../../validation/manifests/observer_arrival_error_ledger_v1.json)
identifies nine required forward-model error categories without certified
absolute bounds. A passing audit means these gaps remain explicit and prevent
qualification; it does not mean that their numerical values passed an accuracy
threshold. All production strict observing/ranking/export gates remain closed.

## Evidence classes and current budget

| Evidence class | Meaning | Allowed use |
|---|---|---|
| Sampled discrepancy | Difference between implementations on specified inputs | Describe those samples; cannot become a domain-wide physical bound |
| Conditional absolute bound | A proved inequality subject to recorded hypotheses and domain | Add conservatively with other non-overlapping absolute terms |
| Standard uncertainty | Distribution/fit interpretation with covariance | Propagate by the appropriate joint model, separately from absolute bounds |
| Library inclusion audit | A term is present in a specific implementation path | Prevent omissions or double counting; no accuracy certification |
| Unknown | Missing bound, interpretation or supporting evidence | Preserve null and reasons; never substitute zero |

The existing 21.1 microsecond maximum inverse discrepancy and 47.6 ns maximum
solver residual remain sampled Mission 38 results. Neither establishes a
continuous-domain bound. Its 1 ms threshold is an acceptance decision for that
comparison, not a measured or derived physical error budget.

The ledger separates ephemeris-vector, site-vector, Earth-orientation,
target-direction/motion, finite-distance, clock-model, solar-Shapiro,
other-relativistic and numerical-evaluation errors. Each remains `unknown` for
the intended real-source use. Inclusion in a model does not establish a bound on
its remaining error. Entries must cover the same domain, be present exactly once
and carry evidence. Overlapping effects must be partitioned explicitly; a
precomputed combined term must replace its components rather than add to them.

Source ephemeris uncertainty, fit extrapolation/TTV, timestamp measurement,
exposure integration and source-convention identity are separate requirements.
They must not disappear because a conversion budget is small. Solver residual
and output representation error also have separate positions in the inverse
bound below. A deterministic geometric model can be numerically resolved while
remaining physically unqualified.

## Conditional bounds and their derivations

These are mathematical consequences of **supplied inequalities**, not measured
bounds for AstroScope's sky domain. Let `R` bound the relevant observer-vector
norm, `delta_r` bound a vector error, and `alpha` bound the unit-direction angular
separation in radians. From the triangle and Cauchy–Schwarz inequalities,

\[
 E_{\rm vector}\le\frac{\delta r}{c},\qquad
 E_{\rm direction}\le\frac{R\min(\alpha,2)}{c}.
\]

The second expression uses the unit-vector chord bound
`||n1-n2|| <= min(alpha,2)`. Use a radius bound valid for the vector in the chosen
decomposition. For example, decompose the vector/direction difference as
`(r_true-r_used).n_true + r_used.(n_true-n_used)`; no independence assumption is
needed. Direction errors from position, motion and epoch must cover the complete
query/solving interval, with the proper interpretation of RA and declination.
An angular example is not a catalogue uncertainty or a proper-motion solution.

For the spherical versus plane-wave geometric model, set `q=r.n`, `|r|<=R`, and
`d>=d_min>R`. Rationalizing the exact geometric remainder gives

\[
 0\le\frac{|d\hat n+r|-d-q}{c}
 =\frac{|r|^2-q^2}{c(|d\hat n+r|+d+q)}
 \le\frac{R^2}{2c(d_{\min}-R)}.
\]

The denominator bound follows from `|d n+r|>=d-R` and `q>=-R`.
This conservative inequality is not the truncated Taylor approximation. It
rejects `d_min<=R`. It applies to the stated geometric convention; source
distance, direction origin and their errors still need evidence.

The observer term `r_site.v_earth/c²` has conditional amplitude bound
`R_site V_earth/c²`. **Amplitude is not residual error when the term is already
included.** This example must not be added blindly to the clock-model ledger.

| Illustrative assumptions | Upward-rounded conditional value |
|---|---:|
| Vector error <= 10 m | 33.357 ns |
| R <= 1.1 au, direction error <= 0.000004848137 rad (rounded above one arcsecond) | 2.661167912 ms |
| Same R, direction change <= 0.000121203425 rad (rounded above 25 arcseconds) | 66.529197782 ms |
| Same R, distance >= 3×10^16 m | 1.505450996 ms |
| Site radius <= 6.4×10^6 m, Earth speed <= 31,000 m/s | 2.207498 microseconds (term amplitude only) |

The angular inputs can illustrate a 25-year accumulation of one arcsecond/year
only if that angular-rate bound holds throughout the interval. The radius,
distance, speed and angular assumptions above have **not been certified for a
production domain**. They explain sensitivity and qualification requirements.

### From a forward bound to an inverse bound

Define `F(t)` in source-coordinate seconds and let `t` be continuous observer
TAI seconds relative to fixed origins. Suppose a common bracket contains the
true root `t*` and approximate solution `t_hat`, a root exists, and the intended
forward map is differentiable with `F'(t)>=m>0` throughout that bracket. Suppose
`|F-F_hat|<=E_F` there and the candidate's absolute evaluated residual is at most
`rho`, with evaluation error included in `E_F`. The mean-value theorem yields

\[
 |t_{\rm hat}-t_*|\le\frac{E_F+\rho}{m},\qquad
 E_{\rm arrival}\le\frac{E_F+\rho}{m}+E_{\rm output}.
\]

The slope includes the TDB/TAI clock rate, geometric velocity and any evolving
target/correction terms; it is not implicitly one. A finite-difference sample
cannot prove the required lower bound or root existence. Unknown `E_F` or `m`
keeps the arrival bound unknown. The helper computes only this conditional
expression; it does not discover a root or verify the hypotheses.

A synthetic example `E_F=1 ms`, `rho=100 ns`, `m=0.9998`, and
`E_output=1 ns` gives an upward-rounded `1.000301061 ms`. This is an arithmetic
example, not a new acceptance tolerance. Absolute error contributions use a
linear sum, not root-sum-square. Standard uncertainties require covariance and
remain distinct from this deterministic bound.

## Clock inclusion audit and independent source basis

The [archived implementation audit](../evidence/arrival_clock_inclusion_audit_v1.json)
records Astropy 8.0.1/PyERFA 2.0.1.5, source/documentation hashes and a reproducible
offline dispatch probe. Without a site, Astropy passes zero site arguments to
`erfa.dtdb`. With the Tokyo example, it passes nonzero longitude, cylindrical
radius and height relative to the equatorial plane. The probe replaces the
numerical result with zero and measures **dispatch only**. A separate regression
test checks this inclusion behavior in the installed CI version.

[Astropy's implementation](https://docs.astropy.org/en/stable/_modules/astropy/time/core.html)
shows this location-aware call. [ERFA's documented `dtdb` model](https://github.com/liberfa/erfa/blob/master/src/dtdb.c)
includes an approximate topocentric contribution and says zero site coordinates
remove it. Therefore, before adding an explicit observer Einstein correction,
review model equivalence and overlap or replace the existing convention with a
validated alternative. Inclusion alone does not supply a remaining-error bound;
upstream model-accuracy claims are not automatically adopted as project evidence.

[Eastman, Siverd & Gaudi (2010), equations 2, 6 and 7](https://arxiv.org/html/1005.4415v3)
provide the geometric and observer-term definitions underlying the conditional
derivations above. Their decomposition also motivates explicitly accounting for
clock, Shapiro, direction, finite-distance and exposure effects. No precision
claim from the paper transfers to this project. The inequalities and acceptance
contract here are project derivations and decisions.

The constants are exact `c=299792458 m/s` from
[NIST](https://physics.nist.gov/cuu/Constants/Value/c.html) and
`au=149597870700 m` from the
[IAU definition](https://iauarchive.eso.org/public/themes/measuring/).
[NIST uncertainty propagation](https://physics.nist.gov/cuu/Uncertainty/combination.html)
supports retaining covariance in standard-uncertainty calculations. It does not
justify treating a standard deviation as a worst-case error bound. Sources were
inspected on 2026-10-18 UTC. No scientific catalogue or observational data were
added and no internet retrieval is needed to reproduce the audit.

## Prospective resolved-event contract

The [machine-readable contract](../../../validation/manifests/resolved_event_contract_v1.json)
is a design manifest, **not a runtime JSON schema, parser or resolved-event
implementation**. Its 20 scenarios are all marked `not_executed_in_production`.
It specifies twelve required sections: identity, source, observer, model, data,
instants, conversion evidence, uncertainty, query, observing margins, eligibility
and persistence. Its traceability links identify related Mission 36 requirements
without modifying that historical manifest.

| Contract area | Required behavior before production adoption |
|---|---|
| Source convention | Identify scale, reference location and correction inventory; BJD TDB alone does not authenticate which algorithm produced a source value |
| Resolved instants | Preserve TAI two-part decimal dates for midpoint and contacts; retain original source values and conversion provenance |
| Evidence binding | Bind model/data versions, bounded domains, solving bracket, derivative and error evidence to each event |
| Contact and margin semantics | Resolve each contact in its declared duration basis, then apply SI-elapsed observing margins on TAI |
| Uncertainty | Transport a complete supported joint model; retain unknown/null values and reasons; do not copy a source sigma into observer time blindly |
| Eligibility | Derive permission for each operation from validated evidence and policy; a stored true flag is not authoritative |
| Persistence | Round-trip exact values, units, source/model/data identity and unknowns; revalidate imported evidence; never promote legacy or unresolved files automatically |
| Batch reporting | Keep rejected, outside-domain and indeterminate candidates with reasons and full denominators |

For `F(t,q)=B`, the local implicit Jacobian has `dt/dB=1/F_t` and
`dt/dq=-F_q/F_t`. A future supported uncertainty calculation must use the complete
joint covariance `J Sigma J^T`, including correlations, units and validated
linearization behavior. Unknown contributing terms stay unknown. TTV,
extrapolation validity and observation clock errors need their own treatment;
they are not automatically calibrated by ephemeris covariance.

### Query enclosure and boundary decisions

For a proven monotone mapping, use outward-rounded enclosures of transformed
query endpoints, including conversion bounds, to enumerate every possibly
intersecting source cycle. Then classify the resolved nominal arrival interval.
An unproven fixed light-time padding or observed sampling rate is insufficient
to guarantee no missed cycles. No candidate enumerator is implemented here.

The exact helper probes a **closed nominal error interval `[L,U]`** against an
exact observer query. It does not attach probability or observing eligibility:

| Query | Definitely inside | Definitely outside | Otherwise |
|---|---|---|---|
| Closed `[a,b]` | L >= a and U <= b | U < a or L > b | `boundary_indeterminate` |
| Half-open `[a,b)` | L >= a and U < b | U < a or L >= b | `boundary_indeterminate` |

An empty `[a,a)` is always outside. A closed point query includes an exact
zero-width arrival interval at that point. If the arrival interval straddles a
boundary, retain the candidate with an indeterminate reason; do not shift the
boundary with a floating epsilon. If query endpoints are themselves uncertain,
propagate their enclosures or remain indeterminate; this primitive requires exact
query endpoints. Source statistical uncertainty is separate from the nominal
conversion interval and from the chosen observing-window policy.

Leap seconds stay representable internally. Unsupported datetime/calendar
representations must reject explicitly. A serialized record cannot establish
its own eligibility, nor can a valid checksum establish that scientific evidence
is sufficient: semantic review and domain binding are additional requirements.

## Executable audit and reproduction

`validation.arrival_budget` uses only standard-library Fraction arithmetic.
Inputs are finite decimal strings, with explicit size bounds. Authoritative
outputs are integer numerator/denominator pairs. Display bounds use integer
ceiling to twelve decimal places, so they cannot round inward. The checksum
manifest pins the policy, ledger, contract, clock audit and Mission 38 canonical
record; a missing or changed input rejects.

```sh
python -m validation.arrival_budget --output work/arrival_budget_run.json
python -m pytest -q tests/validation/test_arrival_budget.py
python -m pytest -q
python -m ruff check .
```

The clock-dispatch audit separately uses Mission 38's pinned candidate environment.
To reproduce its observations/hashes, execute the `reproduction_python` field
in its local JSON and compare the resulting fields, allowing explicitly reviewed
version/source changes. It contains no network retrieval or observed-accuracy
comparison.

The mission adds **69 tests**. They use exact unit conversions, a Pythagorean
geometry case, an affine inverse with a known root, outward-rounding inequalities,
unknown-vs-zero and evidence-class traps, missing/duplicate/domain-mismatched
budget terms, exact closed/half-open and sub-float boundary cases, corruption
checks, a subprocess forbidding astronomy imports/network connections, and the
site-aware clock dispatch probe. Contract syntax/traceability checks do not count
as execution of future production scenarios.

The full local suite passed **3,004 tests in 114.70 seconds**, including the 69
new tests. Ruff passed. The test environment used Python 3.12.14, Astropy 8.0.1,
PyERFA 2.0.1.5, NumPy 2.5.3 and Streamlit 1.66.0. The pure arithmetic audit
does not require these astronomy packages.

The seven existing benchmark steps remain unchanged. An eighth CI artifact
retains this conditional budget audit; it is labelled an audit, not an additional
physical accuracy benchmark. Canonical evidence and final PR checks record the
implementation/source hashes and actual test environment.

The [canonical audit record](../../../validation/results/arrival_budget_reference_run.json)
was generated from clean implementation
`5db627692860fd18cfb5ae8f733a5b182c65512f`. It retains all six exact conditional
example results, nine unknown required terms, a null physical arrival bound,
disabled observing eligibility and twenty unexecuted prospective scenarios.
Compilation, all four policy-pinned baseline file hashes and 29 relative
documentation links were also checked successfully before publication.

Delivery is tracked in [PR #39](https://github.com/wolfchil345/astroscope-ai-observatory/pull/39).
Its final published-head Quality Gate, test count and eight retained artifacts
must be verified before merge; the PR description records that run and exact
head without changing the clean canonical implementation record.

## Remaining gate

No aggregate physical timing limit, continuous-domain derivative certificate,
observational accuracy claim, production adapter, uncertainty transport,
query enumerator or resolved serializer is delivered by Mission 39.
The existing research candidate remains useful for its original bounded study.

Proposed **Mission 40 — Observer-Arrival Source Convention and Reference-Domain
Qualification** should select one explicit intended source convention and a
feasible independent reference/domain protocol. It must decide which corrections
are included, replaced or bounded and establish reference uncertainty before
physical qualification or integration. Its exact implementation depends on that
evidence; it was not started in Mission 39. Mission 39 subsequently merged in PR #39 on
2026-10-18 as `eaf3e22b8fb819ef37e0f803595de5330d21e0c7`; post-merge CI passed.
[Mission 40](source_reference_qualification.md) now develops the source convention
and bounded component reference. The historical Mission 39 audit and null
physical timing bound remain unchanged.
