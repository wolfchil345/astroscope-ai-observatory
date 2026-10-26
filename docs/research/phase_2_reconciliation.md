# Mission 59 — Phase 2 Coverage and Provenance Reconciliation

**Subsequent status:** Mission 59 merged at `9303287a591026b63921844630e90b772bfa0226`;
Mission 60 merged at `e94271adfaf90c22c986fe2433f91b2a0b844489`, both with passing
post-merge CI. [Mission 61](validation/catalogue_correction_validation.md) corrects
the bounded catalogue findings with 1,252 passing current acceptance cases and an
enforced chart domain; bounded G59-01 closure is recommended on review/merge.
Mission 60's original 17 failures remain isolated historical evidence. The original
audit below and its baseline ledger remain historical; no Phase 2 exit is granted.

## Decision

**W05 has complete bounded evidence through Missions 56–58; this PR recommends
its bounded closure. W06 reconciliation is delivered with explicit findings.
Phase 2 exit is not approved.** Catalogue-derived numerical quantities and
educational models still need a bounded validation dossier (G59-01). Historical
provenance and catalogue scope limitations need an explicit exit disposition
(G59-02/G59-03), and physical qualification X01 remains blocked.

The inspected baseline is Mission 58 merge
`bbad4c43982cd6a5ae88a07471c63b8f99e260df`.
[Post-merge Quality Gate 40207906117](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/40207906117)
passed **6,120 tests with nine historical strict expected failures** and retained
26 unexpired artifacts for that commit. All artifact identities were checked;
four archives (M50, M56, M57, M58) were downloaded, digest-verified and checked
for the relevant payload assertions. The other 22 archives were inventoried,
not downloaded in this audit. Exact receipts are in the
[reconciliation ledger](evidence/phase_2_reconciliation_v1.json).

This is a documentary review of existing source, tests, policies, results and
reports. It creates no independent numerical reference or new scientific
experiment. It changes no production code, test, tolerance, fixture, canonical
result or CI workflow. The ledger pins 160 inspected files and the unchanged
production/test/validation/workflow trees. Counts below overlap and must not be
summed into a percentage of scientific completeness.

The [Mission 51 audit](phase_2_coverage_audit.md) remains the historical baseline
for the eight original areas and E01–E08 requirements. This supplement records
what changed through Mission 58, rather than rewriting that audit's old findings.
Review and merge of this PR confirm the documentary disposition; W07 still owns
the formal Phase 2 exit decision.

## Original-scope crosswalk

| Area | Evidence credited | Current bounded claim and exclusions |
|---|---|---|
| P2-01 Observer and time handling | M25, M27, M32, M33 | Bounded civil-time, interval and fixed-site arithmetic; physical arrival clocks remain X01. |
| P2-02 Coordinate conversion | M33 | Bounded fixed ICRS/WGS84 unrefracted transforms; no proper-motion/refraction accuracy or Gaia display-projection qualification. |
| P2-03 Visibility | M33, M34, M54 | Sampled boundaries and sensitivity characterized; no continuous observing coverage certificate. |
| P2-04 Solar System positions | M34, M53 | Sun/Moon and seven enabled planets in recorded 2024 domains; no native rise/set API or universal error bound. |
| P2-05 Telescope and imaging | M52 | Independent ideal-geometry dossier; no measured optics, seeing or empirical magnification/sampling calibration. |
| P2-06 Planner and schedule heuristics | M32, M55 | Controlled heuristic/scheduling evidence; forecast skill, optimality and observing utility remain uncalibrated. |
| P2-07 Transit calculations | M35, M38, M39, M40, M41, M42, M43, M44, M45, M46, M47, M48, M49, M50, M54 | Scalar/nominal arithmetic plus separate research conversion evidence. All strict observing consumers remain blocked; TC01–TC26 crosswalk retained. |
| P2-08 Light-curve analysis | M56, M57, M58 | Frozen 252-trial production acceptance with ten required recoveries; historical failures preserved; no universal FAP, discovery or physical timing qualification. |

