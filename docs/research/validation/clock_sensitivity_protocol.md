# Mission 48 frozen sensitivity protocol

Frozen before new numerical evaluation, following Mission 47 merge
`d1c2d0d39ea5e50da761a220004e65fc25bf5062` and successful post-merge
Quality Gate 39650383938. Primary sources inspected on 2026-10-21 UTC.
The adjacent [policy](../../../validation/manifests/clock_sensitivity_policy_v1.json)
fixes samples, constants, controls, numerical limits and archived input hashes.

## Integrated sensitivity contract

Let b denote TDB seconds, t TT seconds, D(b,p)=TT−TDB, and F=dD/db.
For a fixed coordinate anchor b*,

    D(b,p) = D*(p) + integral[b*,b] F(u,x(u,p),p) du
    D_p(b,p) = D*_p + integral[b*,b] (F_x S_xp + F_p) du
    S_xp = partial x(u,p) / partial p

These are derivatives at fixed b and b*. A moving anchor would add a boundary
term and is outside this fixed-anchor contract. A conventional fixed D* gives
D*_p=0 for those parameters by definition; this does not certify physical
accuracy. An uncertain physical anchor requires its own covariance and cross
covariances. A fitted parameter response requires the trajectory sensitivity
S_xp; instantaneous state partials alone cannot supply it.

