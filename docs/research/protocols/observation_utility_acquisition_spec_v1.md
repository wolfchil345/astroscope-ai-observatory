# Observation-utility acquisition specification v1 — conditional, not authorized

This specification implements Mission 69's
[feasibility decision](../observation_utility_source_feasibility.md). It preserves
[P3-UTILITY-001-v1](observation_utility_v1.json) and its
[data contract](observation_utility_data_contract_v1.md). The
[disposition JSON](observation_utility_acquisition_v1.json) contains no sample
observations, model selections or fitted parameters. All counts below are proposed
pilot resource ceilings, not sample-size requirements or scientific acceptance.

## 1. Source-owner evidence intake

Before requesting observational bytes, obtain one identified source/programme
and a responsible owner with authority to provide the required records. No such
owner is currently assigned. The intake packet must contain:

1. One fixed site/instrument/setup, task/target definition and programme scope;
   site datum/elevation, named IANA observing-night convention and configuration
   validity period. Do not use unresolved strict-transit inputs.
2. A schema and redacted structural example for the full planned-exposure roster,
   creation/revision timestamps, predecision snapshot mechanism, execution-event
   history and stable product joins. Structural examples are not scientific data.
3. Source-specific access and release terms for roster, images, calibrations,
   forecasts and operational evidence, attribution and retention plan. Resolve
   the LCO licence-version discrepancy if that route is chosen. Separate public
   release permissions from private access. Keep authentication material outside
   the research release; use opaque actor identifiers where possible.
4. An explicit forecast product/version and per-variable model/run provenance,
   proposed capture and availability receipts, decision-time mapping and evidence
   for every required field. Retrospective initialization metadata is insufficient.
5. An independent measurement pipeline and reference plan, raw/calibration
   availability, saturation and target-matching rules, uncertainty definition,
   plus an independent reviewer/custodian and prospective access design.

Review the packet against the 13 prerequisites below. Acceptance of intake permits
only a separately scoped development pilot; it does not close execution gates or
authorize a confirmatory campaign. If the owner cannot supply a complete roster
or capture provenance, retain the no-go. A different estimand needs a new reviewed
protocol rather than an undocumented relaxation of M68.

## 2. Conditional development pilot and stop rules

Only after a reviewed source-specific intake and explicit acquisition scope:

- Cap a pilot at one programme/site/setup, seven consecutive observing nights,
  100 planned opportunities, 500 total source objects and 2 GiB transferred bytes,
  whichever limit is reached first. Account for roster, image, calibration, log
  and forecast objects. An incomplete cap-limited roster is a failed feasibility
  pilot, not a truncated accepted cohort. These ceilings do not imply adequate
  power, class support or a qualified campaign length.
- Freeze the date range and inclusion rules before looking at weather scores or
  outcome quality. Export all roster pages/statuses for that range, preserving
  query parameters, page receipts, counts and snapshot revisions. Reconcile with
  the owner's independently supplied total and event ledger. Pagination during
  mutation must use a consistent snapshot or be rejected.
- Use one concurrent request and at most one request per second, also honoring
  provider quotas and retry headers. Stop at the cap, access/rights ambiguity,
  schema drift, missing snapshot evidence, unexplained roster mismatch or hash
  conflict. Log unsuccessful/partial retrievals; no automatic budget expansion,
  repeated searches for favourable nights, bulk backfill or paid subscription.
- Mark every inspected outcome as development/exposed. Historical public data
  are not sealed evaluation. A pilot can demonstrate joins and reduction
  feasibility but cannot create past capture receipts. Future prospective capture
  requires its own authorized start/stop and a working immutable receipt process.
- Do not submit/cancel observing requests or change operational decisions. This
  study remains shadow-only; the site's established safety policy governs it.

No pilot was run in M69. No downloader, scheduler, account session, automatic
capture service or measurement implementation is supplied.

## 3. Required mapping and rejection criteria

| Contract object | Candidate mapping | Acceptance evidence or rejection |
|---|---|---|
| Opportunity identity | LCO programme/request/configuration/exposure-slot tuple, or owner-defined ESO programme/OB/exposure-slot tuple | Immutable roster ID fixed before decision; exact expansion and repeat/retry policy required; request-level completion never labels every exposure automatically |
| Planned start, site and setup | Owner's predecision roster; request window/configuration only supporting context | Window bounds or eventual frame time/site alone are insufficient; one fixed task/configuration and explicit timing tolerance required |
| Complete denominator | Owner snapshot plus all cancellation/non-delivery and amendment events | Independently reconcile totals and IDs, retain failed/unattempted opportunities and superseded records; missing image alone is not a zero |
| Product join | LCO frame request/observation links and FITS `REQNUM`; ESO actual schema plus owner crosswalk | Verify one-to-many relationships on real permitted samples; quarantine ambiguous joins; no matching by free-text target name alone |
| Reduction lineage | Raw frame, calibrations, reduction versions and related products | One opportunity, all original/reprocessed products retained; fixed selection rule, no best-quality reduction selection after evaluation |
| Target outcome | Independent calibrated target signal/error, PSF measurement, masks and actual execution evidence | Demonstrate units, target matching, saturation, uncertainty and thresholds; catalogue flux/error or frame FWHM alone does not establish Y |
| Forecast lineage | Explicit product/run plus original response and receipt | Preserve all contributing model versions and transformations; unknown lineage does not qualify |
| Forecast timing | Provider availability evidence and independently timestamped capture | Prove initialization <= availability <= capture <= planned-start minus 24 h; pin clock basis and receipt hashes; do not substitute historical retrieval time |
| Forecast valid time | Per-field instant or interval plus frozen exposure mapping | Fix grid, elevation and interpolation/aggregation recipe before use; no silent hourly shift, interpolation or precipitation redistribution |
| Rights | Per-object class policy/version, permission record and attribution | Essential restricted bytes prevent an unrestricted public-offline claim; a repository code licence cannot replace data terms |

