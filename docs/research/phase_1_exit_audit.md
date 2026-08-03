# Phase 1 Exit Audit — Research Software Architecture

## Executive Verdict

**PASS — Phase 1 can close and Phase 2 Scientific Validation may begin.**

The architecture is sufficient for controlled, headless scientific validation. Phase 1
completion does not imply perfect architecture or zero technical debt. The audit identified no
Class A architecture blocker before Phase 2; remaining debt is intentionally deferred until a
research or later-phase requirement reaches its documented trigger.

Regression tests establish behavioral preservation. They do not establish scientific
correctness, calibration, or publication readiness.

## Baseline

- Repository: `wolfchil345/astroscope-ai-observatory`
- Phase 1 exit baseline commit: `f63ef603cdac948aa4cdf3241e78c6740e9bad5b`
- Mission 24: PR #15
- Tracked test baseline: 732 tests
- Phase 0 research baseline release: v0.2.0
- Phase 1 followed the v0.2.0 baseline through Missions 21–24.

The exit audit was read-only and made no scientific or product implementation changes. This
document records its result after the implementation missions were complete. The
[research baseline audit](research_baseline_audit.md),
[architecture and limitations map](architecture_limitations_map.md), and
[v0.2.0 research baseline](v0.2.0_research_baseline.md) remain the governing Phase 0 records.

## Phase 1 Deliverables

| Mission | Deliverable | GitHub history |
|---|---|---|
| 21 | Transit Schedule Application Boundary Extraction | PR #12 |
| 22 | Observatory Presentation Boundary Extraction | PR #13 |
| 23 | Observation Schedule Visualization Boundary Extraction | PR #14 |
| 24 | Sky Map Visualization Boundary Extraction | PR #15 |

Together, these missions established the following architectural properties:

- `app.py` is a thin application-composition and navigation layer.
- Observatory rendering is separated from application composition.
- Transit-schedule request and application helpers are callable without Streamlit.
- Observation-schedule calculation is callable without Plotly.
- Sky-map calculation is callable without Plotly.
- Schedule and sky-map figure construction live in dedicated visualization modules.
- Required legacy compatibility imports retain their established identities.
- Scientific cores can be called directly from plain Python.
- The exit audit found no top-level internal dependency cycle.

## Exit Criteria

| Criterion | Status | Exit-audit evidence |
|---|---|---|
| Scientific cores independently callable | PASS | Observer, coordinate, visibility, Solar System, telescope, imaging, planner, schedule, transit, and light-curve modules expose direct Python functions and result models. |
| Scientific cores independently testable | PASS | Core tests call scientific functions without requiring application navigation or page rendering; the tracked baseline contains 732 tests. |
| Core validation paths free from Streamlit | PASS | A clean-process import of the planned Phase 2 scientific modules loaded no Streamlit module. |
| Relevant scientific paths free from Plotly | PASS | The same clean-process import loaded no Plotly module; schedule and sky-map presentation builders are separate. |
| Presentation boundaries adequate | PASS | Application composition, Observatory rendering, schedule figures, and sky-map figures have distinct boundaries adequate for the planned validation work. |
| Application boundaries adequate for Phase 2 | PASS | Repository-owned validation harnesses can call the scientific modules directly; a universal use-case layer is not required to begin. |
| Result contracts stable enough for benchmarks | PASS | Deterministic functions and immutable result dataclasses provide comparison surfaces, provided experiments declare units and conventions explicitly. |
| External services do not block controlled validation | PASS | Gaia and Exoplanet support injected transports, while catalogue parsing, weather parsing, and derived calculations can use controlled fixtures. |
| Minimum reproducibility achievable | PASS | Per-experiment manifests can record source, environment, data, configuration, reference results, and tolerances without another architecture extraction. |
| Minimum provenance achievable | PASS | Versioned fixtures, checksums, source attribution, retrieval metadata, and transformation details can accompany Phase 2 results. |
| Validation failures can be localized to science rather than UI | PASS | Numerical paths can run without Streamlit navigation, session state, or Plotly figure construction. |
| No known architectural blocker to Phase 2 | PASS | No presentation dependency, circular import, live-service requirement, or inaccessible scientific workflow prevents controlled validation. |

These criteria establish readiness to validate the software. They do not validate any scientific
formula, heuristic, uncertainty model, or numerical claim.

## Remaining Architecture Debt

**Class A — blocker before Phase 2: None.**

Class B items should be addressed during a later phase when their trigger is reached. Class C
items are acceptable or intentional debt under the current architecture.