M31's provider-contract evidence supplements observer/time and weather rows;
M36–37 provide the strict transit design and implementation boundary. They are
not additional numerical benchmark artifacts. The ledger explicitly links the
new dossiers and the common E01–E06 claim/provenance review. The catalogue and
visualisation inventory below extends this crosswalk where baseline features
have derived quantities embedded in adapters or figure builders.

## W05 bounded closure review

| Requirement | Evidence and disposition |
|---|---|
| Inputs/protocol fixed before evaluation | M56 synthetic injection/null/noise/alias/gap fixtures, preprocessing stages and Kepler selection remain byte-identical; M58 separately froze the physical-membership contract before corrected evaluation. |
| Independent checks | M56 direct weighted LS calculation and exhaustive physical BLS upper bound; M58 independent Fraction finite-grid oracle. Upstream fast/slow comparisons are diagnostics, not independent references. |
| Recovery and numerical acceptance | M58 current production passes all 252 trials and ten required recoveries; all nine prior numerical failures now pass unchanged goals. Two approved constant-curve LS rejections remain visible. |
| Failure history | M56 canonical failure, observation variants and nine strict xfails remain; M57's 95 measurements and 22 fast-bound violations remain historical. Production has a separate passing runner. |
| Published data and time semantics | Kepler-8 Q4 DR25 raw product and original row selection retained; 1,322 rows, BKJD_TDB, rounded reference period 3.523 days. No arrival conversion. MAST terms/source attribution remain in M56. |
| Bias/null/alias interpretation | Preprocessing outcomes, depth ratios, aliases, red/white null flags and their denominators are retained. The fixed small paired sample does not establish population efficiency or universal false-alarm calibration. |
| Reproducibility | Pinned inputs, source hashes, clean canonical identity and current post-merge CI agree within the recorded limits. Full finite-grid search is slower; numerical and physical limits remain explicit. |

The [M56 dossier](validation/light_curve_validation.md),
[M57 investigation](validation/bls_discrepancy_investigation.md) and
[M58 correction](validation/physical_bls_validation.md) support bounded closure
of the original W05 deliverable. This is not approval for discovery claims,
astrophysical confirmation, calibrated detection efficiency, transit-parameter
posteriors or physical timing precision. The nine historical xfails are deliberate
reproduction evidence; they are not nine unresolved current-production failures.

## TC01–TC26 reconciliation

The original [M36 scenarios](../../validation/manifests/transit_time_contract_v1.json)
and [M37 coverage record](../../validation/manifests/transit_timing_boundary_coverage_v1.json)
remain unchanged. Direct source comparison confirms that `transit_timing.py`,
its dashboard and both M37 test files are unchanged since the M37 merge.
The current production tally therefore remains **13 implemented boundary,
five partial boundary, eight deferred**. These are boundary-implementation
categories, not a count of physically qualified timing scenarios.

The [M37 report](validation/strict_transit_timing_boundary.md) defines the guards;
[M38](validation/observer_arrival_validation.md) supplies separate research
conversion/leap/fault evidence; [M39](validation/observer_arrival_error_budget.md)
defines a prospective resolved-event contract. M40–50 investigate physical
qualification without adding a production arrival adapter. M54 sampled-window
evidence requires explicit observing times and does not promote strict predictions.
The ledger gives exact test selectors and source paths for every applicable row.

