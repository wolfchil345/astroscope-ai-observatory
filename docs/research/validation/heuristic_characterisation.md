# Planner, Weather, Ranking and Schedule Heuristic Characterisation — Mission 55

Mission 55 supplies bounded W04 evidence from the
[Phase 2 audit](../phase_2_coverage_audit.md). It checks the arithmetic, thresholds,
missing-input conventions and selection behaviour of existing heuristics. It
establishes neither forecast skill nor observing success nor calibrated utility.
No production source is changed. Phase 2 remains active.

## Independent protocol and scope

The stdlib-only reference generator uses Decimal arithmetic at precision 60,
including logarithms and exponentials, and enumerates all eight paths through
three two-target schedule slots. Reference code imports no AstroScope, Astropy,
NumPy or ERFA. A subprocess regeneration test blocks those imports and socket
connections and requires byte-identical output. The score equations themselves
are the application's declared policies, not independent physical laws: this is
independent arithmetic and algorithm characterization, not external calibration.

The original 352-case corpus, acceptance policy and evaluator were committed at
`429cc0a` before production evaluation; all 352 passed on the first run. Three
additional algebraic weight-reversal controls were committed at `e7e5756` before
their evaluation. All 355 checks pass in the clean canonical record at
`e7e5756e635c28cc53fcb3cadeda1dd33589a1ca`. No tolerance was fitted to residuals,
and no failed scientific case was discarded.

The fixed absolute numerical goal is 1e-10 score units, with exact categorical
and Boolean agreement. Input strings are converted to Decimal before arithmetic.
One-decimal values use half-even rounding; the corpus deliberately avoids
ambiguous binary half-ties and uses 0.001 offsets at scalar thresholds. This does
not qualify all extreme floating-point magnitudes or underflow/overflow paths.
The very large timing-decay control may underflow in binary arithmetic; its
absolute error remains negligible under the declared goal, with no relative
accuracy claim near zero.

## Coverage and results

| Benchmark group | Cases | Evidence |
|---|---:|---|
| Planner components and ratings | 90 | Altitude/airmass/darkness saturation; Moon minimum 0/30/near-90/90/near-180/180; Moon-target exception |
| Planner recommendation combinations | 40 | Missing airmass, Moon exception, status gate and threshold membership |
| Transit scalar components | 39 | Altitude, Moon separation, log-depth, exponential timing and brightness |
| Weather scores and ratings | 66 | Seven one-factor sweeps, joint rain/gust caps, label thresholds |
| Dew classifications | 54 | 9 spread values × 6 humidity values, including adjacent boundaries |
| Transit weighted totals | 54 | Three controlled candidates × 18 weight profiles |
| Exhaustive schedule controls | 9 | Alternating, constant and tied scores × switch penalties 0/5/20 |
| Weight reversals | 3 | Default, depth-only and observable-fraction-only policies |
| **Total** | **355** | **All pass** |

Maximum scalar/aggregate residual is 7.106e-15 score units; maximum weighted-total
residual is 1.422e-14. These are numerical residuals, not physical uncertainties.
The fixture contains 289 scalar/plan cases, 54 weighted candidates and nine
schedules. The three algebraic tradeoffs are explicitly defined in the runner.

There are 439 new tests and 613 passing focused tests with the existing planner,
weather, ranking, schedule and strict-timing suites. Ruff passes. Additional tests
cover all six candidate input permutations for each of 18 profiles, common
weight scaling, negative/nonfinite/all-zero weights, missing numeric weather
inputs, weather monotonicity, threshold gates, stable ties, temporal sampling,
offline replay and independent reference regeneration.

## What the heuristics mean

The transit priority is a normalized weighted sum, not a probability:

\[
S=100\frac{\sum_i w_i c_i}{\sum_i w_i}.
\]

Profiles include the default, sevenfold common scaling, each of eight one-hot
weights, and each default weight doubled in turn. Common scaling leaves priority
unchanged. Controlled candidates isolate component behaviour; their summary
fields are deliberately supplied independently and are not asserted to describe
physically self-consistent observing windows. Mission 54 owns sampled-window
geometry. No catalogue or unresolved timing prediction is converted here.

| Controlled comparison | Result | Interpretation |
|---|---:|---|
| Missing depth/brightness versus known zero depth and magnitude 16 | +7.5 points under defaults | Missing values receive 0.5 components, with explicit missing-field labels; missing is not evidence of quality |
| A: observable fraction 1, depth 0; B: observable fraction 0, depth 10,000 ppm; other components equal | A−B = +20 default, −100 depth-only, +100 visibility-only | Rankings depend on chosen weights |
| Rain increases from 0.499 to 0.5 mm | Score capped at 25 | Hard policy boundary, not an empirical weather transition |
| Gusts increase from 59.999 to 60 km/h | Score capped at 20 | Both caps apply when present; rating becomes unsuitable |
| Minimum Moon separation crosses 90° | Ideal reference switches from 90° to 180° | Component values can change abruptly; this is existing policy |

