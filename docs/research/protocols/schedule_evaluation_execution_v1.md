# Mission 67 — Frozen Scheduler Evaluation Execution Plan v1

Status at this document's source checkpoint: prepared before any reserved
candidate output. This is an execution specification, not a result statement.
User authorization: the project owner's explicit “Start mission 67” request on
2026-10-26 JST, following the reported and GitHub-verified Mission 66 merge.
The [M63 protocol](../phase_3_entry_protocol.md) and its immutable
[JSON specification](observation_optimisation_v1.json) remain authoritative.

## Prerequisites and execution scope

Before the first reserved method call, verify Mission 66 merge
`7f9f4d0276fc998224f9ba1d0e03ce24f0551b20`, both post-merge workflows and all 31
artifact archives. Commit the adapter, runner, tests, this plan and configuration;
then commit their hash manifest separately. Execute from the clean manifest
checkpoint. Preserve source history in an offline Git bundle before publication.

The complete fixed inventory is 216 primary development cases, 16 development
controls, then 216 evaluation-reserved cases, in existing fixture order within
each group. All three methods run serially in the same process and machine.
This produces 1,344 method-case rows: 696 development/control and 648 reserved.
Each row has one warmup and five measured calls, for 8,064 method invocations;
3,888 of these are reserved. Controls are excluded from primary denominators.
No seed, case, cost profile, score, eligibility mask or threshold is changed.

## Adapter and exposure boundary

The adapter reuses the exact frozen B0/B1/B2 Python code objects with private
copies of their global mappings. Only the development-input guard is replaced
by a guard requiring exact frozen case bytes and an active verified session for
reserved cases. B0's block decoder receives that same private guard. Algorithms,
production scheduler, independent checks and original module guards are unchanged.
B0 still calls the actual strict production scheduler through its existing
controlled planner boundary. This is serial research execution, not a new
production entry point or a claim of thread-safe deployment.

Pre-freeze tests compute development outputs only. Reserved inputs may be read
and rejected, or admitted by an input-only unit test with a mocked evidence tree;
no reserved method output is computed in tests. Such fixtures test mechanics and
are not scientific authorization. Real reserved execution requires all frozen
file hashes, the accepted merge receipt and a clean checkout. These are accidental
access/reproducibility checks, not security against rewritten source or manifests.

All development outputs/metrics/counters must reproduce M66 before reserved
computation. If development preflight fails, keep all remaining reserved rows as
not executed; the audit is incomplete. If a reserved method fails or times out,
retain its error and completed outputs/timings, and attempt the other declared
methods/cases. Never reduce the denominator or substitute a case.

## Acceptance and reporting

B0/B1 must remain feasible and follow their frozen policies; positive regret and
B1 losses are results. B2 must have exact integer objective equality with E0,
zero regret and exact canonical path equality for every declared case/control.
No float tolerance or minimum improvement is introduced. Frozen independent
path arithmetic and exhaustive E0 remain separate from candidate computation.
The access-journal checker imports no candidate and reconciles every invocation
identity and output digest against the complete result record.

Retain all paths, gross score, changes, cost, net objective, regret and regret
normalized by 100N, durations, blocks, feasibility, counters, five timing samples,
median and range. Report family/split/cost denominators, failures, mean/median/max
regret and paired win/tie/loss counts (B1–B0, B2–B0, B2–B1). Timing includes adapter,
input hashing, journaling and guard overheads, which differ by method. There is
no algorithm-speedup claim or portable runtime acceptance threshold. The CI audit
cap is ten minutes; timeout means incomplete.

## Durable records and replay labels

The first canonical run uses `first_frozen_evaluation`; its JSON record and
append-only JSONL journal are retained verbatim. Before each method invocation,
flush an access event with UTC timestamp, sequential invocation ID, case/split,
method and repetition. Append completion/output digest or error afterward.
An initial incomplete JSON record and partial journal survive interruption.
Refuse to overwrite existing output or journal paths.

After first exposure, all offline and CI reruns use `exposed_regression_replay`.
The existing first record prevents selecting the first-run label at the published
revision. The clean historical checkpoint can be reconstructed; replay there must
still be explicitly labelled exposed. These public inputs are not a blind holdout.
No model is trained. Any repair after reserved exposure requires new versioned
source/results, retained original failures, and exposed-regression labels. A new
confirmatory study needs a separately reviewed input release.

## Preserved boundaries

Keep both prior workflows byte-identical; add a separate evaluation workflow and
32nd artifact containing result plus journal. Handoff requires all three workflows
at the same final head and all 32 archives verified. Branch protection is unchanged.
M65/M66 development records remain historical, including their zero-reserved-output
statements at those checkpoints and M65's environment provenance correction.

This is a finite supplied-input comparison. It does not qualify observation
utility, catalogue truth, forecast calibration, physical timing or hardware
operation. X01 remains blocked with null physical bounds and 288 blocked / zero
executed arrivals; all M62 exclusions and historical failures remain. Production
integration and Phase 3 exit require separate evidence and review.
