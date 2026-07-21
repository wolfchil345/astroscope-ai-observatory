🌐 Language: [English](../en/interactive_sky_map.md) | [日本語](../ja/interactive_sky_map.md) | [한국어](../ko/interactive_sky_map.md) | [ไทย](../th/interactive_sky_map.md)

# Interactive Local Sky Map

The sky map displays objects that are above the observer's local horizon.

## Polar-map geometry

- The centre represents the zenith
- The outer circle represents the horizon
- Azimuth determines angular position
- Zenith distance determines radial position

The radial coordinate is calculated as:

`radial distance = 90 degrees - altitude`

## Object categories

- Catalogue stars and the Andromeda Galaxy
- Sun, Moon, and planets

## Interaction

Hovering over a marker displays:

- Object name
- Altitude
- Azimuth
- Cardinal direction
- Visibility status

## Implemented files

- `src/astroscope/sky_map.py`
- `src/astroscope/sky_map_messages.py`
- `tests/test_sky_map.py`