Planner missing airmass earns zero component credit. Transit missing depth and
brightness use the neutral prior. Required numeric weather score inputs reject
negative, nonfinite or null values (null may raise TypeError rather than a typed
service exception). No forecast ingestion imputation is introduced. Dew controls
use finite supplied temperature/spread/humidity; they do not establish condensation
prediction skill or qualify arbitrary invalid temperature inputs.

Recommendation uses the rounded one-decimal planner total plus altitude, status
and Moon gates. The score alone is insufficient. Equality is inclusive at the
applicable thresholds. The Moon target bypasses its separation gate. Planner
weights are fixed constants; this mission does not expose a new tuning API.

Transit ordering resolves score ties using full-window flag, observable fraction,
midpoint altitude, casefolded planet name and transit number. Fully identical keys
retain input order; a casefold collision is not a universal identifier tie-break.
Schedule score/altitude ties also retain input order. The tests disclose these
rules rather than pretending every permutation yields an identical winner.

## Greedy selection and sampling limits

The controlled alternating score matrix is:

| Target | Slot 1 | Slot 2 | Slot 3 |
|---|---:|---:|---:|
| A | 90 | 89 | 90 |
| B | 89 | 90 | 89 |

With independent equal-duration slots and no switching penalty, A→B→A attains
270, the sum of per-slot maxima. It is optimal for that deliberately uncoupled
objective. With a synthetic 20-point charge per switch, the same sequence earns
230, while A→A→A earns 269: regret is 39. Exhaustive enumeration establishes the
reference optimum over all eight sequences. This is an objective-mismatch
counterexample, not a failed contract or evidence that production claims to
optimize switching costs. No real slew time, acquisition time, minimum dwell,
weather uncertainty or instrument constraint is modelled.

A 120-minute grid skips the hour-1 preference for B and selects A throughout;
60- and 30-minute grids select A→B→A. All report 180 scheduled minutes. Occupancy
therefore does not prove continuously preferred selection. The controlled
upstream planner is patched only inside the validation harness; the existing
scheduler itself executes unchanged. No sky-position accuracy is inferred from
these injected trajectories. Mission 32 retains interval semantics and Mission
54 retains physical visibility-sampling limits.

## Reproduction and provenance

Install `.[dev,validation]` and run from the repository root:

```bash
python -m validation.reference_generation.heuristic_characterisation
python -m pytest -q tests/validation/test_heuristic_characterisation.py tests/test_planner.py tests/test_weather.py tests/test_transit_ranking.py tests/test_schedule.py tests/test_transit_timing.py
python -m validation.heuristic_characterisation --output /tmp/heuristic_characterisation_reference_run.json
```

Reference generation uses Python's standard library only. The runtime uses the
existing installed project dependencies and frozen JSON, without weather HTTP
requests, ephemeris downloads, reference-generator imports or randomness.
The [manifest](../../../validation/manifests/heuristic_characterisation_v1.json)
hashes the generator, policy and fixture. The
[canonical result](../../../validation/results/heuristic_characterisation_reference_run.json)
records source/input hashes, clean implementation identity, dependency versions,
all cases, expected/actual values, residuals, missing labels and regret.

CI adds `heuristic-characterisation-validation-record` as artifact 23 while
retaining the previous 22. Final-head full-suite CI, artifact inventory and
new-artifact verification are recorded in the PR before handoff.

## Limits and next work

This is a bounded W04 dossier. It does not establish calibrated score weights,
empirical utility, forecast probabilities, uncertainty propagation or a general
optimal scheduler. Correlated factors and missingness can bias interpretation;
no fitted or observational data are claimed. These remain Phase 3 tasks.

X01 is unchanged: six physical error-budget components remain unknown, 48 site
clocks remain unqualified, 18 covariance requirements remain unestablished and
all 288 combined arrival candidates remain blocked (240 solar-eligible and 48
excluded). No physical covariance was acquired or propagated. Strict unresolved
predictions still cannot enter observing/export paths. Phase 2 remains active;
Phases 3–8 remain planned. W05 light-curve campaigns, W06 reconciliation and W07
reviewed exit are separate remaining packages.

## Method references

- [Python Decimal](https://docs.python.org/3/library/decimal.html): independent
  decimal representation, precision, rounding and transcendental arithmetic.
- [Python Cartesian products](https://docs.python.org/3/library/itertools.html#itertools.product):
  enumeration of all finite candidate paths and ordering permutations.
- [Mission 51 audit](../phase_2_coverage_audit.md): scope and exit requirements.
- [Mission 54 visibility sampling](visibility_sampling_validation.md): distinction
  between sampled values and continuous observing coverage.
