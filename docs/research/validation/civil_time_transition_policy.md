# Observer-Instant Civil-Time Transition Policy

## 1. Correctness Defect

A named local civil time is not always a unique physical instant. During a backward UTC-offset
transition, one wall-clock value can identify two UTC instants. During a forward transition, an
interval of wall-clock values does not identify any UTC instant. Python `ZoneInfo` permits an
offset to be attached to either kind of input, so conversion alone does not demonstrate that the
input represents one real instant.

Before Mission 26, AstroScope's compatibility converter accepted both situations. It preserved an
explicit PEP 495 fold for ambiguous times, but it could silently use the default fold when no
choice was made and could return a UTC value for a nonexistent local time that did not round-trip
to the supplied clock reading.

## 2. Mission 25 Pre-Correction Evidence

The [Mission 25 Observer-Time Validation Baseline](observer_time_validation.md) is immutable
historical evidence. It validated the unchanged `local_datetime_to_utc()` function against a
pinned IANA 2026c reference:

- seven normal or date-crossing conversions passed;
- two explicit New York fall-back folds passed;
- two spring-forward gaps were characterized as expected unsupported behavior; and
- the established invalid-timezone error passed.

Mission 25 did not validate the strict resolver introduced by Mission 26. Its fixture, manifest,
benchmark implementation, canonical run record, and report remain unchanged.

## 3. Strict Classification Method

`classify_local_datetime()` accepts a date, time, and named timezone. It discards any fold carried
by the input time and evaluates fold 0 and fold 1 explicitly. For each candidate it:

1. attaches the validated named timezone;
2. converts the candidate to UTC;
3. converts that UTC instant back to the named timezone; and
4. compares the round-tripped wall-clock fields with the original timezone-naive input.

One unique real UTC instant is `normal`, two distinct real UTC instants are `ambiguous`, and no
real candidate is `nonexistent`. Any other candidate structure is an error rather than a guessed
classification.

## 4. Candidate and Round-Trip Semantics

Candidates are always recorded in fold-0, fold-1 order. Each candidate retains its UTC instant,
UTC offset, round-tripped local datetime, round-trip fold, and wall-clock match result. Seconds and
microseconds remain part of every comparison and conversion.

For normal inputs, the two fold evaluations may produce duplicate UTC candidates. Classification
deduplicates them by UTC instant when deciding status without discarding the two recorded pieces
of fold evidence.

## 5. Normal-Time Policy

A normal civil time resolves directly to its one real UTC instant. An omitted fold, fold 0, and
fold 1 all produce that same instant. Existing Julian-date, modified-Julian-date, apparent
sidereal-time, Earth-location, formatting, and result-model behavior remains unchanged.

## 6. Ambiguous-Time Policy

An ambiguous civil time has no default resolution in the strict API. `fold=None` raises
`AmbiguousCivilTimeError`. Fold 0 selects the earlier occurrence and fold 1 selects the later
occurrence. A fold stored on the input `time` object is deliberately ignored until the caller
supplies an explicit resolver argument.

The Observatory describes the choices as earlier and later occurrences. It does not require users
to understand PEP 495 fold terminology.

## 7. Nonexistent-Time Policy

A nonexistent civil time always raises `NonexistentCivilTimeError`. Fold 0 and fold 1 do not make
the input valid. AstroScope never shifts the input forward or backward automatically and does not
offer an implicit correction policy.

## 8. Gap-Boundary Method

For a nonexistent input, the two candidate UTC instants bracket the relevant UTC-offset
transition. AstroScope sorts those instants, verifies distinct offsets, and uses deterministic
binary search until the transition is isolated to adjacent UTC microseconds. The previous valid
local time is the instant one microsecond before the transition; the next valid local time is the
transition instant itself.

Both boundaries must convert back to their UTC instants, bracket the missing wall-clock value, and
describe a local gap equal to the offset increase. Failure to demonstrate one forward transition
raises `CivilTimeResolutionError`. The method does not step in minutes or assume a one-hour gap.

## 9. Observatory Interaction Policy

The Observatory creates one civil-time resolution context from its shared timezone, date, and
local-time inputs. Normal inputs add no visible control. Ambiguous inputs display both UTC
candidates and offsets and require an unselected earlier/later choice. Nonexistent inputs display
the exact valid boundaries and provide no correction control.

Until the shared instant is resolved, these five actions are disabled:

