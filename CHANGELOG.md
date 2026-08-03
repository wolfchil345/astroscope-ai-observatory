# Changelog

This file records documented AstroScope release baselines. Development history before v0.2.0 is
available from Git history and is not reconstructed here as a release narrative.

## [Unreleased]

No changes recorded after the v0.2.0 research baseline.

## [0.2.0] - 2026-08-03

### Phase 0 research baseline

- Froze the five-page Streamlit capability set as the official Phase 0 comparison baseline.
- Recorded the complete supported scientific workflow inventory.
- Consolidated the Mission 18 scientific audit and Mission 19 architecture map.
- Documented scientific, architectural, data, provenance, uncertainty, dependency,
  external-service, and operational limitations.
- Defined reproducibility and validation expectations for future research phases.
- Recorded Phase 0 freeze acceptance criteria.
- Updated project package metadata from `0.1.0` to `0.2.0`.

### Included capability areas

- Observer time, coordinates, visibility, Solar System geometry, and local sky mapping
- Heuristic observation planning, night scheduling, and weather-aware conditions
- Telescope and astrophotography geometry
- Structured observation logging and exports
- Gaia DR3 and NASA Exoplanet Archive exploration
- Light-curve processing, Lomb–Scargle analysis, phase analysis, Box Least Squares, and diagnostics
- Exoplanet transit prediction, visibility analysis, ranking, visualization, and export
- Four-language Streamlit navigation across five standalone pages

### Validation baseline

- Ruff passed.
- Python compilation passed.
- The complete suite passed with 702 tests.
- `git diff --check` passed.
- Internal documentation links and version references were verified.

### Readiness statement

v0.2.0 is a research-capable educational prototype and a controlled baseline for future work. It
is not publication-grade validated research software, calibrated operational planning software,
or an autonomous/robotic observatory-control system.

See the [v0.2.0 Research Baseline Freeze](docs/research/v0.2.0_research_baseline.md) for the exact
capability boundary, limitations, acceptance criteria, and future validation expectations.
