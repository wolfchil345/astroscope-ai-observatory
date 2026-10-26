# Mission 65 — Controlled Scheduler Baselines and Adapter Validation

**B0 and B1 follow their declared policies on all 216 frozen development cases
and 16 controls.** B0 calls the unchanged production strict scheduler through a
validation-only planner adapter. B1 is an immediate cost-aware policy confined
to validation. This is development acceptance, not a completed optimizer study.
The 216 evaluation-reserved cases have no candidate executions or outputs;
B2 is not implemented. Production and physical qualification are unchanged.

Mission 64's [PR #64](https://github.com/wolfchil345/astroscope-ai-observatory/pull/64)
merged at `0577e5461797491ce3578b03ed94cbcc331b22a6`. Its
[merge-CI receipt](../evidence/mission64_merge_ci_v1.json) verifies run
40300307076, 8,377 passing tests, 26 retained historical expected failures and
all 29 downloaded archives. The [accepted protocol](../phase_3_entry_protocol.md),
[input/reference release](controlled_schedule_corpus.md) and their historical
ledgers remain unchanged. This mission's [ledger](../evidence/schedule_baselines_v1.json)
records the later state; Mission 65 itself awaits review and merge.

## Implementation and independent checks

| Component | Implementation / boundary |
|---|---|
| [B0 adapter and B1](../../../validation/schedule_baselines.py) | Strict development access guard, canonical IDs, supplied-input policies only |
| Real B0 function | `astroscope.schedule.calculate_observation_schedule_strict`; source unchanged |
| Patched call | Only `schedule.calculate_observation_plan`, scoped and restored even after exceptions |
| [Independent policy verifier](../../../validation/schedule_baseline_checks.py) | Traverses returned actions and compares every feasible per-slot alternative; imports neither baseline |
| Independent objective | M64's retained path scorer filters non-idle IDs before counting changes |
| Independent optimum | M64's frozen E0 output; no oracle import or lookup inside either policy |
| [Audit](../../../validation/schedule_baseline_audit.py) | Complete development inventory, per-method failures, metrics, timing and grouped denominators |
| [Tests](../../../tests/validation/test_schedule_baselines.py) | 530 cases, including genuine scheduler block mutations and seven B1 code mutants |

B0 supplies N+1 snapshots at exact aware UTC times, including the terminal
snapshot. Date crossing uses explicit dates rather than hour-only indexing.
Only literal eligibility=true with a known score is recommended. Known zero
remains usable; missing scores map to zero only in unrecommended injected entries,
and missing-score/unknown-eligibility masks remain in every B0 record. All targets
have the same 45° altitude, `catalog` category and canonical ID order. Geometry
is a fixed test placeholder, with no observational interpretation. `minimum_score=0`
is an API placeholder; recommendation comes from the frozen supplied mask.

The actual scheduler retains its original score/altitude/stable-input-order
selection. Experiment canonicalization gives its declared tie behavior without
changing or claiming permutation invariance for the production UI. B0 ignores
switch cost, as required. B1 includes idle, subtracts a change charge from each
feasible immediate reward, keeps the first maximizing canonical action and
retains the last non-idle target. First acquisition is free.

The adapter decodes half-open blocks and rejects off-grid/out-of-range times,
overlap, reverse ordering, incorrect duration, invalid targets, bridges over
unusable slots, inconsistent peaks or unmerged adjacent identical blocks. It
checks N+1 calls, timeline IDs/times/masks, sample and target counts, scheduled
minutes and result endpoints. C13 supplies the preregistered recommended endpoint
with score 100; the real scheduler observes the sole real-slot winner with score
10 and excludes the endpoint. C09/C14 retain gaps between repeated targets.

Network sockets, name resolution, subprocess execution and live astronomical
planner calls are blocked during the audit. The real production modules remain
importable; their versions are recorded. The exhaustive solver import is blocked
while methods run. Guard tests attempt every evaluation-reserved input, including
split/replicate relabelling, before the scheduler can be reached. The audit also
checks immutable input hashes and selects only the fixed development inventory.
This is an accidental-access safeguard, not a security boundary against rewriting
the experiment's code or case identity.

