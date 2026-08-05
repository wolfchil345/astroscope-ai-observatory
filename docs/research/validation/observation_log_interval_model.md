# Mission 30 — Observation-Log Interval Model and Fold-Provenance Persistence

## Purpose and claim boundary

Mission 30 corrects the production observation-log interval model and records
regression evidence for that correction. It is not independent authoritative
civil-interval scientific validation, and it does not claim Mission 32
evidence, which does not yet exist.

## Reproduced pre-correction behavior

The former model compared and subtracted aware local datetimes that shared a
`ZoneInfo` object. Python therefore used wall-clock arithmetic around offset
transitions. A New York session from `2026-11-01 00:00-04:00` to
`04:00-05:00` is physically 300 minutes but previously summarized as 240.
A target from repeated `01:00` fold 0 to repeated `01:00` fold 1 is
physically 60 minutes but was rejected as equal. Spring transitions could
overstate duration, and directly attached nonexistent local values could be
accepted.

## Strict endpoint and interval policy

An observation-log interval has two independently resolved civil endpoints.
Each request retains local date, local time, and an optional fold. A normal
endpoint requires a null fold, an ambiguous endpoint requires fold 0 or 1,
and a nonexistent endpoint always rejects. The existing Mission 26 strict
civil-time resolver remains the authority; no gap is shifted silently.

Resolved endpoints retain the named timezone, local named-zone datetime, and
canonical UTC instant. `start_utc < end_utc` is required. Durations, ordering,
session summaries, and target-within-session checks use UTC instants. Session
and target intervals use half-open `[start_utc, end_utc)` semantics: an
observation may begin with its session or end exactly with it, but may not
physically extend outside it. Target overlap is deliberately not validated.

## Compatibility-aware aware datetimes

Existing `ObservationSession` and `TargetObservation` constructors retain
their `started_at_local` and `ended_at_local` inputs. An aware legacy datetime
is already instant-bearing, so it may be accepted when its local label, offset,
and physical instant match exactly one valid candidate in the session named
zone. This differs from new civil UI input, where an ambiguous label must
receive an explicit user fold. Normal endpoints normalize to null fold;
nonexistent or inconsistent local/offset/zone values reject.

Each session has one authoritative named timezone. Its target observations are
validated against that same timezone provenance.

## Schema version 2 and migration

Schema v2 keeps the prior offset-bearing `started_at_local` and
`ended_at_local` values and adds endpoint provenance for sessions and targets:

- explicit fold (`null`, `0`, or `1`);
- canonical UTC ISO 8601 using `Z`.

The importer accepts `Z` and `+00:00`, and verifies every redundant local,
fold, offset, named-zone, and UTC field. Seconds and microseconds are kept.

Schema v1 remains importable. Migration parses the offset-bearing local ISO,
uses the session `timezone_name`, classifies the wall label, and verifies that
the stored instant and offset match a valid named-zone candidate. Ambiguous v1
values infer a fold only when exactly one candidate matches. Nonexistent,
impossible, or inconsistent provenance rejects rather than being repaired.
Successful migration restores named-zone datetimes in memory.

## CSV, reports, and dashboard

CSV v2 retains every earlier column in its existing order and appends schema,
fold, and canonical UTC columns. Reports retain their existing structure,
display civil timestamps and offsets, add fold text only when meaningful, and
obtain duration figures from the UTC-authoritative models.

The existing free-text valid-IANA timezone entry remains unchanged. Session
start and end dates/times remain explicit. Target observations now have
explicit start date/time and end date/time; overnight target dates are no
longer inferred. The four endpoint roles are classified independently.
Ambiguous endpoints display UTC candidates and offsets and require a separate
occurrence selection. Nonexistent endpoints show an observation-log error and
do not mutate saved target state. Their session-state keys are isolated under
`mission12_*`.

## Regression coverage and limitations

Mission 30 adds 48 collected regression cases: 31 model/interval cases, 10
persistence cases, 3 CSV/report cases, and 4 dashboard/localization cases.
The matrix covers ordinary compatibility, New York, London, Lord Howe, fold,
gap, precision, ordering, containment, schema migration, export, reporting,
and UI behavior.

This correction does not add a generic shared civil-interval module, change
Mission 29 scheduling, change weather behavior, expand timezone selection, or
create independent interval validation fixtures, manifests, benchmarks, or
canonical records. Mission 31 remains weather-only and Mission 32 remains the
future observation-schedule evidence mission.