- astronomical-time calculation;
- local visibility calculation;
- Solar System position calculation;
- sky-map generation; and
- observation-plan generation.

One effective `time` value carries the selected fold to all five actions. Coordinate conversion,
telescope and imaging tools, schedule and weather windows, and observation-log intervals are not
disabled by this policy.

## 10. Localization Policy

Ambiguity, candidate, offset, selection, nonexistent-time, boundary, and blocked-action messages
are complete in English, Japanese, Korean, and Thai. New transition outcomes use those translated
messages instead of exposing core exception strings. Existing translation keys and language
selection behavior remain unchanged.

## 11. Backward-Compatibility Bridge

Mission 26 adds `classify_local_datetime()` and `resolve_local_datetime()` rather than replacing
the historical converter. `calculate_astronomical_time()` adds an optional keyword-only fold and
uses the strict resolver. Existing normal callers remain compatible; ambiguous and nonexistent
inputs now require scientifically explicit handling in that calculation path.

No package-root export or broad public-API redesign is introduced. Existing Observatory
session-state keys are preserved. The new input fingerprint and selected-fold keys are additive,
and the selection is cleared whenever timezone, date, hour, minute, second, or microsecond changes.

## 12. Preserved Legacy Converter

`get_timezone()` and `local_datetime_to_utc()` retain their signatures and implementations. The
legacy converter continues to preserve a supplied `time.fold`, normal conversion behavior, and
the exact `Unknown time zone: <name>` validation message required by Mission 25.

This compatibility path is not the strict policy and must not be cited as rejecting nonexistent
times or requiring an ambiguity choice.

## 13. Transition-Zone UI Reachability Limitation

The production Observatory timezone list remains `Asia/Tokyo`, `Asia/Bangkok`, `Asia/Seoul`, and
`UTC`. Those options do not expose the validated New York or Lord Howe transition cases. Mission
26 tests inject those zones into the existing selector to characterize the generic UI policy; the
mission does not add timezone options or observer presets.

## 14. Interval-Flow Exclusions

Schedule windows, weather windows, and observation-log session or target intervals construct
timezone-aware boundary values independently. Their start/end ambiguity, gap, duration, and
cross-midnight semantics are not changed by this single-instant mission. Transit scheduling uses
separate UTC date-range behavior and is also unchanged.

## 15. Scientific Limitations

- Classification depends on the installed IANA timezone data and is not a substitute for a pinned
  reference across all zones and dates.
- Correction tests cover authoritative New York one-hour and Lord Howe thirty-minute examples,
  not every historical or future transition.
- The policy validates civil-time-to-UTC resolution only; it does not validate time scales,
  Julian dates, sidereal time, coordinates, IERS data, ephemerides, or observing-site accuracy.
- The preserved compatibility function remains permissive by design.
- The interval flows listed above retain separate civil-time risks.

## 16. Claims Supported After Mission 26

Subject to the tested timezone database and cases, Mission 26 supports the claims that:

- the new classifier distinguishes normal, ambiguous, and nonexistent observer instants by UTC
  round-trip evidence;
- the new resolver preserves normal conversions and subsecond fields;
- explicit New York fold choices resolve to their evidenced UTC instants;
- New York and Lord Howe gaps are rejected without silent shifting;
- their exact transition boundaries are located without assuming an hour-sized change; and
- the Observatory's five shared single-instant actions require the same explicit resolution.

## 17. Claims Still Prohibited

Mission 26 must not be used to claim:

- authoritative post-correction agreement with an independent reference;
- correctness for every timezone, date, historical rule, or future database release;
- safe interval-boundary handling in schedule, weather, or observation-log workflows;
- validation of downstream astronomy calculations or external services;
- publication-grade, operational, or safety-critical readiness; or
- that Mission 25 validated the new strict resolver.

## 18. Mission 27 Recommendation

Mission 27 should create a new authoritative post-correction validation package for
`resolve_local_datetime()`: a versioned fixture, manifest, offline benchmark, canonical run
record, and report that remain distinct from Mission 25. It should independently verify normal,
ambiguous, nonexistent, subsecond, and transition-boundary results before AstroScope makes a new
scientific validation claim.

The implementation and regression tests are recorded in
[`test_civil_time_policy.py`](../../../tests/validation/test_civil_time_policy.py). Phase status
remains governed by the [research roadmap](../roadmap_status.md).
