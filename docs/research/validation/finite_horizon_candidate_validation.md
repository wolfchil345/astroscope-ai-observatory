# Mission 66 — Finite-Horizon Candidate Development Validation

**B2 matches the frozen exhaustive E0 objective and canonical optimal path on all
216 development cases and 16 controls.** This validates the finite supplied-input
model on development data. The 216 evaluation-reserved cases have no candidate
executions or outputs. Production integration, observational calibration and
Phase 3 exit remain unapproved.

Mission 65 was accepted by [PR #65](https://github.com/wolfchil345/astroscope-ai-observatory/pull/65)
merge `b4e6cd13282ab2b87715aa659d74446f1ccab5a4`. Its
[post-merge receipt](../evidence/mission65_merge_ci_v1.json) verifies Quality Gate
40313315784: 8,907 passed, 26 historical expected failures and all 30 downloaded
artifact archives. The [M63 protocol](../phase_3_entry_protocol.md),
[M64 input/E0 release](controlled_schedule_corpus.md), and
[M65 baseline evidence](controlled_scheduler_baselines.md) remain byte-identical.
Their historical statements describe their own checkpoints. The
[new ledger](../evidence/schedule_candidate_v1.json) records Mission 66's later
state; review/merge of this mission remains pending.

## Candidate and independent reference

| Component | Method and boundary |
|---|---|
| [B2](../../../validation/schedule_candidate.py) | Integer backward dynamic programming over slot and last non-idle target; development guard before recurrence |
| [Independent checker](../../../validation/schedule_candidate_checks.py) | Imports no candidate; uses retained raw path scorer and frozen E0 objective/path |
| E0 | Unchanged exhaustive Cartesian-product traversal from M64; no DP or candidate imports |
| B0/B1 | Unchanged M65 methods; all 464 output/metric/operation records match the corrected M65 canonical record |
| [Audit](../../../validation/schedule_candidate_audit.py) | One process for three methods; independent checks, preserved failures, per-group denominators and timing samples |

For the last non-idle target \(\ell\), B2 implements the already registered model:

\[
V_N(\ell)=0,\qquad
V_t(\ell)=\max_{a\in A_t}\{r_t(\ell,a)+V_{t+1}(f(\ell,a))\}.
\]

Idle gives zero reward and preserves \(\ell\). Observing target \(j\) gives its
known integer score minus the nonnegative change cost when \(\ell\) is a different
previous target; first acquisition is free. Only literal true eligibility with
a non-null score admits a target. Actions are ordered by canonical target ID,
then idle. A strict greater-than update retains the first maximizing action.
Backward induction supplies an optimal tail; selecting the smallest maximizing
action and its canonical optimal tail gives the lexicographically smallest
optimal full path. This model argument and the implementation evidence are
separate claims. No terminal snapshot is a selectable slot.

Bertsekas's [MIT 6.231 lecture notes, PDF pages 17 and 20–26](https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/dae6c8dca97f89b45bd0d7877a5433c9_MIT6_231F15_Notes.pdf)
provide background for backward induction and state augmentation (rechecked
2026-10-26 JST). They do not supply benchmark values or astronomical validation.
The objective and supplied-input constraints are project definitions. E0 is
algorithmically independent; the shared specification, common authorship and
possible common interpretation errors remain limitations. No separate human
scientific review is asserted.

B2 stores \((N+1)(M+1)\) value cells and \(N(M+1)\) policy cells, and considers
\((M+1)\sum_t |A_t|\) action values. This gives nominal
\(O(N(M+1)^2)\) work and \(O(N(M+1))\) storage, excluding input validation and
Python overhead. Across one call per development/control case the measured
counters total 13,306 action values, 4,649 state updates, 5,448 value cells and
4,649 policy cells. These are aggregate logical counters, not peak bytes or
portable wall-clock speedup measurements.

## Bounded development results

Controls are excluded from the following primary denominator of 216.

| Measure | B0 | B1 | B2 |
|---|---:|---:|---:|
| Zero objective regret | 164 | 200 | 216 |
| Positive objective regret | 52 | 16 | 0 |
| Mean objective regret | 7.782407 | 1.074074 | 0 |
| Median objective regret | 0 | 0 | 0 |
| Maximum objective regret | 156 | 59 | 0 |

| Paired primary comparison | Wins | Ties | Losses |
|---|---:|---:|---:|
| B1 versus B0 | 44 | 166 | 6 |
| B2 versus B0 | 52 | 164 | 0 |
| B2 versus B1 | 16 | 200 | 0 |

All 232 B2 canonical paths match E0 exactly. The
[canonical audit](../../../validation/results/schedule_candidate_reference_run.json)
retains all 696 method-case records, slot paths, gross score, changes, costs,
net score, exact/normalized regret, durations, block counts, feasibility,
operation counts and timing samples. It aggregates by family/split/cost with
explicit denominators and incomplete-pair counts. B1's six adverse cases remain;
for `P3-F3-N06-M03-R00-C20`, B0=576, B1=531 and B2=E0=590.
These correlated designed cases do not establish generalization, statistical
significance, forecast skill or calibrated scientific yield.

## Tests and failure sensitivity

[763 new tests](../../../tests/validation/test_schedule_candidate.py) passed locally.
Combined M64–M66 regression testing passed 1,314 tests and 1,004 subtests.
Parametrizations are software checks, not independent scientific experiments.
Coverage includes:

- Every development/control objective and exact canonical path, with input immutability.
- All 216 reserved IDs rejected before recurrence, including split/replicate relabelling.
- All 48 malformed variants from M64 rejected before recurrence.
- Consistent target-storage permutation on every development/control case and
  control-based UTC translation, appended idle, unusable-target removal and
  positive integer score/cost scaling.
- Ten analytic controls without using E0, including free first acquisition,
  optional idle, idle history, terminal exclusion and canonical ties.
- Eleven code mutants: erased idle history, omitted/doubled change cost, first
  acquisition charge, admitted unknown eligibility, missing-as-zero, reversed
  ties, nonzero terminal value, skipped first slot, discarded future value and
  idle-history loss during reconstruction. Every mutant causes a substantive
  solution defect detected on development inputs, rather than only a counter mismatch.
- Falsified objectives/paths/counters, nondeterminism and controlled timeout
  retention; later cases continue and failed denominators are retained.
- A fresh `python -S` subprocess proves B2 needs no science package, baseline or
  oracle imports. Its recurrence receives only the supplied case data.

The audit blocks sockets, subprocesses, live planner computation and E0 imports
while methods execute. B2 file opens are additionally blocked during every call.
These are reproducibility and accidental-access guards, not a security boundary
against maliciously rewritten code or fully relabelled input content.
The public reserved inputs are not a blind holdout. No trained model is involved.

## Freeze, access and reproduction

Source/config/tests/new workflow are committed at
`c2b09e0a1eb3983e4eab216398811ae9d9a252b2`, followed by the
[hash manifest](../../../validation/manifests/schedule_candidate_freeze_v1.json)
at `671b1b88504063842b5b625f88b56dbdc64a8047`. The canonical audit ran from that clean
checkpoint with Python 3.12.14, imported NumPy 2.5.4 and Astropy 8.0.2; both imported
versions agree with metadata lookup. Installed versions, OS, architecture,
source/input hashes, implementation/checkout/parent commits and commands are
recorded. UTC is used; ephemerides/EOP are unused and geometry is synthetic.

The [access record](../evidence/schedule_candidate_access_v1.json) discloses
pre-freeze development tests and post-freeze canonical execution. Every method
has one warmup and five timed calls: 4,176 method invocations per complete audit,
including 1,392 B2 invocations. All five samples, median and range are retained.
B0 includes actual scheduler injection/decoding; B1 includes its guard; B2 includes
its guard, tables and file-blocking context. No algorithm-speedup comparison or
wall-time acceptance threshold is claimed. The audit's ten-minute CI cap makes
a timeout incomplete, never accepted. Exact paths/metrics are deterministic;
timing and environment fields are deliberately run-dependent.

After installing the repository's development/validation dependencies:

```bash
python -m pytest -q tests/validation/test_schedule_candidate.py
python -m validation.schedule_candidate_audit --output /tmp/schedule_candidate_run.json
python docs/research/evidence/verify_schedule_candidate.py
python -m ruff check .
python -m pytest -q
```

The [offline Git history bundle](../../../validation/reference_generation/schedule_candidate_history_v1.bundle)
requires the M65 main-history baseline. An isolated checkout initially lacking
the source objects successfully recovered them from this bundle and replayed all
696 method records with identical outputs, metrics, counters and aggregates,
without GitHub/network access. After squash merge or branch deletion,
restore the source/freeze objects without GitHub access:

```bash
git bundle verify validation/reference_generation/schedule_candidate_history_v1.bundle
git fetch validation/reference_generation/schedule_candidate_history_v1.bundle refs/research/mission66-freeze
```

The retained M65 bundle provides its earlier source/freeze objects when its
historical documentary checker is run. Original M65 environment-reporting defects,
raw records and both prior bundles remain unchanged.

## CI and remaining gates

M65 froze `.github/workflows/quality-gate.yml`; it remains byte-identical and runs
the full test suite and all 30 existing audits/artifacts. The separate
[Schedule Candidate Validation workflow](../../../.github/workflows/schedule-candidate-validation.yml)
adds the B2 audit and artifact 31. Acceptance requires both workflows at the exact
final PR head; artifact receipt verification spans both run IDs. The new check is
not assumed to be a branch-protection requirement. Final CI/test counts and all
31 archive receipts are recorded in the PR before handoff.

P3-E03 has development correctness evidence for all three methods; complete
reserved correctness/comparison remains pending. P3-E04 remains incomplete.
P3-E05 observational calibration and P3-E06 integration/exit remain open. No
production source, previous scientific files, fixture thresholds or historical
expected failures are modified. M56's nine and M60's 17 historical failures remain.
X01 retains 18 unestablished requirements, six unknown components, 48 unqualified
clocks and 288 blocked / zero executed arrivals. Physical clock/site/arrival
bounds remain null; all five M62 exclusions and the 13/5/8 strict-transit categories
carry forward.

**Proposed Mission 67 — Frozen Evaluation-Reserved Scheduler Comparison.** After
M66 review/merge and a separately recorded execution configuration/access gate,
compare frozen B0/B1/B2 across the complete reserved inventory under the M63
protocol. Preserve development-only entry points and historical sources; use a
separate, explicitly scoped evaluation adapter. Freeze any adapter before first
reserved output, keep all failures, and label any repaired replay as exposed
regression. This remains a finite-model comparison, with no physical promotion
or Phase 3 exit. Mission 67 has not started.
