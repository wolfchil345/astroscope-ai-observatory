# Mission 35 — Exoplanet Transit Ephemeris Validation

## Starting point and predeclared protocol

Mission 34 was verified merged through PR #34 at
`7fdc96f4c9739969ae600bb3477ba394379197df` on 2026-10-15 at 16:44:47 UTC.
Mission 35 starts from that exact main commit. Phases 0 and 1 remain complete;
Phase 2 is active. This mission validates the existing transit ephemeris APIs;
no later phase or unrelated feature is authorized by this work.

The [acceptance policy](../../../validation/manifests/transit_ephemeris_policy_v1.json)
is committed before generation/comparison. Reference generation will use only
Python's standard library, 60-digit Decimal arithmetic and independently enumerated
cycles, with no production import. Published parameters are frozen historical
arithmetic inputs, not a current observing ephemeris or measured timing truth.

The comparison covers midpoint, symmetric first/fourth contacts, baselines,
independent symmetric uncertainty, positive/negative cycles, inclusive midpoint
selection, empty intervals and capacity/invalid-input contracts. Exact dyadic
boundaries are unambiguous; non-dyadic boundaries within 0.2 ms of a midpoint
are retained as numerically indeterminate and cannot inflate the topology pass rate.

Time-coordinate identity must be supplied externally: the core model has no
scale/reference-position field. The application constructs JD UTC ranges;
visibility and calendar exports interpret event JD as UTC without a barycentric
correction. Therefore arithmetic agreement cannot establish safe use of BJD TDB
or HJD catalog ephemerides in those downstream paths.

## Independent primary references

- NASA Exoplanet Archive, [Transit Algorithms](https://exoplanetarchive.ipac.caltech.edu/docs/transit/transit_algorithms.html), accessed 2026-10-15: linear midpoint prediction and distinction between contacts and padded windows. This mission does not claim equivalence to the archive's full uncertainty/window model or service output.
- NIST, [Combining uncertainty components](https://physics.nist.gov/cuu/Uncertainty/combination.html), accessed 2026-10-15: variance propagation including covariance; the zero-covariance restriction is explicit here.
- Maciejewski et al. (2011), [High-precision photometry of WASP-12 b transits](https://arxiv.org/abs/1102.2421v1), DOI 10.1051/0004-6361/201016268: historical BJD TDB coefficients in the abstract. No observed timings are reproduced or claimed as ground truth.
- Eastman, Siverd & Gaudi (2010), [Achieving better than 1 minute accuracy in the Heliocentric and Barycentric Julian Dates](https://arxiv.org/abs/1005.4415): time scale and reference position must accompany timestamps.

Results and reproducibility details will be added after executing the frozen protocol.
