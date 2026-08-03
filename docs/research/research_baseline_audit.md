# Mission 18 — Research Baseline Audit

## Executive assessment

AstroScope is a substantial, modular scientific-software prototype with broad unit-test
coverage and clear user-facing cautions. Its strongest research foundations are deterministic
domain models, explicit input validation, reusable calculation modules, transparent scoring
rules, and synthetic recovery tests for light-curve analysis.

The project is not yet research-ready for publication-grade claims, calibrated observing
decisions, or unattended operations. The current tests primarily demonstrate internal
correctness against project-defined expectations. They do not yet establish agreement with
authoritative ephemerides, published astronomical datasets, independent software, calibrated
observations, or stable external-service contracts. Units, time standards, provenance, and
uncertainty are also represented unevenly across subsystems.

**Baseline classification:** research-capable educational prototype; ready for a formal
validation programme, but not yet validated research software.

## Audit scope and method

This audit is documentation-only. It inventories the merged Mission 17 codebase without adding
features or performing scientific refactors.

- Baseline branch: `main`
- Baseline commit: `1f17011a65ef51d76585a3787ab6e0a7adaee7a4`
- Baseline pull request: PR #7, Multipage Observatory Navigation
- Audit date: 2026-08-03
- Python package modules: 58 files under `src/astroscope`
- Application entry point: 4,063-line `app.py`
- Test suite: 43 files and 702 collected test cases
- CI baseline: Python 3.12, Ruff, and pytest

The assessment used module boundaries, imports, public calculations, documentation cautions,
external-service endpoints, CI configuration, and pytest collection. No live scientific service
was queried during the audit.

## Scientific module inventory

### Observer geometry and celestial mechanics

| Modules | Current responsibility | Reusability |
|---|---|---|
| `observer.py` | Observer locations, time-zone conversion, UTC, JD, MJD, and apparent sidereal time | Reusable scientific core |
| `coordinates.py` | ICRS parsing and conversion to Galactic and Cartesian coordinates | Reusable scientific core |
| `visibility.py` | ICRS-to-AltAz transforms, visibility classes, cardinal direction, and airmass | Reusable scientific core |
| `solar_system.py` | Built-in-ephemeris positions, separations, local AltAz, and Moon illumination | Reusable scientific core |
| `sky_map.py` | Catalogue and Solar System sky-map point generation plus Plotly rendering | Mixed calculation and presentation |

### Observation planning and equipment

| Modules | Current responsibility | Reusability |
|---|---|---|
| `planner.py` | Transparent altitude, airmass, Moon-separation, and darkness ranking | Reusable heuristic core |
| `schedule.py` | Sampled night timeline and greedy observation-block construction | Mixed calculation and Plotly presentation |
| `weather.py` | Open-Meteo retrieval, forecast parsing, weather score, rating, and dew risk | Mixed service adapter and heuristic core |
| `weather_charts.py` | Weather-condition and score figures | Reusable presentation component |
| `telescope.py` | Telescope/eyepiece geometry, magnification, pupil, field, and resolution estimates | Reusable calculation core |
| `telescope_visuals.py` | Field-of-view classification and figure generation | Mixed geometry and presentation |
| `imaging.py` | Sensor geometry, image scale, seeing sampling, framing, and mosaics | Reusable calculation core |
| `imaging_visuals.py` | Rotated sensor and mosaic figures | Reusable presentation component |

### Catalogues and external science data

| Modules | Current responsibility | Reusability |
|---|---|---|
| `gaia_catalog.py` | Gaia DR3 ADQL, synchronous TAP access, CSV parsing, distance and absolute-magnitude estimates | Reusable service/science layer |
| `gaia_export.py` | Deterministic catalogue CSV exports | Reusable data adapter |
| `gaia_visuals.py` | Sky, colour–magnitude, and proper-motion figures | Reusable presentation component |
| `exoplanet_catalog.py` | NASA archive ADQL, TAP access, parsing, density, transit probability/depth, and temperate screening | Reusable service/science layer |
| `exoplanet_export.py` | Deterministic exoplanet CSV exports | Reusable data adapter |
| `exoplanet_visuals.py` | Population diagrams and an educational trapezoidal transit model | Mixed scientific approximation and presentation |

