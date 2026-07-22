# Exoplanet Transit Observation Scheduler

The scheduler predicts, evaluates, ranks, visualizes, and exports exoplanet transit observing windows.

## Capabilities

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
