# Mission 49 — Ephemeris Covariance Provenance and Applicability Qualification

## Outcome

No complete, applicable physical covariance receipt was established for either
archived geocentric clock product in the bounded public-source review. This is
an evidence qualification result, not evidence that no covariance exists.
Four synthetic transformations pass independent exact-rational comparisons;
this qualifies supplied-input algebra only. Physical clock and arrival bounds
remain unknown. No production code, additional target or site was changed.

Mission 48 merged as `8e635a9331d2bf508e4552384c16d47d6be2b687` and its
post-merge Quality Gate [39660413036](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39660413036)
passed before this mission. The [protocol](ephemeris_covariance_protocol.md)
and [policy](../../../validation/manifests/ephemeris_covariance_policy_v1.json)
were frozen in `7585741` before new numerical evaluation on 2026-10-21 UTC.

## Evidence and applicability

The [nine-source ledger](../evidence/ephemeris_covariance_evidence_v1.json)
records source URLs, locations, classifications, findings and limitations.
These are our bounded review findings, not archived original documents.

| Reviewed material | Qualification for this clock task |
|---|---|
| JPL export and DE440/441 paper | Nominal interpolation/model context; no complete fitted covariance receipt acquired |
| INPOP21a catalog and release note | Nominal distribution and release evidence; no complete covariance/trajectory product identified in the inspected catalog |
| Fienga et al. 2024, section 2.2.2 | Explicit covariance use for lunar libration; not a supplied full planetary clock covariance |
| Rambaux et al. 2026 institutional abstract | Separate later publication; full text inaccessible through inspected publisher and institutional links (HTTP 403) |
| Rambaux et al. CDS supplement | Five lunar librational/polar series; no complete fitted covariance/clock response in the inspected supplement |
| JPL SBDB and Horizons docs | Small-body uncertainty scope; cannot transplant to planetary geocentric clock uncertainty |

The lunar result matters: internally used covariance must not be misreported as
nonexistent. Published angular marginals cannot reconstruct correlations, and
simulated augmented lunar data are not our nominal planetary solution. The
2024 preprint was read directly; it was not treated as the inaccessible 2026
full text. A provider may have additional applicable products not acquired here.
No provider was contacted and no private dataset was accessed.

The nominal products remain pinned to their original acquisitions:

| Clock | Nominal kernel SHA-256 | Physical receipt |
|---|---|---|
| DE440t | `4f003b4437a8b479aaca262716a779e3683413200adfd6353c4901aab5de800e` | Not qualified |
| INPOP21a | `b39d3faab00cd609685430e8f7f6c39c174341db24b387cad117199e11768687` | Not qualified |

Each requires nine established items: covariance payload; parameter basis/units;
reference epoch/scale; nominal fit linkage; complete correlations; parameter
roles; integrated trajectory response; anchor/cross-covariance treatment; and
validity interval. The nominal quantity/origin/scale are already known; the
corresponding covariance-product metadata are not. All 18 target requirement
entries remain null. These nulls mean unestablished evidence, never zero error.

## Numerical reference and receipt controls

The [reference generator](../../../validation/reference_generation/ephemeris_covariance.py)
uses Fraction matrix multiplication and diagonal/cross-term variance expansion.
The [candidate](../../../validation/ephemeris_covariance.py) uses Decimal direct
index scaling and Mission 48's covariance validation. Every transformed matrix
entry and sensitivity is checked exactly. No new numerical tolerance was tuned.

| Synthetic case | Transformation | Linearized output variance (synthetic seconds squared) |
|---|---|---:|
| Identity | No basis change | 52 |
| Permutation | Reorder all rows, columns and response components | 52 |
| SI permutation | Reorder plus km→m, km/s→m/s and km³/s²→m³/s² | 52 |
| Singular SI permutation | Same conversion, rank-one covariance cancellation | 0 |

The nonzero cross term in the SI case is −2×10¹² in the product of its two
parameter units; changing only diagonal terms would be wrong. Removing the
consider parameter from the first case changes its variance to 44. Neither 52
nor zero is an astronomical measurement, accuracy estimate or physical bound.

The synthetic-only receipt validator requires matching fit, kernel, output,
origin, frame, time scale, numeric epoch, ordered units/roles, interval,
integrated response and anchor metadata. It rejects square-root representations
rather than silently decoding them as covariance, and rejects unknown cross
entries rather than filling them with zeros. Singular positive-semidefinite
matrices are valid; indefinite matrices are rejected. This is a bounded research
interface, not a general physical-data ingestion API or provider authentication.

A full matrix and an instantaneous rate gradient still cannot propagate fitted
trajectory uncertainty into the integrated clock. Mission 48's integrated
parameter-response equation and joint anchor terms remain required. A formal
standard uncertainty also needs coverage/distribution interpretation and does
not bound model discrepancy or nonlinear remainder by itself.

## Reproduction and verification

Run from the repository root with the existing validation environment:

```sh
python -S -m validation.reference_generation.ephemeris_covariance --output /tmp/ephemeris_covariance_fixture.json
cmp /tmp/ephemeris_covariance_fixture.json validation/fixtures/ephemeris_covariance_v1.json
python -m validation.ephemeris_covariance --output /tmp/ephemeris_covariance_run.json
python -m pytest -q tests/validation/test_ephemeris_covariance.py
python -m ruff check .
python -m pytest -q
```

Reference generation has standard-library imports only and both audit and
reference paths deny network connections. The manifest pins policy, fixture,
generator, protocol, ledger, reused validator, prior result and production
boundary. CI adds `ephemeris-covariance-qualification-record` as artifact 18.
The canonical record is generated from a clean implementation commit before
being added to Git. Runtime Python and Git fields are compared separately;
all scientific values must match exactly across local and CI environments.

Initial targeted verification passed 73 tests; the canonical comparison was
intentionally deferred until its clean record existed. No numerical or
scientific failure occurred and no frozen acceptance criterion was changed.
The [canonical record](../../../validation/results/ephemeris_covariance_reference_run.json)
was generated from clean implementation commit
`ef7417ef4118086fc9201856f42722e7737bc804`; its SHA-256 is
`e8bb0ec2f8c721353cfefd3cb73455318643c62d75e0b5035e6358c71b0fb639`.
The complete regression suite and final-head CI verification are pending.

## Remaining qualification gate

All six unresolved components remain; 48 site clocks are unqualified. Combined
counts are 288 candidates, zero executed, 288 blocked, 240 solar eligible and
48 solar excluded. The three physical bounds remain null, full reference
unqualified and `observing_eligible=false`.

Before physical propagation, acquire a provider-supported complete receipt with
the nine items above, then review it against the exact nominal kernel and
integrated clock model. If unavailable, retain the unknowns. A later mission may
validate integrated parameter-response machinery under a separately frozen
protocol, but this mission does not start it or substitute synthetic results
for provider evidence. Mission 49 awaits review and merge.