For delta=TDB−TT, delta+D(t+delta,p)=0. Implicit differentiation gives

    partial delta / partial D_perturbation = -1/(1+D')
    partial delta / partial t = -D'/(1+D')
    partial b / partial t = 1/(1+D')
    partial delta / partial p = -D_p/(1+D')

The first expression is for a small additive change in D at fixed argument.
The second is sensitivity of the offset, not of the absolute barycentric time.
We replay final CSPICE derivatives from all 14 DE440t and 14 INPOP21a archived
solutions. A denominator above 0.5 is required at each sampled argument;
this is not a uniform bound over an interval or a physical accuracy statement.

## Declared rate term and numerical independence

INPOP08 section 2.4, equation (10), gives the clock rate in terms of alpha and
beta; section 2.1 defines alpha's kinetic and monopole contributions. We select
only the following term, retaining its prefactor A=1+LB−LG:

    F_KU = A * (LB - (v_E.v_E/2 + sum_A mu_A/r_A)/c^2) - LG
    d_A = x_A - x_E; r_A = norm(d_A)
    partial F_KU / partial v_E = -A*v_E/c^2
    partial F_KU / partial d_A = A*mu_A*d_A/(c^2*r_A^3)
    partial F_KU / partial mu_A = -A/(c^2*r_A)

Use the 12 unique geocentric controls of Mission 45, selecting the unique state
whose argument equals the last solution-trace argument. Only nominal Earth
velocity, ten body displacements and GMs are reused, never previous calculated
reference coefficients. TDB-compatible positions are metres, velocities m/s,
and supplied km^3/s^2 GMs are multiplied by 10^9 to m^3/s^2. Under the established
affine coordinate scaling the barycentric velocity is unchanged. Each case has
3 velocity, 30 displacement and 10 GM partials, 516 total. This is a declared
ten-body truncated rate, not a reconstruction of either full fitted ephemeris.
The c^-4 contribution, additional bodies and other model terms remain omitted
and unbounded. Do not label the difference from an archived full rate a pure
c^-4 remainder. No such physical-error estimate is made here.

Absolute position derivatives follow by the chain rule: the Earth position
derivative is minus the sum of body-displacement derivatives. Relative states
share the Earth state and generally correlate. Holding a GM fixed while varying
a state gives a partial derivative; changing a fitted GM also changes trajectories.

An isolated Python standard-library generator computes Decimal analytic values
at 100 digits, with no candidate, NumPy, Astropy, ERFA or astronomy-package imports.
The audit independently implements vectorized NumPy analytic derivatives and
complex-step differentiation of a scalar rate function (no conjugation or absolute
values). Steps are 0.001 m/s, 1 m and 10^-12 times GM, respectively. Exact-rational
mapping and covariance references are compared with 70-digit Decimal candidates.
Shared inputs, constants and equations mean this is numerical independence only.
Checks establish supplied-input algebra, never observational independence.

## Correlation, unknowns and nonlinear limitations

For a complete parameter covariance C and row sensitivity J, first-order output
variance is J C J^T. For an integrated rate this requires cross-time covariances:

    Var(D) = Var(D*) + 2 integral Cov(D*,F(u)) du
             + double_integral Cov(F(u),F(v)) du dv

The parameter-Jacobian form can account for these correlations through shared
fitted parameters. Sparse instantaneous derivatives cannot be integrated into
a trajectory covariance without additional evidence. Cross-model differences,
solver residuals and reader agreement are not covariances or error bounds.

Nine frozen synthetic controls exercise independent, positive, negative and
perfect correlation, cancellation, a constant uncertain rate over two time
intervals, anchor/rate correlation, zero variance and two forms of missing
covariance. Seven have known covariance; two must remain unknown. Numbers are
arbitrary synthetic values, not astronomy uncertainties. J carries output/input
units; interval weights 2 and 3 and rate weight 5 are seconds. Covariance entries
carry products of the corresponding input units. Known covariance must be square,
symmetric and positive semidefinite, allowing singular cases. Reject an indefinite
matrix even if one selected quadratic form is positive. Never replace unknown
cross entries with zero. Invalid/nonfinite inputs fail closed.

Independently supplied nonnegative deterministic input bounds b_i give
sum |J_i| b_i, a bound for the linearized model only. These synthetic box bounds
are separate assumptions, not standard deviations converted into bounds. No
physical confidence interval, distribution, coverage probability or remainder
bound is inferred. JCGM's 2026 amendment requires treatment of significant
nonlinearity in both the estimate and uncertainty; this mission does not establish
a physical linearization domain or supply higher-order corrections.

## Evidence availability and acceptance

The evidence ledger must distinguish available nominal states/GM/clock rates
from a complete fitted covariance, cross-epoch covariance, trajectory Jacobians,
model discrepancy and nonlinear remainder bounds. The latter are not established
by the reviewed sources. This is a bounded source review, not a claim that no
such data exist anywhere. Physical bounds remain null, all six existing unresolved
components remain, 48 site clocks stay unqualified and 288 arrival cases blocked.

Freeze all engineering tolerances in the policy before evaluation. Require every
partial, rate, mapping and covariance control to pass, exact inventories and
integrity checks, deterministic offline regeneration, rejection tests, the complete
existing suite, and a CI artifact. Preserve any scientific/numerical failure with
its cause and repair; do not tune thresholds after viewing results. No new kernel,
physical clock integration, target/site sample, production feature or eligibility.

## Primary sources

- [Fienga et al., INPOP08](https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop08_preprint.pdf), sections 2.1 and 2.4: family rate equation, integration and normalization.
- [Park et al. 2021, DE440/DE441](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf), sections 2.3 and 3.1: integrated time and a dynamical inventory exceeding our ten-body truncation.
- [JCGM 100:2008, chapter 5](https://www.iso.org/sites/JCGM/GUM/JCGM100/C045315e-html/C045315e_FILES/MAIN_C045315e/05_e.html), sections 5.1–5.2: local sensitivity and correlated uncertainty propagation.
- [JCGM 100:2008/Amd.1:2026](https://www.bipm.org/documents/20126/2071204/JCGM_100_Amd1_2026.pdf), page 1: significant nonlinearity can affect both the estimate and uncertainty.
- [INPOP21a release paper](https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop21a.pdf): release-specific orbital/model evidence, not an established complete clock covariance.

Source PDFs are not redistributed. Derived equations, citations and bounded
availability findings are retained. Any later change to this protocol requires
an explicit amendment; this frozen file is not a results report.
