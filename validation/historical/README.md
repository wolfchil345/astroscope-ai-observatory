# Historical numerical implementation

`mission57_light_curve_transit_search.py` is an exact copy of
`src/astroscope/light_curve_transit_search.py` from merged Mission 57,
commit `e2caf52d42ff1f053b05557be0ce045f251ef8bb`.
SHA256: `daa92537c91274c774379385de85dfce3862fda73ccd891c2001054ecd2fd55a`.
It remains under the repository's MIT licence.

Only the historical Mission 56 validation runner imports it. It is not installed
as an AstroScope production backend, exposed as a user option or silently selected
on error. Keeping these bytes preserves the nine known failures and both original
platform observation variants after the production correction. Historical records
and historical expected-failure tests are not failures of the corrected production
engine; Mission 58 has its own non-xfailed scientific replay and CI artifact.

Do not format or repair this frozen source. Any future historical reproduction
change must be explicitly versioned and reviewed.


## Mission 60 catalogue baseline

`mission60_catalogue/` retains the four source modules evaluated in Mission 60.
Only the visuals' two catalogue import prefixes change to keep replay isolated.
`validation/manifests/mission60_retained_sources_v1.json` pins original and retained
hashes; reversing those prefixes reconstructs the original bytes. Do not format
or modernize these snapshots. The historical runner keeps all 17 failed goals;
`validation.catalogue_correction` evaluates current production separately.