For a future API adapter, the seven required input names map to the documented
Open-Meteo parameter family as follows. This is a proposed name/unit mapping,
**not** evidence of joint availability in a selected model/run/site:

| Unchanged weather input | Provider parameter | Required units / temporal rule |
|---|---|---|
| cloud_cover_percent | cloud_cover | %, documented valid instant |
| precipitation_probability_percent | precipitation_probability | %, documented event threshold and probability interval required |
| precipitation_mm | precipitation | mm, preserve accumulation interval |
| visibility_m | visibility | m, documented valid instant |
| relative_humidity_percent | relative_humidity_2m | %, documented valid instant |
| wind_speed_kmh | wind_speed_10m | km/h, documented valid instant |
| wind_gusts_kmh | wind_gusts_10m | km/h, preserve maximum interval |

Verify exact returned unit metadata and finite domains for every selected product;
reject bools as numbers, NaN, infinity, undocumented missing sentinels and mixed
units. Keep raw fields, normalized fields and transforms separately. Reject
unqualified predictors with a reason, retaining the opportunity; later U1 uses
U0 fallback and D0 is null. Do not impute zero or change score weights.

## 4. Offline package and independent release

A future package must include original bytes and an object manifest with stable
object ID, role, source locator, UTC retrieval/capture time, byte size, SHA-256,
licence/permission locator, split/access class, parent hashes and local path.
Provider checksums supplement SHA-256; expiring URLs are not durable storage.
Store the exact schema version, retrieval envelope (without secrets), response
status, parameters and model/transform versions. Preserve raw originals;
normalized or redacted derivatives have distinct hashes and documented ancestry.

Required roles: roster snapshot and amendments; independent execution events;
raw images; calibration inputs and recipe; forecast response/capture/availability
receipts; target measurements and adjudication; rights/attribution; source and
environment locks; split/lineage manifest; independent expected outputs; ordered
access journal; original and rejected/ambiguous-record ledgers. A metadata-only
release may document missingness but cannot establish full raw reproducibility.

The independent reference must derive measurements from observational evidence
without importing AstroScope scores or candidate label/metric helpers. Freeze
task thresholds and the uncertainty-crossing rule before outcome assessment;
retain Y=0/1/null with evidence. An uncertainty or membership dispute remains
visible; no reference is invented from the forecast. Validate direct hand-computed
examples and all 18 M68 future controls in a separately reviewed implementation.
They remain specified, unexecuted here.

Offline verification must fail on missing/hash-mismatched required objects,
network access, altered lineage, late captures or unauthorized evaluation access.
Keep development and future evaluation outcome access separate; record first
access and prediction freezes. Future evaluation must be prospective after
protocol/code freeze. Replays of exposed outcomes are explicitly regression.

## 5. Closure evidence for every M68 prerequisite

| ID | Evidence required before execution | M69 disposition |
|---|---|---|
| U68-R01 | Named site/setup/task, field, filter, exposure and timing contract | Unresolved; no programme selected |
| U68-R02 | SNR/FWHM/saturation rules, uncertainty decision and sensitivity thresholds | Unresolved; provider QC does not choose task thresholds |
| U68-R03 | Owner-verified complete predecision roster and operating policy | Unresolved; frame archive is insufficient |
| U68-R04 | Applicable rights for every raw/derived/log object and lawful offline release | Unresolved; LCO version conflict, no selected dataset release |
| U68-R05 | Explicit seven-field model lineage, valid-time mapping and timely raw captures | Unresolved; archive initialization alone is insufficient |
| U68-R06 | Independent outcome pipeline and raw/calibration validation | Unresolved; documented products are only candidates |
| U68-R07 | Exact chronological splits, lineage groups and purge gap | Unresolved; no data or dependence assessment |
| U68-R08 | Named evaluation custodian, masking and first-access records | Unresolved; no person assigned |
| U68-R09 | Predeclared calendar stop, sample/class support and power/precision basis | Unresolved; pilot resource caps are not sample adequacy |
| U68-R10 | Effect/precision/missingness limits fixed before evaluation | Unresolved; no thresholds invented |
| U68-R11 | Resampling settings and development-only dependence/coverage qualification | Unresolved; no simulation or inference executed |
| U68-R12 | Reliability and measurement-sensitivity acceptance rules | Unresolved; no calibration claim |
| U68-R13 | Offline candidate/reference implementations, immutable inputs and all controls | Unresolved; documentary checker is not a science pipeline |

All six U68 readiness gates remain open. M69's source review does not change
U0/U1/D0, night-balanced Brier contrasts, unknown-outcome bounds, chronological
splits or conditional inference rules. No P3-E05/P3-E06, physical or production
acceptance follows from a successful document check or a later pilot.
