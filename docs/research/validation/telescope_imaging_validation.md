# Mission 52 — Telescope and Imaging Scientific Validation

## Scope and decision

This implements W01 / P2-05 of the [Mission 51 audit](../phase_2_coverage_audit.md).
Mission 51 merged at `b3a4345786565bd112e1d4cd6be90762c3a5725d`;
[post-merge Quality Gate 39714054048](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39714054048)
passed before this work began. Phases 0 and 1 remain complete, Phase 2 active,
and Phases 3–8 planned. No phase-exit approval is made.

The independent ideal-geometry corpus exposes a diagonal field-of-view defect.
The baseline passes 272/307 cases and fails 35/307, all on diagonal angular
field. The corrected implementation passes 307/307 with unchanged acceptance
thresholds. These results qualify the stated numerical model over the corpus,
not measured telescope performance or arbitrary finite floating-point inputs.

## Sources, independence and model

The [frozen manifest](../../../validation/manifests/telescope_imaging_v1.json)
records sources, retrieval date, file hashes, policy and counts. References are:

1. Gregory Hollows and Nicholas James, Edmund Optics,
   [Understanding Focal Length and Field of View](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/understanding-focal-length-and-field-of-view),
   Equation 1, accessed 2026-10-22. The full field is
   `2 atan(sensor_dimension / (2 effective_focal_length))` in the ideal
   rectilinear infinity-focus model. Real distortion and illumination are outside it.
