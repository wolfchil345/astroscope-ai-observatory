🌐 Language: [English](../en/astrophotography_planner.md) | [日本語](../ja/astrophotography_planner.md) | [한국어](../ko/astrophotography_planner.md) | [ไทย](../th/astrophotography_planner.md)

# Astrophotography Sensor and Mosaic Planner

The planner evaluates a telescope and camera combination for astronomical imaging.

## Calculated values

- Effective focal length and focal ratio
- Sensor dimensions
- Image scale in arcseconds per pixel
- Horizontal, vertical, and diagonal sky field
- Seeing-disk sampling
- Dawes-resolution sampling
- Suggested image-scale range

## Sampling assessment

Sampling is evaluated relative to the selected atmospheric seeing:

- Oversampled
- Well sampled
- Undersampled
- Severely undersampled

## Target framing

Built-in target presets include:

- Moon
- Andromeda Galaxy
- Pleiades
- Orion Nebula
- Rosette Nebula
- Lagoon Nebula

The planner calculates frame fill, required horizontal and vertical panels, total mosaic panels, and resulting coverage.

## Rotation

Sensor rotation is displayed geometrically in the visualizer. Mosaic panel counts currently use unrotated horizontal and vertical field dimensions.

## Limitations

Target dimensions are approximate. Actual framing depends on the camera orientation, optical distortion, cropping, guiding, dithering, stacking, and the visible extent of faint objects.

## Implemented files

- `src/astroscope/imaging.py`
- `src/astroscope/imaging_visuals.py`
- `src/astroscope/imaging_messages.py`
- `tests/test_imaging.py`
- `tests/test_imaging_visuals.py`
