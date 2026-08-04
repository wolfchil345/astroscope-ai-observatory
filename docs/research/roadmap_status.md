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
- Mission 27: Active — Strict Civil-Time Resolution Validation Evidence

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

## Mission 27 Active Checklist

### Mission 27 — Strict Civil-Time Resolution Validation Evidence

- [x] Establish an offline IANA 2026c strict civil-time reference fixture
- [x] Cover normal, ambiguous, rejection, nonexistent, and invalid-input cases
- [x] Add fixture, manifest, integrity checks, and offline benchmark harness
- [x] Add a pending-results validation protocol document
- [ ] Generate a canonical fresh-environment validation record
- [ ] Update the validation protocol with canonical results
- [x] Run the complete quality gate and internal Markdown-link verification
- [ ] Open pull request
- [ ] Merge Mission 27

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

## Phase 2 Deliverables

- [Observer-Time Validation Baseline](validation/observer_time_validation.md)
- [Observer-Instant Civil-Time Transition Policy](validation/civil_time_transition_policy.md)

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
