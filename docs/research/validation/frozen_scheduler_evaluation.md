# Mission 67 — Frozen Evaluation-Reserved Scheduler Comparison

**B2 matches the frozen exhaustive E0 objective and canonical optimal path on all
216 evaluation-reserved cases.** The complete audit also reproduces the 216
development cases and 16 controls: 448 cases, 1,344 method-case records, zero
scientific acceptance failures. This is bounded finite-model evidence; production,
physical observing qualification and Phase 3 exit remain unchanged.

Mission 66 was accepted by [PR #66](https://github.com/wolfchil345/astroscope-ai-observatory/pull/66)
merge `7f9f4d0276fc998224f9ba1d0e03ce24f0551b20`. Its
[post-merge receipt](../evidence/mission66_merge_ci_v1.json) verifies Quality Gate
40318487525 and Schedule Candidate Validation 40318487393: 9,670 tests passed,
26 historical expected failures retained and all 31 downloaded archives checked.
The [M63 protocol](../phase_3_entry_protocol.md), [M64 E0 release](controlled_schedule_corpus.md),
[M65 baselines](controlled_scheduler_baselines.md) and [M66 B2 development evidence](finite_horizon_candidate_validation.md)
remain byte-identical. Their historical zero-reserved-execution statements apply
to their own checkpoints; this report records the later exposure.
Mission 67 review/merge is pending.

## What was frozen before exposure

The [execution plan](../protocols/schedule_evaluation_execution_v1.md),
[configuration](../../../validation/manifests/schedule_evaluation_v1.json), adapter,
runner, journal checker, tests and new workflow were committed at
`c2e55b1c12c0ecba2f292aa31bfe5fc2530fe312`. The separate
[hash manifest](../../../validation/manifests/schedule_evaluation_freeze_v1.json)
was committed at `a30ee60e6d119ee12df8364cbf4e0533941b294c`.
The first canonical run used that clean checkpoint. No reserved candidate output
was computed before these commits; preflight tests used development computations
and reserved-input guard checks only.

The [adapter](../../../validation/schedule_evaluation.py) binds the identical
frozen Python method code objects to private copies of their global mappings.
It substitutes only a guard for exact frozen corpus bytes and, for reserved
cases, an active verified evaluation session. B0's decoder uses the same private
guard and identical decoder code. B0 still invokes the actual strict production
scheduler through the existing controlled planner boundary. Original B0/B1/B2
module guards remain unchanged and continue to reject reserved execution even
while the new session is active. There is no permanent global-guard patch,
algorithm rewrite or new production API.

The gate verifies source/config/input hashes and the predecessor acceptance
receipt; the runner requires a clean checkout. All 232 development/control cases
must reproduce M66 before any reserved execution. A development failure would
leave reserved rows present but not executed, marking the audit incomplete.
A reserved failure would retain outputs/errors and continue the remaining methods
and cases. These controls address accidental access and reproducibility; they
are not security against rewritten source or manifests.

## Complete frozen results

Primary development and reserved denominators are each 216; the 16 controls are
separate. All B2 paths match E0 exactly, with zero feasibility violations and
zero integer objective regret.

| Split | Method | Zero regret | Positive regret | Mean regret | Median | Maximum |
|---|---|---:|---:|---:|---:|---:|
| Development | B0 | 164 | 52 | 7.782407 | 0 | 156 |
| Development | B1 | 200 | 16 | 1.074074 | 0 | 59 |
| Development | B2 | 216 | 0 | 0 | 0 | 0 |
| Evaluation-reserved | B0 | 176 | 40 | 7.032407 | 0 | 144 |
| Evaluation-reserved | B1 | 201 | 15 | 0.902778 | 0 | 31 |
| Evaluation-reserved | B2 | 216 | 0 | 0 | 0 | 0 |

| Split | Paired comparison | Wins | Ties | Losses |
|---|---|---:|---:|---:|
| Development | B1 vs B0 | 44 | 166 | 6 |
| Development | B2 vs B0 | 52 | 164 | 0 |
| Development | B2 vs B1 | 16 | 200 | 0 |
| Evaluation-reserved | B1 vs B0 | 34 | 175 | 7 |
| Evaluation-reserved | B2 vs B0 | 40 | 176 | 0 |
| Evaluation-reserved | B2 vs B1 | 15 | 201 | 0 |

On controls, B0 has 14 zero-regret and two positive-regret outcomes; B1 and B2
have zero regret on all 16. The original M55 and optional-idle examples remain.
Every development/control method output, metric and operation count matches M66.
Policy correctness does not imply greedy optimality. All seven new reserved B1
losses are retained, in addition to the six earlier development losses:

| Reserved case ID | B0 objective | B1 objective | B2 = E0 |
|---|---:|---:|---:|
| P3-F3-N06-M03-R02-C05 | 576 | 571 | 576 |
| P3-F3-N06-M03-R02-C20 | 561 | 552 | 573 |
| P3-F4-N06-M02-R02-C20 | 78 | 70 | 92 |
| P3-F4-N09-M03-R03-C20 | 413 | 396 | 413 |
| P3-F5-N06-M02-R02-C05 | 264 | 262 | 264 |
| P3-F5-N06-M02-R02-C20 | 234 | 232 | 234 |
| P3-F5-N09-M02-R02-C05 | 452 | 448 | 452 |

The [canonical record](../../../validation/results/schedule_evaluation_reference_run.json)
contains all paths, integer objective components, exact/normalized regret,
feasibility, observed/idle durations, block counts, counters and timing samples.
Aggregates retain family/split/cost denominators, failures and incomplete-pair
counts. No case was dropped, rerolled, repaired or assigned a new threshold after
exposure. These deterministic, correlated designed cases and shared cost profiles
are not independent statistical samples. No significance, generalization,
forecast skill, calibrated observing yield or algorithm-speedup claim is made.

## Independent checks and tests

The unchanged independent M65 policy checker verifies B0/B1. M66's checker
recomputes B2 path arithmetic and compares the exact objective and canonical path
with M64's frozen exhaustive E0. E0 uses complete path enumeration, not the
candidate's backward recurrence. Algorithmic independence, common authorship and
a shared specification are distinguished; no separate human scientific review
is asserted. The method background and limitations remain those in the M63/M66
reports; this mission adds evaluation execution evidence, not a new mathematical model.

[531 new tests](../../../tests/validation/test_schedule_evaluation.py) passed before
source freeze. Combined M64–M67 regressions passed 1,845 tests and 1,004 subtests.
The new tests cover every development/control adapter output, all 216 reserved
IDs rejected without a session, relabelling, 48 malformed variants, changed but
schema-valid inputs, identical code-object binding, real scheduler invocation,
planner restoration on exceptions, session expiry, source/input/configuration
faults, partial results after timeout and seven access-journal corruption modes.
A mocked evidence tree is used only for development computation and input-only
session checks; no reserved candidate output is computed in any unit test.
Existing M65/M66 mutation, metamorphic, terminal, slot-boundary and original
reserved-guard tests remain unchanged in the full suite.

The [journal checker](../../../validation/schedule_evaluation_checks.py) imports
no candidate and independently reconciles every invocation, case/split, method,
phase, repetition and output hash with the complete record. Sockets, subprocesses,
live astronomy and E0 imports are blocked during execution. B2 file opens are
also blocked during each candidate call. Synthetic geometry/EOP/ephemeris fields
remain explicitly unqualified or unused.

## First exposure and reproducibility

The [first access journal](../../../validation/results/schedule_evaluation_first_access.jsonl)
is retained verbatim alongside the raw canonical JSON. It has 16,133 sequential,
UTC-stamped events covering all 8,064 invocations, including 3,888 reserved calls.
Each method-case has one warmup and five measured calls. Method-start events are
flushed before invocation, followed by completion/output digest or error. The
runner initially writes an incomplete result; partial JSON/journal evidence
survives interruption. Existing output/journal paths cannot be overwritten.

The first record is labelled `first_frozen_evaluation`. All later local/CI runs
are explicitly `exposed_regression_replay`; they are not new unseen evidence.
The public inputs were never a blind holdout, and no model is trained. The
[access ledger](../evidence/schedule_evaluation_access_v1.json) records preflight,
first exposure, offline recovery and the future replay policy. A future repair
would retain the original record and require new versioned results labelled as
exposed regression.

The canonical environment records Python 3.12.14, imported NumPy 2.5.4 and Astropy
8.0.2, resolved package metadata, OS/architecture, commits, clean state and all
source/input hashes. Imported versions agree with metadata lookup. Timing is
measured in one process/machine and includes binding, case hashing, journaling,
guards and differing adapter overheads. All five samples, medians and ranges are
retained. The ten-minute CI cap marks overruns incomplete; no portable time pass
threshold is imposed. Paths, metrics, counters and aggregates are deterministic;
run timestamps, journal digests, timing samples and environments are not.

With the repository's development/validation dependencies installed:

```bash
python -m pytest -q tests/validation/test_schedule_evaluation.py
python -m validation.schedule_evaluation_audit \
  --access-label exposed_regression_replay \
  --output /tmp/schedule_evaluation_new_replay.json
python docs/research/evidence/verify_schedule_evaluation.py
python -m ruff check .
python -m pytest -q
```

Use a fresh output path for each replay. The published canonical record prevents
reuse of the first-run label at the published revision. A historical freeze
checkout can be reconstructed, but subsequent execution there must also be
labelled exposed replay.

The [offline source-history bundle](../../../validation/reference_generation/schedule_evaluation_history_v1.bundle)
requires the M66 main-history baseline. An isolated checkout initially missing
the source commits recovered them and reproduced all 1,344 method records and
aggregates as an exposed replay, without a GitHub/network fetch. Its access
journal passed the same reconciliation. Recover source objects offline with:

```bash
git bundle verify validation/reference_generation/schedule_evaluation_history_v1.bundle
git fetch validation/reference_generation/schedule_evaluation_history_v1.bundle refs/research/mission67-freeze
```

Historical M65/M66 bundles and provenance defects remain preserved. Current
replay does not establish universal original-environment reconstruction,
fully vendored raw-reference regeneration or cross-platform equivalence.

## CI and remaining research gates

Both prior workflow files remain byte-identical. The separate
[Schedule Reserved Evaluation workflow](../../../.github/workflows/schedule-evaluation-validation.yml)
adds artifact 32, containing both the replay result and its journal. Handoff
requires Quality Gate, Schedule Candidate Validation and Schedule Reserved
Evaluation at the exact final head, with all 32 archives downloaded and checked.
The PR records final run IDs, test counts, archive/JSON/journal digests and
mergeability. Branch protection is unchanged.

P3-E03/P3-E04 now have complete method-correctness/comparison evidence within the
frozen finite study, pending this mission's review. P3-E05 observational calibration
and P3-E06 integration/exit remain open. This does not complete Phase 3's broader
planner/weather/ranking scope. Production, the M37 timing boundary, all 26 strict
xfails, M56's nine and M60's 17 historical failures remain unchanged. X01 retains
18 unestablished requirements, six unknown components, 48 unqualified clocks and
288 blocked / zero executed arrivals with null physical bounds. All five M62
exclusions and the 13 implemented / five partial / eight deferred transit categories
carry forward.

**Proposed Mission 68 — Observation-Utility Calibration Study Design.** After
M67 review/merge, define a source-supported observational-calibration protocol:
provenance-bearing inputs/outcomes, score interpretation, missingness, independent
references, prospective splits, uncertainty, acceptance and stop rules. Dataset
acquisition/evaluation and any production integration require their own approved
scope. Preserve X01 restrictions; synthetic optimizer success cannot qualify
physical predictions. Mission 68 has not started.