| Debt | Class | Severity | Phase 2 blocker | Recommended future owner | Rationale | Remediation trigger |
|---|---|---|---|---|---|---|
| 3,969-line Observatory renderer | B | Medium | No | Later UI maintenance; Phase 6 if operational workflows require it | Its review surface is large, but scientific calculations are already callable outside it. | Validation requires scientific logic available only inside the renderer. |
| Helpers remaining in Streamlit dashboards | B | Medium | No | Phase 2, per affected subsystem | Most benchmarks can pass explicit inputs directly to scientific cores. | A benchmark cannot reproduce a UI-owned default, request, or policy headlessly. |
| Lack of a universal application layer | B | Medium | No | Incremental future architecture work | Repository-owned validation can call internal modules directly. | A complete multi-module workflow requires consistent orchestration, provenance, and error handling. |
| Gaia transport, parsing, and science coupling | B | High | No | Gaia validation work; Phase 7 interoperability | Injected transports and fixtures permit controlled parsing and numerical tests. | Raw archive fields and project-derived values need separate versioning or attribution. |
| Exoplanet transport, parsing, and science coupling | B | High | No | Exoplanet validation work; Phase 7 interoperability | Fixture-based parsing and derived calculations remain possible. | Service-schema failures must be separated formally from derived-science failures. |
| Weather transport, parsing, and scoring coupling | B | High | No | Phase 3 Observation Optimisation | Scoring and parsing can be tested with controlled payloads without a live forecast. | Live replay, calibration, caching, or structured adapter errors become required. |
| Scientific transit approximation in `exoplanet_visuals.py` | B | High | No | Phase 2 before validating that model | It is outside the initial validation targets but is scientific logic in a presentation module. | A benchmark or scientific claim concerns the displayed trapezoidal transit approximation. |
| `SkyMapPoint.radial_distance_degrees` | C | Low | No | Future sky-map contract cleanup | It is characterized display geometry and does not load Plotly. | A scientific consumer begins treating it as an astronomical measurement. |
| `altitude_to_radial_distance()` placement | C | Low | No | Future presentation cleanup | Its placement is imperfect but deterministic and independently testable. | Sky-map result contracts are redesigned or reused outside polar presentation. |
| Shared typed application state absent | B | Medium | No | Phase 6 Robotic Observatory Control | Session-state architecture does not constrain isolated numerical experiments. | Persistent, replayable, multi-session, or operational workflows are introduced. |
| Incomplete common provenance envelope | B | High | No | Minimum metadata in Phase 2; full package in Phase 8 | Experiment-local manifests are sufficient for initial validation. | Results become durable, shared, aggregated, or publication-facing. |
| Limited architecture and import enforcement | B | Medium | No | Ongoing engineering | Missions 21–24 protect their critical seams, but no package-wide rule exists. | A new module introduces UI or visualization dependencies into a scientific core. |
| No supported public research API | C | Medium | No | Phase 7 Professional Astronomy Interoperability | Internal APIs pinned to a commit are adequate for repository-owned experiments. | External notebooks or integrations require compatibility guarantees. |
| Dependency environment not locked | B | High | No | Phase 2 experiments; publication form in Phase 8 | Validation can begin, but accepted results need exact dependency evidence. | The first authoritative benchmark is recorded or compared across machines. |
| Implicit units, time scales, frames, and duplicated conventions | B | High | No | Phase 2 Scientific Validation | These are validation inputs and subjects rather than architecture prerequisites. | A reference comparison would otherwise be ambiguous or irreproducible. |
| Uncalibrated planner, schedule, weather, and ranking heuristics | B | High | No | Phase 2 characterization and Phase 3 calibration | The heuristics are deterministic but cannot support calibrated claims. | Performance or observational-quality claims are proposed. |

## Phase 2 Readiness

| Scientific subsystem | Readiness | Required validation approach | Architecture prerequisite |
|---|---|---|---|
| Observer and time handling | Ready | Reference timezone and daylight-saving cases, UTC conversions, time-scale comparisons, and recorded timezone/IERS data | None |
| Coordinate conversion | Ready | Fixed reference points compared with Astropy/ERFA or another authoritative implementation using explicit frames and tolerances | None |
| Visibility | Ready | Independent AltAz, horizon, darkness, and airmass comparisons with an explicit refraction policy | None |
| Solar System positions | Conditional | Comparison with an authoritative ephemeris while pinning Astropy, IERS, and ephemeris configuration | Experiment environment and reference-data pinning only |
| Telescope and imaging | Ready | Analytic cases and independent calculators with explicit equipment units and idealization assumptions | None |
| Planner and schedule heuristics | Conditional | Component invariants, sensitivity analysis, deterministic scenarios, and later observational calibration | Preserve the uncalibrated designation |
| Transit calculations | Conditional | Published or synthetic ephemerides, uncertainty cases, visibility references, and sampling-sensitivity analysis | Document the linear-ephemeris limitations |
| Light-curve analysis | Conditional | Versioned synthetic and published datasets covering recovery, nulls, aliases, gaps, red noise, and false positives | Explicit time units, scales, and dataset provenance |

Here, **Conditional** means that scientific-method prerequisites exist. It does not identify an
architecture blocker or require another Phase 1 implementation mission.

## Phase 2 Entry Conditions

Mission 25 and subsequent Phase 2 work must meet these conditions:

1. Use a machine-readable benchmark manifest before accepting benchmark results.
2. Record the commit, Python version, dependency versions, operating system, machine architecture,
   timezone-data version, Astropy version, IERS data, and ephemeris configuration or version.
3. Version reference fixtures.
4. Record each fixture's source, licence, retrieval time when applicable, checksum, and
   transformations.
5. Declare units, time scales, coordinate frames, observing sites, algorithm settings, random
   seeds where applicable, and numerical tolerances.
6. Separate deterministic offline benchmarks from optional live-service checks.
7. Characterize current behavior before changing scientific formulas or conventions.
8. Keep heuristic outputs explicitly labelled uncalibrated until they are validated.
9. Never use regression success alone as evidence of scientific accuracy.

## Deferred Research-Software Work

- **Phase 2 — Scientific Validation:** validation-specific conventions, benchmark provenance,
  per-experiment dependency pinning, and only the targeted boundary work a benchmark proves
  necessary.
- **Phase 3 — Observation Optimisation:** weather, planner, schedule, and ranking calibration and
  optimisation.
- **Phase 6 — Robotic Observatory Control:** persistent and typed operational state if robotic
  workflows require it.
- **Phase 7 — Professional Astronomy Interoperability:** external interoperability and supported
  research API boundaries.
- **Phase 8 — Research Publication Package:** complete publication reproducibility, provenance,
  environment, and reference-data packaging.

Other deferred items should remain demand-driven rather than being assigned to a phase without
new evidence.

## Exit Decision

**Phase 1 — Research Software Architecture: COMPLETE**

**Phase 2 — Scientific Validation: READY TO START, NOT YET STARTED**

**Mission 25: NOT STARTED**
