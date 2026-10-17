# Exoplanet Transit Observation Scheduler

The default workflow previews nominal transit events in an explicitly declared
source time coordinate. It preserves source metadata and distinguishes unknown
uncertainty from zero. These predictions are not UTC observing times.

## Timing workflows

- **Source-coordinate preview (default):** enter a source identifier, parameter
  set, reference/version, coordinate and decimal epoch/period/duration values.
  Mark an uncertainty as supplied only when its value and interpretation are
  known. Downloads preserve the source coordinate and unknown values. Visibility,
  ranking and UTC/calendar export are unavailable until an observer-arrival
  adapter has independent validation.
- **Legacy scheduler:** select it explicitly and acknowledge its unvalidated UTC
  and uncertainty assumptions. It retains the previous numerical behavior; it
  must not be used to interpret unconverted BJD/HJD values as observing times.
  CSV/JSON/calendar exports now carry an unvalidated timing label.

The interface supports English, Japanese, Korean and Thai. Switching workflows,
revoking acknowledgement or submitting an invalid replacement clears stale
results. Source-coordinate JSON is an unresolved prediction record, not a
schema upgrade or conversion of a legacy observing schedule.

See the [Mission 37 boundary and migration notes](research/validation/strict_transit_timing_boundary.md)
for supported input domains, API behavior and remaining scientific limitations.

## Legacy scheduler capabilities

The scheduler can:

- Predict transit midpoint, ingress, egress, and observation windows
- Propagate orbital-period and reference-epoch timing uncertainty
- Calculate target altitude, azimuth, and airmass
- Evaluate astronomical darkness using solar altitude
- Calculate Moon separation and illumination
- Rank predicted events by observing priority
- Display interactive timeline, altitude, and score visualizations
- Export schedules as CSV, JSON, and iCalendar
- Display the interface in English, Japanese, Korean, and Thai

## Running the application

Run this command from the repository root:

    make run

## Running quality checks

    make checks

## Important note

Long-term predictions can accumulate timing uncertainty when orbital-period uncertainty is nonzero.
