[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [ไทย](README.th.md)

# AstroScope AI Observatory 🔭

An intelligent multilingual observatory planner and interactive planetarium.

## Supported languages

- English
- Japanese
- Korean
- Thai

## Implemented features

- Gaia DR3 stellar catalogue explorer
- Interactive sky, colour–magnitude, and proper-motion diagrams
- Gaia source inspector and CSV export

- Structured observation logbook
- Visual and astrophotography session summaries
- JSON, CSV, and Markdown session exports

- Astrophotography sensor and mosaic planner
- Image-scale and seeing-sampling analysis
- Rotatable sensor-frame and mosaic visualization

- Telescope and eyepiece simulator
- Barlow and focal-reducer calculations
- Interactive angular field-of-view visualizer

- Weather-aware observing conditions
- Hourly cloud, rain, wind, and visibility forecast
- Observing-weather score and dew-risk warnings

- Full-night observation timeline
- Automatic chronological target schedule
- Interactive score-change chart

- Smart observation target ranking
- Transparent 100-point quality score
- Moon-separation and darkness filters

- Interactive local all-sky polar map
- Catalogue and Solar System object layers
- Multilingual hover information

- Solar System apparent-position calculations
- Sun, Moon, and eight-planet explorer
- Solar elongation and Moon illumination

- Four-language Streamlit interface
- Observer latitude, longitude, and elevation
- Time-zone conversion
- UTC datetime
- Julian Date and Modified Julian Date
- Local apparent sidereal time
- ICRS right ascension and declination
- Galactic-coordinate transformation
- Cartesian celestial direction vectors
- Local altitude and azimuth
- Horizon and observability classification
- Cardinal direction and approximate airmass

## Install

Run `python -m pip install -e ".[dev]"`.

## Run

Run `make run`.

## Test

Run `make checks`.

## Documentation

- [Gaia DR3 stellar catalogue explorer](docs/en/gaia_explorer.md)

- [Observation logbook](docs/en/observation_logbook.md)

- [Astrophotography sensor and mosaic planner](docs/en/astrophotography_planner.md)

- [Telescope and eyepiece simulator](docs/en/telescope_simulator.md)

- [Weather-aware observing conditions](docs/en/weather_conditions.md)

- [Night timeline and observation schedule](docs/en/night_schedule.md)

- [Smart observation planner](docs/en/observation_planner.md)

- [Interactive local sky map](docs/en/interactive_sky_map.md)

- [Solar System explorer](docs/en/solar_system.md)

- [English documentation](docs/en/index.md)
- [Observer location and astronomical time](docs/en/observer_time.md)
- [Equatorial coordinates](docs/en/equatorial_coordinates.md)
- [Horizontal coordinates and visibility](docs/en/horizontal_visibility.md)

<!-- mission-14-exoplanet-explorer -->
## Mission 14: NASA Exoplanet Transit and Temperate-World Explorer

AstroScope can query confirmed-planet data from the NASA Exoplanet Archive and turn the returned catalogue into an interactive scientific dashboard.

### Features

- Filter planets by discovery method, transit status, distance, radius, and equilibrium temperature
- Compare planetary populations using radius-period, mass-radius, and temperature-insolation diagrams
- Inspect orbital, planetary, stellar, and derived transit properties
- Simulate an educational trapezoidal transit light curve
- Screen for temperate terrestrial candidates
- Download the returned catalogue as CSV
- Inspect the generated ADQL query

### Scientific caution

The temperate classification is a screening tool, not evidence that a planet is habitable. Transit probability, density, and climate-related values use simplified calculations or reported archive parameters. The transit simulator does not include limb darkening, stellar activity, atmospheric effects, or instrumental noise.

### Data source

Catalogue data are retrieved from the NASA Exoplanet Archive `pscomppars` table through its TAP service.
