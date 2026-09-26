# Mission 33 — Celestial Coordinate Validation Benchmark

## Purpose and scope

This continues Phase 2 after Mission 32 on the existing Phase 0–8 roadmap.
It validates public AstroScope input handling, WGS84 observer positions, UTC
instants, local apparent sidereal time, ICRS-to-horizontal transformations,
altitude, azimuth, horizon classification and the approximate secant airmass
model. Production scientific code is unchanged. No scientific defect was found
in the benchmark's supported domain. The earlier civil-time and interval
validation evidence is preserved.

The evidence comprises **768 astronomical cases** and **13 separate rejection
contracts**. Reference generation does not call AstroScope, Astropy or ERFA.
The runner exercises the production functions, and neither tests nor CI regenerate
references. The [canonical record](../../../validation/results/celestial_coordinates_reference_run.json)
contains all inputs, expectations, errors, exclusions, statistics and provenance.

## Dataset and conventions

Eight WGS84 sites cover Tokyo, Greenwich, Paranal, an idealized equatorial site,
northern and southern high latitudes, and longitudes +179.999 and −179.999 degrees.
Coordinates/elevations are fixed benchmark inputs, not surveyed observatory data.

Four seasonal dates in 2024 are sampled at 00:00:00, 06:15:30.5 and 23:59:59.5 UTC.
At the date-line sites an additional case at 00:00:00.5 on the following day forms
an explicit one-second midnight crossing. The fixture covers:

- 576 grid cases, including RA wraparound, northern/southern declinations,
  celestial equator, near-polar/circumpolar directions and targets below the horizon.
- 96 cases close to culmination, including azimuth values on both sides of north.
- 84 equatorial cases at independently solved reference altitudes −0.1, +0.1,
  4.9, 5.1, 19.9, 20.1 and 89.5 degrees.
- Four exactly-on-reference-horizon cases and eight next-day UTC cases.

Inputs alternate between decimal unit strings, numeric strings with whitespace,
and sexagesimal strings. Independent decimal RA/Dec expectations verify parsing
as well as the transformed result. Thirteen rejected inputs cover malformed,
nonfinite and out-of-range coordinates and out-of-range observer positions;
these are public API contract checks, not astronomical reference measurements.

### Independent reference

Skyfield **1.55** uses **JPL DE421**, distributed in skyfield-data **7.0.0**.
The fixture records NumPy, jplephem and sgp4 versions and SHA-256 hashes for the
kernel, generator and Earth-orientation snapshot. AstroScope uses Astropy/ERFA's
built-in Earth ephemeris. WGS84 geocentric site positions come from Skyfield's
`itrs_xyz`; production positions come from `create_earth_location`.
JD/MJD references use Gregorian datetime arithmetic relative to the Unix epoch.
The supported time API's formatted UTC strings have whole-second precision;
the JD/MJD checks separately verify the retained fractional-second instant.

Star inputs are fixed ICRS directions with zero proper motion, radial velocity and
parallax. Both engines calculate **apparent topocentric, unrefracted** directions;
this is not an uncorrected geometric RA/Dec rotation. Azimuth increases eastward
from north. Angular residuals wrap at 360 degrees; sidereal residuals at 24 hours.

### Earth orientation, UTC and numerical precision

A committed 16-row IERS B snapshot is extracted from astropy-iers-data
`0.2026.9.21.0.56.25`. The snapshot records its full source-file checksum, URL,
filename, distribution version and units. Each observation is bracketed by
consecutive daily records; sparse gaps between seasons are never interpolated
for a test instant. Both paths linearly interpolate DUT1 and polar motion.

For these 2024 dates TAI−UTC = 37 seconds and TT−UTC = 69.184 seconds. Skyfield's
TT−UT1 is set to 69.184 − DUT1 at each instant. Production Astropy uses the same
IERS observations under a temporary offline table. The harness restores prior
settings, including on exceptions. Leap-second instants themselves are excluded:
Python datetime cannot represent 23:59:60. No claim is made for future leap tables
or arbitrary epochs outside the fixture.

Calculations use float64. Decimal coordinate strings retain 15 places and
sexagesimal seconds 12 places. JD/MJD use double precision; their 0.1 ms bound
allows representation rounding. Shared IERS observations and astronomical
conventions mean this is independent **software agreement**, not independent
measurement of the sky or a proof of absolute physical accuracy.

## Acceptance criteria and difficult geometries

Bounds were chosen before comparing the values, as planner regression criteria.
They are not fitted to residuals and must not be automatically relaxed.

| Metric | Limit | Justification |
|---|---:|---|
| WGS84 geocentric observer components | 0.000001 m | Same datum; floating-point conversion allowance |
| Parsed RA / Dec | 0.0000001 arcsec | Formatting and floating-point parsing only |
| Altitude and great-circle sky direction | 2 arcsec | Sub-arcminute planning, allowing model differences |
| Azimuth component | 10 arcsec | Component sensitivity increases near zenith |
| Local apparent sidereal time | 0.05 seconds of time | 0.75 arcsec of Earth rotation |
| JD / MJD | 0.0001 seconds | Floating-point date representation allowance |
| Secant airmass at altitude ≥20° | 0.00005 relative | Propagated coordinate error with margin |
| Secant model only at 5° ≤ altitude <20° | 0.0002 relative | Larger derivative at low altitude |

Atmospheric refraction is disabled in both paths. This deliberately avoids a
weather-dependent horizon correction. Physical refraction near the horizon is
not validated.

**Zenith:** 12 cases exceed absolute altitude 89°. Their azimuth-component limit
is explicitly excluded because that coordinate becomes ill-conditioned; altitude
and great-circle direction still must pass. Raw azimuth errors remain in every
record. Component statistics disclose their denominator of 756 and 12 exclusions.
There are no exact-zenith cases, where azimuth is undefined.