| Scenario | Current production category | Later evidence or unchanged boundary | Outstanding production scope |
|---|---|---|---|
| TC01 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC02 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC03 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC04 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC05 | deferred | M39 defines a prospective converted-query contract; no production range selector. | All unresolved observing queries reject; coordinate-aware candidate selection is not implemented. |
| TC06 | deferred | M38 independently compares 288 geometric cases across signs/sites/seasons/directions. M40–50 investigate missing physical components; no complete physical qualification. | No converter or independent timing-pair corpus exists in Mission 37. |
| TC07 | partial boundary | M38 rejects missing context/data coverage and failed/nonfinite solves in research code. Full production failure plumbing and physical motion evidence remain absent. | Observer metadata bounds and universal unresolved gate tested; conversion coverage/nonconvergence deferred. |
| TC08 | deferred | M38 rejects an explicit already-corrected state and resolves separate endpoint probes. This is not authenticated provenance or an integrated production contact pipeline. | No arrival adapter exists; double-correction and endpoint conversion cases remain deferred. |
| TC09 | deferred | M35 retains exact dyadic legacy arithmetic controls; no strict range selector. | Only one-cycle nominal prediction is implemented; strict range selection is deferred. |
| TC10 | deferred | M32 validates civil schedule intervals; it does not implement a strict converted-transit date query. | Strict calendar-date request path is not enabled; legacy inclusive request stays unchanged. |
| TC11 | deferred | M35 retains non-dyadic boundary disclosures; M39 specifies future indeterminate membership. Neither supplies production converted-boundary classification. | Strict converted-boundary classification is not implemented; Mission 35 evidence is unchanged. |
| TC12 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC13 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC14 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC15 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC16 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC17 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC18 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC19 | partial boundary | M49 physical ephemeris covariance receipt review does not supply a catalogue-to-strict transit-ephemeris adapter or joint-fit covariance. | Unsupported errors retain original description and yield unknown; unrelated-fit declaration prevents total propagation. No catalogue adapter. |
| TC20 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC21 | deferred | M38 tests a continuous-TAI elapsed margin through the historical leap; production contacts/baselines are still unresolved. | Duration basis is enforced for nominal arithmetic; elapsed observing margins/leap seconds deferred. |
| TC22 | deferred | M38 research datetime adapter rejects leap instants; no resolved production calendar exporter. | Strict UTC/calendar export is gated entirely; no resolved leap-second exporter is implemented. |
| TC23 | partial boundary | Legacy export labels remain unvalidated; no migration/import reader was added. | Legacy export labels and rejection of promotion tested; no legacy file reader/migration added. |
| TC24 | partial boundary | M37 nominal JSON/UI/null evidence remains; M39 resolved-event schema is prospective, not an implemented parser or round trip. | Nominal JSON preserves metadata/null and UI state is tested in four languages. No resolved-event parser/round trip. |
| TC25 | implemented boundary | No later production expansion; original nominal/boundary evidence remains the applicable claim. | Covered by strict nominal/domain and eligibility tests; no observer timing accuracy claim. |
| TC26 | partial boundary | M38 detects wrong-sign, scale-only and omitted-site faults. End-to-end conversion/uncertainty/export mutation validation remains absent. | Unknown-to-zero and covariance-sign contract assertions exist. No converter mutation experiment is claimed. |

For TC01–04 and TC12–18/20/25, “implemented” refers to the nominal/domain
contract: source attribution, supported coordinates, known/unknown uncertainty,
signed covariance, validity and rejection behavior. For TC13, known zero remains
an explicit model value rather than a claim of perfect knowledge. TC19 still has
no catalogue adapter supplying joint-fit uncertainty semantics. TC23–24 have
legacy labels and nominal JSON/UI evidence, not a resolved-event importer.

**All strict predictions remain ineligible for observing, ranking and UTC/calendar
export.** Research helpers, raw-number legacy APIs and diagnostic endpoint probes
are not production adapters. Legacy scheduling remains explicitly unvalidated;
manual extraction of numbers cannot manufacture scientific provenance.

## Catalogue, derived quantities and visualisation

