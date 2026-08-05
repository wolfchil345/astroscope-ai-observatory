# Mission 32 — Observation-Schedule Interval Validation Evidence

## Independent IANA 2026c Reference Evidence

The committed 37-case fixture is deterministically generated from pinned IANA
TZDB 2026c source data, the release's `zic` and `zdump` tools, and plain UTC
datetime arithmetic. The checked-in captured `zdump` transformation is tested
when CI does not provide the source archives; archive mode verifies both pinned
archive hashes and rebuilds the same input evidence.
It records ordinary intervals, gaps, folds, UTC ordering, elapsed duration,
fixed UTC grids, final sentinels, and Lord Howe's 1,800-second transitions.
Stage A never imports AstroScope scheduling code or uses Python `ZoneInfo` as
an expected-value oracle.

## Mission 29 Implementation Agreement

Stage B runs the Mission 29 scheduler against the committed independent fixture.
It verifies strict endpoint resolution, fold selection, gap rejection, UTC
ordering, the 18-hour cap, UTC sampling, half-open occupancy, UTC block
continuity, block duration, and scheduled-minute aggregation. It records both
the Mission 29 origin commit and the current execution checkout.

## AstroScope Regression Semantics

The normal benchmark requires no network service and records fixture/manifest
integrity, benchmark-input provenance, Python/tzdata versions, the canonical
empty `PYTHONTZPATH` / `zoneinfo.TZPATH` environment, TZif hashes, and execution
provenance. It records that network is not required; it does not claim to
enforce network isolation. The final grid endpoint is a display/evaluation
sentinel, while occupancy remains half-open.

## Claim Boundary

Mission 32 may claim independently generated pinned-IANA-2026c schedule
interval evidence, implementation agreement with its committed cases,
transition-aware UTC ordering and elapsed duration, fixed-UTC sampling,
half-open occupancy, and reproducible offline Stage B execution.

It does not validate astronomical target ranking, ephemerides, visibility,
planner quality, weather-provider behavior or skill, observation-log behavior,
robotic operations, or replace Mission 27 endpoint evidence.
