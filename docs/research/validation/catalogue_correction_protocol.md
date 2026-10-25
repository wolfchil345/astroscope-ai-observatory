# Mission 61 — Catalogue correction protocol

Frozen before corrected production evaluation. Mission 60 is merged at
`e94271adfaf90c22c986fe2433f91b2a0b844489`; its original corpus, pilot, binary-input
amendment, observations and canonical run remain immutable. Four historical
modules retain its behavior; only internal import prefixes change, with reversible
byte/hash verification. Its 17 acceptance failures remain historical failures.

## Contract and independent reference

The successor fixture retains all 911 original inputs and IDs, explicitly records
each changed interpretation, and adds 640 projection boundary cases plus 21
extreme arithmetic/model cases. No tolerance is relaxed. Constants/coherence are
tightened. Density, depth and circular exterior-orbit probability use one stated
nominal convention. Current acceptance must pass every case; historical replay
success is not current scientific acceptance.

IAU 2015 B3 supplies equatorial Earth radius 6378100 m, solar radius 695700000 m
and Earth GM 3.986004e14 m3/s2. The au is 149597870700 m. The **spherical planet**
density coefficient uses mass GM/G, CODATA 2018 G=6.67430e-11, and spherical volume
at that radius. This is neither measured terrestrial density nor the IAU nominal
ellipsoidal Earth volume. G has measurement uncertainty; this arithmetic validation
does not propagate it. Archive composite rows may mix source conventions. The new
record/export marker states the assumed calculation convention, not provenance
qualification; legacy/manual records default to unknown.

The area model supports Rp <= Rstar; larger ratios return unknown. Circular
probability requires a > Rstar + Rp; embedded/contact orbits return unknown.
Unrepresentable positive results return unknown, never infinity or silent zero.
Finite positive representable extreme values must agree with independent arithmetic.
Required Gaia CSV coordinates reject outside RA [0,360), Dec [-90,90]; nonfinite
derived SNR, colour, motion and distance become unknown. Nonfinite screen radii
are insufficient data. Trapezoid depth is in (0,1000000] ppm; all positive finite
durations are supported by the direct model, with controlled rejection of an
unresolved plotting grid. No physical transit fit is introduced.

References use standard-library Decimal, exact binary64 inputs and a distinct
spherical dot-product domain check. Flux uses a 1600-digit normalized clipped
ramp reference; production may use exact rational contact intervals. Offline
regeneration blocks production, NumPy, Astropy, Plotly and network access.
Integration tests cover translated projection handling, export conventions,
unknown propagation, finite plotting grids and all historical failure IDs.

## Enforced projection domain and bound

Keep x=wrapped(alpha-alpha0) cos(delta0), y=delta-delta0, in degrees, only for
|delta0| <=60 degrees and actual great-circle separation <=0.25 degrees plus an
explicit 1e-10 degree floating boundary allowance. Validate source coordinates
first. Reject the entire unsupported chart with a translated notice; other
catalogue views remain available. This is an enforced scope correction, not a
spherical projection replacement or an astrometric uncertainty claim.

For a unit-speed great circle parameterized by arc length s (radians),
delta''=-sin(delta) cos(delta) alpha'^2 and
alpha''=2 tan(delta) alpha' delta'. Since
delta'^2+cos(delta)^2 alpha'^2=1, we have |delta''|<=tan(dmax)
and |alpha''|<=tan(dmax) sec(dmax), where dmax=60 degrees+rho and
rho=(0.25+1e-10) degrees. The planar coordinate derivative at the center equals
the geodesic east/north direction. Integrating each second-derivative bound twice,
and using cos(delta0)<=1, bounds the difference from the spherical log map by

`rho^2 / 2 * tan(dmax) * sqrt(sec(dmax)^2 + 1)` radians.

The frozen generator evaluates this conservative bound, which is below 10 arcsec.
The field cannot reach a pole and the continuous RA branch stays within the wrap
interval, so the derivative argument applies across the 0/360 seam. Samples are
additional controls, not the proof. Numeric comparison tolerances remain separate.

## Claims and retained restrictions

This mission addresses G60-01 through G60-07 and the bounded G59-01 dossier.
It does not approve Phase 2 exit, advance Phase 3, qualify composite provenance,
calibrate habitability, or change X01 physical arrival restrictions. G59-02 and
G59-03 and formal W07 review remain open. Sources and all frozen inputs are
checksum registered in `catalogue_correction_v1.json` and its source register.
