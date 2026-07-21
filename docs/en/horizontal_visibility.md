🌐 Language: [English](../en/horizontal_visibility.md) | [日本語](../ja/horizontal_visibility.md) | [한국어](../ko/horizontal_visibility.md) | [ไทย](../th/horizontal_visibility.md)

# Horizontal Coordinates and Visibility

This module transforms ICRS right ascension and declination into the observer's local horizontal coordinates.

## Altitude

Altitude measures the angle above or below the horizon.

- Horizon: 0 degrees
- Zenith: 90 degrees
- Below the horizon: negative altitude

## Azimuth

Azimuth is measured eastward from north.

- North: 0 degrees
- East: 90 degrees
- South: 180 degrees
- West: 270 degrees

## Visibility classification

A target is classified as:

- Observable
- Above the horizon at low altitude
- Below the horizon

The user can select a minimum observing altitude.

## Airmass

The application displays a simple approximate airmass only when altitude is at least 5 degrees.

## Atmospheric refraction

Mission 4 uses geometric horizontal coordinates with atmospheric refraction disabled.

## Implemented files

- `src/astroscope/visibility.py`
- `src/astroscope/visibility_messages.py`
- `tests/test_visibility.py`
