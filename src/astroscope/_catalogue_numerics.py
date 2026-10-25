"""Finite-result helpers for catalogue calculations; no physical qualification."""

from math import frexp, isfinite, ldexp


def finite_or_none(value: float) -> float | None:
    return value if isfinite(value) else None


def positive_ratio(numerators: tuple[float, ...], denominators: tuple[float, ...]) -> float | None:
    """Multiply positive finite factors without intermediate range loss.

    Mantissas are renormalized at each step; only the final binary64 rounding may
    overflow or underflow. An unrepresentable positive result is unknown.
    """
    mantissa, exponent = 1.0, 0
    for factors, divide in ((numerators, False), (denominators, True)):
        for value in factors:
            part, power = frexp(value)
            mantissa = mantissa / part if divide else mantissa * part
            exponent += -power if divide else power
            mantissa, shift = frexp(mantissa)
            exponent += shift
    try:
        result = ldexp(mantissa, exponent)
    except OverflowError:
        return None
    return result if isfinite(result) and result > 0 else None
