# AstroScope AI Observatory Research Roadmap Status

## Current Status

- Phase 0: Complete
- v0.2.0: Released
- Phase 1: Complete — Research Software Architecture
- Mission 21: Complete — Transit Schedule Application Boundary Extraction, merged in PR #12
- Mission 22: Complete — Observatory Presentation Boundary Extraction, merged in PR #13
- Mission 23: Complete — Observation Schedule Visualization Boundary Extraction, merged in PR #14
- Mission 24: Complete — Sky Map Visualization Boundary Extraction, merged in PR #15
- Phase 1 Exit Audit: PASS — Phase 1 complete
- Phase 2: Active — Scientific Validation
- Mission 25: Complete — Observer-Time Validation Baseline, merged in PR #17
- Mission 26: Complete — Observer-Instant Civil-Time Transition Policy and Correction, merged in PR #19
- Mission 27: Complete — Strict Civil-Time Resolution Validation Evidence, merged in PR #21
- Mission 28: Complete — Civil-Time Interval Semantics and Validation Design, merged in PR #23
- Mission 29: Complete — Strict Observation-Schedule Interval Boundary Resolution, merged in PR #25
- Mission 30: Complete — Observation-Log Interval Model and Fold-Provenance Persistence, merged in PR #27
- Mission 31: Complete — Weather Interval Provider-Contract Evidence and Correction, merged in PR #29
- Mission 32: Complete — Observation-Schedule Interval Validation Evidence and Benchmark, merged in PR #31