### Light-curve analysis

| Modules | Current responsibility | Reusability |
|---|---|---|
| `light_curve.py` | Validated photometry models and metadata | Reusable scientific core |
| `light_curve_io.py` | CSV import, column detection, CSV/JSON serialization | Reusable data adapter |
| `light_curve_processing.py` | Normalization, sigma clipping, and polynomial detrending | Reusable scientific core |
| `light_curve_period.py` | Lomb–Scargle periodograms, candidates, and false-alarm probability | Reusable scientific core |
| `light_curve_phase.py` | Phase folding, cycle tracking, and weighted/unweighted phase bins | Reusable scientific core |
| `light_curve_transit_search.py` | Box Least Squares searches and ranked candidates | Reusable scientific core |
| `light_curve_transit_diagnostics.py` | Box models, depth and residual diagnostics | Reusable scientific core |
| `light_curve_exports.py`, `light_curve_analysis_exports.py` | CSV/JSON analysis products | Reusable data adapters |
| `light_curve_visuals.py`, `light_curve_analysis_visuals.py` | Plotly analysis figures | Reusable presentation components |

### Transit observation scheduling

| Modules | Current responsibility | Reusability |
|---|---|---|
| `transit_scheduler.py` | Linear ephemeris predictions and timing-uncertainty propagation | Reusable scientific core |
| `transit_visibility.py` | Sampled target, Sun, and Moon geometry across observation windows | Reusable scientific core |
| `transit_ranking.py` | Weighted priority score for predicted transits | Reusable heuristic core |
| `transit_schedule.py` | Multi-target prediction, visibility analysis, limits, and ranking | Reusable orchestration core |
| `transit_schedule_exports.py` | CSV, JSON, and iCalendar schedule exports | Reusable data adapter |
| `transit_schedule_visuals.py` | Timeline, altitude, and ranking figures | Reusable presentation component |

### Observation records and support

| Modules | Current responsibility | Reusability |
|---|---|---|
| `observation_log.py` | Validated session/equipment/target records, summaries, JSON import/export, and CSV | Reusable domain/data layer |
| `observation_report.py` | Markdown observation reports | Reusable reporting adapter |
| `i18n.py`, `*_messages.py`, `light_curve_i18n.py`, `transit_schedule_i18n.py` | Four-language interface copy and labels | UI support, not scientific logic |
| `__init__.py` | Empty package marker | No defined public package API |

## UI-only versus reusable components

### Streamlit-coupled UI

Only five source entry points import Streamlit directly:

- `app.py`
- `gaia_dashboard.py`
- `exoplanet_dashboard.py`
- `light_curve_dashboard.py`
- `transit_schedule_dashboard.py`

These modules own widgets, page state, downloads, and rendering order. The four specialist
dashboards are now standalone navigation destinations, but their Streamlit modules still mix UI
orchestration with some pure request-building, formatting, and export helper functions.

### Reusable layers

Most calculations, domain models, parsers, serializers, and Plotly figure builders do not import
Streamlit. They can be called by tests, notebooks, command-line tools, or future APIs. This is a
strong starting point for research software architecture.

Plotly modules are reusable presentation components rather than UI-only code. They are not
headless scientific cores because they return figures and sometimes contain display-oriented
transformations such as marker sizing or label formatting.

### Separation gaps

- `app.py` still contains the approximately 4,000-line Observatory implementation in one callable.
- `schedule.py` and `sky_map.py` combine calculations with Plotly construction.
- `weather.py` combines HTTP access, response parsing, and observing heuristics.
- Catalogue modules combine query construction, transport, parsing, derived calculations, and
  result packaging.
- Dashboard modules contain pure helpers that cannot be imported without loading Streamlit.

These are architecture findings only; Mission 18 does not refactor them.

## External data sources and dependencies

### External data and reference services

