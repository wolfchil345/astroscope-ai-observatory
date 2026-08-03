# AstroScope AI Observatory Research Roadmap Status

## Current Status

- Phase 0: Complete
- v0.2.0: Released
- Phase 1: Active — Research Software Architecture
- Mission 21: Active — Transit Schedule Application Boundary Extraction

## Phase Progress

| Phase | Theme | Status |
|---|---|---|
| 0 | Feature Freeze & Research Baseline | ✅ Complete |
| 1 | Research Software Architecture | 🚧 In Progress |
| 2 | Scientific Validation | ⏳ Planned |
| 3 | Observation Optimisation | ⏳ Planned |
| 4 | Real AI Layer | ⏳ Planned |
| 5 | Uncertainty-Aware Planning | ⏳ Planned |
| 6 | Robotic Observatory Control | ⏳ Planned |
| 7 | Professional Astronomy Interoperability | ⏳ Planned |
| 8 | Research Publication Package | ⏳ Planned |

## Current Mission Checklist

### Mission 21 — Transit Schedule Application Boundary Extraction

- [x] Create a UI-independent transit-schedule application module
- [x] Move the approved request-construction dataclass and helpers without duplication
- [x] Preserve dashboard compatibility imports and object identity
- [x] Add characterization tests for date boundaries, request fields, and target mapping
- [x] Enforce the Streamlit-free and Plotly-free dependency boundary in a clean subprocess
- [x] Preserve scientific calculations, defaults, exports, translations, session state, and UI
- [x] Run the complete quality gate and internal Markdown-link verification
- [ ] Open pull request
- [ ] Merge Mission 21

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