- Mission 33: Complete — Celestial Coordinate Validation Benchmark, merged in PR #33 (`4c673bab7d0c940327b5d623d6fbd51bdba8d00b`)
- Mission 34: Complete — Solar, Lunar, and Twilight Validation, merged in PR #34 (`7fdc96f4c9739969ae600bb3477ba394379197df`)
- Mission 35: Complete — Exoplanet Transit Ephemeris Validation, merged in [PR #35](https://github.com/wolfchil345/astroscope-ai-observatory/pull/35) (`1a5e09612662d1756289dfe45465233fb6f0153d`); bounded arithmetic validation only
- Mission 36: Complete — Transit Time-Coordinate and Uncertainty Contract, merged in [PR #36](https://github.com/wolfchil345/astroscope-ai-observatory/pull/36) (`e5a3c70e8aca77ed0132091d3b088eb73e2f1fcf`); design evidence only
- Mission 37: Complete — Strict Transit Timing Metadata and Eligibility Boundary, merged in [PR #37](https://github.com/wolfchil345/astroscope-ai-observatory/pull/37) (`809b0bc89aa0e4b96de2e8f35d81c417b1609650`); production observer-arrival conversion remains unavailable
- Mission 38: Complete — Observer-Arrival Reference Protocol and Conversion Validation, merged in [PR #38](https://github.com/wolfchil345/astroscope-ai-observatory/pull/38) (`9012c675b509f49df61a1ec83b7a330dd5efe99d`); research-only geometric inversion and historical TAI/UTC evidence, no production eligibility
- Mission 39: Complete — Observer-Arrival Error Budget and Resolved-Event Contract, merged in [PR #39](https://github.com/wolfchil345/astroscope-ai-observatory/pull/39) (`eaf3e22b8fb819ef37e0f803595de5330d21e0c7`); physical timing bound remains unknown
- Mission 40: Complete — Observer-Arrival Source Convention and Reference-Domain Qualification, merged in [PR #40](https://github.com/wolfchil345/astroscope-ai-observatory/pull/40); selected research convention and supplied-input solar component comparison only, full timing reference unqualified
- Mission 41: Active — Matched-Convention Observer-Arrival Reference Validation; unsuccessful independent clock qualification retained, combined evaluation blocked
- Proposed next: Mission 42 — Independent Time-Ephemeris Reference Acquisition and Clock Mapping; not started, pending Mission 41 review and merge

## Phase Progress

| Phase | Theme | Status |
|---|---|---|
| 0 | Feature Freeze & Research Baseline | ✅ Complete |
| 1 | Research Software Architecture | ✅ Complete |
| 2 | Scientific Validation | 🚧 Active |
| 3 | Observation Optimisation | ⏳ Planned |
| 4 | Real AI Layer | ⏳ Planned |
| 5 | Uncertainty-Aware Planning | ⏳ Planned |
| 6 | Robotic Observatory Control | ⏳ Planned |
| 7 | Professional Astronomy Interoperability | ⏳ Planned |
| 8 | Research Publication Package | ⏳ Planned |

## Mission 26 Completion Checklist

### Mission 26 — Observer-Instant Civil-Time Transition Policy and Correction

- [x] Add strict normal, ambiguous, and nonexistent civil-time classification
- [x] Add explicit fold resolution without silent gap shifting
- [x] Preserve the Mission 25 compatibility converter and validation evidence
- [x] Require one shared Observatory resolution across five single-instant actions
- [x] Add complete English, Japanese, Korean, and Thai transition messages
- [x] Add exactly 22 core and Observatory regression tests
- [x] Document policy, compatibility, scientific limitations, and interval exclusions
- [x] Run the complete quality gate, benchmark, and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 26 through PR #19

## Mission 27 Completion Checklist

### Mission 27 — Strict Civil-Time Resolution Validation Evidence

- [x] Establish an offline IANA 2026c strict civil-time reference fixture
- [x] Cover all normal, ambiguous, rejection, nonexistent, and invalid-input scenario categories
- [x] Add fixture, manifest, integrity checks, and offline benchmark harness
- [x] Add the civil-time validation report
- [x] Generate a canonical fresh-environment validation record
- [x] Record canonical results in the validation report
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 27 through PR #21

## Mission 28 Completion Checklist

### Mission 28 — Civil-Time Interval Semantics and Validation Design

- [x] Audit scheduling, weather, and observation-log interval workflows
- [x] Distinguish elapsed windows, forecast-sample envelopes, and historical provenance intervals
- [x] Define endpoint fold, gap, ordering, overnight, and precision rules
- [x] Define workflow-specific inclusion and duration semantics
- [x] Define the future policy-neutral civil-interval domain boundary
- [x] Define the transition edge-case and independent validation strategy
- [x] Record immutable evidence, exclusions, risks, and implementation split
- [x] Add the Mission 28 design document
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 28 through PR #23

## Mission 29 Completion Checklist

### Mission 29 — Strict Observation-Schedule Interval Boundary Resolution

- [x] Define a strict schedule-specific endpoint and resolved-interval boundary
- [x] Require independent endpoint folds and reject nonexistent schedule endpoints
- [x] Preserve legacy ordinary scheduling while rejecting unsafe legacy transition inputs
- [x] Use UTC for schedule sampling, block continuity, duration, and aggregation
- [x] Preserve planner fold forwarding and correct timeline figure chronology
- [x] Add minimal reference-zone reachability and endpoint controls to the Observatory
- [x] Add 40 strict scheduling regression cases and implementation documentation
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 29 through PR #25

## Mission 30 Completion Checklist

### Mission 30 — Observation-Log Interval Model and Fold-Provenance Persistence

- [x] Define strict observation-log endpoint and UTC-authoritative interval values
- [x] Preserve aware-datetime constructor compatibility through named-zone provenance checks
- [x] Require independent folds, reject gaps, and use UTC ordering and containment
- [x] Add schema v2 JSON provenance and verified schema v1 migration
- [x] Preserve CSV compatibility while appending provenance columns
- [x] Add transition-aware dashboard controls, reports, localization, and regression coverage
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 30 through PR #27

## Mission 31 Completion Checklist

### Mission 31 — Weather Interval Provider-Contract Evidence and Correction

- [x] Capture first-party archived provider timestamp-format evidence offline
- [x] Add strict named-zone endpoint resolution and UTC-authoritative weather sample selection
- [x] Preserve legacy ordinary and overnight weather compatibility while rejecting unsafe endpoints
- [x] Add provider metadata, transition, dashboard, chart, and regression coverage
- [x] Add offline provider-contract fixture, manifest, validator, and claim boundary report
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 31 through PR #29

## Mission 32 Completion Checklist

### Mission 32 — Observation-Schedule Interval Validation Evidence and Benchmark

- [x] Define an independent IANA 2026c fixture-generation boundary
- [x] Add the 37-case schedule interval fixture, manifest, and offline benchmark
- [x] Verify strict endpoints, UTC grids, occupancy, continuity, and aggregation
- [x] Record canonical result provenance and claim boundaries
- [x] Add CI retention for the schedule-interval validation record
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 32 through PR #31

## Mission 25 Completion Checklist

### Mission 25 — Observer-Time Validation Baseline

- [x] Build an offline, pinned civil-time-to-UTC reference fixture from IANA 2026c
- [x] Validate seven unambiguous/date-crossing cases and two explicit fold conversions
- [x] Characterize two nonexistent-time cases as expected unsupported behavior
- [x] Preserve the existing invalid-timezone validation behavior
- [x] Record package, timezone-database, Git, dependency, and environment provenance
- [x] Add exactly 16 validation tests and a CI benchmark artifact
- [x] Preserve production scientific code and document the missing UI fold/gap policy
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 25 through PR #17

## Mission 24 Completion Checklist

### Mission 24 — Sky Map Visualization Boundary Extraction

- [x] Move sky-map chart labels and Plotly figure construction into a dedicated visualization module
- [x] Keep sky-map result models, radial geometry, and workflow calculations unchanged
- [x] Make the production Observatory import visualization symbols from the new boundary directly
- [x] Preserve legacy sky-map visualization imports lazily with exact object identity
- [x] Keep ordinary scientific sky-map imports free from Plotly and visualization dependencies
- [x] Add scientific, figure, dependency-boundary, compatibility, and AST characterization
- [x] Preserve astronomy behavior, result contracts, translations, navigation, state, and styling
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 24 through PR #15

## Mission 23 Completion Checklist

### Mission 23 — Observation Schedule Visualization Boundary Extraction

- [x] Move schedule chart labels and Plotly figure construction into a dedicated visualization module
- [x] Keep timeline generation and scheduling heuristics in the scientific/workflow module
- [x] Make the production Observatory import visualization symbols from the new boundary directly
- [x] Preserve legacy schedule visualization imports lazily with exact object identity
- [x] Add independent numerical characterization for grids, planner forwarding, and scheduling heuristics
- [x] Add exact figure, dependency-boundary, compatibility, and AST characterization
- [x] Preserve scientific formulas, thresholds, tolerances, navigation, state, translations, and styling
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 23 through PR #14

## Mission 22 Completion Checklist

### Mission 22 — Observatory Presentation Boundary Extraction

- [x] Move the complete Observatory presentation implementation into a dedicated module
- [x] Keep `app.py` responsible for page configuration, shared language selection, and navigation
- [x] Preserve the Observatory page wrapper and language delegation
- [x] Preserve page count, ordering, callables, titles, icons, and default-page behavior
- [x] Preserve the Observatory rendering body mechanically without internal decomposition
- [x] Add navigation, import-side-effect, compatibility, and Streamlit smoke coverage
- [x] Preserve scientific behavior, widgets, session state, translations, exports, and defaults
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 22 through PR #13

## Mission 21 Completion Checklist

### Mission 21 — Transit Schedule Application Boundary Extraction

- [x] Create a UI-independent transit-schedule application module
- [x] Move the approved request-construction dataclass and helpers without duplication
- [x] Preserve dashboard compatibility imports and object identity
- [x] Add characterization tests for date boundaries, request fields, and target mapping
- [x] Enforce the Streamlit-free and Plotly-free dependency boundary in a clean subprocess
- [x] Preserve scientific calculations, defaults, exports, translations, session state, and UI
- [x] Run the complete quality gate and internal Markdown-link verification
- [x] Open pull request
- [x] Merge Mission 21 through PR #12

## Mission 20 Completion Checklist

### Mission 20 — v0.2.0 Research Baseline Freeze

- [x] Reconcile the Mission 18 and Mission 19 documentation
- [x] Define the exact v0.2.0 capability baseline
- [x] Document supported scientific workflows
- [x] Consolidate known limitations across all required categories
- [x] Define future reproducibility and validation expectations
- [x] Record Phase 0 freeze acceptance criteria
- [x] Add v0.2.0 release notes and package metadata
- [x] Verify internal documentation links and version references
- [x] Run the complete quality gate
- [x] Open pull request
- [x] Merge Mission 20 through PR #10

## Completed Missions

- Mission 17 — Multipage Observatory Navigation, merged in PR #7
- Mission 18 — Research Baseline Audit, merged in PR #8
- Mission 19 — Architecture & Limitations Map, merged in PR #9
- Mission 20 — v0.2.0 Research Baseline Freeze, merged in PR #10
- Mission 21 — Transit Schedule Application Boundary Extraction, merged in PR #12
- Mission 22 — Observatory Presentation Boundary Extraction, merged in PR #13
- Mission 23 — Observation Schedule Visualization Boundary Extraction, merged in PR #14
- Mission 24 — Sky Map Visualization Boundary Extraction, merged in PR #15
- Mission 25 — Observer-Time Validation Baseline, merged in PR #17
- Mission 26 — Observer-Instant Civil-Time Transition Policy and Correction, merged in PR #19
- Mission 27 — Strict Civil-Time Resolution Validation Evidence, merged in PR #21
- Mission 28 — Civil-Time Interval Semantics and Validation Design, merged in PR #23
- Mission 29 — Strict Observation-Schedule Interval Boundary Resolution, merged in PR #25
- Mission 30 — Observation-Log Interval Model and Fold-Provenance Persistence, merged in PR #27

## Mission 35 Completion Checklist

### Mission 35 — Exoplanet Transit Ephemeris Validation

- [x] Verify Mission 34 merge and freeze acceptance policy before residual measurement
- [x] Add independently generated Decimal reference, source records and integrity manifest
- [x] Validate midpoint, contacts, padding, uncertainty and signed-cycle range selection
- [x] Retain indeterminate boundaries and unsupported time-coordinate/covariance limitations
- [x] Add offline benchmark, failure-sensitivity tests and CI artifact retention
- [x] Record canonical evidence and complete quality gate
- [x] Open pull request — [PR #35](https://github.com/wolfchil345/astroscope-ai-observatory/pull/35)
- [x] Merge Mission 35 — PR #35, 2026-10-17 at 15:00:04 UTC

## Mission 36 Completion Checklist

### Mission 36 — Transit Time-Coordinate and Uncertainty Contract

- [x] Verify Mission 35 merge and successful post-merge Quality Gate
- [x] Audit timestamp, uncertainty, query, visibility, ranking and export boundaries
- [x] Record source hashes and reproducible offline characterization separately from accuracy evidence
- [x] Define source coordinates, resolved observer instants and strict eligibility rules
- [x] Define unknown uncertainty, covariance, duration, inclusion and persistence semantics
- [x] Record 26 prospective acceptance scenarios and independent-reference requirements
- [x] Define implementation split and preserve existing scientific evidence
- [x] Verify baseline quality gate and local design-integrity checks; require PR CI before merge
- [x] Open pull request — [PR #36](https://github.com/wolfchil345/astroscope-ai-observatory/pull/36)
- [x] Merge Mission 36 — PR #36, 2026-10-17 at 15:18:20 UTC

## Mission 37 Completion Checklist

### Mission 37 — Strict Transit Timing Metadata and Eligibility Boundary

- [x] Verify Mission 36 merge and successful post-merge quality gate
- [x] Commit bounded implementation policy before implementation and testing
- [x] Add immutable timing, source, observer-context and uncertainty metadata
- [x] Add source-coordinate nominal arithmetic and unknown-aware covariance propagation
- [x] Reject unresolved strict records at observing, ranking, visualization and export boundaries
- [x] Default to strict preview; require explicit legacy acknowledgement in all four languages
- [x] Preserve original scalar arithmetic and frozen numerical evidence; label legacy exports
- [x] Add 100 contract/UI tests and document partial/deferred coverage of the 26 design scenarios
- [x] Run local full suite (2,887 passed), Ruff and compilation; require PR CI before merge
- [x] Open pull request — [PR #37](https://github.com/wolfchil345/astroscope-ai-observatory/pull/37)
- [x] Merge Mission 37 — PR #37, 2026-10-17 at 15:56:41 UTC; post-merge CI passed

## Mission 38 Completion Checklist

### Mission 38 — Observer-Arrival Reference Protocol and Conversion Validation

- [x] Verify merged Mission 37 baseline and post-merge quality gate
- [x] Freeze independent reference protocol and tolerances before measurement (`de84208`)
- [x] Archive 288 Skyfield/DE421 geometric pairs and five independently derived leap pairs
- [x] Pin and checksum reference inputs; reproduce without network access
- [x] Implement research-only bounded inversion and historical TAI/UTC adapter
- [x] Detect wrong-sign, scale-only and omitted-site faults; disclose all denominators
- [x] Add 48 failure/precision/integrity/independence tests and seventh CI artifact
- [x] Document model omissions and keep all production observing gates closed
- [x] Run full local quality gate: 2,935 tests passed, Ruff and compilation; require published-head CI before merge
- [x] Open pull request — [PR #38](https://github.com/wolfchil345/astroscope-ai-observatory/pull/38)
- [x] Merge Mission 38 — PR #38, 2026-10-18 at 05:23:07 UTC; post-merge CI passed

## Mission 39 Completion Checklist

### Mission 39 — Observer-Arrival Error Budget and Resolved-Event Contract

- [x] Verify Mission 38 merge and post-merge quality gate
- [x] Freeze conditional mathematical/evidence policy before computations (`2952633`)
- [x] Preserve sampled discrepancies as samples; retain null physical total and nine unknown required bounds
- [x] Audit site-aware clock inclusion to prevent double counting
- [x] Derive and test exact conditional bounds, outward rounding and tri-state interval semantics
- [x] Specify twelve resolved-event sections and twenty prospective scenarios without claiming production execution
- [x] Add 69 tests and an offline CI audit artifact; preserve all seven existing benchmarks
- [x] Run full local suite: 3,004 tests passed in 114.70 seconds; Ruff passed
- [x] Configure CI to rerun all seven benchmarks and retain eight artifacts; published-head verification is recorded in PR #39 and required before merge
- [x] Open pull request — [PR #39](https://github.com/wolfchil345/astroscope-ai-observatory/pull/39)
- [x] Merge Mission 39 — PR #39, 2026-10-18 at 05:56:33 UTC; post-merge CI passed

## Mission 40 Completion Checklist

### Mission 40 — Observer-Arrival Source Convention and Reference-Domain Qualification

- [x] Verify Mission 39 merge and successful post-merge quality gate
- [x] Freeze source convention, reference-domain guards and numerical threshold before generation (`827cf8f`)
- [x] Audit PINT sign, normalization and actual input types; retain unsuccessful setup attempts
- [x] Archive 45 synthetic cases and all 288 historical candidates, including 48 explicit exclusions
- [x] Compare 285 eligible inputs against pinned PINT with independent Decimal arithmetic
- [x] Disclose complete sign/radial-omission fault-detection denominators
- [x] Add 57 tests and ninth CI artifact; preserve seven prior benchmarks and budget audit
- [x] Keep full reference/physical qualification incomplete and all observing gates closed
- [x] Complete full local quality gate: 3,061 tests passed in 119.45 seconds; Ruff, compilation and documentation links passed
- [x] Open pull request — [PR #40](https://github.com/wolfchil345/astroscope-ai-observatory/pull/40); published-head CI and nine artifacts must be verified before merge, with the final run recorded in the PR
- [x] Merge Mission 40 — PR #40, 2026-10-18 at 07:07:19 UTC (`176ba2a504e64464f6f69e642dddb4bb98a05efc`); post-merge Quality Gate 39106487552 passed

## Mission 41 Completion Checklist

### Mission 41 — Matched-Convention Observer-Arrival Reference Validation

- [x] Verify Mission 40 merge and successful post-merge quality gate
- [x] Freeze route requirements, diagnostic census and blocking policy before values (`5b63ed2`)
- [x] Audit four routes, tracing shared backends and retaining the unsupported ephemeris attempt
- [x] Archive 48 unique site instants and 12 unique geocentric instants with frozen EOP/leaps
- [x] Clarify the selected UTC approximation to UT1 without changing the convention
- [x] Retain unsuccessful clock qualification and all 288 blocked combined cases with null results
- [x] Add 46 tests, including live algorithm regression and rejection of false independence
- [x] Reproduce the archived fixture byte-for-byte offline; preserve all historical records and gates
- [ ] Complete full local quality gate and retain clean canonical evidence
- [ ] Open pull request and verify published-head CI with ten artifacts
- [ ] Merge Mission 41

## Phase 2 Deliverables

- [Matched-Convention Observer-Arrival Reference Validation — Mission 41](validation/clock_reference_validation.md)

- [Observer-Arrival Source Convention and Reference-Domain Qualification — Mission 40](validation/source_reference_qualification.md)

- [Observer-Arrival Error Budget and Resolved-Event Contract — Mission 39](validation/observer_arrival_error_budget.md)

- [Observer-Arrival Reference Protocol and Conversion Validation — Mission 38](validation/observer_arrival_validation.md)

- [Strict Transit Timing Metadata and Eligibility Boundary — Mission 37](validation/strict_transit_timing_boundary.md)

- [Transit Time-Coordinate and Uncertainty Contract — Mission 36](validation/transit_time_coordinate_contract.md)

- [Exoplanet Transit Ephemeris Validation — Mission 35](validation/transit_ephemeris_validation.md)

- [Solar, Lunar, and Twilight Validation — Mission 34](validation/solar_lunar_twilight_validation.md)

- [Celestial Coordinate Validation — Mission 33](validation/celestial_coordinate_validation.md)

- [Observer-Time Validation Baseline](validation/observer_time_validation.md)
- [Observer-Instant Civil-Time Transition Policy](validation/civil_time_transition_policy.md)
- [Strict Civil-Time Resolution Validation Evidence](validation/civil_time_validation.md)
- [Civil-Time Interval Semantics and Validation Design](validation/civil_time_interval_semantics.md)
- [Observation-Schedule Interval Resolution](validation/observation_schedule_interval_resolution.md)
- [Observation-Log Interval Model and Fold-Provenance Persistence](validation/observation_log_interval_model.md)
- [Weather Interval Provider-Contract Evidence](validation/weather_provider_contract.md)

## Phase 1 Deliverables

- [Phase 1 Exit Audit](phase_1_exit_audit.md)
- Mission 21 — Transit Schedule Application Boundary Extraction, PR #12
- Mission 22 — Observatory Presentation Boundary Extraction, PR #13
- Mission 23 — Observation Schedule Visualization Boundary Extraction, PR #14
- Mission 24 — Sky Map Visualization Boundary Extraction, PR #15

## Phase 0 Deliverables

- [Research Baseline Audit](research_baseline_audit.md)
- [Architecture & Limitations Map](architecture_limitations_map.md)
- [v0.2.0 Research Baseline Freeze](v0.2.0_research_baseline.md)
- [v0.2.0 Changelog](../../CHANGELOG.md#020---2026-08-03)

## Research Rule

After Phase 0, new work must primarily contribute to at least one of:

- scientific validation
- mathematical optimisation
- machine learning
- uncertainty modelling
- control engineering
- astronomy interoperability
- experimental evaluation
- research reproducibility

Random feature growth is frozen.
