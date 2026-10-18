# Mission 44 — Relativistic Site-Frame Mapping and Error-Bound Evidence

## Outcome and claim boundary

All 48 frozen Mission 43 site inputs pass the declared scaled, first
post-Newtonian spatial-component comparison. Twelve algebraic zero-position
controls also pass. An exact rational residual certificate bounds numerical
inversion error relative to the unique root of the specified polynomial.
It does not bound physical station-coordinate, clock, or observer-arrival error.
Physical qualification remains incomplete; all 288 combined arrival cases
remain blocked and observing eligibility remains false.

This experiment supplies an explicit frame mapping where Mission 43 used a
leading-order site-vector surrogate. It holds the earlier event arguments fixed;
it does not solve a new coupled space/time transformation or recompute the clock.
The selected arrival convention remains `astroscope-tdb-solar-au-v1`.
Production timing code is unchanged.

## Baseline and frozen design

Mission 43 merged in [PR #43](https://github.com/wolfchil345/astroscope-ai-observatory/pull/43)
at `6982a2419bdc7c3ced22bd5abe5d6d79d7c05c17`, on
2026-10-18 at 13:59:09 UTC. Its post-merge
[Quality Gate run 39133947130](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39133947130)
passed before Mission 44 changes began.

The [policy](../../../validation/manifests/site_frame_policy_v1.json) and
[generator requirements](../../../validation/reference_generation/site-frame-requirements.txt)
were committed at `d777e2c` before new external-state evaluations, spatial
transformations, inversion certificates, or residuals. Every historical case is
retained. No tolerance or case selection was adjusted after viewing residuals.

| Predeclared check | Limit |
|---|---:|
| Candidate/reference L1 displacement | 2e-8 m |
| Potential replay discrepancy | 1e-6 m²/s² |
| Acceleration replay L1 discrepancy | 1e-16 m/s² |
| Archived/fresh Earth velocity L1 discrepancy | 1e-6 m/s |
| Reference update replay L1 discrepancy | 1e-29 m |
| Reference equation residual L1 | 1e-20 m |

These are numerical engineering checks for supplied inputs. No physical accuracy
acceptance threshold is inferred from them. The manifest pins the policy,
generator, dependency lock, fixture, nine historical files, and production timing
source. Earlier experiments remain intact.

## Coordinates, scaling, and event assignment

The IAU 2000 B1.3 spatial transformation, reproduced in Soffel et al. [1], gives
the following polynomial through order c^-2 in aligned BCRS/GCRS axes:

```text
H(r) = r + P(r)/c²
P(r) = v(v·r)/2 + W r + r(a·r) − a(r·r)/2
r = x_station(t) − x_E(t)
```

Here `v` and `a` are Earth's barycentric velocity and acceleration, and `W` is
the external potential at Earth. Both barycentric positions use the same TCB
coordinate argument `t`. Replacing `x_E(t)` with Earth at a different coordinate
time would change this relation. The omitted spatial terms are O(c^-4); this
order notation alone supplies no numerical physical error bound.

For this experiment, the Mission 43 nominal WGS84 rotated vector is explicitly
interpreted as TT-compatible, `X_TT`. This is a declared scale assumption, not
evidence of a surveyed ITRF station realization. IERS Chapter 11 [3] explains the
TT-compatible convention for terrestrial coordinates; it does not certify these
nominal inputs. The transformations using the exact defining constants [2, 5]
are:

```text
F_B = 1 − 1.550519768e-8
F_G = 1 − 6.969290134e-10
X = X_TT/F_G
v_TCB = v_TDB
W_TCB = W_TDB
a_TCB = F_B a_TDB
H(r) = X
r_TDB = F_B r
```

Velocity and GM/r are invariant under simultaneous time, coordinate and mass
scaling. The acceleration relation follows by differentiating the scaled
coordinates twice with respect to scaled time. Mixing TT-compatible vectors
with TDB-compatible ephemerides without these factors is not this model.

Every row retains the earlier site, rotated vector, Earth velocity, geocentric
identifier, and final actual binary64 ET argument. The TT/TDB pair was assigned
by the Mission 43 surrogate. Holding that assignment fixed isolates a spatial
component; a consistent full spacetime solution remains future work.

## External coefficients and independent computation

The fixture uses ten Newtonian point masses: Sun; Mercury, Venus, Mars, Jupiter,
Saturn, Uranus and Neptune system barycentres; Pluto-system barycentre; Moon.
Their NAIF IDs are `10, 1, 2, 4, 5, 6, 7, 8, 9, 301`. Earth and the Earth-Moon
barycentre are excluded, preventing Earth self-potential and double counting.
For each frozen ET, CSPICE geometric `J2000`, `NONE` displacements relative to
Earth (399) and the DE440 GMs give:

```text
W = Σ μ_i / |d_i|
a_TDB = Σ μ_i d_i / |d_i|³
```

The archived source vectors are TDB-compatible metres. GMs from the NAIF text
kernel [7] are converted from km³/s² to m³/s². Planet-system barycentre lumping,
omitted asteroids/KBOs, multipoles and relativistic force corrections are explicit
approximations without a claimed physical error envelope.

| Source | Bytes | SHA-256 |
|---|---:|---|
| `de440t.bsp` | 152747008 | `4f003b4437a8b479aaca262716a779e3683413200adfd6353c4901aab5de800e` |
| `gm_de440.tpc` | 12406 | `924ddf4fb9ead9fe8a1aa55780bcabde40b09d00065d58226e24b68d8092f140` |

The [reference generator](../../../validation/reference_generation/site_frame.py)
uses NumPy 2.5.4, SpiceyPy 8.3.0 and CSPICE N0067. Its spatial inverse is an
independent componentwise matrix/quadratic expansion using exact `Fraction`
arithmetic on supplied decimal coefficients. It starts at `X` and takes four
fixed-point updates, rounding each component to a 1e-30 m grid. Its first update
is the first-order inverse `X − P(X)/c²`.

The live [audit candidate](../../../validation/site_frame.py) uses a NumPy
rank-one matrix expression and binary64 arithmetic. A separate compact rational
implementation replays reference updates and certifies residuals. A 90-digit
Decimal calculation replays potential and acceleration from the archived source
vectors and GMs. Generator imports exclude AstroScope, Astropy, ERFA, PINT,
Skyfield and the candidate module. The two inverses share the declared equation
and supplied inputs, not a common implementation; this establishes numerical
model agreement, not independence of the physical assumptions.

## Numerical inverse certificate

Use the L1 norm, radius `R = 13000000 m`, `V1 = ||v||1`, and `A1 = ||a||1`.
Coefficient guards are `V1 ≤ 70000 m/s`, `A1 ≤ 0.03 m/s²`, and
`0 ≤ W ≤ 2e9 m²/s²`. On the closed radius-R ball, the derivative of `P/c²`
has induced L1 norm bounded by

```text
q = (V1²/2 + |W| + 3 A1 R)/c².
```

The velocity outer product contributes at most `V1²/2`; the two derivatives of
`r(a·r)` contribute at most `2 A1 R`, and the derivative of `−a(r·r)/2`
contributes at most `A1 R`. The fixed-point map `G(r)=X−P(r)/c²` maps the ball
into itself when

```text
||X||1 + ((V1²/2 + |W|)R + 1.5 A1 R²)/c² ≤ R.
```

The audit verifies this inequality and `q < 1` with exact rational arithmetic.
Banach's contraction theorem then gives a unique root `r*` in the ball, and
for each tested point `z` inside it:

```text
||z − r*||1 ≤ ||H(z) − X||1 / (1 − q).
```

Certificates cover the first-order point, four-update reference, and actual
binary64 candidate point, the latter converted with `Fraction.from_float` and
divided by exact `F_B`. All certificates are in **unscaled TCB-compatible L1
metres**, rounded upward to a 1e-36 m reporting grid. Exact iteration of a
truncated polynomial does not recover missing physical O(c^-4) terms.

## Measured results

All displacement magnitudes below are **L1 norms**, not Euclidean distances.
The 48 rows are historical site/event samples; the 12 zero controls are algebraic
checks using retained coefficients, not additional physical epoch samples.

| Diagnostic across 48 rows | Minimum | Maximum |
|---|---:|---:|
| Scale-only displacement, m | 0.0946961 | 0.1632754 |
| 1PN-only displacement, m | 0.0622985 | 0.1399161 |
| Total mapped displacement, m | 0.1571119 | 0.3024025 |
| Fixed-argument leading clock-term change, ps | −0.0619903 | +0.0590831 |
| First-order/four-update inverse difference, m | 6.06625e-10 | 1.96946e-9 |

The clock diagnostic is `v·(r_TDB−X_TT)/c²` at the frozen arguments. It is a
frame-only change to the leading term, not a full clock residual or a physical
uncertainty estimate. No c^-4 clock term or new normalization is added.

| Numerical check or certificate | Maximum |
|---|---:|
| Candidate/reference L1 discrepancy | 1.53337e-9 m |
| Potential replay absolute discrepancy | 2.31934e-7 m²/s² |
| Acceleration replay L1 discrepancy | 3.72487e-18 m/s² |
| Contraction factor q | 1.87377e-8 |
| Reference inverse error certificate | 1.270303e-30 m |
| First-order inverse error certificate | 1.96946e-9 m |
| Binary64 candidate inverse error certificate | 1.53337e-9 m |

Displayed certificate maxima above are rounded upward. The very small reference
certificate describes arithmetic proximity to a polynomial root only.

## Applicability of published accuracy statements

Primary sources were inspected on 2026-10-18. The machine-readable evidence
register preserves every source's physical bound as `null`.

| Source and locator | Evidence | Application to this experiment |
|---|---|---|
| Soffel et al. [1], Appendix A, printed p. 35 | Complete c^-2 spatial expression with O(c^-4) remainder | Defines the polynomial; supplies no numerical remainder bound |
| Klioner [2], Eqs. 7–9, 23–25, §6 | TDB/TT-compatible scaling and mixed-model requirements | Establishes scale relations; no station uncertainty estimate |
| IERS [3], §11.1.3 | TT-compatible terrestrial-coordinate convention | Motivates the declared input scale; no survey certification |
| IAU 2000 B1.5 [4], note 1 | Stated 5e-18 rate accuracy and 0.2 ps quasi-periodic phase amplitude | Conditional on the specified full formulation and domain; not transferable as a total bound here |
| IAU 2006 B3 [5], notes 2, 5 | Expected drift with other ephemerides of at most 1 ns/year; conventional normalization | An expectation, not a measured DE440t physical error envelope |
| Park et al. [6], §2.3, Eqs. 3–6 | Integrated clock formulation and site terms | No applicable complete site-clock hard bound supplied in the inspected section |

The B1.5 statement concerns its specified formulation, farther than a few solar
radii, with the TCB/TCG transformation within 50000 km of Earth. It explicitly
allows astronomical-input errors to be larger. It cannot establish a physical
bound for the truncated spatial model or the current DE440t-based site surrogate.

Geocentric time-ephemeris error, Earth velocity, station coordinates, Earth
orientation, higher-order spatial terms, omitted gravity/force terms, and full
spacetime coupling remain unresolved components. Physical spatial, site-clock
and arrival bounds remain `null`. Combined counts remain 288 candidates,
0 executed, 288 blocked, 240 solar-domain eligible and 48 solar-domain excluded.

## Offline reproduction and verification

Normal audit and CI execution require only the checked-in inputs and ordinary
project NumPy dependency. They require neither the raw kernel nor SpiceyPy.
The audit blocks socket connections and fails on checksum or claim-boundary
violations. Numerical comparison failures remain visible in the result rows.

```bash
python -m validation.site_frame --output /tmp/site_frame_reference_run.json
python -m pytest -q tests/validation/test_site_frame.py
```

To regenerate the independent reference, first provision the two source files
from [7, 8] and a Python 3.12 environment with the pinned generator requirements.
Acquisition and dependency installation are preparatory network operations;
generation itself is offline and checks source sizes and hashes.

```bash
python -m venv /tmp/site-frame-reference
/tmp/site-frame-reference/bin/pip install -r validation/reference_generation/site-frame-requirements.txt
/tmp/site-frame-reference/bin/python -m validation.reference_generation.site_frame \
  --kernel /path/to/de440t.bsp --gm-source /path/to/gm_de440.tpc \
  --output /tmp/site_frame_v1.json
cmp validation/fixtures/site_frame_v1.json /tmp/site_frame_v1.json
```

An independent regeneration was byte-identical. All **3306 tests** passed,
including **74 Mission 44 cases**. Coverage includes closed-form linear roots,
an exact nonlinear known-root construction, certificate inequalities and upward
rounding, rotation covariance, zero/orthogonal limits, corrupted claims and
provenance, input-domain rejection, and offline execution. Five faulty candidates
(omitted PN mapping, omitted TDB scaling, omitted TT unscaling, reversed PN sign,
and omitted acceleration) are rejected across all 48 rows each.

The Quality Gate preserves the twelve earlier artifacts and adds
`site-frame-mapping-record`. The retained canonical result and its clean
implementation provenance are recorded after the implementation commit.

## Next research boundary

Proposed Mission 45: **Coupled Relativistic Site-Clock Model and Reference
Qualification**, pending Mission 44 review and merge. It should address consistent
space/time event assignment and applicable physical reference uncertainty before
any full arrival comparison can be considered qualified. It is not started here.

## Primary references

1. [Soffel et al. (2003), IAU 2000 reference systems](https://arxiv.org/pdf/astro-ph/0303376), Appendix A B1.3 and §3.4.
2. [Klioner (2008), relativistic scaling of astronomical quantities](https://arxiv.org/abs/astro-ph/0508292), Eqs. 7–9, 23–25 and §6.
3. [IERS Conventions (2010), Chapter 11](https://iers-conventions.obspm.fr/content/chapter11/tn36_c11.pdf), §11.1.3.
4. [IAU 2000 resolutions](https://syrte.obspm.fr/IAU_resolutions/Resol-UAI.htm), B1.5 note 1.
5. [IAU Division A Commission A3 resolutions archive](https://iau-a3.gitlab.io/res.html), IAU 2006 B3 and defining constants.
6. [Park et al. (2021), DE440 and DE441](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf), §2.3.
7. [NAIF DE440 gravitational parameters](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc).
8. [JPL DE440t SPK](https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440t.bsp).
