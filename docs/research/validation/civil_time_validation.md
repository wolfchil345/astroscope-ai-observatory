# Mission 27 — Strict Civil-Time Resolution Validation Evidence

## Scientific Purpose and Scope

Mission 27 supplies an authoritative, offline, reproducible validation record
for AstroScope's strict civil-time resolution behavior. It validates only
classify_local_datetime() and resolve_local_datetime() against independently
evidenced named-zone transitions.

The committed canonical record validates Commit 1
e3a7006aa55f1548add8f0aac31811852a220286. Commit 2 contains the evidence
record and this report only; it does not change scientific implementation
behavior.

The benchmark does not validate the legacy local_datetime_to_utc()
compatibility converter, calculate_astronomical_time(), Julian Date, Modified
Julian Date, sidereal time, coordinates, visibility, Solar System ephemerides,
IERS, schedules, weather, observation logs, interval semantics, or
transition-zone UI reachability. Coordinate frame, observing site, ephemeris,
and IERS are explicitly not_applicable scientific contexts in the canonical
record.

## Independent Reference Basis

The fixture is based on IANA TZDB 2026c and Python tzdata 2026.3. Expected
values were generated from the official, versioned release archives:

- tzcode2026c.tar.gz SHA-256:
  b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8
- tzdata2026c.tar.gz SHA-256:
  e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4

The 2026c release's own zic compiled the TZif reference files and its own
zdump supplied the transition evidence. Expected UTC instants were derived
from independently evidenced offsets using plain datetime arithmetic. Fixture
generation did not call AstroScope civil-time APIs and did not use Python
ZoneInfo as an expected-value oracle.

## Fixture and Integrity Contract

The fixture contains 16 scenarios:

- 7 normal-resolution cases: UTC, Tokyo date crossing, Bangkok, ordinary New
  York, London date crossing, and Lord Howe daylight and standard time;
- 3 explicit ambiguous-time resolutions: New York, London, and Lord Howe;
- 3 unresolved ambiguous-time rejections in those same zones;
- 2 nonexistent-time rejections: New York and Lord Howe; and
- 1 invalid timezone input, Planet/Mars.

Seconds and microseconds are preserved in normal and transition cases. The
fixture also confirms the existing invalid-timezone message unchanged:
Unknown time zone: Planet/Mars.

| Input | SHA-256 |
|---|---|
| Manifest file | a041cfdd5494b858354d2b028abc4c888ad79ff71be3265750bbc9cba1e617a2 |
| Manifest payload | 05e2abfa68149327e9c84f00b7f1ef3d8a08d25a16b64ffd0c7c0d9031f9dd5f |
| Fixture | ef0a8d76851d8c8701f4583f79848b30463941673981a60d0f4d2444afb33a2a |
| Benchmark input | 3cf2c6b2db929b47ba509bda15fb12b5baa19b25026f65fe54f86cd9aead4e9d |
| Canonical run record | 9b85785374bd29c5f7fd2dd0327861a7b3c897a4e4bec287a05b453f6999be77 |

## Canonical Environment and Result

The canonical benchmark ran in a fresh CPython 3.12.10 environment on Darwin
25.5.0 (arm64). It installed AstroScope 0.2.0 with .[dev,validation], used
tzdata 2026.3 reporting IANA 2026c, and set PYTHONTZPATH=""; consequently
zoneinfo.TZPATH was empty and the pinned tzdata distribution supplied the six
referenced TZif files. The structured record includes their hashes, the
complete installed dependency version list, operating-system provenance, the
immutable fixture SHA and manifest path, and complete per-case actual results.
The fixture supplies the corresponding independently generated per-case
expected results under that verified SHA.

Both implementation_commit and checked_out_commit in the record are
e3a7006aa55f1548add8f0aac31811852a220286. The tracked worktree was clean
before the record was written. Benchmark execution requires no network access;
package installation occurred before execution and is outside that claim.

| Result | Count |
|---|---:|
| passed | 10 |
| expected_rejection | 5 |
| invalid_input | 1 |
| failed | 0 |
| Total | 16 |

The aggregate status is passed. expected_rejection is successful strict
behavior: unresolved ambiguous times require an explicit fold, while
nonexistent times reject every fold without silently correcting the local time.

## Transition Evidence and Interpretation

New York spring-forward changes from EST (-18000) at
2024-03-10 06:59:59 UTC to EDT (-14400) at 07:00:00 UTC; its fall-back
changes from EDT at 2024-11-03 05:59:59 UTC to EST at 06:00:00 UTC.
London's 2024 fall-back changes from BST (+3600) at 00:59:59 UTC to GMT
(0) at 01:00:00 UTC; the fixture also records its spring-forward boundary.

Lord Howe's fall-back changes from +11 (39600) at 2024-04-06 14:59:59 UTC
to +10:30 (37800) at 15:00:00 UTC. Its spring-forward changes from +10:30
at 2024-10-05 15:29:59 UTC to +11 at 15:30:00 UTC. The latter is an
independently evidenced 1,800-second civil-time gap. The benchmark checks the
exact previous and next valid local boundaries, both PEP 495 fold candidates,
offsets, UTC instants, round trips, and rejection behavior.

## Limitations and Reproducibility

This record establishes strict single-instant civil-time resolution only. It
does not prescribe an interval fold/gap policy, validate UI reachability of
transition controls, or establish astronomy, coordinate, visibility, or
external-service correctness. Reproduction requires the committed inputs, the
recorded CPython and package environment, PYTHONTZPATH="", and the pinned
timezone database. The committed record is immutable evidence for Commit 1;
future changes require a new validated record rather than reinterpretation of
these results.
