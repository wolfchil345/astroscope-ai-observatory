# Visibility and Transit-Window Sampling Validation — Mission 54

Mission 54 implements the bounded W03 package from the
[Phase 2 audit](../phase_2_coverage_audit.md). It validates the existing
`analyze_transit_visibility` API with explicitly supplied UTC observing instants.
It does not convert catalogue epochs, enable strict predictions, or establish
continuous observing coverage. No production source is changed.

## Protocol and independence

The reference corpus and acceptance policy were committed at `8869df6` before
production residual evaluation. All 48 window/grid comparisons passed on the
first scientific run. The generator imports Skyfield, NumPy and skyfield-data;
it does not import AstroScope, Astropy or ERFA. Reference regeneration was tested
with those modules disabled and socket connections prohibited, yielding the
same fixture SHA-256 `3b63651777f2e66de59fafc63144363c884a5c38f0a1e39520d8a805422a0e5a`.

Skyfield 1.55 and skyfield-data 7.0.0 supply the DE421 reference. The generator
records the kernel hash. It reuses the unchanged Mission 34 daily IERS table;
DUT1 and polar motion are linearly interpolated. Shared Earth-orientation inputs,
WGS84 geometry and underlying astronomical conventions limit independence.
The bundled skyfield-data `finals2000A.all` expiry warning is irrelevant here:
that file is not used; the committed historical IERS rows are installed explicitly.
The runtime needs neither Skyfield nor a kernel nor network access.

The coordinates are fixed ICRS directions with no proper motion, parallax or
radial velocity. The synthetic northern target is not a qualified Polaris
catalogue record. Skyfield apparent topocentric directions are compared with the
existing Astropy builtin transformations. Pressure is zero: no refraction,
atmospheric extinction, terrain, horizon dip or instrumental obstruction is modelled.
Time is UTC in 2024, TAI−UTC is 37 s and TT−TAI is 32.184 s. No leap-second
boundary is present. Existing civil-time and timing missions retain those scopes.

## Corpus and acceptance

There are 16 independent scenarios: equator, Greenwich, Arctic and Paranal;
March equinox and June solstice; equatorial and northern target directions.
Each window starts at 16:00 UTC, lasts 12 hours and has a synthetic four-hour
transit from window hour 2 to hour 6. Its midpoint at hour 4 deliberately does
not coincide with the window centre. A supplied zero uncertainty is an input
placeholder, not a measured or certified physical bound.

For each scenario the production API is evaluated at 3, 9 and 25 inclusive
uniform samples: 48 comparisons, 592 returned samples and 1,776 angular
residuals. The reference also supplies 241 nodes per scenario (three-minute
spacing), used only for sensitivity diagnostics. Repeated grid nodes are not
independent observations and no statistical confidence is inferred.

Frozen goals are 5 arcsec for target altitude and Sun altitude, and 60 arcsec
for target–Moon separation, following the planner-scale budgets of Missions
33–34. These are acceptance goals, not global error or covariance bounds.
Every finite residual must meet its goal. Independent classification uses
lower/upper count bounds: nodes within the angular goal of a threshold are
indeterminate; outside that guard they must agree. No ambiguous node is silently
removed from the denominator. Default thresholds are target altitude >= 20°
and Sun altitude <= −18°. Equality and adjacent floating-point values are
separately tested as API contracts, not independent accuracy evidence.

The runner also checks exact grid membership, nearest sampled midpoint,
returned-angle flags, extrema, finite-airmass maximum, Moon separation minimum
and the all-samples visibility flag. Tests preserve the existing first-on-tie
midpoint rule and zero-duration duplicate-node behaviour. Inputs that cut off
ingress or egress are rejected by the chronological event contract. The existing
strict timing tests verify unresolved predictions are rejected before observing
or export access.

## Results and sampling limitations

All 48 comparisons pass; maximum target-altitude residual is
0.0000001081°, Sun-altitude residual 0.000004033°, and Moon-separation residual
0.0004818°, within the frozen goals.

| Samples | Largest absolute difference from 241-node observable fraction |
|---|---:|
| 3 | 0.438451 |
| 9 | 0.066851 |
| 25 | 0.022407 |

These are fractions of sampled nodes, **not duration integrals**. The dense
reference is itself finite and does not prove convergence or capture every
crossing. Three of the sixteen scenarios have partial transit visibility in the
dense diagnostic; the runner retains event-only and full-window fractions
separately. Full-window baseline visibility and transit visibility are different
questions. The public API's `full_observation_window_visible` means every sampled
node passed; it cannot certify the continuous interval.

An analytic injected-gap control makes this limitation explicit: a gap between
20% and 30% of a window is missed by all three coarse nodes, while the nine-node
grid detects it and returns 8/9. This is a synthetic aggregation counterexample,
not a claim that terrain gaps are part of the astronomical model. Nearest-node
midpoint offsets are recorded; the API does not independently sample the exact
mid-transit instant. No automatic sampling-density recommendation follows from
this small corpus, and no continuous-coverage guarantee is introduced.

Two initial test-harness controls supplied null site/target objects even though
the summary needs their names; the controls were corrected to valid named inputs.
A direct `pytest` launcher also lacked the repository root on its import path;
the documented `python -m pytest` invocation resolves it. Neither issue involved
a scientific residual failure or a production-code change.

## Reproduction and evidence

From the repository root after installing `.[dev,validation]`:

```bash
python -m pytest -q tests/validation/test_visibility_sampling.py tests/test_transit_visibility.py tests/test_transit_timing.py
python -m validation.visibility_sampling --output /tmp/visibility_sampling_reference_run.json
```

Reference regeneration additionally needs the pinned reference requirements
from Missions 33–53 (`skyfield==1.55`, `skyfield-data==7.0.0`, `jplephem==2.24`,
`sgp4==2.27`; this run uses NumPy 2.5.4):

```bash
python -m validation.reference_generation.visibility_sampling
```

The [manifest](../../../validation/manifests/visibility_sampling_v1.json) hashes
the corpus, policy, generator and shared IERS input. The
[canonical result](../../../validation/results/visibility_sampling_reference_run.json)
records clean implementation identity, environment, source/input hashes, every
residual, denominator, contract and sampling diagnostic. CI runs the complete
suite and publishes `visibility-sampling-validation-record` as artifact 22,
preserving the previous 21. Final-head CI evidence is recorded in the PR before
handoff.

## Qualification limits and remaining work

This completes a bounded W03 sampling dossier, not Phase 2 or X01. Existing
physical site/clock/arrival bounds remain unknown; all 288 combined arrival
candidates remain blocked, including 240 solar-eligible and 48 excluded cases.
The six unknown budget components, 48 unqualified site clocks and 18 unestablished
covariance requirements are unchanged. No applicable physical covariance was
acquired or propagated and no observing eligibility was promoted.

W04 heuristic characterisation, W05 light-curve campaigns, W06 reconciliation
and W07 reviewed exit remain separate work. Phases 3–8 remain planned.

## Independent method references

- [Skyfield apparent positions](https://rhodesmill.org/skyfield/positions.html):
  astrometric light-time followed by apparent aberration/deflection and topocentric geometry.
- [Astropy AltAz](https://docs.astropy.org/en/stable/api/astropy.coordinates.AltAz.html):
  WGS84 horizontal frame, pressure-zero unrefracted geometry.
- [Mission 33 coordinate dossier](celestial_coordinate_validation.md) and
  [Mission 34 solar/lunar dossier](solar_lunar_twilight_validation.md): inherited
  EOP provenance, independent model limitations and component budgets.
