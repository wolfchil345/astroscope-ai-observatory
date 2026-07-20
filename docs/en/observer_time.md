🌐 Language: [English](../en/observer_time.md) | [日本語](../ja/observer_time.md) | [한국어](../ko/observer_time.md) | [ไทย](../th/observer_time.md)

# Observer Location and Astronomical Time

This module converts an observer's local date and time into astronomical time quantities.

## Observer coordinates

The observer is described by:

- Latitude
- Longitude
- Elevation above sea level
- Time-zone identifier

East longitude is positive and west longitude is negative.

## UTC

Local civil time is converted to Coordinated Universal Time before astronomical calculations are performed.

## Julian Date

Julian Date is a continuous count of days used in astronomy.

## Modified Julian Date

Modified Julian Date is calculated as:

MJD = JD - 2400000.5

## Local apparent sidereal time

Local apparent sidereal time indicates which right ascension is currently crossing the observer's local meridian.

## Implemented files

- `src/astroscope/observer.py`
- `tests/test_observer.py`
- `app.py`

## Run

Use `make checks` to run linting and tests.

Use `make run` to open the Streamlit application.
