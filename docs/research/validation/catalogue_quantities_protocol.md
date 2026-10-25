# Mission 60 — frozen catalogue validation protocol

This protocol addresses C02/C03/C05/C06/C07 and G59-01 from
[Mission 59](../phase_2_reconciliation.md). It is source-informed and fixed before
the first production evaluation. No claim of blinded validation is made. The
generator, corpus, policy and source register are committed together before the
runner is evaluated. The later report will name that commit and retain failures.

## Independent references and scope

| Area | Reference construction | Acceptance and limitation |
|---|---|---|
| Gaia distance and absolute G | 60-digit Decimal reciprocal; distance modulus evaluated in distance space | Arithmetic of naive positive-parallax inversion only; no distance posterior, extinction, zero-point correction or uncertainty propagation |
| Gaia colour, motion, SNR | Decimal difference, square-root norm and ratio; synthetic CSV | pmra is already the RA-direction component; no extra cosine factor. Explicit supplied fields take precedence. No claim that supplied fields are mutually consistent |
| Local-sky offsets | 3-D great-circle point construction and spherical log-map diagnostic; Decimal cosine reference for display formula | Arithmetic comparison plus sampled distortion across the allowed cone sizes, including poles; no global astrometric projection accuracy bound |
| Density, depth, probability | Decimal/Fraction arithmetic, independent SI reference constants and definition sensitivity | Legacy constant arithmetic and cross-quantity convention consistency are distinct tests; no fitted physical parameters or errors |
| Temperate screen | Independently expressed closed-interval decision table | Policy characterization only; temperature OR insolation is sufficient under this screen, even when they conflict |
| Transit illustration | Exact rational clipped ramp in normalized time | First-to-fourth-contact duration and each ingress duration are independently specified; nonnegative unit-normalized flux, contacts, symmetry and area checked |

The complete machine-readable requirements and fixed tolerances are in
[the policy](../../../validation/manifests/catalogue_quantities_policy_v1.json).
The [generator](../../../validation/reference_generation/catalogue_quantities.py)
uses no application code, external numerical library or network. References are
computed from mathematical definitions and explicitly stated constants; this is
independent numerical implementation, not an independent observational campaign.

Scientific sources are recorded in
[the source register](../../../validation/manifests/catalogue_quantities_sources_v1.json).
The main sources are Gaia's published field definitions, Bailer-Jones (2015),
IAU 2015 Resolution B3, JPL's astronomical-unit definition, NASA's Earth fact
sheet, the Exoplanet Archive's composite-table derivations, and Winn (2010,
version 5). The spherical vector and clipped-ramp constructions are derived here;
the heuristic intervals come from existing product policy, not those papers.

## Domains and scientific goals

Ordinary arithmetic grids use positive inputs within their explicitly listed
ranges. Invalid inputs, missing fields and boundary values are separate cases.
Extreme finite inputs are robustness probes, not realistic celestial objects.
Unrepresentable results may be rejected or returned as unknown; accidental
overflow, division by zero, nonfinite derived values and silent intermediate
underflow/overflow are not valid scientific outputs. The corpus distinguishes
representable extreme answers from impossible binary64 outputs.

The existing `Earth radius` label does not state a separate convention for depth
and probability. The two implied SI radii must agree within their rounding
intervals for a common-unit claim. This test does not predetermine which
convention a later correction should adopt. Individual mean/equatorial reference
checks remain separate. The density normalization is an approximate educational
constant; the mass/volume diagnostic does not confer an uncertainty estimate.

For display offsets the tested formula is wrapped RA difference times cosine of
the centre declination, and declination difference. Spherical log-map coordinates
provide a transparent diagnostic comparator. Their disagreement is measured by
cone radius and centre declination without inventing an accuracy requirement the
app never established. Finite sampling cannot establish a continuous envelope.

The depth model assumes an opaque planet and uniform stellar surface, without
grazing geometry or dilution. A planet larger than its star cannot produce a
relative depth above one. The circular probability cap is retained as arithmetic
behavior, but inputs with an orbit inside the sum of the radii are marked outside
the physical exterior-orbit interpretation. Nonzero catalogue eccentricity does
not turn this calculation into an eccentric-orbit probability.

The trapezoid is an educational piecewise-linear model. Its acceptance does not
qualify a physical light-curve fit, exposure smearing, limb darkening or physical
timing. The temperate screen does not estimate habitability or rocky composition.

## Reproduction and retained findings

Fixtures regenerate offline using only Python after checkout. No mutable live
catalogue response is needed, and no external raw binary data is required.
Original authored fixtures/code are repository material; external papers and
catalogues retain their own terms. The register contains factual constants and
brief original summaries, not redistributed papers or catalogue records.

Default benchmark execution must fail on any unmet acceptance goal. If failures
are discovered, a separately labelled CI reproduction audit may retain a complete
observed record. Its success proves regression reproduction only, never scientific
acceptance. New failures, unexpected improvements and altered inputs must require
review; known failures must not disappear behind a green aggregate.

Production correction is not part of this baseline mission. Existing source and
historical validation remain unchanged. G59-01 can be reassessed only from actual
results; G59-02/G59-03 and the W07 exit decision remain explicit. All X01 physical
bounds stay unknown, strict observing eligibility stays false, and Phase 2 stays
active regardless of the numerical results.
