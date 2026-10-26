# Mission 62 — Phase 2 Exit Readiness and Provenance Disposition

**Decision: LIMITED-SCOPE EXIT PROPOSED; owner review is pending.** The accumulated
evidence supports closing the bounded scientific-validation programme for the
supplied-input claims below. It does **not** support an unrestricted scientific,
operational or physical timing qualification. Phase 2 remains active in this
pre-approval record, and Phase 3 has not started.

Merging this mission's PR after its final-head checks approves only this explicit
scope and its retained restrictions. The next mission must verify that merge and
record the accepted transition before beginning a separately requested Phase 3
entry protocol. A green CI run alone is not the exit decision.

## Governing evidence and baseline

The original eight areas and nine entry conditions in the
[Phase 1 exit audit](phase_1_exit_audit.md), the
[v0.2.0 research baseline](v0.2.0_research_baseline.md), and the E01–E08 requirements
in the [Mission 51 audit](phase_2_coverage_audit.md#phase-2-exit-gates) govern this
review. The [Mission 59 reconciliation](phase_2_reconciliation.md) supplies the
historical crosswalk; Missions 60–61 address its remaining catalogue dossier.
Original requirements, references, tolerances, failures and canonical records
are retained. No new numerical experiment or independent scientific reference is
created by this documentary review.

The inspected baseline is Mission 61's merged commit
`ef21bc7cbec61a0f8b9b389e88683368dfcd42ed`, from PR #61.
[Post-merge Quality Gate 40256448851](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/40256448851)
passed **8,356 tests with 26 historical strict expected failures**, in 268.46
seconds. All **28 artifact archives** were downloaded: names, head identities,
expiry, ZIP digests, primary JSON identities, available path-labelled file hashes,
acceptance/audit status and guarded claims were checked. This is broader archive
inspection than the five-archive sample used for Mission 61's final handoff.

The [merge-CI receipt](evidence/mission61_merge_ci_v1.json) records every artifact
ID and archive/record digest. It also preserves the job-log digest and selected
environment evidence: CPython 3.12.15, Ubuntu 24.04 runner image
`20261012.334.1`, Linux x86_64, Astropy 8.0.2, NumPy 2.5.4 and Plotly 7.1.0.
The installation log excerpt supplies additional package versions. These are
**current CI facts**, not replacements for missing historical environment fields.
The downloaded M45 record reports 64 coefficient-guard significand bits.

The [exit-readiness ledger](evidence/phase_2_exit_readiness_v1.json) pins 182
baseline evidence paths, 28 experiment mappings, eight original areas, eight
gates, C01–C08 and all TC01–TC26 scenarios. Source, test, validation, workflow and
dependency-definition trees are unchanged by this mission. Hashes establish
identity; original independent comparisons establish the bounded scientific
claims. Neither counts nor hashes measure a percentage of scientific completeness.

## Scope proposed for acceptance

| Original area | Accepted bounded evidence | Claims excluded from this exit |
|---|---|---|
| P2-01 Observer/time | Pinned civil-time, fold/gap, interval/grid and fixed-site time arithmetic in M25–34 | Physical observer-arrival clock qualification; future timezone correctness beyond the recorded data |
| P2-02 Coordinates | M33 fixed supplied ICRS/WGS84 unrefracted comparisons; M61's separately enforced small-field display domain | Stellar proper-motion/distance/refraction accuracy; general spherical-chart precision |
| P2-03 Visibility | M33/34 geometry and M54's 48 sampled-window cases with boundary/sensitivity disclosures | Continuous observing coverage or unresolved transit-arrival conversion |
| P2-04 Solar System | M34 Sun/Moon/twilight corpus; M53's 623 cases for seven enabled planets in the recorded 2024 domain | Universal positional accuracy, physical covariance, or a native rise/set API |
| P2-05 Telescope/imaging | M52's 307 independent ideal-geometry cases and declared heuristics | Measured optics, seeing, detector or equipment calibration |
| P2-06 Planning heuristics | M32 interval semantics and M55's 355 controls, including adversarial schedules and trade-offs | Optimality, forecast skill, observing success or utility calibration |
| P2-07 Transit calculations | M35 bounded scalar arithmetic; M37's strict metadata/rejection boundary; M54 sampling on explicit observing-time inputs; M61 nominal catalogue/model arithmetic | Qualified strict observer-arrival UTC/schedules/ranking/calendar exports, a strict catalogue adapter, or physical transit fitting |
| P2-08 Light curves | M56–58's frozen recovery/null/noise/alias/gap/published-data campaign; current M58 passes 252 trials and 10 required recoveries | Discovery confirmation, universal false-alarm calibration or physical timing qualification |

Catalogue C02/C03/C05/C06/C07 now have M60 characterization and M61 correction
evidence: **1,252 current acceptance cases pass**, including deliberate rejection
and unknown outcomes. They are not 1,252 observational accuracy measurements.
G60-01–G60-07 and G59-01 have bounded closure through Mission 61's merge.
M61's assumptions, exterior-orbit/radius constraints and chart domain remain part
of the accepted claim. Its geometric chart bound is not an astrometric uncertainty.

The 26 xfails are intentional historical evidence: nine M56 BLS failures and
17 M60 catalogue failures. M57's 22 fast-bound violations remain a historical
mechanism result. The current M58 and M61 runners have separate passing acceptance;
the older audit modes cannot turn their original failures into scientific passes.
W01–W05 therefore have bounded dossiers; W06's remaining issues receive the
explicit dispositions below rather than being silently erased.

## G59-02: historical provenance disposition

**Proposed disposition: accept current frozen-fixture replay within scope; retain
the limitations on original-environment reconstruction and raw regeneration.**

All **28 recorded implementation commit objects were recovered and inspected**;
15 were fetched because they were absent from the local checkout. The original
M59 finding that commits were outside the merged ancestry did not establish
remote loss. The [historical source receipt](evidence/phase_2_historical_provenance_v1.json)
now records each commit/tree, original runner hash, static absolute-import closure,
and **185 matching recorded file-hash checks with zero mismatches**. This count
includes path-labelled hashes and scalar hashes whose file mapping was established;
it is not a claim that every historical datum had a checksum field.

All original runners except M56, M57 and M60 match the current runner bytes.
Those three changes are the reviewed routing to retained historical code;
current corrected production is assessed independently in M58/M61. Fetching source
does not execute it, recreate its operating system, preserve remote refs forever,
or authenticate an originally unrecorded environment.

| Provenance issue | Evidence and materiality | Disposition for this proposal |
|---|---|---|
| Fourteen canonical OS fields absent: M38–50 and M57 | Original records omit OS; M45's report supplies Linux/precision context but not a complete historical OS fingerprint | Preserve the missing-field labels; no universal original-environment recreation claim |
| Thirteen architecture entries absent: M38–50 | Source recovery cannot reconstruct hardware/ABI; current CI supplies its own platform evidence | Current Linux replay accepted; historical architecture remains unestablished |
| M39/M40/M41 package inventories absent | Their audit replay paths use the standard library only; external reference generation has separate locks and source evidence | Package inventory is not applicable to those audit computations; do not extend that exemption to reference generation |
| M49/M50 package inventories absent | Their static import closures include Astropy/NumPy through reused validators, despite much of the arithmetic being Decimal | Keep original versions unestablished; same-job current CI evidence supplements current replay only |
| Dedicated randomness fields absent in some records | Original frozen fixtures, generators and policy/settings identify deterministic or seeded choices | Link those original choices; do not invent historical seeds |
| M45 extended precision | Production audit requires at least 64 significand guard bits and rejects binary64-only longdouble | Enforced platform condition; no cross-platform-equivalence claim |
| External raw reference inputs | Frozen derived-data replay is available; DE421/DE440t/INPOP and reference tools can require separate acquisition | No fully vendored raw-regeneration claim or new redistribution permission |

These restrictions are material to broader reproducibility claims. They do not
invalidate a demonstrated current replay or supply missing physical evidence.
E04 is qualified only for the named current frozen-fixture workflow. It is **not**
an unconditional pass on every historical provenance entry condition.
The static import inspection does not trace dynamic imports or create a lockfile.
Raw-reference regeneration still requires each dossier's pinned sources, rights,
checksums and isolated tools; none is regenerated or downloaded in this mission.
The retained Kepler product keeps its original MAST attribution/terms, not an
assumed repository-code licence.

M31 remains a supplemental static provider-contract summary without full execution
metadata; its source/manifest and tests support the limited contract claim. M37's
coverage JSON is a design/implementation crosswalk, not a physical conversion
result. Neither is counted as an additional benchmark artifact.

## G59-03: catalogue and static-input disposition

**Proposed disposition: accept transport/presentation and supplied-input arithmetic;
exclude maintained-source accuracy, archive completeness and strict promotion.**

| Path | What remains enabled | Limit and reopening trigger |
|---|---|---|
| C01 Gaia TAP/CSV | Row-limited queries, parsing and numerical calculations on supplied values | No retained raw-response/retrieval envelope or maintained catalogue snapshot; freeze a provenance-bearing input before research reuse |
| C04 Exoplanet composite TAP/CSV | Parsing, nominal calculations and export of `calculation_convention` | Marker describes an assumption, not source qualification; mass provenance, covariance and mixed references remain unresolved; no strict ephemeris adapter |
| C08 Static coordinates/sizes and presentation | Curated presets and calculations using those inputs | No maintained epoch/source accuracy or survey completeness; replace or freeze/qualify inputs before quantitative optimisation claims |

These are **documentary research-scope restrictions**, not technical access blocks
on the explorers. Existing educational notes do not certify input accuracy.
Technical rejection is separately established for unsupported local-sky domains,
invalid catalogue numerics, unsupported physical geometry and strict unresolved
timing consumers. Phase 7 may improve interoperability, but any Phase 3 benchmark
must first freeze and qualify its own input semantics. Live archive output cannot
be treated as benchmark truth merely because it parses or produces a plot.

## X01 and contract exclusions

X01 remains blocked, neither closed nor automatically deferred: **18** covariance
requirements unestablished, **six** unknown physical components, **48** unqualified
site clocks and **288** blocked combined arrivals (**240** solar-eligible,
**48** excluded), with **zero executed**. Physical geocentric-clock, site-clock
and arrival bounds remain null; physical covariance is neither acquired nor
propagated. Tiny solver residuals, synthetic covariances or cross-model differences
cannot replace this evidence.

All 26 strict-transit scenarios retain their original categories: **13 implemented
boundary, five partial boundary and eight deferred**. These are implementation
categories, not physically qualified observing cases. The production timing core
remains unchanged since M37. Source and tests retain rejection in visibility,
ranking, scheduling and exports; coordinate JSON retains unknown states and
`observing_eligible=false`. Legacy approximate workflows remain separate and
are not promoted to a strict physical timing capability by this proposal.

The five excluded-claim entries L62-01–L62-05 in the ledger assign owners and
reopening triggers. No provider contact, private-data acquisition, hardware control,
new adapter or Phase 3 implementation is authorized by this audit.

## E01–E08 decision matrix

| Gate | Verdict for the proposed limited scope | Remaining condition |
|---|---|---|
| E01 Coverage | Qualified inventory | Owner accepts the explicit eight-area/C01–C08 scope |
| E02 Independent references | Qualified within original bounded domains | X01 and broader observational calibration remain excluded, not passed |
| E03 Robustness/integration | Qualified within frozen cases | Retain failure history and domain restrictions; no universal robustness claim |
| E04 Provenance/replay | Qualified for current frozen-fixture replay only | Original environment/raw-regeneration limitations stay explicit |
| E05 Claims/uncertainty | Qualified with specified exclusions | Distinguish executable guards from documentary claim restrictions |
| E06 Contract traceability | Qualified with 13/5/8 deferred-boundary disposition | No strict observing promotion or catalogue adapter |
| E07 Software acceptance | Baseline passed; final Mission 62 head required | Full CI, lint and 28-artifact verification recorded in the PR before handoff |
| E08 Reviewed exit | **Pending owner review** | Merge records acceptance of this limited scope, not an unrestricted qualification |

An unrestricted Phase 2 exit is **not supported**. This proposal is useful because
Phase 3's controlled comparison of observation-planning methods does not require
claiming physical observer-arrival precision or validated live catalogue inputs.
Any future method that reaches an excluded capability must reopen its gate first.

## Conditional Phase 3 entry boundary

After explicit scope approval, proposed **Mission 63 — Phase 3 Entry Protocol and
Observation-Optimisation Baseline Definition** should freeze the research question,
controlled scenarios, input provenance, resource/visibility constraints, objective
functions, baseline methods, evaluation metrics and held-out evaluation policy.
Use explicit observing-time inputs and report only measured outcomes. Sensitivity,
adversarial cases, missing information and uncertainty must remain visible.

It must not enable strict arrival conversion, infer truth from mutable catalogues,
claim calibrated observing success/optimality without evidence, rewrite Phase 2
references to favour a method, or start unrelated later-phase features. Phase 3
is still planned and Mission 63 is not started by this PR.

## Documentary verification and offline inspection

The accompanying checker validates baseline hashes, protected trees, 28 receipt
mappings, original-source hashes, gate/scenario coverage, retained unknowns and
the pre-approval decision boundary. Its negative controls reject altered hashes,
missing evidence/scenarios, unknown-to-zero changes and an unauthorized exit flag.
These are documentary integrity checks, not a new numerical benchmark or an
additional scientific test count. Local Markdown targets and Ruff are checked.

```bash
python docs/research/evidence/verify_phase_2_exit_readiness.py
python docs/research/evidence/verify_phase_2_exit_readiness.py --history
```

The first command checks the merged-baseline evidence available in an ordinary
full repository checkout. `--history` additionally requires the recorded historical
commit objects. Fetch them by their recorded SHA from `origin` before disconnecting;
the checker itself makes no network calls. A missing local object is reported as
missing evidence, never as remote data loss or a successful verification.

The existing 28 validation runners and commands are indexed in the ledger; their
offline behavior and reference-generation prerequisites remain in their original
dossiers. There is no new scientific test, artifact, production change or threshold
revision in Mission 62. Final-head acceptance and downloaded-archive receipts are
recorded in its PR rather than substituted with this baseline's successful run.