| Source | Endpoint or mechanism | Usage | Current provenance state |
|---|---|---|---|
| ESA Gaia Archive | `https://gea.esac.esa.int/tap-server/tap/sync`, table `gaiadr3.gaia_source` | Cone searches and stellar parameters | ADQL is retained; data-release identifier is encoded in the table name; response time/version metadata are not persisted |
| NASA Exoplanet Archive | `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`, table `pscomppars` | Confirmed-planet and host parameters | ADQL is retained; archive snapshot/version and retrieval time are not persisted |
| Open-Meteo | `https://api.open-meteo.com/v1/forecast` | Hourly weather forecast | Attribution and CC BY 4.0 are documented; model/run/version metadata are not retained |
| Astropy built-in ephemeris | `solar_system_ephemeris.set("builtin")` or Astropy `get_body` | Solar System, planner, and transit geometry | Dependency version is available from the environment; ephemeris/table version is not recorded in results |
| Astropy IERS data | Astropy time and coordinate transforms | Earth orientation and time-dependent transforms | Tests disable automatic downloads in affected suites; operational freshness is not explicitly controlled or reported |
| System time-zone database | Python `zoneinfo` | Local-to-UTC conversion | Time-zone name is stored, but tzdata version is not recorded |
| User-supplied photometry | CSV/TSV/TXT upload | Light-curve analysis | Target metadata is supported; observatory, instrument, filter, time scale, and source provenance are not mandatory |

Network access is synchronous and timeout-bounded. No application-level retry, caching,
rate-limit policy, or offline snapshot mechanism was found.

### Declared Python dependencies

| Dependency | Declared range | Role and audit note |
|---|---|---|
| Python | `>=3.12` | CI currently exercises Python 3.12 only |
| Astropy | `>=8.0` | Coordinates, time, ephemerides, Lomb–Scargle, Box Least Squares |
| NumPy | `>=2.0` | Light-curve processing/search and transit sampling |
| pandas | `>=2.2` | Declared, but no direct project import was found |
| Plotly | `>=6.0` | Interactive scientific and planning figures |
| Streamlit | `>=1.45` | Multipage application and dashboards |
| SciPy | no lower bound | Declared, but no direct project import was found |
| pytest | `>=8.0` | Development test runner |
| Ruff | `>=0.11` | Linting and import checks |

There is no lockfile, constraints file, or exact research environment snapshot. Broad minimum
versions make installation convenient but do not guarantee numerical reproducibility over time.

## Existing test coverage summary

The suite contains 43 test files, 437 explicitly declared `test_*` functions, and 702 collected
cases after parametrization. All 702 passed at the Mission 17 baseline.

| Area | Collected cases | Evidence |
|---|---:|---|
| Light-curve models, I/O, processing, period, phase, BLS, diagnostics, exports, figures, i18n, and dashboard | 271 | 15 `test_light_curve*` files |
| Transit prediction, visibility, ranking, schedule, exports, figures, i18n, and dashboard helpers | 174 | 8 transit test files |
| Observer, coordinates, visibility, Solar System, sky map, planner, night schedule, weather, telescope, imaging, logs, reports, and shared i18n | 208 | 16 test files |
| Gaia catalogue and figures | 20 | 2 test files |
| Exoplanet catalogue and figures | 29 | 2 test files |
| **Total** | **702** | **43 test files** |

### What the tests establish

- Input ranges, invalid-data handling, and deterministic serialization are exercised broadly.
- Core geometry and scoring functions have boundary and parametrized tests.
- Light-curve Lomb–Scargle and Box Least Squares tests recover injected synthetic signals.
- Catalogue and weather transport paths use injected or monkeypatched responses rather than live
  services.
- Plotly figures are checked for traces, labels, layout, ordering, and expected values.
- Light Curve and Transit Schedule dashboard behaviour is tested with faked Streamlit surfaces.
- CI runs Ruff and the full pytest suite for pushes and pull requests targeting `main`.

### What is not measured or exercised

