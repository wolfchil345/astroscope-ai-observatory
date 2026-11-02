# Observation-utility data contract v1 — design only

Companion to [Mission 68](../observation_utility_calibration_design.md) and its
[machine-readable design](observation_utility_v1.json). No populated observational
rows, acquisition code or outcome implementations are supplied by this mission.
All requirements below apply to a future separately reviewed release.

## Row identity and units

Use an immutable opportunity ID and separate raw-product IDs. A row is a planned
exposure request, not each detector pixel, reprocessed frame or forecast revision.
The cohort starts from the full predecision request roster, including cancellation
and non-delivery records. No score-dependent retrospective roster selection.

| Group | Required fields and constraints |
|---|---|
| Identity | study/version, opportunity ID, campaign, site/setup ID, target/field ID, roster revision/hash, record creation time |
| Task | frozen filter/bandpass, planned duration in seconds, start/end UTC, allowable acquisition tolerance, target measurement region, quality contract/version |
| Geometry | site coordinates with datum/elevation, target coordinate source/frame/epoch and uncertainty, applicable geometry method/version; no unresolved strict transit timing |
| Grouping | local observing-night ID with named IANA zone and definition, UTC boundaries, campaign/setup group, repeated-exposure/reduction/calibration/forecast lineage IDs |
| Decision | planned-start minus 24 h, recorded UTC; snapshot includes only information available then |
| Forecast | provider and explicit model/version, run initialization, publication/availability evidence, capture timestamp, request parameters, raw bytes/hash, response metadata, selected grid cell/elevation |
| Variable semantics | per-field unit, valid instant or interval boundaries, aggregation convention, lead/age, interpolation/regridding recipe or explicit none; source values remain preserved |
| Weather inputs | cloud cover and precipitation probability (%), precipitation (mm), visibility (m), relative humidity (%), mean wind/gust (km/h); finite documented domains; null remains null |
| Predictors | unchanged weather function/source hash, score or null and reason; U0/U1/D0 values and training hash when implemented; never overwrite raw scores with calibrated probabilities |
| Acquisition | requested/attempted/delivered state, actual UTC bounds, setup/exposure, instrument/operator/safety logs, non-delivery reason and independent evidence |
| Outcome | Y=0/1/null; raw image/calibration hashes; net signal and standard uncertainty with units; SNR; PSF FWHM in arcsec and uncertainty; validity flags; independent pipeline/version and adjudication record |
| Rights | source URLs/identifiers, retrieval date, licence/version, permitted use/redistribution, attribution, access restrictions, retention/location of required original bytes |
| Provenance | parents/transforms with input/output hashes, source commit, environment, source and output paths, rejection/warning ledger, access-event IDs |

Use literal JSON booleans, finite numeric values and explicit nulls; do not accept
bool as numeric, NaN, infinity, empty string as zero, implicit unit conversion,
naive civil timestamps or a null uncertainty relabelled as exact. Encode UTF-8,
sorted JSON keys, stable array ordering, no NaN and one trailing newline. Store
original provider/image bytes unchanged alongside normalized records. Use
half-open acquisition intervals; provider accumulation semantics are separate
fields, never guessed from a timestamp. Boundary tolerances require units and a
reviewed justification. No schema-valid record alone establishes truth.

## Independent label decision table

| Evidence | Label | Retention |
|---|---|---|
| All delivery/configuration/measurement requirements independently pass | 1 | Measurements, errors, calibration and pipeline provenance |
| Delivery is independently confirmed absent/cancelled | 0 | Cancellation and operational causes, even if unrelated to weather |
| At least one reliable task-contract measurement conclusively fails | 0 | Violated criterion and other unknown fields |
| Missing/corrupt image, missing logs or unresolved/conflicting reduction, with no conclusive failure | null | Unknown reason and all available evidence; no automatic deletion |

Uncertainty intervals crossing a threshold do not silently change a point-estimate
label. The acquisition release must specify whether the contract tests estimates
or a conservative uncertainty bound and freeze that rule for every criterion.
If it uses point estimates, carry measurement uncertainty into a predeclared
borderline-label sensitivity analysis. Its tolerances and method are a readiness
blocker. Alternative adjudications never overwrite the original determination.