## Executed results and retained adverse cases

The [canonical clean-checkout record](../../../validation/results/schedule_baselines_reference_run.json)
contains every path, missing-data mask, B0 block/snapshot record, metric, timing
sample, failure field and aggregate. All 232 cases × two methods satisfy policy
faithfulness and feasibility. Optimality is not a baseline acceptance condition.

| Development-only measure | B0 | B1 |
|---|---:|---:|
| Primary cases | 216 | 216 |
| Exact optimum objective attained | 164 | 200 |
| Positive regret retained | 52 | 16 |
| Mean regret, nominal points | 7.782407 | 1.074074 |
| Median regret | 0 | 0 |
| Maximum regret | 156 | 59 |

On the 216 primary development cases, B1 versus B0 has **44 wins, 166 ties and
six losses** in net objective. These are descriptive designed-corpus results;
the three cost profiles share core matrices and are not independent statistical
samples. No significance, operational benefit or generalization is inferred.
The full record groups denominators, failures and regret by family, split and
cost, keeping controls separate. No case or adverse outcome was dropped.

For example, development case `P3-F3-N06-M03-R00-C20` has E0 objective 590:
B0 scores 576 while B1 scores 531. An immediate change penalty can discourage
a useful change; this six-slot case demonstrates a limitation of B1 rather
than a policy implementation failure. No future-aware B2 result is implied.

| Retained control | B0 net | B1 net | E0 net |
|---|---:|---:|---:|
| C07 published M55 alternating example | 230 | 269 | 269 |
| C12 optional middle-slot idle | 161 | 200 | 200 |
| C13 high-score terminal snapshot | 10 | 10 | 10 |

C07 remains reused development evidence, not a new holdout. Scores are nominal
points and costs are not physical slew time or calibrated scientific yield.

## Fault sensitivity and measurements

All 530 new tests passed locally before the corrected source freeze, including
a regression check for shadowed dependency installations. They cover 232
development/control cases, 216 reserved-input rejection cases, 48 malformed-input
variants, real scheduler invocation/patch restoration, ten block-output fault
types, wrong ties and missing/unknown eligibility, all five preregistered
metamorphic relation types, live-planner/network/oracle isolation, and seven
mutated B1 implementations. Test counts include parametrizations; they are not
530 independent scientific experiments.

The B1 mutants erase idle history, omit or double change cost, charge first
acquisition, admit unknown eligibility, treat missing scores as zero, or reverse
tie order. Each is rejected by the independent policy verifier on development
inputs. Block faults include terminal selection, off-by-one grid membership,
overlap and gaps; these now exercise outputs from the actual scheduler rather
than the numeric-only boundary checks in Mission 64. No production source is edited.

Every method/case receives one untimed warmup and five timed calls in the same
process/machine using `perf_counter_ns`: 2,784 total baseline invocations per
complete audit. The record gives all samples, median/range and operation counts.
**B0 timing includes the strict API, injection and block decoding; B1 includes its
input guard.** These scopes differ, so no algorithmic speedup is claimed and no
portable wall-time acceptance threshold is used. The CI step's ten-minute cap
marks an overrun incomplete, never passed. All per-method exceptions are retained
as failures, and remaining cases are attempted.

## Freeze, access and offline reproduction

The corrected source, tests and configuration are frozen at
`3627d475c839a407a9d3b055fb850db81e63fb24`, followed by the
[v2 hash manifest](../../../validation/manifests/schedule_baselines_freeze_v2.json)
at `f5222bb413b3ce16adf056a12996ddf99bb9e520`.
The initial source and manifest checkpoints (`92f3c732` and `1c886c99`) are
retained in the v1 history bundle. Their
[original audit record](../../../validation/results/schedule_baselines_initial_environment_record.json)
reported NumPy 2.3.5 because a duplicate installed-distribution listing overwrote
the imported environment's version. Inspection found the imported NumPy was
2.5.4. The v2 runner resolves each distribution name through metadata lookup and
also records actual imported Astropy/NumPy versions. The original record is
retained as evidence with a known environment-reporting defect. All 464 method
outputs, integer metrics, operation counts and aggregates are unchanged in the
corrected run; timing samples differ normally. No policy, input, threshold or
reserved-access rule changed. This is a provenance repair, not an optimization
result repair or a new confirmatory sample.

