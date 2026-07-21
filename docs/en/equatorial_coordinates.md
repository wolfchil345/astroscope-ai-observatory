🌐 Language: [English](../en/equatorial_coordinates.md) | [日本語](../ja/equatorial_coordinates.md) | [한국어](../ko/equatorial_coordinates.md) | [ไทย](../th/equatorial_coordinates.md)

# Equatorial Coordinates

This module represents celestial objects using right ascension and declination in the ICRS reference frame.

## Right ascension

Right ascension is the celestial equivalent of longitude.

- 24 hours equals 360 degrees
- 1 hour equals 15 degrees
- Valid range: 0 hours to less than 24 hours

## Declination

Declination is the celestial equivalent of latitude.

- Positive values indicate the northern celestial hemisphere
- Negative values indicate the southern celestial hemisphere
- Valid range: -90 degrees to +90 degrees

## Coordinate transformations

AstroScope converts ICRS coordinates into:

- Sexagesimal right ascension
- Decimal right ascension
- Sexagesimal declination
- Decimal declination
- Galactic longitude and latitude
- Cartesian unit direction vector

## Implemented files

- `src/astroscope/coordinates.py`
- `src/astroscope/coordinate_messages.py`
- `tests/test_coordinates.py`
