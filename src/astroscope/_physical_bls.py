"""Physical half-open transit windows; no quantized phase-bin padding.

This module computes every tested phase and duration at every supplied period.
Astropy supplies only the outer period grid. Likelihood retains the existing
BLS convention: improvement over the fitted outside level, holding it fixed.
"""

from types import SimpleNamespace

import numpy as np


def physical_bls_power(times, values, uncertainties, periods, durations, oversample, objective):
    """Compute a finite-grid BLS periodogram using sorted phase prefix sums."""
    origin = float(np.min(times))
    elapsed = np.asarray(times, dtype=float) - origin
    y = np.asarray(values, dtype=float) - np.median(values)
    weights = (
        np.ones(len(y))
        if uncertainties is None
        else 1 / np.asarray(uncertainties, dtype=float) ** 2
    )
    total_w = np.sum(weights)
    total_y = np.sum(weights * y)
    width = float(np.min(durations)) / oversample
    output = {
        k: [] for k in ["power", "duration", "transit_time", "depth", "depth_err", "depth_snr"]
    }
    for period in periods:
        phase = np.remainder(elapsed, period)
        order = np.argsort(phase, kind="stable")
        phase = phase[order]
        phase2 = np.concatenate([phase, phase + period])
        w = weights[order]
        wy = w * y[order]
        sw = np.concatenate([[0.0], np.cumsum(np.tile(w, 2))])
        sy = np.concatenate([[0.0], np.cumsum(np.tile(wy, 2))])
        centers = np.arange(int(np.ceil(period / width)), dtype=float) * width
        centers = centers[centers < period]
        # Score the representable returned times, including absolute-epoch rounding.
        absolute_centers = origin + centers
        centers = absolute_centers - origin
        best = None
        for duration in durations:
            starts = np.remainder(centers - 0.5 * duration, period)
            ends = starts + duration
            left = np.searchsorted(phase2, starts, side="left")
            right = np.searchsorted(phase2, ends, side="left")
            wi = sw[right] - sw[left]
            yi = sy[right] - sy[left]
            wo = total_w - wi
            valid = (wi > 0) & (wo > 0)
            depth = np.zeros(len(centers))
            error = np.ones(len(centers))
            depth[valid] = (total_y - yi[valid]) / wo[valid] - yi[valid] / wi[valid]
            error[valid] = np.sqrt(1 / wi[valid] + 1 / wo[valid])
            score = depth / error if objective == "snr" else 0.5 * wi * depth**2
            valid &= (depth >= 0) & np.isfinite(score) & np.isfinite(error)
            score[~valid] = -np.inf
            index = int(np.argmax(score))
            if not valid[index]:
                continue
            if best is None or score[index] > best[0]:
                # Refit the selected partition directly to avoid accumulated-sum
                # cancellation in the reported quantities. Same interval/indices.
                members = order[np.arange(left[index], right[index]) % len(y)]
                mask = np.zeros(len(y), dtype=bool)
                mask[members] = True
                win, wout = weights[mask].sum(), weights[~mask].sum()
                dep = np.average(y[~mask], weights=weights[~mask]) - np.average(
                    y[mask], weights=weights[mask]
                )
                err = np.sqrt(1 / win + 1 / wout)
                snr = dep / err
                power = snr if objective == "snr" else 0.5 * win * dep**2
                best = (
                    float(score[index]),
                    float(power),
                    float(duration),
                    float(absolute_centers[index]),
                    float(dep),
                    float(err),
                    float(snr),
                )
        if best is None:
            raise ValueError("No finite nonnegative physical transit fit at a tested period")
        for key, value in zip(output, best[1:], strict=True):
            output[key].append(value)
    return SimpleNamespace(
        period=np.asarray(periods), **{k: np.asarray(v) for k, v in output.items()}
    )