The canonical audit ran from that clean checkpoint. Development outputs were
inspected while implementing and testing the baselines; this is disclosed in the
[access record](../evidence/schedule_baselines_access_v1.json). No reserved
candidate outputs were generated, inspected or used for tuning. M64's public E0
replays remain distinct from candidate evaluation.

With the existing project development/validation dependencies installed:

```bash
python -m pytest -q tests/validation/test_schedule_baselines.py
python -m validation.schedule_baseline_audit --output /tmp/schedule_baselines_run.json
python docs/research/evidence/verify_schedule_baselines.py
python -m ruff check .
python -m pytest -q
```

Policy paths and integer metrics are deterministic. Runtime samples and environment
records are deliberately machine/run dependent; the whole benchmark JSON is not
claimed byte-identical. M64 input/reference files remain byte-identical and hashed.
The canonical record includes implementation/checkout/parent commits, dirty state,
Python, platform, architecture, installed dependency versions, source/input hashes,
commands and UTC convention. Ephemerides/EOP are explicitly unused, and geometry
is explicitly synthetic. Imported astronomy packages do not qualify those fields.

The [local Git history bundle](../../../validation/reference_generation/schedule_baselines_history_v2.bundle)
preserves both freeze commits after squash merge/branch deletion. With the complete
main history and the ledger's verified bundle hash, restore missing objects offline:

```bash
git bundle verify validation/reference_generation/schedule_baselines_history_v2.bundle
git fetch validation/reference_generation/schedule_baselines_history_v2.bundle refs/research/mission65-freeze-v2
```

All prior CI steps/artifacts remain; the baseline audit is artifact 30. The full
final-head test and archive receipts are recorded in the PR before handoff.
The documentary checker verifies protected historical files, freeze ordering,
current source hashes, exact inventory and inherited restrictions. Earlier M63/M64
documentary checkers describe their own historical workflow snapshots; their
baseline execution is retained in merge receipts, not reinterpreted as M65 state.

## Roadmap boundaries and next work

| Gate | Current status |
|---|---|
| P3-E01 / P3-E02 | Protocol and frozen input/E0 release accepted through M63/M64 merge |
| P3-E03 | B0/B1 development evidence implemented; M65 review pending; B2 absent |
| P3-E04 | Development characterization only; evaluation-reserved comparison pending |
| P3-E05 | Observational calibration remains deferred with its evidence prerequisite |
| P3-E06 | Production integration and Phase 3 exit not approved |

Proposed **Mission 66 — Finite-Horizon Candidate Development Validation**:
after review/merge, implement B2 under the same finite model, compare exact
development objectives and canonical paths with frozen E0, and freeze its source
and configuration before any evaluation-reserved candidate-output access.
The complete reserved comparison is separate later work. Mission 66 has not started.

All five accepted M62 exclusions and X01 remain unchanged: 18 unestablished
requirements, six unknown components, 48 unqualified site clocks and 288 blocked
arrivals, zero executed. Physical bounds stay null; strict transit coverage stays
13 boundary / five partial / eight deferred. M56's nine and M60's 17 historical
failures and all 26 strict expected failures are retained. No production feature,
catalogue truth assumption or physical observing eligibility is added.

Method definitions and primary references remain those of the
[M63 protocol](../phase_3_entry_protocol.md#verification-and-method-sources).
The [M64 reference dossier](controlled_schedule_corpus.md) explains E0's independence
and its limits: algorithmic separation is not separate human scientific review.
