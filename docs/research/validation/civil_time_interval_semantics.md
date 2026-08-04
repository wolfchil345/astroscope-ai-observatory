# Mission 28 — Civil-Time Interval Semantics and Validation Design

## Scientific Purpose

A civil-time interval cannot safely be treated as two ordinary local datetimes.
Around a named-zone UTC-offset transition, either endpoint can be ambiguous or
nonexistent, and elapsed UTC duration can differ from an apparent wall-clock
duration. An interval therefore needs an endpoint-resolution policy as well as
an inclusion and duration policy.

Mission 28 defines intended semantics and validation design only. It changes
no production behavior, scientific calculation, provider request, persistence
format, export, or user interface. The current workflows remain unvalidated
for transition-zone interval handling until later implementation and evidence
missions are complete.

## Terminology

- **Civil endpoint:** a local date, local time, named timezone, and, when
  necessary, a PEP 495 fold selection.
- **Normal endpoint:** a civil endpoint that maps to one real UTC instant.
- **Ambiguous endpoint:** a civil endpoint in a backward offset transition
  that maps to two real UTC instants.
- **Nonexistent endpoint:** a civil endpoint in a forward offset transition
  that maps to no real UTC instant.
- **Fold:** the explicit `0` or `1` selection identifying one occurrence of an
  ambiguous local clock value.
- **Wall-clock ordering:** ordering of local date/time fields without using
  resolved UTC instants.
- **UTC ordering:** ordering of resolved physical instants.
- **Elapsed duration:** `end_utc - start_utc`.
- **Interval inclusion:** the rule deciding whether a boundary or sample is
  inside an interval.
- **Discrete forecast sample:** an external provider's timestamped point
  selected by a request window; it is not itself an elapsed-duration interval.
- **Transition-spanning interval:** an interval whose resolved endpoints bound
  a UTC-offset transition.

## Audited Workflows

### Observation scheduling

Audited files: `src/astroscope/schedule.py`, `src/astroscope/planner.py`,
`src/astroscope/observatory_dashboard.py`, and `tests/test_schedule.py`.

Current behavior attaches `ZoneInfo` directly to start and end local values.
It infers an overnight end date from a wall-clock comparison, converts both
values to UTC, builds a fixed UTC sampling grid, and appends the final endpoint
to that grid. Each grid value is then forwarded to the planner as reconstructed
local date/time fields. The planner uses the legacy
`local_datetime_to_utc()` converter. Schedule-block duration and continuity
also use local-datetime arithmetic and comparison.

This produces a useful ordinary-night grid, but it does not define strict
fold/gap semantics and can lose a resolved fold when a planner call is rebuilt
from local fields.

### Weather request/filter window

Audited files: `src/astroscope/weather.py`,
`src/astroscope/observatory_dashboard.py`, and `tests/test_weather.py`.

Current behavior requests provider data by local calendar date. It attaches
`ZoneInfo` directly to local start and end values. Offset-free provider
timestamps are also given the selected timezone directly, and matching points
are selected with an inclusive local comparison. A repeated local hour cannot
be assigned a fold identity without authoritative provider evidence; this
document does not assume such a provider contract.

### Observation-log intervals

Audited files: `src/astroscope/observation_log.py`,
`src/astroscope/observatory_dashboard.py`, `tests/test_observation_log.py`,
and `tests/test_observatory_dashboard.py`.

Current records store aware local datetimes. Start/end ordering and containment
use local-datetime comparison, and durations use local-datetime subtraction.
JSON and CSV preserve ISO offsets, while a session also stores `timezone_name`.
Explicit endpoint folds and canonical UTC endpoints are not persisted as
separate provenance fields.

### Excluded UTC date-range workflow

`src/astroscope/transit_schedule_application.py` and
`tests/test_transit_schedule_application.py` construct a UTC date-range
boundary directly. They are outside Mission 28 because they are not a
named-zone civil-time interval workflow.

## Locked Cross-Workflow Invariants

Future named-zone civil intervals must have one named timezone and two
independently resolved civil endpoints. Each endpoint has its own fold.
Normal endpoints resolve without a fold; ambiguous endpoints require fold `0`
or `1`; and nonexistent endpoints reject for every fold. No workflow may
silently shift a nonexistent civil value.

Seconds and microseconds must be preserved. `start_utc < end_utc` is required:
equal UTC instants and reversed UTC intervals reject. Naïve wall-clock ordering
never overrides UTC ordering. The future domain boundary will require explicit
endpoint dates for overnight intervals rather than inferring them from a time
comparison. Mission 26 endpoint exceptions and messages remain authoritative.

## Workflow-Specific Policies

### Observation scheduling

Scheduling will independently resolve start and end endpoints, reject an
unselected fold or any gap, and use `start_utc` and `end_utc` as the physical
observing window. Samples will advance in fixed elapsed UTC increments.
Occupancy slots are half-open, `[start_utc, end_utc)`; the final endpoint may
remain as an evaluation or display sentinel only. Planner computation must
receive or preserve the resolved UTC instant instead of reconstructing it from
local fields. Schedule-block durations must derive from UTC instants.

