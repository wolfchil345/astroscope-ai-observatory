"""Independent Fraction enumeration on rational fixtures; no production/Astropy imports."""

import math
from fractions import Fraction


def brute_grid(times, values, errors, period, durations, oversample, objective):
    """Enumerate physical windows with rational arithmetic, returning all optima."""
    t = list(map(Fraction, times))
    y = list(map(Fraction, values))
    w = [1 / Fraction(e) ** 2 for e in errors]
    p = Fraction(period)
    durs = sorted(map(Fraction, durations))
    step = durs[0] / oversample
    phase = [(x - min(t)) % p for x in t]
    best = None
    optima = []
    center = Fraction(0)
    centers = []
    while center < p:
        centers.append(center)
        center += step
    for duration in durs:
        for center in centers:
            inside = [((x - center + duration / 2) % p) < duration for x in phase]
            wi = sum(v for v, m in zip(w, inside, strict=True) if m)
            wo = sum(w) - wi
            if not wi or not wo:
                continue
            yin = sum(v * z for v, z, m in zip(w, y, inside, strict=True) if m) / wi
            yout = sum(v * z for v, z, m in zip(w, y, inside, strict=True) if not m) / wo
            depth = yout - yin
            if depth < 0:
                continue
            variance = 1 / wi + 1 / wo
            score = depth**2 / variance if objective == "snr" else wi * depth**2 / 2
            row = {
                "depth": float(depth),
                "depth_error": math.sqrt(float(variance)),
                "depth_snr": float(depth) / math.sqrt(float(variance)),
                "power": math.sqrt(float(score)) if objective == "snr" else float(score),
                "duration": float(duration),
                "transit_time": float(min(t) + center),
                "indices": [i for i, m in enumerate(inside) if m],
            }
            if best is None or score > best:
                best = score
                optima = [row]
            elif score == best:
                optima.append(row)
    return optima
