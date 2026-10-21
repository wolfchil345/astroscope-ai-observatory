# Mission 50 frozen integrated clock parameter-response protocol

Mission 49 merged as `3ba8af17232286d12f6f3d174ce6076c97da7614`.
Post-merge Quality Gate 39664651386 passed before this freeze. Source/design
inspection occurred on 2026-10-21 UTC. Commit this protocol and its policy
before new integration, reference generation or numerical comparison.

## Scope and mathematical contract

Validate the missing integrated parameter response in the geocentric clock
research pipeline using manufactured one-dimensional systems. These are not
Solar System trajectories, physical geocentric clock models, or uncertainty
estimates for either nominal ephemeris. Mission 49 established no applicable
physical covariance receipt; that outcome and all physical unknowns persist.
No new kernel, astronomical epoch, site, target or production conversion.

For fixed coordinate anchor b*, p-dependent initial conditions and
x'=f(b,x,p), forward sensitivities satisfy S'=f_x S+f_p and
S(b*)=partial x*/partial p. A clock functional D'=F(b,x,p) requires
G'=F_x S+F_p, G(b*)=partial D*/partial p. The direct term and the
trajectory term are both necessary; an instantaneous gradient does not supply
S. The anchor is fixed while differentiating: no moving-boundary term is used.

Set u=b−b*. The five ordered parameters are p=(x0,v0,a,kappa,D0), in
(m, m/s, m/s^2, dimensionless, s). Candidate state is (x,v,D) with a
3-by-5 sensitivity matrix. Initial sensitivities are x_x0=1, v_v0=1,
D_D0=1, all others zero. The manufactured equations are

    x' = v
    v' = a                         [constant acceleration]
    v' = a - omega^2*x             [forced oscillator]
    D' = kappa + lambda*x + beta*v^2
    G_i' = lambda*Sx_i + 2*beta*v*Sv_i + 1[i=kappa]

lambda=0.002 m^-1, beta=0.003 s^2/m^2, omega=0.5 s^-1 are fixed synthetic
coefficients; they are not the alpha/beta functions or constants of INPOP.
Acceleration sensitivity includes +1 for parameter a and oscillator transport
−omega²*Sx. Treating a as a direct clock-rate coefficient would be wrong.

At fixed manufactured TT coordinate t, solve b+D(b,p)−t=0. The reference
constructs t from a frozen nominal endpoint and its independently computed D;
the candidate must recover that endpoint without receiving it as a root guess.
Use b=t−D0 initially, at most 12 Newton iterations and integrate anew at every
trial b. Require 1+F>0.5 at each trial and absolute equation residual <=1e-35 s.
The output response is b_p=delta_p=−G/(1+F), at fixed t. The small discrete
solver residual is not a bound on integration error or physical time accuracy.
Check the recovered b and all five responses against the independent reference.
The sampled denominator checks do not establish a uniform physical domain.

## Independent reference and integration

Eight frozen cases: two families, each with zero, positive, negative and
shifted-anchor intervals. The policy fixes all inputs before computation.
The candidate integrates the 18 augmented variables with classical RK4 in
60-digit Decimal at 16, 32, 64 and 128 equal signed steps. No adaptive tolerance
fitting, NumPy/scipy integrator or candidate/reference sharing of analytic
trajectory functions. The existing covariance validator is reused unchanged.

The standalone standard-library reference uses closed-form trajectories and
clock antiderivatives, with Fraction arithmetic for the polynomial family and
100-digit Decimal for the oscillator. Sine/cosine use 80 Taylor terms at the
bounded frozen arguments, independently of RK4. Derivatives are of the closed
forms, not differences of candidate trajectories. Regenerate bit-for-bit with
python -S. Shared equations and synthetic inputs give numerical independence,
not independent astronomical observations or physical models.

For constant acceleration, with u=b−b*:

    x=x0+v0*u+a*u^2/2; v=v0+a*u
    D=D0+(kappa+lambda*x0+beta*v0^2)*u
      +(lambda*v0/2+beta*v0*a)*u^2
      +(lambda*a/6+beta*a^2/3)*u^3

