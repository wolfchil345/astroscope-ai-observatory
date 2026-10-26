# Mission 64 — Controlled Schedule Corpus and Independent Oracle

Mission 63's reviewed protocol now has a frozen, offline input and exhaustive
reference release. **All 432 primary cases and 16 separate controls are present;
no B0, B1 or B2 comparison has been executed.** Acceptance here concerns the
finite synthetic corpus and E0 reference, not an optimizer, observing yield,
forecast skill or physical astronomical accuracy.

The predecessor [PR #63](https://github.com/wolfchil345/astroscope-ai-observatory/pull/63)
merged at `c489863badae5d28e6ae05e3b5d2f65565a0b1aa`. Its
[post-merge CI receipt](../evidence/mission63_merge_ci_v1.json) verifies run
40283019178, 8,356 passed tests, 26 historical strict expected failures and all
28 downloaded artifact archives. The [M63 protocol](../phase_3_entry_protocol.md)
and its [machine-readable specification](../protocols/observation_optimisation_v1.json)
remain unchanged as historical preregistration records. Their original
"not executed" and "review pending" fields describe Mission 63's snapshot.
The [M64 release ledger](../evidence/schedule_corpus_release_v1.json) records the
later execution and approval state; M64 itself awaits review and merge.

## Frozen release and independence

| Artifact | Purpose |
|---|---|
| [Input release](../../../validation/fixtures/schedule_corpus_v1.json) | Explicit scores, eligibility, IDs, times, costs, splits and provenance for every input |
| [Reference release](../../../validation/fixtures/schedule_exhaustive_v1.json) | E0 canonical optimum path, gross/net score, change count and enumeration counts for all 448 cases |
| [Release manifest](../../../validation/manifests/schedule_corpus_v1.json) | Source commit, SHA-256 digests, exact denominators, resource cap and exclusions |
| [Generator and contract](../../../validation/schedule_corpus.py) | Deterministic construction, strict schema, canonical column ordering and independent path scoring |
| [Independent E0 module](../../../validation/reference_generation/schedule_exhaustive.py) | Standard-library Cartesian enumeration with direct raw-input traversal |
| [Checks](../../../validation/schedule_corpus_checks.py) | Separate formula transcription, hand-derived controls, metamorphic and mutation checks |
| [Canonical audit](../../../validation/results/schedule_corpus_reference_run.json) | Clean-checkout replay, actual environment, per-case verification and retained scope limits |
| [Access record](../evidence/schedule_corpus_access_v1.json) | Public input/reference exposure history, with zero candidate-output access |
| [Source/release history bundle](../../../validation/reference_generation/schedule_release_history_v1.bundle) | Offline Git objects for both freeze commits, retained even after squash merge or branch deletion |

Source, tests and execution configuration were committed first at
`ef71cec709a775e76f2c21bcbdb4aa156b1fd47c`. Inputs and E0 outputs were then
generated and committed separately at `a9dc0b9496d7c7d940fdbfa078c159d9d70e963b`.
The canonical audit ran from that clean release checkout. No primary oracle
results existed when the source checkpoint was made. Public input formulas,
generated matrices and development-control results were inspected during
implementation; that exposure is explicitly recorded.

E0 imports only `itertools.product`; it imports no AstroScope, numerical library,
generator, verifier, transition helper or candidate function. It enumerates the
entire Cartesian space in canonical action order and retains the first maximizing
path. It rejects infeasible paths through direct traversal; it performs no DP,
branch pruning or memoized optimization. Lexicographic enumeration plus strict
improvement preserves the canonical tie rule. The all-idle path is always feasible.

The separate verifier computes changes by removing idle actions and comparing
adjacent remaining IDs. Thus it does not reuse E0's running-last-target loop.
It checks score/cost arithmetic and feasibility, while full E0 regeneration and
analytic controls establish the bounded optimum reference. Feasibility counts
are also checked against the product of each slot's usable-action count plus idle.
The generator is checked against a separate transcription using hexadecimal
digest prefixes. These are distinct implementations of one written model,
**not independent human review or external observational calibration**.

## Executed coverage

| Check | Executed result | Interpretation |
|---|---:|---|
| Primary profile inputs | 432 | 144 core matrices × three cost profiles |
| Development / evaluation-reserved | 216 / 216 | Public, not blind; no candidate outputs generated |
| Per family F1–F6 | 72 each | Fixed designed corpus, not population sampling |
| Independent formula checks | 432 | Every primary score and eligibility cell checked |
| Analytic boundary/control references | 16 | Exact integer objective and canonical path agreement |
| Enumerated primary paths | 20,645,496 | Includes infeasible paths; no early stopping |
| Enumerated control paths | 313 | Separate from primary denominator |
| Total enumerated / feasible paths | 20,645,809 / 11,209,126 | Operation counts, not speed or scientific-yield measurements |
| Invalid input classes / concrete variants | 16 / 48 | All rejected without coercing booleans or missing values |
| Metamorphic checks | 59 | All five preregistered relation types exercised |
| Fault checks | 9 | Seven mutated oracle implementations; two invalid returned-path checks |
| New automated test functions | 21 | Many contain case-wise subchecks; not 21 independent science experiments |
| Input and reference regeneration | Byte-identical | Tested in a fresh `-I -S` interpreter with no installed packages |
| B0 / B1 / B2 evaluations | 0 / 0 / 0 | Method-comparison acceptance remains unset |

Each reference case visits exactly \((M+1)^N\) paths, at most 262,144.
The fixed cap is N≤9 and M≤3; the new CI step has a ten-minute timeout.
Missing output, an exception or a timeout is a failed/incomplete audit, never
permission to drop a case. The protocol's one-warmup/five-repeat timing policy
remains for future method comparisons; no comparative timing was performed here.

## Analytic controls and fault sensitivity

Let A=`target_00`, B=`target_01`, I=`IDLE`. Idle retains the last observed target;
first acquisition is free. These hand-derived expectations were fixed in source
before primary E0 generation.

| Control | Expected canonical path | Net points | Reason |
|---|---|---:|---|
| C01 empty targets | I | 0 | Only idle exists |
| C02 known zero | A | 0 | Target precedes idle on a zero tie |
| C03 missing scores | III | 0 | Missing is unusable, not zero |
| C04 false eligibility | III | 0 | All observations forbidden |
| C05 unknown eligibility | III | 0 | Unknown is not literal true |
| C06 exact ties | AAA | 210 | Equal scores, no changes, earliest target |
| C07 retained M55 example | AAA | 269 | Switching cannot compensate its 20-point cost |
| C08 idle retains history | AIB | 80 | 50+50−20 |
| C09 same target after idle | AIA | 100 | No change between observations |
| C10 free first acquisition | A | 1 | No initial charge |
| C11 zero-cost alternation | ABA | 270 | Sum of independent slot maxima |
| C12 optional idle | AIA | 200 | Middle B gains 1 but would charge two changes |
| C13 endpoint excluded | A | 10 | Numeric problem contains only the one real slot |
| C14 one-target gaps | AIA | 100 | Middle slot unusable |
| C15 UTC date crossing | BAB | 170 | BAB and BBB tie; A wins the second-slot tie |
| C16 score boundaries | BAA | 195 | 100+100−5; final known zero keeps A |

C07 reuses the published M55 input and is a development control. It is not new
held-out evidence. C13 preserves its high-score endpoint override separately for
the future real-scheduler adapter. **M64 does not test production endpoint
sampling or block decoding.** Its last two fault checks reject an extra terminal
action and a missing slot; UTC half-open membership is checked on the input grid.
Actual B0 sentinel, overlap and block-continuity tests remain required later.

The seven executed oracle mutants erase idle history, omit or double change cost,
charge first acquisition, admit unknown eligibility, convert missing score to
known zero, or choose the wrong tied optimum. Each fails its preassigned analytic
control. The mutation machinery reports its mechanism rather than claiming a
production regression test. The independent scorer also retains negative net
values for valid paths, although the optimal all-idle lower bound is zero.

## Reproduction and provenance

From a complete repository checkout, Python 3.12 and its standard library suffice
for M64's generator, reference and audit. The full project suite still requires
the existing development/validation dependencies.

After a squash merge or branch deletion, import the bundled freeze history once
if its commits are absent. This local fetch uses no network; the complete main
history supplies the M63 prerequisite commit. Verify the bundle hash against the
release ledger before import:

```bash
git bundle verify validation/reference_generation/schedule_release_history_v1.bundle
git fetch validation/reference_generation/schedule_release_history_v1.bundle refs/research/mission64-release
```

```bash
python -m unittest discover -s tests/validation -p test_schedule_corpus.py -v
python -m validation.schedule_corpus_audit --output /tmp/schedule_corpus_audit.json
python docs/research/evidence/verify_schedule_corpus_release.py
python -m ruff check .
python -m pytest -q
```

The fresh-interpreter test uses `-I -S`, so site packages are unavailable.
During computation, sockets, name resolution, subprocess execution and imports
of production/scientific libraries are blocked. The guard itself is tested.
Git provenance collection happens before the computation block; it is local and
does not fetch anything. Method-source websites are never downloaded at runtime.
JSON parsing rejects duplicate keys, NaN and infinity; serialization is UTF-8,
sorted keys, two-space indentation, ASCII escapes and exactly one final newline.

The canonical record gives implementation and checkout/parent commits, dirty
state, Python/platform/architecture, installed packages, source/input hashes,
commands and split IDs. UTC is explicit. Geometry, ephemerides and EOP are marked
not applicable to this synthetic model. No production planner is imported, so
the later B0 adapter will need its own real dependency-environment record.

To reconstruct the *initial generation* rather than replay an existing release,
use a separate clean checkout of the source checkpoint and run:

```bash
python -m validation.schedule_corpus_audit \
  --freeze-source-commit ef71cec709a775e76f2c21bcbdb4aa156b1fd47c
```

That command refuses to overwrite an existing versioned release. Subsequent
repairs must retain exposed outputs and produce an explicitly versioned release,
source and access record. The access log describes the local implementation,
generation, test and canonical-replay stages; each later CI audit is an additional
public E0 replay recorded by its run/head/artifact. It is not a claim of a blind
holdout. Candidate evaluation-reserved outputs must remain unopened until their
own source/configuration freeze; none exist in this mission.

## Roadmap and remaining claims

| Gate | After Mission 64 implementation |
|---|---|
| P3-E01 | M63 protocol approved through merge |
| P3-E02 | Frozen corpus/E0 implemented and checked; M64 review/merge pending |
| P3-E03 | B0 adapter and B1/B2 implementations/acceptance pending |
| P3-E04 | Comparative evaluation and metrics pending |
| P3-E05 | Observational calibration remains deferred with its evidence prerequisite |
| P3-E06 | Production integration and Phase 3 exit not approved |

Proposed **Mission 65 — Controlled Scheduler Baselines and Adapter Validation**:
after this release is reviewed and merged, implement the validation-only B0
adapter and B1 policy, test development controls and the actual scheduler's
endpoint/block behavior, and freeze their source/configuration before any
evaluation-reserved candidate-output access. B2 and comparative evaluation remain
separate subsequent work; no production optimization is authorized by this release.

All M62 limited-scope exclusions remain. X01 still has 18 unestablished covariance
requirements, six unknown physical components, 48 unqualified site clocks and
288 blocked arrivals with zero executed. Physical bounds remain null. The strict
transit coverage remains 13 implemented boundary / five partial / eight deferred.
M56's nine and M60's 17 failures remain historical evidence, with all 26 strict
xfails preserved. No existing source, scientific fixture, threshold, result or
test was edited. CI retains all old steps and adds the M64 audit as artifact 29.

## Primary method references

- Python Software Foundation, Python 3.12 [`itertools.product`](https://docs.python.org/3.12/library/itertools.html#itertools.product): Cartesian enumeration and ordering.
- Python Software Foundation, Python 3.12 [`hashlib`](https://docs.python.org/3.12/library/hashlib.html): SHA-256 byte and hexadecimal digest interfaces.
- M63's [Bertsekas method citation and finite-model argument](../phase_3_entry_protocol.md#verification-and-method-sources) remain background for the future DP candidate; no DP was implemented here.

The two Python primary references were checked on 2026-10-26 (JST). Their role is
API/method documentation, not external measured schedule truth. They are linked,
not redistributed. Synthetic inputs, reference outputs and project code are MIT
licensed under the repository's [licence](../../../LICENSE).
