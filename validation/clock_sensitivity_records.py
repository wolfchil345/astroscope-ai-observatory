"""Compare audit records without demanding portable binary64 residual bit patterns.

Only floating-point diagnostics may vary, and both records must independently
satisfy the original reference limits. Everything else compares exactly except
explicit Git/runtime provenance. Standard library only, for downloaded artifacts.
"""

from __future__ import annotations

import copy
from decimal import Context, Decimal, localcontext

RUNTIME = {
    "python_version",
    "candidate_packages",
    "implementation_commit",
    "checkout_commit",
    "working_tree_dirty",
}
ERROR_KEYS = ("analytic_minus_reference", "complex_step_minus_reference")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decimal(value):
    require(isinstance(value, str), "diagnostic_string_required")
    result = Decimal(value)
    require(result.is_finite(), "nonfinite_diagnostic")
    return result


def checked_structure(record, policy, fixture):
    require(record["audit_passed"] is True, "audit_failed")
    require(record.get("working_tree_dirty", False) is False, "dirty_record")
    clean = {k: copy.deepcopy(v) for k, v in record.items() if k not in RUNTIME}
    numeric, rate_errors, partial_fractions = [], [], []
    require(len(clean["rates"]) == len(fixture["rates"]) == 12, "rate_inventory")
    for row, ref in zip(clean["rates"], fixture["rates"], strict=True):
        require(row["id"] == ref["id"] and row["et_seconds"] == ref["et_seconds"], "rate_context")
        require(row["passed"] is True, "rate_failed")
        value = row.pop("rate_seconds_per_second")
        error = row.pop("rate_minus_reference")
        decimal(value)
        expected_error = Decimal.from_float(float(value)) - decimal(ref["rate_seconds_per_second"])
        require(decimal(error) == expected_error, "rate_error_inconsistent")
        require(
            abs(expected_error) <= decimal(policy["limits"]["rate_seconds_per_second"]),
            "rate_limit_exceeded",
        )
        numeric.extend([value, error])
        rate_errors.append(abs(expected_error))
        require(len(row["partials"]) == len(ref["partials"]) == 43, "partial_inventory")
        for partial, fixed in zip(row["partials"], ref["partials"], strict=True):
            require(
                partial["id"] == fixed["id"] and partial["reference"] == fixed["value"],
                "partial_reference_changed",
            )
            limit = decimal(policy["limits"]["partial_absolute"]) + decimal(
                policy["limits"]["partial_relative"]
            ) * abs(decimal(fixed["value"]))
            require(decimal(partial["tolerance"]) == limit, "partial_limit_changed")
            require(partial["passed"] is True, "partial_failed")
            for key in ERROR_KEYS:
                raw = partial.pop(key)
                residual = abs(decimal(raw))
                require(residual <= limit, "partial_limit_exceeded")
                numeric.append(raw)
                partial_fractions.append(residual / limit)
    diagnostics = clean["diagnostics"]
    require(
        decimal(diagnostics.pop("max_absolute_rate_error_seconds_per_second")) == max(rate_errors),
        "rate_summary_inconsistent",
    )
    require(
        decimal(diagnostics.pop("max_partial_error_fraction_of_tolerance"))
        == max(partial_fractions),
        "partial_summary_inconsistent",
    )
    return clean, numeric


def compare_records(expected, actual, policy, fixture):
    with localcontext(Context(prec=70)):
        left, a = checked_structure(expected, policy, fixture)
        right, b = checked_structure(actual, policy, fixture)
        require(left == right, "exact_scientific_contract_changed")
        differing = sum(x != y for x, y in zip(a, b, strict=True))
        return dict(
            scientific_contract_matches=True,
            binary64_diagnostic_fields_differing=differing,
            binary64_diagnostics_identical=differing == 0,
        )
