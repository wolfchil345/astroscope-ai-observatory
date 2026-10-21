# Mission 49 frozen ephemeris covariance qualification protocol

Mission 48 merged as `8e635a9331d2bf508e4552384c16d47d6be2b687`;
post-merge Quality Gate 39660413036 passed. Primary-source inspection preceded
this freeze on 2026-10-21 UTC. Commit this protocol and its
[policy](../../../validation/manifests/ephemeris_covariance_policy_v1.json)
before generating references or evaluating new numerical controls.

## Question and scope

Can an acquired, source-matched covariance product support propagation of
uncertainty into the delivered DE440t or INPOP21a geocentric TT−TDB clock?
Qualify provenance and applicability, not just a matrix's mathematical validity.
Keep the exact previously acquired nominal kernel hashes. No new ephemeris,
clock integration, target, site, production behavior or observing eligibility.

A receipt must establish all nine requirements: actual covariance bytes and
checksum; ordered parameter basis and units; numeric reference epoch and time
scale; exact fit/model/nominal-kernel linkage; full correlations; estimated,
considered and fixed parameter treatment; integrated trajectory response;
clock anchor treatment and its cross correlations; and supported validity
interval. Frame, origin and output quantity must also match. A product's nominal
file coverage is not evidence for the covariance's validity interval. A year or
release family name alone is not an exact fit identity. Conventional anchor
values need no stochastic variance by convention; an uncertain anchor must be
included jointly with fitted parameters or have documented cross covariances.

For a fixed TDB anchor, Mission 48 requires
`D_p = D*_p + integral (F_x S_xp + F_p) db` and
`delta_p = -D_p/(1+D')`. The 43 instantaneous rate partials do not provide
`S_xp`, the fitted trajectory response, or anchor uncertainty. An alternative
joint time-path covariance must retain cross-time and anchor correlations.
Neither sparse nominal states nor assuming independent epochs supplies this.
No actual covariance is acquired in the bounded source review frozen here.
All nine requirements remain unestablished for both archived clock products.
This is an acquisition/qualification outcome, not a claim that providers lack
covariance internally or that every public/unpublished product was searched.

## Source distinctions and access limitations

Review the nine sources named in the policy and retain a concise, cited evidence
ledger with locations and specific limitations. JPL export files describe
nominal Chebyshev series. Park et al. describe DE440/DE441's differing dynamical
models. Inspect the INPOP21a release note and public distribution inventory.
Fienga et al. 2024 section 2.2.2 explicitly uses INPOP21a covariance and partials
for lunar libration; its reported angular marginals are not a complete planetary
clock covariance. Do not manufacture a diagonal matrix from them. Section 3
also describes additional simulated lunar observations, not our nominal fit.

Rambaux et al. 2026 is a separate publication. Its institutional abstract and
CDS supplement were readable; publisher HTML/PDF and institutional full PDF
returned HTTP 403. Do not claim a full-text review. CDS lists five libration
and polar-coordinate series, not a complete covariance/trajectory product.
Record these access limits and leave any unreviewed material unqualified.
JPL SBDB and Horizons uncertainty documentation concerns small bodies: an
underlying planetary ephemeris identifier does not convert an asteroid orbit
covariance into that planetary ephemeris's covariance. SBDB representations,
units, solution epoch and labels demonstrate why an explicit input contract is
necessary; this mission does not implement an SBDB importer.

## Independent controls

Use four frozen synthetic three-parameter cases: identity, permutation,
SI scaling with permutation, and singular correlated cancellation with that
scaling. Inputs are arbitrary synthetic numbers, never measured astronomical
uncertainties. The parameters carry km, km/s and km^3/s^2; SI factors are 10^3,
10^3 and 10^9. For permutation pi and positive scaling s,

    q_i = s_i p_pi(i)
    Cq_ij = s_i s_j Cp_pi(i),pi(j)
    Jq_i = Jp_pi(i) / s_i
    Jq Cq Jq^T = Jp Cp Jp^T

A standalone standard-library Fraction generator constructs the transformation
matrix A, multiplies A C A^T, and expands diagonal/cross terms for the variance.
The candidate uses Decimal index/scaling and the established Mission 48
covariance validator. Compare every transformed covariance element, Jacobian
component and both variances exactly as Decimal values. These terminating
controls require no tuned numerical tolerance. Numerical independence only:
equations and synthetic inputs are shared; neither implementation is an
independent physical ephemeris or measurement.

A research-only synthetic receipt validator requires matching solution hash,
quantity, origin, frame, scale, epoch, ordered units/roles, validity, response
and anchor metadata between covariance and response. Reject missing context,
unknown representation, duplicates, fixed-as-estimated roles, invalid intervals,
nonfinite/ragged/asymmetric/indefinite matrices and unknown correlations.
Reject physical receipts rather than declaring unreviewed data qualified. This
bounded interface exercises future ingestion requirements; a future physical
adapter requires a new acquisition protocol and independent provider evidence.
A valid synthetic receipt qualifies only supplied-input algebra. It can never
establish a physical covariance, timing bound or observing eligibility.

## Acceptance and preservation

Require all four references to regenerate identically offline with `python -S`,
all source/target inventories and manifest hashes, meaningful rejection tests,
the complete regression suite, Ruff and a new CI artifact. Pin the prior Mission
48 record and production timing boundary. Fail closed if any prior scientific
status or bound is promoted. Preserve all six unresolved components, 48
unqualified site clocks and combined counts 288 candidates, zero executed,
288 blocked, 240 solar eligible and 48 solar excluded. All three physical
bounds stay null, full reference unqualified and observing eligibility false.
A formal covariance is not a deterministic bound; physical distribution,
coverage, omitted physics and nonlinear remainder remain separate obligations.
Preserve failures and causes; change neither controls nor acceptance after
seeing results without an explicit protocol amendment. Freeze is not a report.

## Primary references

- [JPL ephemeris export](https://ssd.jpl.nasa.gov/planets/eph_export.html)
- [Park et al. 2021](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf)
- [INPOP21a catalog](https://ftp.imcce.fr/pub/ephem/planets/inpop21a/)
- [INPOP21a note](https://www.imcce.fr/content/medias/recherche/equipes/asd/inpop/inpop21a.pdf)
- [Fienga et al. 2024, v1](https://arxiv.org/html/2409.10043v1)
- [Rambaux et al. institutional record](https://researchportal.northumbria.ac.uk/en/publications/lunar-reference-systems-and-their-realisations-using-inpop-epheme/)
- [Rambaux et al. CDS supplement](https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/A%2BA/705/A88?format=html&tex=true)
- [JPL SBDB API](https://ssd-api.jpl.nasa.gov/doc/sbdb.html)
- [JPL Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html)

Full source documents are not redistributed. The ledger retains our bounded
findings and citations, not source snapshots or independently authenticated
provider covariances.
