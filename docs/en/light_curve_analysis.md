🌐 Language: English

# Astronomical Light-Curve Analysis Laboratory

The light-curve laboratory imports astronomical time-series photometry and provides tools for inspecting, cleaning, and analysing variable signals.

## Supported data

The dashboard accepts CSV, TSV, and TXT uploads. CSV with a header row is the reference format.

A dataset requires:

- A numerical observation-time column
- A numerical flux or magnitude column
- At least three valid, unique observations

An uncertainty column is optional.

The laboratory supports both flux and magnitude photometry. Magnitude plots use the astronomical convention in which brighter values appear higher.

## Current dashboard workflow

1. Upload a light-curve file.
2. Enter the target name.
3. Select flux or magnitude photometry.
4. Allow AstroScope to detect likely time, value, and uncertainty columns.
5. Inspect the raw light curve.
6. Optionally apply three-sigma clipping.
7. Optionally normalize the photometric values.
8. Compare the processed curve with the original observations.

Invalid rows are skipped. Duplicate observation times use the first valid row.

## Analysis engine

The scientific modules also provide:

### Period search

- Lomb–Scargle periodogram calculation
- Configurable minimum and maximum periods
- Ranked periodic-signal candidates
- False-alarm probability estimates
- Optional uncertainty-weighted analysis

### Phase analysis

- Phase folding with a selected period and epoch
- Cycle tracking
- Equal-width phase binning
- Optional uncertainty-weighted bin values

### Transit analysis

- Box Least Squares transit search
- Ranked candidate periods, durations, depths, and signal-to-noise values
- Folded transit models
- In-transit and out-of-transit diagnostics
- Residual statistics

### Exports

Analysis results can be represented as CSV or JSON, including:

- Period candidates
- Transit candidates
- Transit diagnostic observations
- Scientific-analysis summaries

## Scientific cautions

Detected periods and transit-like features are candidates, not confirmed astrophysical discoveries.

Reliable interpretation requires attention to:

- Consistent time standards and units
- Observation cadence and baseline
- Sampling aliases and data gaps
- Instrumental systematics
- Stellar variability
- Detrending choices
- Independent observations and validation

False-alarm probabilities and transit signal-to-noise values should not be treated as proof of a physical signal.

## Implemented files

- `src/astroscope/light_curve.py`
- `src/astroscope/light_curve_io.py`
- `src/astroscope/light_curve_processing.py`
- `src/astroscope/light_curve_period.py`
- `src/astroscope/light_curve_phase.py`
- `src/astroscope/light_curve_transit_search.py`
- `src/astroscope/light_curve_transit_diagnostics.py`
- `src/astroscope/light_curve_visuals.py`
- `src/astroscope/light_curve_analysis_visuals.py`
- `src/astroscope/light_curve_exports.py`
- `src/astroscope/light_curve_analysis_exports.py`
- `src/astroscope/light_curve_dashboard.py`
- `src/astroscope/light_curve_i18n.py`
- `tests/test_light_curve*.py`
