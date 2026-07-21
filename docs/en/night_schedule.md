🌐 Language: [English](../en/night_schedule.md) | [日本語](../ja/night_schedule.md) | [한국어](../ko/night_schedule.md) | [ไทย](../th/night_schedule.md)

# Night Timeline and Observation Schedule

This module evaluates observation targets repeatedly throughout a selected night.

## Timeline

The user selects:

- Start time
- End time
- Sampling interval
- Minimum altitude
- Minimum Moon separation
- Minimum recommendation score

The end time may occur on the following calendar day.

## Schedule generation

For every interval, the planner selects the highest-ranked recommended target. Consecutive intervals assigned to the same target are merged into one observation block.

## Timeline chart

The interactive chart displays how each target's score changes through the night.

## Limitations

The schedule does not yet include telescope setup time, slewing time, clouds, weather, or target exposure requirements.

## Implemented files

- `src/astroscope/schedule.py`
- `src/astroscope/schedule_messages.py`
- `tests/test_schedule.py`
