# Mission 69 — Observation-Utility Source Feasibility and Acquisition Specification

## Decision and scope

**No-go for acquisition under P3-UTILITY-001-v1 at this checkpoint.** The reviewed
sources do not yet establish a complete predecision exposure roster, admissible
24-hour forecast captures, and independently reproducible task-specific outcomes
for one fixed site/setup. This is a bounded source review, not proof that no
suitable data exist. No observational rows, images, forecasts or labels were
acquired; no models were fitted or scientific evaluations performed.

Mission 68 merged in [PR #68](https://github.com/wolfchil345/astroscope-ai-observatory/pull/68)
at `38c0b5e44a2fee647653574d75c995ea0abd27dd`. Its three post-merge workflows
passed: Quality Gate `41425793437`, Schedule Candidate Validation `41425793656`,
and Schedule Reserved Evaluation `41425793368`. The
[merge receipt](evidence/mission68_merge_ci_v1.json) records 10,201 passing tests,
26 retained historical expected failures and all 32 downloaded, digest-checked
archives. The M67 first-exposure record and journal remain unchanged; its current
CI execution is an exposed regression replay. The merge accepts M68's design,
not execution readiness. Its original pending-review ledger remains historical.

This mission supplies a [source register](evidence/observation_utility_feasibility_sources_v1.json),
[machine-readable disposition](protocols/observation_utility_acquisition_v1.json),
[conditional acquisition specification](protocols/observation_utility_acquisition_spec_v1.md),
and [evidence ledger](evidence/observation_utility_feasibility_v1.json).
Provider documentation was reviewed on **2026-11-02 UTC**. It is not a frozen data
release; no provider pages or datasets are vendored. Locators and bounded findings
are recorded for offline review; refreshing live assertions requires a new dated
review. A failed ESO schema-page retrieval is recorded explicitly.

## Candidate sources and disposition

Selection was purposeful: LCO offers linked request and image interfaces; ESO
offers raw/calibration provenance and quality documentation; Open-Meteo is the
existing forecast-provider family. This is not an exhaustive archive survey.
There is no nominated programme, site, instrument or owner-authorized export.
Documentation establishes possible fields, not actual field completeness.

| Route | Supported by primary documentation | Missing evidence for this study | Disposition |
|---|---|---|---|
| LCO request export plus image archive | Request/window/configuration hierarchy and states; frame/request links [S01]; raw and calibration products [S02] | Complete programme roster frozen before decisions; per-exposure identity and planned start; cancellation history; fixed site/setup; access and release evidence | Conditional candidate, not qualified |
| ESO archive plus programme operations export | Raw/calibration access and public header policy [S08]; TAP/DataLink services [S09–10]; night-log and QC context [S11–12] | Complete predecision OB/exposure roster and unattempted events; exact schema/sample joins; task-specific measurements and prospective forecast captures | Conditional candidate, not qualified |
| Open-Meteo stitched Historical Forecast API | Successive runs' early hours form a continuous series [S13] | Does not supply the required fixed-decision forecast lineage | Excluded as primary predictor under unchanged protocol |
| Open-Meteo Single Runs API | Explicit initialization selects a forecast run [S14] | No acquired contemporaneous capture/availability evidence; exact model/version and seven-field lineage unqualified | Retrospective retrieval alone is insufficient |
| Prospective, explicitly identified Open-Meteo captures | Documented field semantics and model-dependent availability [S15] | No selected site/model, capture process, seven-field demonstration or licensed release | Conditional future route, not started |

### Roster and identity

LCO requests can contain multiple exposures and execution windows. Frame metadata
includes `request_id`, `observation_id`, `version_set` and `related_frames` [S01].
Neither a request ID nor an archived image is automatically one M68 opportunity.
The acquisition specification requires a predecision exposure-slot manifest and
an independently reconciled execution history. Retries and reductions must not
inflate the denominator. Dynamic scheduling can move observations between
resources [S03]; actual execution time/site cannot be substituted retrospectively
for the planned start/site used to define the decision. A broad window without a
prospectively fixed start does not meet this protocol.

ESO's data services describe acquired datasets. The reviewed sources do not
establish an accessible, complete predecision roster for a selected programme.
That is an evidence gap, not a claim that ESO cannot supply such an export. The
attempt to inspect `https://archive.eso.org/tap_obs/tables/eso.raw` through the
research retrieval tool failed; no column list, query result or join success is
claimed. Before any pilot, obtain and pin an actual schema and a provider-approved
roster export. Public metadata counts are not planned-opportunity counts.

### Independent outcomes

BANZAI documents science, mask, error and catalogue extensions, including flux
and flux-error fields [S04]. These are candidates for independent measurement
evidence; they are not validated labels. Its broad reduction goals do not certify
the chosen task. Header `L1FWHM` describes a frame-level source summary [S05], not
necessarily the target's PSF. Preserve pipeline version, raw/calibration lineage,
units, mask/saturation handling and uncertainty semantics. Demonstrate the target
measurement independently before accepting signal/error as SNR.

ESO QC0 grades compare observations with programme constraints [S12]. A grade
cannot replace M68's target-level delivery/configuration/SNR/FWHM outcome; night
logs [S11] can corroborate operational failures but do not by themselves complete
the predecision denominator. Missing image does not mean failure. Retain Y=null
unless independent evidence establishes cancellation/non-delivery or a conclusive
failed criterion. Retain equipment failures and cancellations in the cohort.

### Forecast chronology and coverage

The unchanged requirement is
`initialization <= availability <= capture <= decision < planned start`, with
`decision = planned start - 24 h`. No publication timestamp, retrieval receipt or
original forecast bytes have been acquired. A Single Runs request made today for
an old initialization cannot establish capture before that historical decision.
Historical stitched output, revised forecasts and reanalysis cannot fill this gap.

S14 reports ECMWF IFS HRES archive coverage from 2024-03-14 and most other models
from 2026-04-02; these are provider statements, not verified cohort coverage.
For future captures, S15 shows that NOAA model products differ in field support,
including calculated probability and cross-resolution sourcing. A generic variable
selector does not prove one specified model/run supplies all seven inputs.
Document every field's contributing product/run, transformation and valid interval.
Unresolved model identity or unavailable required fields block predictor
qualification; preserve the opportunity with U1=U0 and D0=null when later
implementing the frozen protocol. All-fallback predictions would not establish
useful score coverage; M68's coverage acceptance limit remains unset.

### Rights and reproducibility

LCO's acknowledgments page specifies CC BY-NC 4.0 [S06], while its terms page
specifies CC BY-NC 2.0 [S07]. Preserve this discrepancy; obtain applicable
dataset-specific terms before redistribution. Both identify noncommercial
scientific/educational use and proprietary restrictions. A code licence does not
relicense observations or private request/operator records. No licence version or
permission for those records is inferred from public image access.

ESO specifies CC BY 4.0, retained headers and provenance credit, with proprietary
access restrictions and exceptions [S08]. This supports a possible public raw-data
release, not permission to publish otherwise restricted programme logs. Open-Meteo
distinguishes CC BY 4.0 data from noncommercial free-service access limits [S16].
The selected access mode and attribution still need recording. These are source
policy observations, not a legal determination for an unselected dataset.

Offline reproduction requires lawful raw bytes, calibrations, roster, forecast
responses, manifests, environment locks and independent expected outputs. A URL,
hash, expiring download link or current online service alone is insufficient.
Restricted essential inputs must be declared as a reproducibility limitation;
they cannot silently be replaced by synthetic examples or a purported open release.

## Readiness and next boundary

All **13 M68 prerequisites remain unresolved**. Source findings narrow U68-R03–R06
and R13 but close none: no owner/export, applicable complete dataset or independent
measurement pipeline has been demonstrated. Task thresholds, split/purge,
custodian, sample/calendar stopping, uncertainty and acceptance criteria remain
unset. The [specification](protocols/observation_utility_acquisition_spec_v1.md)
maps each prerequisite to a concrete evidence item and defines a staged intake.

M69 can be accepted as a documented feasibility no-go without approving
acquisition. Proposed M70 is **Source-owner Evidence Intake and Go/No-go Review**,
conditional on a named source owner/programme and the required evidence packet.
Without that input, pause this workstream; do not substitute repeated source
reviews, invent a programme, silently change to a delivered-image estimand, or
start acquisition. No messages to observatories, account creation, paid services,
observation requests or hardware actions were performed.

P3-E05/P3-E06 remain open; Phases 4–8 remain planned. All five M62 exclusions,
X01's 18 unmet requirements/six unknown components/48 unqualified clocks,
288 blocked arrivals and transit 13/5/8 boundaries remain unchanged. Physical
bounds remain null and observing eligibility remains false.

## Verification

Run offline from the repository root:

```sh
python3 docs/research/evidence/verify_observation_utility_feasibility.py
```

The checker verifies baseline bytes, mission hashes, links, source/route/gate
consistency, the M68 CI receipt and targeted documentary corruption controls.
It neither downloads data nor validates observational outcomes. M68's historical
checker runs at its own unchanged merge tree; its preserved hash manifest should
not be rewritten for this new mission. The existing full Quality Gate and two
scheduler workflows remain required, with all 32 archives inspected at the exact
final PR head before handoff. Their results belong to the PR receipt rather than
an invented self-referential final-commit field in this document.
