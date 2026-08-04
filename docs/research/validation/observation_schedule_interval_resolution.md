# Mission 29 — Observation-Schedule Interval Resolution

## Purpose

Mission 29 corrects the observation scheduler's handling of named-zone civil
time intervals. It is a production correction supported by regression evidence;
it is not an authoritative external interval-validation claim.

## Confirmed Fall-Back Defect

Before this correction, the scheduler generated its grid in UTC but calculated
block duration and continuity with same-zone local datetime arithmetic. For
`America/New_York`, `2026-11-01 00:00` through `04:00`, the physical window is
300 minutes while local subtraction reports 240 minutes. A fully occupied block
therefore underreported both its duration and `scheduled_minutes`.

## Strict Endpoint Contract

Scheduling now accepts a schedule-specific request with explicit start and end
dates, local times, timezone, and independent optional folds. Each endpoint is
resolved through the Mission 26 strict civil-time resolver.

- Normal endpoints resolve without a fold.
- Ambiguous endpoints require fold 0 or 1 independently.
- Nonexistent endpoints reject and are never shifted.
- Resolved instants must satisfy `start_utc < end_utc`.
- Physical elapsed duration cannot exceed 18 hours.
- Seconds and microseconds are preserved in strict schedule data.

The historical `create_local_time_grid()` and
`calculate_observation_schedule()` entry points remain compatibility wrappers
for ordinary callers. They retain historical overnight date inference, but now
reject ambiguous and nonexistent endpoints that cannot be represented safely.

## Sampling and Occupancy

The strict grid advances in fixed elapsed UTC increments from `start_utc` to
`end_utc`. Occupancy slots are half-open, `[start_utc, end_utc)`. The final end
instant remains an evaluation and display sentinel, preserving the previous
timeline behavior.

`ScheduleBlock` retains useful aware local start, end, and peak values and now
also records canonical UTC start and end instants. Block continuity, ordering,
duration, and aggregate scheduled minutes derive from those UTC fields.

## Planner and Visualization

The planner remains unchanged. PEP 495 fold identity survives the scheduler's
existing local date/time forwarding route: both repeated New York `01:00`
occurrences reach distinct UTC planner instants. Regression tests lock that
behavior, including seconds and microseconds.

Timeline figures now use UTC timestamps as their chronology authority while
displaying offset-bearing local times. This avoids incorrect lexical ordering
of London's repeated local hour, where `01:00+01:00` is physically earlier than
`01:00+00:00`.

## Observatory Reachability

The Observatory adds only the transition reference zones needed to exercise
the policy: `America/New_York`, `Europe/London`, and
`Australia/Lord_Howe`. It adds explicit schedule start/end dates and independent
endpoint occurrence selectors only when an endpoint is ambiguous. A
nonexistent schedule endpoint blocks generation with schedule-specific
four-language feedback.

No general IANA selector, schedule export schema, weather behavior, or
observation-log behavior is introduced.

## Transition Coverage

Regression coverage includes New York spring and fall transitions, London
fall-back chronology, and Lord Howe's 30-minute fold and gap. These cases
ensure the implementation does not assume one-hour transitions or use naïve
wall-clock ordering as physical ordering.

## Limitations and Next Evidence Boundary

Mission 29 validates implementation behavior with project regression tests. It
does not add an independent interval fixture, manifest, benchmark harness,
canonical record, report, or CI artifact. That work remains reserved for
**Mission 32 — Observation-Schedule Interval Validation Evidence and
Benchmark**.

Mission 25 and Mission 27 evidence remain immutable and retain their original
scientific claim boundaries.
