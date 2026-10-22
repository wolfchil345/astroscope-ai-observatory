# Mission 51 — Phase 2 Coverage and Exit-Criteria Audit

## Decision

**Phase 2 remains active; this is a coverage audit, not a Phase 2 exit approval.**
The original eight scientific areas have uneven evidence. Civil-time semantics,
fixed-direction coordinates, Sun/Moon geometry and scalar transit arithmetic
have bounded independent benchmarks. Telescope/imaging and light-curve analysis
have useful analytic or synthetic tests but lack the broader validation dossiers
required by the original scope. Physical observer-arrival qualification remains
blocked. Passing regression tests does not change these findings.

Mission 50 merged through [PR #50](https://github.com/wolfchil345/astroscope-ai-observatory/pull/50)
at `4aae68b9035c6cbf7d4ad36d9c1f88ad358d33ed`.
Its post-merge [Quality Gate 39669626225](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39669626225)
passed and retained 19 unexpired artifacts belonging to that commit. This is
the audited baseline. Phases 0 and 1 remain complete; Phases 3–8 remain planned.

## Method and evidence boundary

The governing scope is the eight-row **Phase 2 Readiness** table and nine
**Phase 2 Entry Conditions** in the [Phase 1 exit audit](phase_1_exit_audit.md),
together with the [v0.2.0 validation expectations](v0.2.0_research_baseline.md#validation-expectations-for-future-phases).
The historical statements in those documents describe their own baselines;
they are not rewritten as current execution results.

This audit reads production interfaces, relevant tests, validation reports,
manifest/result inventories and CI configuration. The
[evidence ledger](evidence/phase_2_coverage_audit_v1.json) records source paths
and SHA-256 values at the audited commit, eight coverage rows, exit gates,
work-package dependencies and the baseline artifact inventory. Hashes establish
which evidence was inspected; they do not establish scientific correctness.
Repository reports are internal evidence. Their independent numerical sources
remain those identified in each original experiment; this audit creates no new
independent reference and makes no new numerical accuracy measurement.

Evidence is classified by claim, not by test count:

- **Bounded reference evidence:** an existing independent comparison supports
  its recorded inputs, conventions, tolerances and exclusions.
- **Mixed coverage:** bounded reference evidence covers some of the original
  requirement; remaining claims have only controls or no qualifying dossier.
- **Analytic/synthetic controls:** useful formula, recovery or regression tests
  exist, but do not constitute a complete scientific validation campaign.
- **External qualification blocked:** necessary applicable physical evidence
  is unestablished; a numerical surrogate cannot close the gate.

The eight rows overlap. Airmass, for example, is already checked in Mission 33
and is credited in both coordinates and visibility. Rows, tests and artifacts
must not be added together as independent measures of scientific completeness.
No percentage complete or fixed number of remaining missions is inferred.

## Coverage against the original scope

| ID / original area | Evidence already established | Remaining boundary / work |
|---|---|---|
| P2-01 Observer and time handling | Missions 25–27: pinned-IANA civil-time conversion, folds/gaps and strict rejection. Missions 28–32: interval policy, log/weather contracts and UTC schedule semantics. Mission 33: bounded JD/MJD, sidereal time and site coordinates. | Bounded reference evidence for those domains. Physical time/arrival extensions remain X01; original benchmark scope and historical timezone data must stay explicit. W06 reconciles applicability/provenance rather than repeating the benchmarks. |
| P2-02 Coordinate conversion | Mission 33: 768 astronomical cases and 13 rejection contracts, independent Skyfield/DE421 reference, fixed ICRS directions, WGS84, pinned IERS and unrefracted apparent AltAz. | Bounded reference evidence. Proper motion, finite stellar distance and physical atmospheric refraction are excluded. Preserve zenith exclusions and horizon-indeterminate cases. W06 records these limits; extending them is not required merely to rerun a completed benchmark. |
| P2-03 Visibility | Mission 33 already covers horizon classification and secant airmass, including low-altitude limits. Mission 34 adds solar darkness and Sun/Moon geometry. Unit tests exercise visibility summaries and input rejection. | Mixed coverage: end-to-end sampled observing windows, boundary membership and sampling sensitivity need W03. Unrefracted geometry is the declared policy; no atmospheric accuracy claim is established. |
| P2-04 Solar System positions | Mission 34: 354 snapshots, 120 validation-derived event windows and 188 crossings for Sun/Moon and twilight controls. | Mixed coverage: production also supports Mercury, Venus, Mars, Jupiter, Saturn, Uranus and Neptune. Existing Jupiter range/Venus-format tests do not establish planetary positional accuracy. W02 covers the seven enabled planets and their returned quantities. Native rise/set APIs do not exist; validation-derived roots must not be advertised as a production capability. |
| P2-05 Telescope and imaging | Tests check 130/650-mm telescope examples, accessory scaling, sensor dimensions, atan field geometry, image scale, sampling labels and mosaics. | Analytic controls, not absent testing. W01 supplies a frozen independent reference dossier and distinguishes ideal geometry from empirical magnification/sampling/framing heuristics. No measured optical performance is established. |
| P2-06 Planner and schedule heuristics | Mission 32 independently validates interval/grid/occupancy semantics. Planner/ranking tests check score ranges, monotonic behavior and deterministic ordering; schedule tests characterize greedy selection. Mission 31 validates weather timestamps. | Mixed coverage: W04 adds systematic weight, sampling and missing-input sensitivity and adversarial schedules. Forecast skill, observing success and optimality remain uncalibrated; observational calibration/optimisation belongs to Phase 3. |
| P2-07 Transit calculations | Mission 35: independent Decimal scalar ephemeris arithmetic and disclosed boundary cases. Missions 36–37: strict metadata, covariance semantics and rejection of observing/export promotion. Missions 38–50: research conversion, error-budget and numerical response evidence with explicit failures/unknowns. | Mixed coverage plus X01. W03 addresses visibility/sampling only with explicit observing-time inputs; it cannot enable unresolved strict predictions. W06 reconciles the 26 Mission 36 scenarios (Mission 37 reports 13 implemented-boundary, 5 partial, 8 deferred) against later research without counting research-only code as a production adapter. |
| P2-08 Light-curve analysis | Deterministic sinusoid Lomb–Scargle recovery, box-transit BLS recovery with sinusoidal contaminants, weighting, detrending, phase folding, diagnostics and import/export tests exist. | Analytic/synthetic controls. W05 requires versioned synthetic and published-data campaigns for nulls, aliases, gaps, red noise, false positives and recovery after preprocessing. A false-alarm probability constrained to [0,1] is not empirical false-positive calibration. Time labels/units need explicit validation; the default BJD_TDB metadata string is not proof of conversion. |

Direct evidence entry points are linked in the ledger. In particular, the
[coordinate report](validation/celestial_coordinate_validation.md),
[solar/lunar report](validation/solar_lunar_twilight_validation.md),
[schedule interval report](validation/schedule_interval_validation.md),
[transit arithmetic report](validation/transit_ephemeris_validation.md) and
[strict timing boundary report](validation/strict_transit_timing_boundary.md)
must be read with their exclusions. Current tests include
[optics](../../tests/test_telescope.py), [imaging](../../tests/test_imaging.py),
[planetary smoke checks](../../tests/test_solar_system.py),
[transit visibility](../../tests/test_transit_visibility.py),
[period recovery](../../tests/test_light_curve_period.py) and
[transit recovery](../../tests/test_light_curve_transit_search.py).

## Physical blocker X01

The [Mission 49 receipt review](validation/ephemeris_covariance_qualification.md)
leaves 18 requirements unestablished across DE440t and INPOP21a. This is a
bounded evidence finding, not a claim that providers possess no covariance.
The [Mission 50 record](../../validation/results/integrated_clock_response_reference_run.json)
preserves six unresolved components: geocentric time ephemeris, Earth state,
station coordinates, Earth orientation, omitted physics/coefficient model and
higher-order remainder. It records 48 unqualified site clocks and 288 combined
arrival candidates: 0 executed, 288 blocked, 240 solar-eligible and 48 excluded.
Geocentric-clock, site-clock and arrival physical bounds remain null;
`observing_eligible=false`. Physical covariance is neither acquired nor propagated.

Reopening X01 requires new applicable evidence or a separately justified
methodological advance: source-matched parameter covariance, trajectory
responses, anchor/cross-covariance metadata and validity domain, followed by
the other physical-component and independent full-reference qualifications.
A covariance receipt alone would not close all six components. More synthetic
clock cases, tiny solver residuals or cross-model agreement cannot supply that
missing physical evidence. No provider contact or private-data access is
authorized by this audit.

Existing rejection gates remain mandatory. X01 may be tracked separately while
other Phase 2 work progresses, but it is not marked complete or silently
deferred. Any future limited-scope phase exit must explicitly review the
unsupported capabilities and their enforced exclusions. This mission grants
neither that scope decision nor permission to enable observer-arrival outputs.

## Phase 2 exit gates

These are proposed acceptance requirements for review in Mission 51, derived
from the original scope. They do not retroactively alter experiment tolerances.
An exit decision must address every gate with linked evidence at a named commit.

| Gate | Required evidence for closure | Baseline assessment |
|---|---|---|
| E01 Coverage inventory | Every original scientific area maps to enabled claims, supported domains, exclusions and evidence; overlaps are explicit. | Documented by this audit; review pending. |
| E02 Reference qualification | Each enabled scientific claim has independent analytic/software/data evidence and a protocol fixed before evaluation, with justified thresholds. | Partial: W01, W02 and W05 have major dossier gaps. |
| E03 Robustness and integration | Relevant nominal, boundary, invalid, null/noise, alias/gap and sensitivity cases are covered; failures and all denominators are retained. | Partial: W03–W05 remain. |
| E04 Reproducibility and provenance | Per experiment, record the applicable commit, Python/dependencies, OS/architecture, data versions/licences/checksums, units/scales/frames, settings/seeds and replay instructions; explain non-applicable fields. Offline replay is reproducible. | Partial: strong existing manifests; W06 must reconcile metadata across differing record schemas and new dossiers. No universal environment-completeness claim is made. |
| E05 Claims and uncertainty | Heuristics remain uncalibrated unless validated; unknowns stay unknown; physical bounds require applicable evidence, and excluded paths stay guarded. | Existing restrictions preserved; X01 blocks physical arrival qualification. A reviewed scope decision is still required for any limited exit. |
| E06 Workflow and contract traceability | Input semantics, adapters and exports preserve scientific meaning; deferred transit scenarios and baseline catalogue/demo limitations have explicit disposition. | Partial: W03/W06, plus X01-dependent production paths. |
| E07 Software acceptance | Full suite, lint and existing audit artifacts pass on the exact proposed exit commit; scientific evidence is assessed separately from regression success. | Baseline CI passed with 19 artifacts; a future exit commit needs fresh acceptance. |
| E08 Exit decision | Reviewed report states supported capabilities, unresolved limitations, gate verdicts and the exact scope allowed into Phase 3. | Not performed. Phase 2 stays active. |

E04 does not require rewriting immutable historical records to make their
schemas identical. Supplements should link to originals, state missing context
honestly and justify whether it affects replay or the supported claim.
Required missing evidence remains a gap. E05 does not convert an external
blocker into success merely because a user-facing warning exists.

## Bounded remaining work

These are work-package IDs, not newly started or guaranteed one-PR missions.
Each future experiment freezes its own cases, references and numeric acceptance
criteria before evaluation. Splitting a package requires explicit traceability
back to these deliverables, rather than expanding the feature catalogue.

| Package | Deliverable and stop condition | Dependencies / phase boundary |
|---|---|---|
| W01 Telescope and imaging | Independent analytic/high-precision reference cases for existing optical geometry, image scale and mosaic coverage; test units/accessory boundaries and separate heuristic labels. Finish with pinned fixture, limits, failure-sensitive tests and report. | Reuse current APIs. Proposed next mission; no hardware/control feature or measured optical-quality claim. |
| W02 Planetary positions | Frozen reference corpus for the seven enabled planets, explicit frame/origin/scale/EOP/ephemeris settings, positional/distance/separation checks and exclusions. | Reuse Mission 33/34 provenance conventions; do not restart Sun/Moon comparisons or add bodies. |
| W03 Visibility and transit sampling | Independent observing-window scenarios, horizon/darkness boundary handling and sample-density sensitivity; disclose incomplete-event coverage and thresholds. | Credit Missions 33–35. Use explicit observing-time inputs; strict unresolved predictions remain blocked. Physical conversion depends on X01. |
| W04 Heuristic characterisation | Deterministic/adversarial planner, schedule, weather-score and transit-ranking cases; weight/threshold/missing-data sensitivity, ties and greedy counterexamples. | Controlled inputs can proceed now; end-to-end claims use W02/W03. Phase 3 owns observational calibration, optimisation and comparative observing utility. |
| W05 Light-curve validation | Freeze synthetic injection/null/noise/alias/gap cases and versioned published data with licences/time semantics; assess LS/BLS recovery, preprocessing bias and false positives against independent expectations. Retain failures and uncertainty limits. | May be split into input/protocol and evaluation missions. Astropy called twice is not an independent oracle. No discovery or universal FAP-coverage claim. |
| W06 Coverage/provenance reconciliation | Crosswalk new dossiers and existing records to E01–E06; reconcile all 26 strict-transit scenarios and baseline catalogue/visualisation limitations, documenting enabled versus research-only paths. | Preserve completed evidence and data hashes; classify catalogue ingestion/transport versus derived quantities. Phase 7 owns professional interoperability, not a blanket exemption from numerical claim validation. |
| W07 Phase 2 exit review | Re-evaluate E01–E08 at a verified commit; issue an explicit pass, limited-scope proposal or hold with unresolved items. | W01–W06 evidence plus X01 disposition review; not automatic approval to start Phase 3. |

**Proposed Mission 52: Telescope and Imaging Scientific Validation (W01).**
It addresses an original-scope gap with bounded, independently reproducible
geometry and does not depend on acquiring planetary-fit covariance. Mission 52
has not started. Later mission numbering is intentionally unassigned pending
the findings and size of these packages; there is no promised completion date.

## Documentation reconciliation and verification

The roadmap records Mission 50 as merged, restores the completed-mission index
through Mission 50, adds Mission 51 and links these exit gates and work packages.
Historical reports remain records of their original validation attempts; a
current merge-status note is added to Mission 50's report without changing its
scientific results. Frozen policies, reference fixtures, results, production
code, tests and CI configuration are unchanged.

Mission 51 adds no numerical benchmark, scientific test or twentieth CI
artifact. Documentation verification checks relative links, evidence paths and
hashes against the baseline, eight unique coverage IDs, gate/work-package
references and preserved physical unknowns. The existing full Quality Gate
must pass on the final PR head, retaining all 19 artifacts. Final execution
evidence belongs in the Mission 51 PR; baseline evidence is not substituted
for that run. Local checks passed for 31 baseline source hashes, 57 relative
documentation links, coverage/gate/package references, the completed-mission
index and inherited physical restrictions. Ruff passed. No Phase 2 completion
or new scientific accuracy is claimed.