2. Celestron,
   [How to Determine Which Eyepieces to Use with Your Telescope](https://www.celestron.com/blogs/knowledgebase/how-to-determine-which-eyepieces-to-use-with-your-telescope),
   2020-07-30, accessed 2026-10-22. Focal length divided by eyepiece focal length
   determines magnification; useful limits depend on conditions. Its 60x/inch
   advice differs from this application's 2x/mm heuristic. Neither is used as
   measured optical calibration here.

The original MIT-licensed synthetic fixture contains no copied reference tables.
The [reference generator](../../../validation/reference_generation/telescope_imaging.py)
uses only Python's standard library: 90-digit Decimal arithmetic, half-angle
reduction and an alternating arctangent series, Machin's formula for pi, and
exact Fraction coverage enumeration for mosaics. It never imports production
code, binary `math` trigonometry, NumPy or Astropy. The alternating series stops
below 1e-85 after reduction to |x| <= 0.1; arithmetic has 90-digit precision.
This is far below the comparison allowances, but is not a formal interval proof.
Known pi digits and exact fixture regeneration are tested.

Independence means a separately implemented analytic numerical oracle, not an
independent optical experiment. Multiplication by Barlow/reducer factors assumes
ideal focal-length scaling at unchanged aperture. Scalar exit pupil follows
aperture divided by magnification. The approximate eyepiece true field remains
apparent field divided by magnification; field stops and distortion are not modelled.

The 206.265 plate-scale coefficient is retained as an explicitly rounded
small-angle convention. Its relative difference from `648/pi` is below 1e-6;
that diagnostic is not an error bound for a distorted optical system. Dawes
116/D, Rayleigh 138/D, maximum 2D, minimum D/7 and sampling/framing labels are
existing conventions. Testing their arithmetic does not validate their physical
adequacy, wavelength dependence, human pupil size or observing usefulness.

## Pre-evaluation protocol

Commit `7262b69` freezes the reference, policy and comparison harness before
production evaluation or repair. The original run has a clean checkout at that
commit. A subsequent lint-only reference edit passes the tiling step explicitly
instead of closing over a loop variable; fixture bytes and all policy values
remain identical. The manifest's generator hash changes accordingly. Historical
manifest bytes are recoverable at the baseline commit and their hash is retained
in the baseline record. No tolerance or case was removed after seeing failures.

| Group | Cases | Coverage |
|---|---:|---|
| Optical | 100 | Five telescope and five eyepiece parameter sets, four accessory combinations |
| Imaging | 105 | Five telescope and five sensor parameter sets, four accessory combinations, five additional wide/narrow/orientation cases |
| Direct sensor field | 6 | Tiny angles, ordinary field, 90-degree analytic geometry, near-180-degree ideal geometry |
| Planar mosaic | 96 | Two widths, two heights, three overlaps, four target widths, two target heights; exact Fraction enumeration |
| Total | 307 | Every case and metric retained, no random seed or network dependency |

The telescope grid spans 70–203 mm aperture and 650–2032 mm native focal length.
Accessory pairs `(Barlow, reducer)` are `(1,1)`, `(2,1)`, `(1,0.63)`, `(2.5,0.8)`.
Additional imaging cases use 50 mm aperture and 20/50/100/100000 mm focal lengths;
these are mathematical stress inputs, not endorsements of realizable hardware.
Sensors span one pixel through the five existing parameter sets, with micrometres
converted to millimetres explicitly. Seeing is fixed to 2 arcseconds for setup
arithmetic; separate tests characterize classification boundaries at 3 arcseconds.

For rounded results the absolute bound is half the public output quantum plus
1e-10 in the output's unit: 0.0005000001 for three decimal places,
0.0000500001 for four, and 0.0050000001 for percentage outputs with two.
Unrounded direct angular fields have a 1e-10 degree bound. Integer panel counts
must match exactly. The slack covers binary input conversion and arithmetic,
not physical uncertainty. Half-quantum comparison intentionally does not enforce
a particular decimal tie-breaking rule.

Mosaic coverage is an axis-aligned planar angular-width abstraction. The reference
adds one overlap-adjusted step until coverage reaches the target instead of
reusing the production ceiling expression. Its binary-exact grid exercises
on-boundary counts without conflating decimal-input uncertainty with topology.
Arbitrary non-binary exact tiling boundaries, rotating celestial footprints,
spherical tiling and large-overlap numerical conditioning remain unqualified.

## Retained failure and correction

The [baseline record](../../../validation/results/telescope_imaging_baseline_run.json)
contains 35 failed cases; each failure is `field_diagonal_degrees`. The largest
error is 9.84628648362235 degrees in the deliberate wide-field stress case
`imaging-100`: old output 104.3395 degrees versus reference approximately
94.49321351637765 degrees. Even some ordinary sensor/telescope combinations
exceed their public rounding allowance. The failure is therefore not solely
an unrealistic-input diagnostic.

Production previously used `hypot(horizontal_angle, vertical_angle)`, a
small-angle approximation. It now uses the physical sensor diagonal
`sqrt(width_mm**2 + height_mm**2)` in the same ideal angular-field equation as
the two axes. Width, height, image scale, sampling, return types and interfaces
remain unchanged. Camera ordering may change where the corrected diagonal
ordering differs; this is the intended geometric correction.

The [corrected record](../../../validation/results/telescope_imaging_reference_run.json)
retains the complete corpus, source/input hashes, commit identity, clean/dirty
state, execution time, Python version, OS/architecture and error metrics. Only
stdlib modules participate in this benchmark; astronomy databases, time scales,
EOP and ephemerides are not applicable. The full project's dependency environment
is separately exercised by the Quality Gate.

## Controls, CI and reproducibility

The [Mission 52 tests](../../../tests/test_telescope_imaging_validation.py)
replay each reference case, reject changed manifest/fixture/generator hashes,
regenerate the reference byte-for-byte with network sockets blocked, and forbid
production/numerical-library imports in the generator. Mutation controls prove
that the old diagonal, a factor-1000 pixel-scale unit error and omitted overlap
are detected. Classification tests cover exact thresholds and neighbouring
representable values, including optical precedence. Invalid finite/sign,
nonfinite, pixel-count, accessory and overlap contracts are checked separately.
These are software and policy controls, not additional scientific observations.

Run from the repository root with Python 3.12 or later and the project's installed
validation/development environment:

```bash
python -m validation.reference_generation.telescope_imaging --output /tmp/telescope_imaging_fixture.json
cmp validation/fixtures/telescope_imaging_v1.json /tmp/telescope_imaging_fixture.json
python -m validation.telescope_imaging --output /tmp/telescope_imaging_run.json
python -m pytest -q tests/test_telescope_imaging_validation.py tests/test_telescope.py tests/test_imaging.py
python -m ruff check .
python -m pytest -q
```

The fixture is deterministic; execution timestamps, checkout identity and platform
provenance in result records naturally vary. The runner exits nonzero on a failed
metric and writes its diagnostic record before returning. CI adds the twentieth
artifact, `telescope-imaging-validation-record`, while preserving the existing
19 audits. Final-head full-suite and artifact evidence is recorded in the PR.

## Remaining boundaries

W01's bounded reference dossier is supplied for review. This does not close
E02–E08 for all Phase 2 areas. W02–W07 remain as defined in Mission 51. No new
hardware control, lens prescription, optimization, target catalogue measurement
or observing-performance claim is introduced.

X01 is unchanged: 18 physical receipt gaps, six unresolved components, 48
unqualified site clocks and 288 blocked arrival candidates remain. Physical
clock/site/arrival bounds remain null, physical covariance unqualified, and
`observing_eligible=false`. This optical mission neither modifies those records
nor relaxes their rejection gates.