**Horizon:** five cases are within the 2-arcsec altitude tolerance band of zero:
the four deliberate horizon cases plus `equator_2024-09-22_1_04` at approximately
−0.752 arcsec. They are labelled `boundary_indeterminate_within_coordinate_tolerance`.
All numerical coordinate checks remain enforced. Independent sign agreement is
required for the other 763 cases. Output boolean/status consistency with the
returned altitude is checked for every case. Exact zero follows production's
`altitude <= 0` below-horizon policy without claiming that an uncertain sky
position has a scientifically definite sign.

**Airmass:** 297 cases at altitude ≥20° compare production to `1/sin(reference
altitude)`, a plane-parallel approximation. This is a model calculation check,
not validation of the actual atmospheric path. Another 102 cases at 5–20° are
labelled `low_altitude_model_only`; they are reported separately and support only
regression of the existing secant model. For 369 cases below 5°, including all
below-horizon positions, `airmass=None` is required. The approximation becomes
poor near the horizon and is not extrapolated there.

## Measured results

The executed benchmark passes all **768/768** astronomical cases and **13/13**
input contracts. Statistics below come from the generated record; errors in this
table are arcseconds. Pass percentages refer to eligible cases, not exclusions.

| Quantity | MAE | Median | RMS | Maximum | Within tolerance |
|---|---:|---:|---:|---:|---:|
| Altitude | 0.000132109 | 0.000103596 | 0.000180918 | 0.000386844 | 768/768 (100%) |
| Azimuth | 0.00000637049 | 0.00000407109 | 0.00000969513 | 0.0000398056 | 756/756 (100%) |

Worst altitude case: `paranal_2024-03-20_2_00`, 2024-03-20 23:59:59.5 UTC,
RA 0.0001 hours, Dec 0°. Worst eligible azimuth case:
`arctic_2024-09-22_0_08`, 2024-09-22 00:00 UTC, near culmination at high declination.
The record preserves full observer and coordinate details for these scenarios.

Maximum great-circle error is 0.000386846 arcsec; sidereal-time error is
0.000000775674 seconds. JD/MJD differences are zero for this fixture. Maximum
observer component difference is approximately 3.03 nanometres. All eligible
parsing, observer-position and airmass checks pass their respective tolerances.
These residuals are computational agreement, not measured physical accuracy.

## Reproduction and provenance

From a checkout of this branch with Python 3.12:

```sh
python -m venv .venv
.venv/bin/python -m pip install -c validation/requirements-celestial.txt -e '.[dev,validation]'
.venv/bin/python -m validation.celestial_coordinates --output work/celestial-run.json
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
```

Only installation needs package access. The benchmark runs offline without
Skyfield or its kernel installed. An actual subprocess test blocks network
connections and Skyfield imports, then executes the full CLI. Tests also check
manifest/fixture integrity, reference provenance, wrapped angles, hard geometries,
state restoration and failures caused by perturbed coordinates, time, horizon and
airmass outputs. NaN/Inf failures remain visible as null values with failed
metrics in strict JSON; they are not silently removed from aggregate statistics.

The existing quality gate runs the new benchmark and retains its record.
`validation/requirements-celestial.txt` constrains the canonical environment;
ordinary CI also tests the allowed dependency range. The canonical run is made in
a fresh environment installed from those constraints. The record identifies
implementation/checkout commits, dirty state, source/input hashes, installed
versions, time, runtime, per-case absolute errors, MAE/median/max/RMS, pass counts,
percentages, exclusions and worst-case scenarios. Implementation and evidence
are committed separately so the evidence can identify an already committed
implementation without a self-referential commit hash.

To explicitly reproduce reference generation (never part of ordinary CI):

```sh
.venv/bin/python -m pip install -r validation/reference_generation/reference-requirements.txt
.venv/bin/python -m validation.reference_generation.extract_celestial_eop
.venv/bin/python -m validation.reference_generation.celestial_coordinates
```

The EOP extractor refuses a different source-file hash. Install the constrained
Astropy/IERS data versions first. Reference regeneration is byte-for-byte checked.
For an intentional dataset change, review the fixture/manifest diffs and update
`EXPECTED_MANIFEST_SHA256` in the runner after review; do not rewrite it as part
of routine tests.

## Quality gate and next mission

Mission 33 adds **807 collected validation tests**. The full suite has **1,808
passing tests**. Ruff, the observer-time/civil-time/schedule-interval benchmarks,
and documentation-link/whitespace checks pass. A one-line existing UI test repair
uses session-state membership instead of Streamlit's removed internal
`filtered_state` attribute; application behavior is unchanged.

Phase 2 remains active; Phases 3–8 have not begun. Mission 34 — Solar, Lunar,
and Twilight Validation — is proposed only. It requires a new instruction before
implementation. This mission does not validate moving targets, finite distances,
proper motion, real refraction, rise/set events, light curves or scheduling quality.

## Sources

- [Skyfield positions and apparent Alt/Az](https://rhodesmill.org/skyfield/positions.html)
- [Skyfield Earth orientation and polar motion](https://rhodesmill.org/skyfield/accuracy-efficiency.html)
- [Skyfield time scales](https://rhodesmill.org/skyfield/time.html)
- [Astropy AltAz and secant airmass](https://docs.astropy.org/en/stable/api/astropy.coordinates.AltAz.html)
- [Astropy IERS handling](https://docs.astropy.org/en/stable/utils/iers.html)
- [JPL planetary ephemerides](https://ssd.jpl.nasa.gov/planets/eph_export.html)
