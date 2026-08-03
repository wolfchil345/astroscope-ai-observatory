# Observer-Time Validation Baseline

## Result

Mission 25 establishes an authoritative, offline validation slice for AstroScope's mapping of
named civil time to UTC. The canonical run passed its aggregate contract:

| Case class | Expected | Observed | Result |
|---|---:|---:|---|
| Supported normal/date-crossing conversions | 7 | 7 | PASS |
| Supported explicit ambiguous-fold conversions | 2 | 2 | PASS |
| Expected unsupported nonexistent-time characterizations | 2 | 2 | EXPECTED UNSUPPORTED |
| Expected invalid timezone input | 1 | 1 | PASS |
| Unexpected failures | 0 | 0 | PASS |

The aggregate is `passed` because all nine supported conversions agreed with the independent
reference, both gap cases were classified `unsupported` rather than scientifically passed, the
invalid input produced the established validation error, and all provenance checks passed. The
durable evidence is the [canonical run record](../../../validation/results/observer_time_reference_run.json).

## Scope and Method

The benchmark calls the unchanged `local_datetime_to_utc()` implementation in
[`observer.py`](../../../src/astroscope/observer.py). It covers UTC, Tokyo, Bangkok, New York,
London, and Lord Howe. It does not validate Julian dates, sidereal time, coordinates, observing
sites, IERS data, or ephemerides; the [manifest](../../../validation/manifests/observer_time_v1.json)
records those contexts explicitly as not applicable.

The [reference fixture](../../../validation/fixtures/observer_time_reference_v1.json) was derived
without the machine timezone database, Python `ZoneInfo`, or AstroScope:

- `tzcode2026c.tar.gz` from the official IANA release location, SHA-256
  `b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8`
- `tzdata2026c.tar.gz` from the official IANA release location, SHA-256
  `e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4`
- archive retrieval at `2026-08-03T18:56:51Z`
- release `version` file contents `2026c`
- release-built `zic (tzcode) 2026c` and `zdump (tzcode) 2026c`

The release's own `zic` compiled isolated TZif files, and its own `zdump` supplied the offset and
transition evidence. Expected UTC values were then obtained as local civil time minus the
evidenced UTC offset. The Lord Howe cases exercise the genuine 30-minute offset change between
39,600 and 37,800 seconds, rather than assuming every daylight-saving transition is one hour.

## Regression Preservation

- No production source file changed in Mission 25.
- The complete tracked-only suite passed: 748 tests, comprising the 732-test Phase 1 baseline and
  exactly 16 new validation tests.
- The new tests deny socket creation and connection while executing the benchmark in process and
  repeat the CLI execution with a socket-denying startup guard.
- The quality gate retains Python 3.12, Ruff, the complete pytest suite, workflow name `Quality
  Gate`, and check name `Python 3.12 tests and lint`.

These results establish regression preservation. They do not by themselves establish scientific
validity outside the committed cases and environment.

## Reference Agreement

All seven normal or date-crossing cases matched IANA 2026c exactly. Both New York fall-back
conversions also matched when the PEP 495 fold was supplied explicitly:

- `2024-11-03 01:30`, fold 0 → `2024-11-03 05:30 UTC`
- `2024-11-03 01:30`, fold 1 → `2024-11-03 06:30 UTC`

This evidence shows that the current helper preserves and applies an explicit `time.fold` value.
It does not show that the UI lets an observer select or understand that policy.

## Expected Unsupported Gap Behavior

The New York `2024-03-10 02:30` and Lord Howe `2024-10-06 02:15` inputs do not exist in their
named civil-time histories. For each input, the benchmark evaluated folds 0 and 1, converted each
candidate to UTC, converted each result back to the original zone, and compared the round-tripped
civil fields. Neither candidate round-tripped to the supplied input, so both cases are correctly
classified `nonexistent` and recorded with status `unsupported`.

The production helper nevertheless returns a UTC value for either fold because it does not detect
gaps or define a gap policy. Mission 25 characterizes that limitation and deliberately does not
correct it, widen a tolerance, or count it as a scientific pass.

## Canonical Environment and Provenance

The canonical record was generated from a clean tracked checkout immediately after implementation
commit `fd21cdabaadc80f84dd36eae9b9eed70e48195ed` in a new Python 3.12 environment:

| Item | Recorded value |
|---|---|
| Python | CPython 3.12.10 |
| Platform | Darwin 25.5.0, arm64 |
| AstroScope source version | 0.2.0 |
| AstroScope installed distribution | 0.2.0 |
| Astropy | 8.0.1 |
| Python `tzdata` distribution | 2026.3 |
| `tzdata.IANA_VERSION` | 2026c |
| `PYTHONTZPATH` | empty string |
| Captured `zoneinfo.TZPATH` | empty list |
| Implementation commit | `fd21cdabaadc80f84dd36eae9b9eed70e48195ed` |
| Checked-out commit | `fd21cdabaadc80f84dd36eae9b9eed70e48195ed` |

Every exercised TZif resource is hashed in the run record. Installed dependency metadata is also
captured in sorted order. IERS configuration and the built-in ephemeris setting are recorded for
environment transparency while both are explicitly marked not applicable to this benchmark.

Integrity identifiers:

- benchmark inputs: `8004b49e425e23bf492203f663c8afd578e758c9630ddfebce41f13b23b61aac`
- manifest file: `314fcdb8a2a25ec9a32c381b68efc9f71e836d290a68c82b592a1e1a7df7d1aa`
- manifest canonical payload: `5695c6fd4ed5d8fb716292a541b6dbf0158f617950996a8b77add4d8740688f7`
- reference fixture: `4f8e7654e854f210bebbb74095444de4214472c7f994d389ea00c183bc2e5af5`

The benchmark verifies the fixed manifest file hash before parsing it, verifies the manifest
payload digest, verifies the fixture file hash before parsing scientific cases, calculates the
benchmark-input digest from committed files, and rejects a canonical environment whose source and
installed package versions differ.

## Claims Supported

This evidence supports only the following claims:

- under Python `tzdata` 2026.3 / IANA 2026c, the nine committed supported mappings agree with the
  independently compiled IANA reference;
- explicit folds distinguish the two committed New York fall-back mappings;
- the two committed gaps are detected reproducibly by round-trip classification and are not
  mislabeled as passing;
- the established invalid-timezone error is preserved; and
- the benchmark is repeatable offline from committed inputs and the pinned validation dependency.

## Claims Prohibited

This evidence must not be used to claim:

- general correctness for every timezone, date, historical rule, or future IANA release;
- that AstroScope currently has a complete UI policy for ambiguous or nonexistent civil times;
- that nonexistent input is corrected, rejected, or safe for observation planning;
- validation of Julian dates, time scales, sidereal time, coordinates, visibility, transit
  prediction, IERS use, or ephemerides;
- publication-grade, operational, or safety-critical readiness; or
- independence from the pinned software and reference versions recorded here.

## Mission 26 Recommendation

Mission 26 should define and implement an explicit observer-time policy without changing the
Mission 25 evidence. It should detect nonexistent civil times before scientific calculation,
return a stable validation message rather than silently selecting a mapping, and provide an
explicit fold choice for ambiguous fall-back times where the UI accepts local civil input. The
policy should be characterized headlessly first, then covered through the Observatory UI and
session-state path. The correction must retain this benchmark as the pre-correction baseline and
must not rewrite the reference fixture to make a changed behavior appear to pass.
