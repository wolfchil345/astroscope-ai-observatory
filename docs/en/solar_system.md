🌐 Language: [English](../en/solar_system.md) | [日本語](../ja/solar_system.md) | [한국어](../ko/solar_system.md) | [ไทย](../th/solar_system.md)

# Solar System Explorer

This module calculates the apparent position of Solar System objects for a selected observer and observation time.

## Supported objects

- Sun
- Moon
- Mercury
- Venus
- Mars
- Jupiter
- Saturn
- Uranus
- Neptune

## Calculated values

- Apparent right ascension and declination
- Observer distance
- Altitude and azimuth
- Cardinal direction
- Visibility status
- Solar elongation
- Angular separation from the Moon
- Approximate Moon illumination

## Ephemeris

Mission 5 uses the Astropy built-in ephemeris. It does not require an external ephemeris-kernel download.

## Moon illumination

Moon illumination is estimated from the apparent angular separation between the Sun and Moon.

## Implemented files

- `src/astroscope/solar_system.py`
- `src/astroscope/solar_system_messages.py`
- `tests/test_solar_system.py`
