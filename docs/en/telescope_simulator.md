🌐 Language: [English](../en/telescope_simulator.md) | [日本語](../ja/telescope_simulator.md) | [한국어](../ko/telescope_simulator.md) | [ไทย](../th/telescope_simulator.md)

# Telescope and Eyepiece Simulator

The simulator estimates how a telescope, eyepiece, Barlow lens, and focal reducer work together.

## Calculated values

- Native and effective focal ratio
- Effective focal length
- Magnification
- Exit pupil
- Approximate true field of view
- Dawes resolution
- Rayleigh resolution
- Approximate useful magnification range

## Eyepiece comparison

All built-in eyepieces can be compared using the selected telescope and optical accessories.

## Field-of-view visualizer

The visualizer compares the telescope's circular field with approximate angular sizes for:

- Moon
- Andromeda Galaxy
- Pleiades
- Orion Nebula

Angular-size presets are educational approximations. Extended objects may appear smaller under light pollution because faint outer regions become difficult to see.

## Safety

Never observe the Sun through a telescope without a correctly installed, certified front-aperture solar filter.

## Limitations

Actual performance also depends on atmospheric seeing, optical quality, collimation, target brightness, observer eyesight, and mechanical stability.

## Implemented files

- `src/astroscope/telescope.py`
- `src/astroscope/telescope_visuals.py`
- `src/astroscope/telescope_messages.py`
- `tests/test_telescope.py`
- `tests/test_telescope_visuals.py`