- No line, branch, or mutation coverage tool or minimum threshold is configured.
- `app.py` multipage navigation has no automated application-level test.
- Gaia and Exoplanet Streamlit dashboards have no direct dashboard test files.
- There are no live or recorded-contract integration tests for Gaia, NASA, or Open-Meteo.
- There are no published-dataset regression suites or cross-software numerical comparisons.
- There is no property-based testing, static type-checking gate, performance benchmark, or
  large-dataset stress test.
- CI does not test multiple supported dependency versions, operating systems, or Python versions.

Test quantity is strong, but it must not be interpreted as measured scientific accuracy.

## Known assumptions and approximations

### Coordinates and ephemerides

- Horizontal transforms set pressure to zero, deliberately disabling atmospheric refraction.
- Airmass is geometric secant airmass and is omitted near/below the horizon in some modules.
- Solar System positions use Astropy's built-in ephemeris rather than a high-precision external
  kernel.
- Moon illumination is estimated from apparent Sun–Moon angular separation.
- Preset catalogue coordinates and target sizes are static application values.

### Planning, weather, and equipment

- Observation Planner scores are a fixed 100-point heuristic: altitude 45, airmass 20, Moon
  separation 20, darkness 15.
- Planner recommendations omit clouds, transparency, seeing, target magnitude, equipment, and
  exposure requirements.
- The night schedule greedily selects the highest-ranked target at each sample and omits setup,
  slew, transition, exposure, calibration, and weather constraints.
- Weather scores and dew categories are project-defined heuristics over forecast variables; they
  are not calibrated measurements of astronomical seeing or transparency.
- Telescope performance uses idealized Dawes/Rayleigh limits, apparent-field divided by
  magnification, a 7 mm maximum pupil, and a 2×-aperture-per-mm magnification rule.
- Imaging sampling uses fixed seeing-to-pixel thresholds. Mosaic panel counts ignore displayed
  sensor rotation, and preset target dimensions are approximate.

### Catalogue-derived values

- Gaia distance uses direct inversion of positive parallax. It does not apply a parallax
  zero-point correction, Bayesian prior, extinction correction, or uncertainty propagation.
- Gaia absolute magnitude derives from that naive distance and is not extinction corrected.
- Exoplanet density assumes Earth-relative mass and radius values.
- Transit probability uses simplified circular-orbit geometry.
- Temperate classification is a threshold-based educational screen, not a habitability result.
- The exoplanet transit visual is a symmetric trapezoid without limb darkening, stellar activity,
  exposure integration, correlated noise, or instrument effects.

### Time-series photometry

- Uploaded time values are unitless floats; period and duration inherit the same implicit unit.
- Time scale, reference position, barycentric/heliocentric correction, instrument, filter, and
  observatory provenance are not required.
- Invalid rows are skipped and duplicate times retain the first valid row.
- Sigma clipping, normalization, polynomial detrending, Lomb–Scargle, and Box Least Squares are
  analysis tools; their candidates and false-alarm or signal-to-noise metrics do not confirm a
  physical signal.
- Sampling-window aliases, red noise, systematics, and model selection are not modeled directly.

### Transit prediction and ranking

- Transit predictions use a linear ephemeris and constant duration.
- Epoch and period uncertainties are combined in quadrature as independent terms; covariance,
  transit-timing variations, and asymmetric/non-Gaussian uncertainties are not represented.
- Visibility is determined from a finite sample grid, geometric airmass, altitude, and a solar
  darkness threshold.
- Ranking is a transparent but uncalibrated weighted heuristic over geometry, depth, timing,
  brightness, and visibility fractions.

## Validation gaps

### Critical before scientific claims

1. Build reference datasets for coordinates, time, AltAz, Solar System positions, Moon geometry,
   and transit visibility, then compare against authoritative ephemerides or independent tools
   with documented tolerances.
2. Validate light-curve period and transit recovery on published, provenance-preserving datasets,
   including null signals, aliases, gaps, red noise, and known false positives.
3. Define explicit units, time scales, reference frames, and provenance for every scientific input
   and exported result.
4. Establish uncertainty models for catalogue-derived quantities, planning outputs, photometry,
   ephemerides, and transit predictions.
5. Calibrate or clearly bound all planner, weather, equipment, and transit-ranking heuristics
   against observations, literature, or expert-labelled baselines.

