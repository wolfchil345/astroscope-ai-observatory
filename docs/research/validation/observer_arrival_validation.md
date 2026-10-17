# Mission 38 — Observer-Arrival Reference Protocol and Conversion Validation

## Baseline and claim

Mission 37 merged in [PR #37](https://github.com/wolfchil345/astroscope-ai-observatory/pull/37)
on 2026-10-17 at 15:56:41 UTC as
`809b0bc89aa0e4b96de2e8f35d81c417b1609650`. Its
[post-merge quality gate](https://github.com/wolfchil345/astroscope-ai-observatory/actions/runs/39047258136)
passed. Phases 0 and 1 remain complete; Phase 2 remains active.

**This mission validates a research candidate against independently generated,
finite, historical reference samples. It enables no production observing path.**
The [policy](../../../validation/manifests/observer_arrival_policy_v1.json) and
extracted leap data were committed as `de84208` before candidate implementation
or numerical comparisons. The acceptance limits have not been tuned to results.
The generator's later explicit kernel check pins the same DE421 payload already
identified by Mission 34; it does not alter the frozen model or numerical limits.

The [Mission 37 rejection gates](strict_transit_timing_boundary.md) remain intact.
All strict source predictions, including observer-TAI predictions, remain
ineligible for observing, ranking and UTC/calendar export. The research code is
under `validation/`; no production module, UI, old fixture or canonical result
has been modified. A `ResearchArrival` also explicitly carries
`observing_eligible=False` and is not a resolved production event.

## Model and independent references

The explicitly named `geometric-plane-wave-tdb-v1` model is

\[
 B_{\mathrm{geom}} = \mathrm{JD}_{\mathrm{TDB}}(t)
 + \frac{\boldsymbol r_{\mathrm{SSB}\rightarrow\mathrm{site}}(t)
         \cdot\hat{\boldsymbol s}_{\mathrm{ICRS}}}{c\,86400}.
\]

Here the vector uses kilometres and the light speed is 299792.458 km/s.
The target is a fixed ICRS direction at infinite distance, with an explicitly
recorded J2000 coordinate epoch and no proper motion. This coordinate must not
be presented as an arbitrary catalogue's fully specified BJD TDB convention.
The forward map uses the observing instant; the inverse iteratively solves for
that instant instead of interpreting the source coordinate as a UTC date.

| Component | Independent reference | Research candidate |
|---|---|---|
| Earth barycentric position | Skyfield 1.55, frozen JPL DE421 kernel | Astropy 8.0.1 / ERFA built-in ephemeris |
| Site vector | Skyfield WGS84 location, ICRS vector dot product | Astropy EarthLocation and `light_travel_time` |
| Earth rotation and polar motion | Explicit interpolation of frozen IERS observations | The same observations installed as an Astropy IERS table |
| TDB clock | Skyfield time model | Astropy/ERFA time-scale transformations with site location |
| TAI truth for known 2024 arrivals | Gregorian ordinal and exact Fraction arithmetic, plus 37 seconds | Two-part Astropy Time |
| 2016 leap transition | Five pairs derived from IERS Bulletin C52, exact rational TAI dates | Pinned ERFA leap table, TAI/UTC conversion |

The reference generator imports neither AstroScope, Astropy nor ERFA and is run
in a separate environment. It constructs geometric coordinates from known
arrival instants; the candidate's inverse is compared against those independent
arrival values, not merely its own forward round trip. The two implementations
still share IERS measurements, IAU orientation theory, WGS84 and physical
constants. This is cross-implementation evidence, not complete independence of
physical models or observed data. Skyfield's geocentric clock approximation and
Astropy's location-aware clock are not identical; their difference contributes
to the sampled comparison rather than being silently subtracted.

The kernel hash is
`a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`.
It is the existing Mission 34 DE421 payload distributed by skyfield-data 7.0.0;
no kernel binary is added to this repository. The committed fixture contains
original synthetic inputs, expected values, generator hash, package versions,
kernel hash and source URL. The checksum manifest includes the fixture, policy,
generator and data files. A manifest digest is pinned in the candidate loader.
No current catalogue row or newly observed transit is involved.

### Source basis and limits

- [Eastman, Siverd & Gaudi (2010), equations 1–2 and sections II–III](https://arxiv.org/html/1005.4415v3)
  distinguish geometric, clock and relativistic timing contributions. This study
  isolates geometric timing with library clock transformations; it omits solar
  Shapiro delay, finite-distance effects, target motion, exposure integration and
  an additional explicit observer Einstein term. The paper's precision claims
  are not transferred to this implementation.
- [Astropy Time documentation](https://docs.astropy.org/en/stable/time/index.html)
  supplies candidate API semantics, including two-part dates and light-travel
  corrections. It is not an independent numerical oracle.
- [Skyfield geographic locations](https://rhodesmill.org/skyfield/api-topos.html)
  and [accuracy documentation](https://rhodesmill.org/skyfield/accuracy-efficiency.html)
  describe the alternative site representation and supplied polar-motion data.
  Skyfield is MIT licensed; reference regeneration uses the existing pinned
  packages and JPL data distribution with its retained source attribution.
- [IERS Bulletin C52](https://datacenter.iers.org/data/16/bulletinc-052.txt)
  supplies the 2016 leap sequence and 36/37-second offsets.
  [Bulletin C68](https://datacenter.iers.org/data/16/bulletinc-068.txt)
  corroborates the 37-second historical offset through 2024. Extracted numerical
  leap facts and the source-file hash are local. The EOP snapshot is reused
  unchanged from Mission 34 with its original attribution and extraction record.

These primary sources were inspected on 2026-10-17 UTC. The acceptance thresholds
and implementation restrictions below are project decisions. Website updates
are not fetched during generation or evaluation.

## Frozen domain and tolerances

The Cartesian grid has four sites (Tokyo, equator, Paranal, Arctic), six sky
directions and four 2024 seasonal dates. Three separate arrival probes at
10:00, 12:00 and 14:00 UTC give **288 reference pairs**. The probe labels
`ingress_probe`, `midpoint_probe`, `egress_probe` test distinct endpoint
conversions; they do not constitute fitted transit contacts or validate a T14
model. Both correction signs are represented. Five further pairs cover the
2016 leap second, including fractional instants within `23:59:60`.

| Quantity | Predeclared limit | Observed local maximum |
|---|---:|---:|
| Forward geometric-coordinate difference | 1 ms | 21.0684 microseconds |
| Inverse observer-arrival difference | 1 ms | 21.1060 microseconds |
| Candidate inverse residual | 100 ns | 47.5995 ns |
| Independent UTC-to-TAI leap-pair difference | 10 ns | 0.00960 ns |

All 288 geometric pairs and five leap pairs passed; **zero samples were
excluded**. Exact UTC labels also matched all five leap references. These maxima
are results on this grid, not upper bounds over continuous dates, sky positions,
or observatories. The canonical JSON stores full precision and environment
metadata; CI records its own versions and exact head.

The 1 ms threshold is an engineering acceptance target for the sampled model
comparison. It allows differences among ephemeris, clock and orientation
implementations while remaining below the approximately 21 ms maximum
terrestrial site term. It is not a derived total physical error budget. The
small solver residual does not bound the external reference error. Numerical
precision, cross-model agreement, omitted physical terms, source uncertainties
and observed-transit errors must remain separate.

The candidate rejects dates outside `[2024-01-02, 2024-12-30)` UTC for geometric
operations. This guard lies inside the archived EOP coverage and leaves space
around the sampled dates; it is **not a claim that the entire interval was
validated**. Observer TAI/UTC probes additionally allow only the small TAI
interval `[2017-01-01T00:00:34, 00:00:38]` around the documented leap. No future
leap-second extrapolation is enabled. Missing or corrupted frozen inputs reject.

## Numerical and failure behavior

The candidate takes decimal JD strings, splits integer and fractional parts
before float conversion, and preserves two-part times throughout inversion.
It subtracts the forward residual in TDB, stops only at an absolute residual
at most 100 ns, and rejects after eight iterations. All residuals must be finite.
Missing/nonfinite site and target fields, incompatible frames, missing motion
assumptions, unsupported coordinate/model labels, an already resolved input
state and dates outside the frozen domain produce structured `ArrivalError`
codes. The explicit input-state marker detects declared double correction; it
cannot authenticate a caller who falsely labels a number as source data.

The serial context pins leap and Earth-orientation tables, disables automatic
retrieval, blocks socket connections and restores prior table data/configuration
on exit, including exceptions. A closed converter rejects further operations.
The context owns process-global astronomy tables and is unsuitable for concurrent
application requests; it is intentionally not production infrastructure.

UTC can represent `23:59:60`, but Python datetime cannot. The research datetime
adapter rejects these instants explicitly; it never shifts them into the next
minute. A separate test confirms that two SI seconds span UTC `23:59:59` to
`00:00:00` at this transition. That test does not implement a padded transit
schedule or uncertainty transport.

| Injected forward-model fault | Detected / tested | Largest discrepancy |
|---|---:|---:|
| Reverse geometric correction sign | 288 / 288 | 1001.5790 s |
| Apply time-scale conversion only | 288 / 288 | 500.7895 s |
| Substitute geocentre for observing site | 254 / 288 | 21.2845 ms |

The other 34 omitted-site samples remain below the 1 ms detection threshold;
this is disclosed, not counted as detection. The fault checks require each
fault class to be detected, not every geometric direction to be sensitive.
Unknown-to-zero and production export-provenance regressions remain covered by
Mission 37; no new claim of conversion-aware uncertainty handling is made.

## Reproduction and verification

Install [the candidate environment](../../../validation/requirements-arrival.txt)
in an isolated Python 3.12 environment, then run from the repository root:

```sh
python -m validation.observer_arrival --output work/observer_arrival_run.json
python -m pytest -q tests/validation/test_observer_arrival.py
python -m pytest -q
python -m ruff check .
```

Reference regeneration uses a separate environment with the existing
[reference requirements](../../../validation/reference_generation/reference-requirements.txt):

```sh
OPENBLAS_NUM_THREADS=1 python validation/reference_generation/observer_arrival.py \
  --output work/observer_arrival_regenerated.json
cmp validation/fixtures/observer_arrival_v1.json work/observer_arrival_regenerated.json
```

Installing dependencies can require network access. Subsequent generation and
benchmark evaluation block socket connections, using committed data and the
installed DE421 payload. CI never regenerates reference values. A different
reference environment must not overwrite the archived fixture casually; source
or environment revisions require a versioned, reviewed protocol.

The mission adds **48 tests** covering the full independent benchmark, exact
coverage denominators, malformed inputs, explicit model restrictions, solver
failure/nonfinite residuals, sub-single-float-JD precision, leap-second rejection,
SI elapsed time, frozen-input tampering, offline operation and state restoration.
The existing six CI benchmarks are retained; a seventh step retains this
research record with the implementation and checkout commits, dependency
versions, source/input hashes, all case residuals and mutation results.
The original Mission 36 prospective manifest and Mission 37 coverage record
remain historical records, not silently reclassified as completed.

## Remaining contract and next gate

| Mission 36 scenarios | Mission 38 evidence | Still required |
|---|---|---|
| TC06 | Both signs/sites/seasons/directions, independent sampled geometric comparisons | Full intended physical model and continuous-domain bounds |
| TC07 | Research metadata, frozen-data, nonfinite and solver rejection checks | Production resolved-event failure plumbing |
| TC08 | Explicit state rejection and separate endpoint probes | Production contact/duration pipeline and authenticated provenance |
| TC21–TC22 | Historical leap conversion, SI elapsed probe, datetime rejection | Integrated observing margins and calendar policy |
| TC26 | Three geometric fault classes detected | Conversion-aware uncertainty and end-to-end export fault checks |
| TC05, TC09–TC11, TC24 | No additional implementation | Query enclosure/membership, indeterminate boundaries and resolved persistence |

The next proposed mission is **Mission 39 — Observer-Arrival Error Budget and
Resolved-Event Contract**. Before enabling a production adapter, define the
supported source timing convention and account for omitted corrections, target
motion, data validity, uncertainty transport, candidate selection, boundary
ambiguity and resolved-event persistence. A finite-grid pass alone is not an
acceptance certificate for production use. Mission 39 is not started here;
Mission 38 remains active until review and merge.
