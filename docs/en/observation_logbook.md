🌐 Language: [English](../en/observation_logbook.md) | [日本語](../ja/observation_logbook.md) | [한국어](../ko/observation_logbook.md) | [ไทย](../th/observation_logbook.md)

# Observation Logbook

The observation logbook records complete visual, imaging, or mixed astronomy sessions.

## Session information

A session contains:

- Observer and location
- Local start and end times
- Coordinates and elevation
- Seeing, transparency, and cloud cover
- Telescope, eyepiece, camera, mount, and filters
- General notes

## Target observations

Each target record contains:

- Object key, name, and category
- Start and end times
- Observation outcome
- Quality rating
- Object altitude
- Imaging exposure and frame counts
- Notes

## Summaries

AstroScope calculates:

- Session duration
- Observation count
- Weighted completion
- Average quality
- Target-observation time
- Frame acceptance rate
- Accepted integration time

## Import and export

The interface supports:

- JSON session export and re-import
- CSV target-observation export
- Markdown observing reports

JSON is the complete reusable session format. CSV contains one row per target observation.

## Implemented files

- `src/astroscope/observation_log.py`
- `src/astroscope/observation_report.py`
- `src/astroscope/observation_log_messages.py`
- `tests/test_observation_log.py`
- `tests/test_observation_report.py`
