🌐 Language: [English](../en/observation_planner.md) | [日本語](../ja/observation_planner.md) | [한국어](../ko/observation_planner.md) | [ไทย](../th/observation_planner.md)

# Smart Observation Planner

The planner ranks night-sky targets using a transparent 100-point heuristic.

## Score components

- Altitude: 45 points
- Airmass: 20 points
- Moon separation: 20 points
- Sky darkness: 15 points

## Recommendation rules

A target is recommended when it:

- Is above the selected minimum altitude
- Is classified as observable
- Meets the minimum Moon-separation requirement
- Meets the minimum total score

The Moon is not penalized for having zero separation from itself.

## Important limitation

This ranking does not yet include clouds, atmospheric transparency, seeing, object magnitude, or telescope characteristics.

## Implemented files

- `src/astroscope/planner.py`
- `src/astroscope/planner_messages.py`
- `tests/test_planner.py`