For the oscillator let w=omega, H=a/w², A=x0−H, theta=w*u:

    x=H+A*cos(theta)+(v0/w)*sin(theta)
    v=−A*w*sin(theta)+v0*cos(theta)
    Ix=H*u+A*sin(theta)/w+v0*(1−cos(theta))/w²
    L=u/2−sin(2*theta)/(4*w); R=u/2+sin(2*theta)/(4*w)
    Iv2=A²*w²*L+v0²*R−A*v0*sin(theta)²
    D=D0+kappa*u+lambda*Ix+beta*Iv2

The reference differentiates these expressions analytically for every parameter.
At the finest grid, compare x,v,D; all 15 sensitivities; implicit b and its
five responses; and the covariance outputs. Absolute engineering limits are
in the policy and apply in each entry's stated SI-derived units. At all grids,
polynomial-family values and sensitivities must agree within 1e-45, reflecting
RK4's exactness here apart from decimal rounding. For each nonzero oscillator
case, all three adjacent refinement ratios in the absolute x error (metres)
must lie between 8 and 32. Zero intervals use exact initial-condition checks;
no undefined zero-over-zero convergence ratio is claimed. Refinement is
empirical numerical evidence on these cases, not a global error certificate.

## Joint parameter covariance and anchor treatment

Freeze one complete positive-semidefinite five-parameter synthetic covariance,
with cross correlations between D0 and x0/a. Entries carry products of parameter
units. Each of the eight cases uses three modes: correlated uncertain anchor;
fixed conventional anchor (entire D0 row/column explicitly zero by assumption);
and unknown anchor cross terms (null, not zero). Compute G C G^T for D at fixed
b and b_p C b_p^T for the implicit argument at fixed t. These are distinct
linearized variances, not standard deviations or physical confidence bounds.

All 24 mode/case pairs retain their declared covariance semantics. Unknown
cross terms make both variances unknown, even in a zero-interval case where
algebraic simplification could cancel the unknown terms: this conservative
complete-input contract deliberately declines partial inference. A future
symbolic partial-covariance contract would require separate validation.
A fixed anchor does not erase correlations between the other parameters.
No independent-epoch root-sum-square or physical covariance fabrication.
Nonlinear clock terms mean the first-order covariance calculation is not in
general an exact propagated distribution. No physical linearization domain,
distribution, model-discrepancy or higher-order bound is established.

## Acceptance and reproducibility

Freeze all limits, precision, iterations, grids, cases and covariance before
evaluation. Require exact inventories, integrity hashes, offline regeneration,
independent reference agreement, refinement, implicit solver closure, unknown
preservation, parameter/shape/domain rejection and tests that detect missing
transport/direct/anchor terms. Retain numerical failures and causes without
loosening criteria. Record clean canonical provenance, complete existing tests,
Ruff, research links, final-head CI and a nineteenth artifact.

Pin the prior result and production boundary. Preserve 18 unestablished
Mission 49 receipt requirements, all six unresolved components, 48 unqualified
site clocks, 288 candidates/blocked arrivals and zero executed arrivals (240
solar eligible, 48 solar excluded). All three physical bounds remain null,
full reference unqualified and observing eligibility false.

## Primary sources and limits of their use

- [SUNDIALS CVODES v7.1.1 mathematics](https://sundials.readthedocs.io/en/v7.1.1/cvodes/Mathematics_link.html), sections 4.2.6, 4.2.7 and 4.2.7.4: forward variational equations, initial sensitivities and sensitivity-dependent quadrature. This is a mathematical source, not an installed solver or reference output.
- [INPOP08](https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop08_preprint.pdf), section 2.4 equation (10): clock-rate integration alongside trajectories motivates the architectural requirement, not the manufactured functional or a reconstruction of INPOP.
- [JCGM 100 chapter 5](https://www.iso.org/sites/JCGM/GUM/JCGM100/C045315e-html/C045315e_FILES/MAIN_C045315e/05_e.html), sections 5.1–5.2: local sensitivity and correlated first-order variance.
- [JCGM 2026 amendment](https://www.bipm.org/documents/20126/2071204/JCGM_100_Amd1_2026.pdf), page 1: significant nonlinearity can affect both estimates and uncertainties.

Our manufactured models, antiderivatives and test design are derived here;
they are not attributed as scientific results of the cited sources. Source
PDFs are not redistributed. This frozen protocol is not a results report.