### Weather

Weather will retain provider calendar-date requests and treat matching results
as a discrete forecast-sample selection envelope, not an elapsed duration.
Fold behavior remains undefined until authoritative provider timestamp
semantics or a committed provider-contract fixture exists. Current inclusive
selection is observed behavior only, not a validated transition policy.
Weather correction is deferred.

### Observation logs

Observation logs will preserve original civil endpoints and selected folds as
provenance, resolve canonical UTC endpoints, and use `[start_utc, end_utc)`.
Duration, ordering, containment, and summaries will derive from UTC. Displays
may round-trip to the original civil endpoints. Any persistence change requires
an explicit schema-version and backward-compatibility policy.

## Proposed Future Domain Boundary

The following is a future internal boundary, not a Mission 28 implementation:

```python
@dataclass(frozen=True, slots=True)
class CivilIntervalEndpoint:
    local_date: date
    local_time: time
    fold: int | None = None

@dataclass(frozen=True, slots=True)
class CivilIntervalRequest:
    timezone_name: str
    start: CivilIntervalEndpoint
    end: CivilIntervalEndpoint

@dataclass(frozen=True, slots=True)
class ResolvedCivilInterval:
    request: CivilIntervalRequest
    start_utc: datetime
    end_utc: datetime
    elapsed: timedelta

def resolve_civil_interval(
    request: CivilIntervalRequest,
) -> ResolvedCivilInterval: ...
```

The generic resolver is workflow-neutral; schedule, weather, and log adapters
own their respective semantics. No package-root export is proposed. Dedicated
interval-order errors may be added later, but Mission 26 endpoint errors must
be preserved rather than wrapped into vague generic errors.

## Inclusion and Duration Matrix

| Workflow | Inclusion | Duration | Selection/provenance | Transition status |
|---|---|---|---|---|
| Scheduling | Half-open | Elapsed UTC | UTC increments; optional final sentinel | Future strict policy |
| Weather | Discrete selection envelope | Not applicable | Currently inclusive local selection | Pending provider evidence |
| Observation log | Half-open | Elapsed UTC | Original civil endpoints and folds | Future strict policy |

## Required Edge-Case Matrix

Future work must specify and test expected behavior for ordinary same-offset
intervals, UTC date crossing, explicit overnight intervals, seconds and
microseconds, zero-length and reversed intervals, one or both ambiguous
endpoints, each fold for an ambiguous start or end, and one or both nonexistent
endpoints.

The matrix must also cover the New York spring gap and fall fold, London fall
fold, Lord Howe's 1,800-second gap and fold, intervals spanning an offset
transition, UTC ordering that differs from naïve wall ordering, repeated local
labels on a UTC sample grid, serialization round trips, legacy-schema imports,
and workflow-specific display/export behavior. This mission deliberately does
not invent future production test names.

## Independent Validation Strategy

IANA 2026c remains the pinned reference and tzdata 2026.3 remains the Python
runtime reference. Mission 27 endpoint evidence may be cited, but it is
immutable and does not validate interval behavior. Future interval validation
requires its own fixture, manifest, benchmark harness, canonical record,
report, and CI artifact.

Independent expected values must use compiled `zic`/`zdump` transition evidence
and plain datetime arithmetic. The future benchmark must run without network
access. Weather provider evidence is separate from IANA interval evidence.

## Planned Mission Sequence

The following are recommendations, not started missions:

1. **Mission 28 — Civil-Time Interval Semantics and Validation Design**
2. **Mission 29 — Strict Observation-Schedule Interval Boundary Resolution**
3. **Mission 30 — Observation-Log Interval Model and Fold-Provenance Persistence**
4. **Mission 31 — Weather Interval Provider-Contract Evidence and Correction**

## Test and CI Plan

Mission 28 adds zero production tests; the clean total remains 791. It makes
no CI workflow change, and the existing Quality Gate remains required. Later
implementation is expected to add approximately 45–60 tests across the
separated missions. Future interval evidence will use a separate artifact.

## Immutable Evidence

Mission 25 and Mission 27 evidence remain immutable: `validation/observer_time.py`,
`validation/civil_time.py`, their manifests, fixtures, canonical records,
reports, and validation tests. Mission 28 neither changes nor extends their
scientific claim boundaries.

## Explicit Exclusions

Mission 28 excludes production code, UI changes, translations, session-state
changes, export or schema changes, weather-provider adapter changes,
package-root exports, timezone-list expansion, astronomy calculations, Mission
29 implementation, and any change to Mission 25 or Mission 27 evidence.

## Acceptance Criteria

Acceptance requires explicit cross-workflow endpoint, fold, gap, ordering,
overnight, inclusion, duration, persistence, display, and export semantics;
workflow-specific policies where purposes differ; a complete edge-case and
independent-validation plan; a recorded implementation split and immutable
evidence boundary; and an active Phase 2 roadmap entry. These criteria define
design readiness only, not production correctness or scientific validation of
intervals.

## Limitations

This document defines intended future semantics. It does not establish
production correctness, provider correctness, or scientific validation of
civil-time intervals.