| ID | Surface and classification | Evidence assessment | Disposition |
|---|---|---|---|
| C01 Gaia TAP/CSV and source fields | transport and ingestion | Queries and injected-response parsing tests; row-limited mutable data with no retained response/retrieval envelope. | G59-03 |
| C02 Gaia distance, absolute G, colour, proper motion and SNR | derived numerical quantities | 1000/parallax, G+5 log10(parallax)-10, BP-RP, hypot(pmra,pmdec), parallax/error. Formula controls exist; no bounded independent corpus, parallax/extinction correction or propagated uncertainty. | G59-01 |
| C03 Gaia local-sky offsets | display approximation | Wrapped delta RA*cos(center Dec), delta Dec; one wraparound control is not a spherical-projection accuracy envelope over the accepted field. | G59-01 |
| C04 Exoplanet TAP/CSV and composite fields | transport and ingestion | pscomppars parameters are parsed without joint-fit uncertainty/reference metadata in ExoplanetRecord; no strict ephemeris adapter. | G59-03 |
| C05 Density, radius-ratio depth, circular probability | derived numerical quantities | Nominal Earth/Sun controls exist; constants, domains, extreme ratios, clamp and source-field fallbacks need bounded reference review. No physical transit fit. | G59-01 |
| C06 Temperate-world classification | heuristic screen | Fixed radius, temperature and insolation thresholds; no habitability probability or empirical calibration. Requires characterization of declared boundary/invalid-input behavior. | G59-01 |
| C07 Trapezoidal transit illustration | educational model | Symmetric piecewise-linear flux model and figure tests; no limb darkening, eccentric geometry or astrophysical fit. Existing model arithmetic/domain claims still require bounded review. | G59-01 |
| C08 Static target presets and sky/imaging presentation | static inputs and presentation | Coordinates and angular sizes are curated display inputs, not a maintained catalogue. M33/M52 validate calculations on supplied inputs, not astrophysical correctness of every preset. | G59-03 |

The source inspection separates four responsibilities: transport/parsing,
scientific derivation, heuristic/educational models, and presentation. Existing
formula and UI tests are credited; no absence of testing is claimed. However,
M52 optical geometry does not validate exoplanet radius conversions or Gaia
parallax inference, M55 planner heuristics do not calibrate a temperate-world
screen, and M58 BLS does not validate the educational trapezoid model.

C02/C03/C05/C06/C07 need a small, predeclared independent corpus and domain/
boundary review before those enabled numerical claims can be accepted for exit.
That is **G59-01**, a remaining Phase 2 evidence task. Phase 7 may later improve
professional catalogue interoperability, but that does not exempt numerical
calculations currently exposed by the app. C01/C04/C08 are separately classified
as mutable ingestion/static-input limitations, with no archive-completeness or
maintained-preset-accuracy claim. No live catalogue was fetched in this mission.

## Provenance reconciliation

There are **26 primary canonical records**, corresponding to the 26 CI artifacts.
The ledger maps each record to its runner, manifest(s), report, source/data
conventions, original implementation identity and offline replay command. It
records JSON pointers for Python, dependencies, OS/architecture and randomness
where present, plus hashes of the original metadata. An absent field is marked
`not_recorded`; the current environment is never substituted for it.

