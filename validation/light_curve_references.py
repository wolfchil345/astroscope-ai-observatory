"""Independent regression/checksum controls; no AstroScope or Astropy imports."""

import math
import struct

import numpy as np


def raw_checksum(data):
    total = sum(x[0] for x in struct.iter_unpack(">I", data))
    while total >> 32:
        total = (total & 0xFFFFFFFF) + (total >> 32)
    return total


def ls_power(times, values, errors, frequency):
    t = np.asarray(times, dtype=float)
    y = np.asarray(values, dtype=float)
    e = np.asarray(errors, dtype=float)
    t = t - t[0]
    design = np.column_stack(
        [np.ones(len(t)), np.sin(2 * np.pi * frequency * t), np.cos(2 * np.pi * frequency * t)]
    )
    fit = np.linalg.lstsq(design / e[:, None], y / e, rcond=None)[0]
    mean = np.average(y, weights=1 / e**2)
    reference = np.sum(((y - mean) / e) ** 2)
    if reference == 0:
        return None
    return float(1 - np.sum(((y - design @ fit) / e) ** 2) / reference)


def exact_box_snr(times, values, errors, period, duration):
    """Enumerate all distinct circular phase-window memberships at fixed P/duration."""
    phase = np.remainder(np.asarray(times) - times[0], period)
    y = np.asarray(values, dtype=float)
    weight = 1 / np.asarray(errors, dtype=float) ** 2
    # Objective uses two independent weighted means, positive dimming only.
    best = 0.0
    for boundary in phase:
        for start in [boundary - 1e-10, boundary - duration + 1e-10]:
            mask = np.remainder(phase - start, period) < duration
            inside = weight[mask].sum()
            outside = weight[~mask].sum()
            if inside == 0 or outside == 0:
                continue
            depth = np.average(y[~mask], weights=weight[~mask]) - np.average(
                y[mask], weights=weight[mask]
            )
            snr = depth / math.sqrt(1 / inside + 1 / outside)
            best = max(best, float(snr))
    return best


def wilson(successes, total):
    """Descriptive 95% Wilson interval; does not validate independence or noise model."""
    z = 1.959963984540054
    rate = successes / total
    center = (rate + z * z / (2 * total)) / (1 + z * z / total)
    half = (
        z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    )
    return [max(0, center - half), min(1, center + half)]
