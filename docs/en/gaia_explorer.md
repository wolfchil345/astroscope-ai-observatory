🌐 Language: [English](../en/gaia_explorer.md) | [日本語](../ja/gaia_explorer.md) | [한국어](../ko/gaia_explorer.md) | [ไทย](../th/gaia_explorer.md)

# Gaia DR3 Stellar Catalogue Explorer

The explorer performs a public Gaia DR3 cone search around an ICRS sky coordinate.

## Search controls

- Right ascension and declination
- Search radius
- Maximum returned rows
- G-magnitude limit
- Optional parallax signal-to-noise filter
- Network timeout

## Visualizations

### Local sky map

The local map plots coordinate offsets from the search centre. Marker size is based on G magnitude and marker colour uses BP−RP when available.

### Colour–magnitude diagram

The diagram plots BP−RP against an estimated absolute G magnitude. The magnitude axis is reversed so intrinsically brighter values appear higher.

### Proper-motion vectors

The vector diagram plots proper motion in right ascension and declination.

## Distance warning

Naive distance is calculated only for positive parallaxes using direct parallax inversion. It is an educational estimate, not a robust scientific distance inference.

## Exports

Search results can be downloaded as CSV. The generated ADQL query is also available for inspection.

## Attribution

Catalogue data: ESA/Gaia/DPAC.

## Implemented files

- `src/astroscope/gaia_catalog.py`
- `src/astroscope/gaia_export.py`
- `src/astroscope/gaia_visuals.py`
- `src/astroscope/gaia_dashboard.py`
- `src/astroscope/gaia_messages.py`
- `tests/test_gaia_catalog.py`
- `tests/test_gaia_visuals.py`