| Mission | Canonical record | Original environment evidence | Meaning of a successful audit/replay |
|---|---|---|---|
| M25 | [Record](../../validation/results/observer_time_reference_run.json) / [report](validation/observer_time_validation.md) | Python recorded; OS recorded; dependencies recorded | Pinned civil-time offsets; no celestial calculation |
| M27 | [Record](../../validation/results/civil_time_reference_run.json) / [report](validation/civil_time_validation.md) | Python recorded; OS recorded; dependencies recorded | Strict IANA folds/gaps and rejection policy |
| M32 | [Record](../../validation/results/schedule_interval_reference_run.json) / [report](validation/schedule_interval_validation.md) | Python recorded; OS recorded; dependencies recorded | Civil interval/grid/occupancy semantics |
| M33 | [Record](../../validation/results/celestial_coordinates_reference_run.json) / [report](validation/celestial_coordinate_validation.md) | Python recorded; OS recorded; dependencies recorded | Bounded fixed-direction coordinates and unrefracted geometry |
| M34 | [Record](../../validation/results/solar_lunar_twilight_reference_run.json) / [report](validation/solar_lunar_twilight_validation.md) | Python recorded; OS recorded; dependencies recorded | Bounded Sun/Moon geometry and validation-derived crossings |
| M35 | [Record](../../validation/results/transit_ephemeris_reference_run.json) / [report](validation/transit_ephemeris_validation.md) | Python recorded; OS recorded; dependencies recorded | Scalar legacy ephemeris arithmetic, with retained boundary limitations |
| M38 | [Record](../../validation/results/observer_arrival_reference_run.json) / [report](validation/observer_arrival_validation.md) | Python recorded; OS not recorded; dependencies recorded | Research geometric inversion and historical leap pairs; physical model incomplete |
| M39 | [Record](../../validation/results/arrival_budget_reference_run.json) / [report](validation/observer_arrival_error_budget.md) | Python recorded; OS not recorded; dependencies no inventory field | Error-budget bookkeeping and prospective resolved-event contract; physical bound unknown |
| M40 | [Record](../../validation/results/source_reference_reference_run.json) / [report](validation/source_reference_qualification.md) | Python recorded; OS not recorded; dependencies no inventory field | Supplied-input solar-component comparison; full timing reference unqualified |
| M41 | [Record](../../validation/results/clock_reference_reference_run.json) / [report](validation/clock_reference_validation.md) | Python recorded; OS not recorded; dependencies no inventory field | Successful audit of unsuccessful independent clock qualification |
| M42 | [Record](../../validation/results/time_ephemeris_reference_run.json) / [report](validation/time_ephemeris_clock_mapping.md) | Python recorded; OS not recorded; dependencies recorded | Kernel reader and geocentric mapping evidence; physical site mapping unqualified |
| M43 | [Record](../../validation/results/site_clock_reference_run.json) / [report](validation/site_clock_mapping.md) | Python recorded; OS not recorded; dependencies recorded | Site-clock diagnostics and conditional sensitivity; no physical bound |
| M44 | [Record](../../validation/results/site_frame_reference_run.json) / [report](validation/site_frame_mapping.md) | Python recorded; OS not recorded; dependencies recorded | Polynomial spatial inverse certificate; no physical clock qualification |
| M45 | [Record](../../validation/results/coupled_clock_reference_run.json) / [report](validation/coupled_site_clock.md) | Python recorded; OS not recorded; dependencies recorded | Coupled model numerical/causal controls; physical components unresolved |
| M46 | [Record](../../validation/results/time_normalization_reference_run.json) / [report](validation/time_ephemeris_normalization.md) | Python recorded; OS not recorded; dependencies recorded | Normalization and synthetic controls; no physical uncertainty established |
| M47 | [Record](../../validation/results/cross_model_time_reference_run.json) / [report](validation/cross_model_time_ephemeris.md) | Python recorded; OS not recorded; dependencies recorded | Cross-model diagnostics; not a physical uncertainty bound |
| M48 | [Record](../../validation/results/clock_sensitivity_reference_run.json) / [report](validation/clock_sensitivity_uncertainty.md) | Python recorded; OS not recorded; dependencies recorded | Sensitivity and synthetic covariance propagation; physical covariance absent |
| M49 | [Record](../../validation/results/ephemeris_covariance_reference_run.json) / [report](validation/ephemeris_covariance_qualification.md) | Python recorded; OS not recorded; dependencies no inventory field | Evidence receipt review and synthetic controls; 18 requirements unestablished |
| M50 | [Record](../../validation/results/integrated_clock_response_reference_run.json) / [report](validation/integrated_clock_response_validation.md) | Python recorded; OS not recorded; dependencies no inventory field | Integrated synthetic parameter response; physical covariance absent |
| M52 | [Record](../../validation/results/telescope_imaging_reference_run.json) / [report](validation/telescope_imaging_validation.md) | Python recorded; OS recorded; dependencies recorded | Ideal optical/imaging geometry; empirical heuristics uncalibrated |
| M53 | [Record](../../validation/results/planetary_positions_reference_run.json) / [report](validation/planetary_position_validation.md) | Python recorded; OS recorded; dependencies recorded | 623 bounded 2024 planetary cases; not a universal astrometric error bound |
| M54 | [Record](../../validation/results/visibility_sampling_reference_run.json) / [report](validation/visibility_sampling_validation.md) | Python recorded; OS recorded; dependencies recorded | 48 sampled-window cases; continuous coverage not certified |
| M55 | [Record](../../validation/results/heuristic_characterisation_reference_run.json) / [report](validation/heuristic_characterisation.md) | Python recorded; OS recorded; dependencies recorded | 355 heuristic controls; no observing-utility calibration |
| M56 | [Record](../../validation/results/light_curve_campaign_reference_run.json) / [report](validation/light_curve_validation.md) | Python recorded; OS recorded; dependencies recorded | Historical 252-trial replay with nine scientific failures, not acceptance |
| M57 | [Record](../../validation/results/bls_discrepancy_reference_run.json) / [report](validation/bls_discrepancy_investigation.md) | Python recorded; OS not recorded; dependencies recorded | Historical 95-measurement mechanism audit; 22 fast-bound violations |
| M58 | [Record](../../validation/results/physical_bls_reference_run.json) / [report](validation/physical_bls_validation.md) | Python recorded; OS recorded; dependencies recorded | Current production 252-trial scientific acceptance; finite-grid BLS only |

