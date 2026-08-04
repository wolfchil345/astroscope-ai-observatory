# Strict Civil-Time Resolution Validation Protocol

## Scope

Mission 27 validates only the strict civil-time APIs
`classify_local_datetime()` and `resolve_local_datetime()`. It does not
validate the legacy compatibility converter, astronomical time, Julian dates,
sidereal time, coordinates, visibility, ephemerides, IERS, schedules, weather,
observation logs, interval semantics, or transition-zone UI reachability.

## Independent Reference Method

The committed fixture uses IANA TZDB 2026c and Python `tzdata` 2026.3. Its
expected offsets and transitions are generated from the official versioned
`tzcode2026c.tar.gz` and `tzdata2026c.tar.gz` archives: the release's `zic`
compiles the TZif files, and the same release's `zdump` records transition
evidence. Expected UTC instants are then computed by ordinary datetime
arithmetic from those independently evidenced offsets.

Fixture generation does not call AstroScope production civil-time APIs and
does not use Python `ZoneInfo` as an expected-value oracle. The benchmark needs
no network access while it runs; CI package installation is outside that claim.

## Evidence Status

Commit 1 establishes the fixture, integrity contract, offline benchmark, and
test protocol. The canonical Mission 27 run record and its final results will
be added only in Commit 2 from a fresh pinned environment. Therefore this
document does not yet claim a canonical scientific result.