Label derivation cannot import weather/planner/transit scores or manufacture
quality from the model's own forecasts. Human adjudicators, when used, must be
masked to U0/U1/D0 predictions with their masking/access evidence retained.
An archive missing failed/unattempted requests does not identify this planned-
opportunity estimand. A conditional delivered-image study would require a new
explicit estimand and reviewed protocol version.

## Chronology, access and lineage

Pin the predecision roster and exact split membership. Capture forecast responses
by the decision time. A previously initialized model retrieved after that time is
not automatically an admissible prospective input. Validate the full timestamp
chain and preserve provider/model update history. Unknown model version or
publication timing is an explicit qualification failure, not inferred metadata.

Do not let the same night, exposure, fitted calibration group or leakage-bearing
forecast lineage appear in multiple splits. Split conflicts are detected before
evaluation; purge and account for affected roster rows according to the frozen
rule. Pure external immutable reference assets have an explicit permitted role.
The grouping graph and all purged/retained IDs must be reproducible offline.

The access journal contains sequence number, UTC time, actor/process, object
path/hash, action/purpose, split and exposure label. Preserve first outcome access,
prediction-freeze identities and any incident. Subsequent analysis of exposed
outcomes is exposed regression. Study access controls are research governance,
not a security boundary against an author rewriting the study.

## Future qualification controls

All 18 controls are **specified, not implemented or executed**. They are distinct
from M68's documentary negative controls and existing 10,201 science/software tests.

| ID | Fault or control | Required future outcome |
|---|---|---|
| U68-C01 | Forecast initialized early but captured after decision | Reject prospective predictor; retain row and U0 fallback |
| U68-C02 | Stitched history/reanalysis substituted for original forecast | Reject prospective qualification |
| U68-C03 | Valid-time/accumulation interval shifted one hour | Detect misalignment; no implicit correction |
| U68-C04 | Units mismatch, NaN, infinity, bool numeric or missing weather field | Reject predictor with reason, retain denominator |
| U68-C05 | Outcome derived from the same heuristic/forecast | Reject reference independence |
| U68-C06 | Known zero versus null and conclusive failure with another unknown | Distinguish all label states exactly |
| U68-C07 | Cancelled or instrument-failed opportunity omitted | Detect roster mismatch; preserve known delivery failure |
| U68-C08 | Duplicate/reprocessed exposure counted twice | Resolve one identity without inflating sample size |
| U68-C09 | Same night/fitted calibration lineage across splits | Reject leakage or apply predeclared purge with accounting |
| U68-C10 | Test-label perturbation changes fitted U0/U1/bin edges | Detect forbidden evaluation access |
| U68-C11 | Bin boundaries 0/20/40/60/80/100 and distinct-night support 19/20 | Exact partition and declared fallback; no out-of-domain clipping |
| U68-C12 | Independent hand-computable Brier and paired-loss examples | Exact rational reference followed by declared float tolerance |
| U68-C13 | Unknown Y=0/1 extremal assignments | Reproduce full-roster lower/upper bounds independently |
| U68-C14 | Unequal frames per night and empty calendar nights | Preserve night weights, calendar dependence and all denominators |
| U68-C15 | Paired block resampling and known dependent simulations | Shared indices, reproducible RNG; coverage qualification/failure retained |
| U68-C16 | Raw/source hash corruption or attempted network access | Reject offline release/run |
| U68-C17 | Calibration error/uncertain threshold crossing | Retain ambiguity and run frozen label-sensitivity analysis |
| U68-C18 | Model/setup change, late reveal or short calendar/count | Preserve original evidence; drift/exposed/incomplete status, no reroll |

Freeze independent expected outputs and failure modes before implementing the
candidate study pipeline. The reference uses direct arithmetic and raw evidence,
not imports of candidate metrics/label routines. Simulated coverage controls test
specified scenarios only; they cannot certify the real unknown dependence law.

## Release and acceptance separation

1. Feasibility specifies sources, rights, schemas and unresolved blockers.
2. A separately authorized acquisition freezes raw data and independently derived
   references, with a complete roster and a lawful offline distribution plan.
3. Development-only code qualification fixes thresholds, gaps, sample/precision
   rules and inference configuration, all before sealed evaluation outcome access.
4. A later evaluated release retains all outcomes and adverse results, with
   conditional/descriptive/qualified claims clearly separated.
5. Production integration and X01 physical qualification remain separate gates.

M68 implements only the documentary design and checker. No observation acquisition,
new observing workflow, telescope control or automatic evaluation is triggered.