The canonical records for M38–50 and M57 omit an OS field. M57 does record
machine/core-type information. M39/40/41/49/50 have no package-inventory field
in their canonical result; the first two are explicitly standard-library
Fraction/Decimal audits, while the others must be read with their runner,
manifest and upstream data/source evidence. Missing metadata is neither proof
of numerical failure nor proof of complete reproducibility.

All 26 recorded implementation commits are outside the merged baseline's
ancestor history in this checkout. Some commit objects are locally available;
others are not. This is consistent with the project's review/merge history and
must not be represented as remote data loss. Historical-code reconstruction may
require fetching original PR refs where available and checking the recorded
source hashes. Current CI tests the merged implementation and retained corpus;
it is not a recreation of every original operating system. **G59-02** leaves the
materiality of these gaps for explicit exit review or targeted supplementation.

The small M31 provider-contract result is a supplemental static summary: it
omits execution identity/environment. Its manifest and report preserve the
provider input and contract. M37's coverage JSON is a design/implementation
crosswalk, not a numerical result. Neither is counted as a 27th artifact.

### Replay, reference regeneration and source rights

After installing the project and its validation dependencies, the existing
workflow replays committed fixtures offline; every runner command is listed
in the ledger. The original dossiers/manifests remain authoritative for seeds,
units, scales, frames, input hashes, EOP/leap choices, numerical settings and
source attribution. A deterministic corpus may encode its choices in the fixture
or generator even when a result has no dedicated `randomness` field.

Replay of committed expected values differs from regenerating them from raw
external sources. M33/34/53 reference generation requires the pinned Skyfield/
DE421 tools/data; M42–50 source work can require separately acquired DE440t or
INPOP data and reader tools. Those raw binaries are not all vendored. No blanket
redistribution grant is inferred. M56 retains a public Kepler FITS product under
its original MAST data-use terms, not the repository code licence. Synthetic
fixtures and mathematical controls retain their original provenance.

This audit adds no new source downloads, licence adjudication or accuracy claim.
It preserves the distinction between reproducible frozen-data replay and full
raw-source regeneration. The source-retention and environment gaps must be
reviewed under E04, rather than hidden behind a single “reproducible” label.

## Exit-gate disposition and next work