### Important for reproducibility and reliability

6. Add coverage measurement and identify untested branches; prioritize application navigation,
   Gaia/Exoplanet dashboards, failure recovery, and scientific edge cases.
7. Add deterministic external-service contract fixtures and optional live integration checks that
   do not gate ordinary offline tests.
8. Record data source, query, retrieval time, service/data-release version, dependency versions,
   and transformation history in scientific exports.
9. Create a pinned or locked reference environment for experiments and publication artifacts.
10. Add performance and memory benchmarks for large catalogues, long light curves, and dense
    transit schedules.

## Architecture risks

| Risk | Evidence | Research impact | Priority |
|---|---|---|---|
| Observatory monolith | `app.py` is 4,063 lines and the default page remains one large callable | Scientific changes are harder to review, isolate, and test | High |
| Mixed UI and domain helpers | Dashboard modules contain both Streamlit calls and pure helper logic | Reuse and headless validation require importing the UI framework | Medium |
| Duplicate scientific concepts | Airmass, Moon illumination, visibility thresholds, and scoring are implemented in multiple modules | Formula or convention drift can create inconsistent results | High |
| Implicit units and time standards | Several APIs exchange bare floats for time, angle, period, duration, magnitude, or flux | Silent unit/time-scale mistakes threaten scientific validity | High |
| Service/parse/science coupling | Gaia, Exoplanet, and Weather modules combine transport, parsing, and transformations | External API changes can be confused with scientific regressions | Medium |
| Synchronous un-cached network calls | No retry, caching, snapshot, or rate-limit strategy was found | Reproducibility and interactive reliability depend on remote state | Medium |
| Unpinned numerical environment | Minimum dependency versions only; no lockfile | Results may drift across installations and future releases | High |
| Undefined package API | Empty `__init__.py` and direct module imports | Research notebooks may couple to unstable internal structure | Medium |
| Partial provenance | Queries are preserved for catalogues, but retrieval/version metadata are incomplete | Results cannot always be reconstructed exactly | High |
| Test-to-validity gap | 702 tests, but no authoritative benchmark suite or coverage metric | Software correctness may be mistaken for scientific validation | High |

## Research-readiness assessment

| Dimension | Assessment | Rationale |
|---|---|---|
| Modular scientific logic | Strong prototype | Most calculations are outside Streamlit and deterministic |
| Defensive software quality | Strong prototype | Broad validation, 702 passing tests, Ruff, and CI |
| Scientific accuracy evidence | Preliminary | Few independent/reference comparisons and no published validation corpus |
| Uncertainty treatment | Uneven | Strongest in light-curve inputs and transit ephemerides; absent from many derived values and scores |
| Data provenance | Partial | Catalogue queries and some schema versions exist, but retrieval and environment metadata are incomplete |
| Reproducibility | Partial | Deterministic tests and exports, but no locked environment or versioned reference data |
| External-service resilience | Preliminary | Bounded requests and parser tests, but no cache/retry/contract snapshots/live checks |
| Architecture for research extension | Moderate risk | Useful cores exist, but the application monolith and duplicated conventions raise change risk |
| Publication readiness | Not ready | Validation protocols, reference results, uncertainty, provenance, and reproducible environments are missing |
| Robotic/operational readiness | Not ready | No hardware control, safety interlocks, calibrated optimization, or failure-management layer |

## Recommended Phase 0 exit criteria

Phase 0 should not be considered complete until the project has:

1. a versioned scientific inventory and public calculation API;
2. explicit unit, time-scale, frame, provenance, and uncertainty conventions;
3. authoritative benchmark datasets with numerical tolerances;
4. a coverage baseline and application-level smoke/navigation tests;
5. recorded external-service contracts and reproducible offline fixtures;
6. a pinned research environment and machine-readable dependency snapshot;
7. a documented validation plan mapping every scientific claim to evidence;
8. a decision record separating educational heuristics from calibrated research algorithms.

Mission 18 establishes the baseline and identifies these gaps. It deliberately does not implement
the refactors or validation programme.