| Gate | Mission 59 assessment | Evidence / remaining condition |
|---|---|---|
| E01 | reconciled inventory review pending | Eight original areas plus C01–C08 inventory; exclusions require W07 review. |
| E02 | partial | W01–W05 bounded dossiers credited; G59-01 and X01 remain. |
| E03 | partial | W03–W05 cases and failures retained; G59-01 has unreviewed robustness/domain coverage. |
| E04 | reconciled with explicit gaps | 26 primary canonical records, M31 supplement, hash pointers, replay commands and source retention boundaries; G59-02/G59-03 remain. |
| E05 | restrictions preserved scope review pending | Uncalibrated heuristics and X01 unknowns remain; no limited-scope exit decision. |
| E06 | reconciled with deferred paths | All 26 strict-transit scenarios and catalogue paths mapped; research-only evidence does not enable adapters. |
| E07 | baseline passed final exit pending | M58 merge CI 40207906117 passed 6120 tests, nine historical xfails, 26 artifacts. Final M59 checks in PR; future exit commit needs fresh CI. |
| E08 | not performed | W07 formal reviewed exit decision remains outstanding. |

The proposed next mission is **Mission 60 — Catalogue-Derived Quantity and
Educational-Model Validation**, addressing G59-01 within the existing Phase 2
scope. It has not started. It should freeze independent references, constants,
valid input domains and acceptance rules before evaluating the existing Gaia,
exoplanet and educational-model paths. It must preserve transport/physical
uncertainty limitations and retain any discovered failures without loosening
thresholds. No unrelated feature expansion is proposed.

G59-02 and G59-03 remain explicit provenance/scope decisions for W07, with targeted
supplements if required. W07 cannot be replaced by passing this documentation
review. X01 remains 18 unestablished covariance requirements, six unknown physical
components, 48 unqualified site clocks, and 288 blocked arrival candidates
(240 solar-eligible, 48 excluded). All three physical timing bounds remain null;
physical covariance is neither acquired nor propagated; observing eligibility
remains false. A limited-scope exit would require a separate reviewed decision
with enforced exclusions. Phases 0–1 remain complete and Phases 3–8 planned.

## Verification and replay

No production tests or benchmark artifacts are added for this documentary
change. Local checks verify all 160 pinned paths/hashes against the named
baseline, 26 unique scenarios with unchanged requirements/categories, test
selectors, eight coverage areas and eight exit gates, 26 artifact mappings,
canonical metadata pointers, unchanged executable/corpus trees and Markdown
link targets. All **160 hash checks and 130 local Markdown targets passed**;
three negative documentary controls rejected a missing scenario, an altered hash
and an unauthorized exit flag. Ruff and whitespace checks passed. The baseline
four-archive checks are described above. Final-head
CI and artifact verification are recorded in [PR #59](https://github.com/wolfchil345/astroscope-ai-observatory/pull/59) before handoff;
the baseline run does not substitute for final-head acceptance.

A minimal offline integrity check from the repository root is:

```python
import hashlib
import json
import subprocess
from pathlib import Path

ledger = json.loads(Path('docs/research/evidence/phase_2_reconciliation_v1.json').read_text())
base = ledger['baseline_commit']
for path, expected in ledger['baseline_file_sha256'].items():
    original = subprocess.check_output(['git', 'show', f'{base}:{path}'])
    assert hashlib.sha256(original).hexdigest() == expected, path
for path, expected in ledger['preserved_tree_oids'].items():
    actual = subprocess.check_output(['git', 'rev-parse', f'HEAD:{path}'], text=True).strip()
    assert actual == expected, path
assert {r['id'] for r in ledger['transit_scenarios']} == {f'TC{i:02}' for i in range(1, 27)}
assert not ledger['phase_2_exit_approved']
assert not ledger['inherited_physical_status']['observing_eligible']
```

This checks documentary integrity, not scientific truth. Hashes refer to the
inspected baseline; later documentation notes need not share their old hashes.
The unchanged-tree check applies to this mission's final head; future intentional
scientific changes require a new review rather than rewriting this ledger.
