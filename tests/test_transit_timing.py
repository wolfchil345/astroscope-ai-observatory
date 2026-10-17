"""Analytic and rejection contracts, not observer-conversion accuracy evidence."""

import json
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
from fractions import Fraction
from types import SimpleNamespace

import pytest

from astroscope.transit_timing import (
    EphemerisProvenance,
    EphemerisUncertainty,
    StrictTransitEphemeris,
    TimeCoordinate,
    TransitTimingError,
    UncertaintyComponent,
    coordinate_prediction_to_json,
    legacy_arithmetic_ephemeris,
    predict_coordinate_transit,
    propagate_uncertainty,
    require_observing_eligibility,
    require_quantified_padding,
)


def make_ephemeris(**changes):
    values = dict(
        planet_name="Analytic b",
        epoch_value="2451545.0",
        period_days="2.125",
        duration_hours="3.0",
        coordinate=TimeCoordinate("jd", "tdb", "barycentric", "BJD TDB"),
        provenance=EphemerisProvenance("synthetic", "joint-1", "analytic", "analytic", "v1", True),
    )
    values.update(changes)
    return StrictTransitEphemeris(**values)


def component(value):
    return UncertaintyComponent(value, "synthetic analytic case")


@pytest.mark.parametrize("cycle", [-10000, -10, -1, 0, 1, 10, 10000])
def test_nominal_contacts_against_independent_rationals(cycle):
    result = predict_coordinate_transit(make_ephemeris(), cycle)
    midpoint = Fraction(2451545) + cycle * Fraction(17, 8)
    # Three hours total is exactly 1/8 day; each contact is 1/16 from midpoint.
    for actual, expected in (
        (result.midpoint_jd_decimal, midpoint),
        (result.ingress_jd_decimal, midpoint - Fraction(1, 16)),
        (result.egress_jd_decimal, midpoint + Fraction(1, 16)),
    ):
        assert Fraction(actual) == expected
    assert result.validity_status == "unknown"
    assert result.timing_uncertainty.value_days is None


def test_repeating_contact_division_has_predeclared_analytic_bound():
    prediction = predict_coordinate_transit(make_ephemeris(duration_hours="1"), 0)
    exact_ingress = Fraction(2451545) - Fraction(1, 48)
    assert abs(Fraction(prediction.ingress_jd_decimal) - exact_ingress) < Fraction(1, 10**70)


@pytest.mark.parametrize(
    ("representation", "value", "offset"),
    [
        ("jd", "2451545.0", None),
        ("mjd", "51544.5", None),
        ("offset", "1545.0", "2450000"),
    ],
)
def test_representation_normalization_preserves_original_value(representation, value, offset):
    ephemeris = make_ephemeris(
        epoch_value=value,
        coordinate=TimeCoordinate(representation, "tdb", "barycentric", "source label", offset),
    )
    prediction = predict_coordinate_transit(ephemeris, 0)
    assert Decimal(prediction.midpoint_jd_decimal) == Decimal("2451545")
    payload = json.loads(coordinate_prediction_to_json(prediction))
    assert payload["prediction"]["ephemeris"]["epoch_value"] == value
    assert payload["coordinate_output_representation"] == "jd"
    assert payload["prediction"]["ephemeris"]["coordinate"]["representation"] == representation


@pytest.mark.parametrize(
    "value",
    [
        2451545.0,
        True,
        "NaN",
        "Infinity",
        "1e-99",
        "1e99",
        "not-a-date",
        "2451545.12345678901234567890123456789",
    ],
)
def test_invalid_or_coerced_source_numbers_reject(value):
    with pytest.raises(TransitTimingError):
        make_ephemeris(epoch_value=value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("period_days", "0"),
        ("period_days", "-1"),
        ("period_days", "0.124"),
        ("period_days", "366"),
        ("duration_hours", "0"),
        ("duration_hours", "25"),
        ("duration_basis", "unknown"),
        ("provenance", {}),
        ("uncertainty", {}),
        ("duration_uncertainty", None),
        ("coordinate", {}),
        ("planet_name", ""),
    ],
)
def test_invalid_domain_metadata_rejects(field, value):
    with pytest.raises(TransitTimingError):
        make_ephemeris(**{field: value})


@pytest.mark.parametrize("cycle", [True, 1.5, "1", -10001, 10001])
def test_cycle_types_and_bounds_reject(cycle):
    with pytest.raises(TransitTimingError, match="cycle_domain"):
        predict_coordinate_transit(make_ephemeris(), cycle)


@pytest.mark.parametrize(
    ("scale", "position"),
    [
        ("unknown", "barycentric"),
        ("tdb", "unknown"),
        ("utc", "heliocentric"),
        ("tdb", "geocentric"),
        ("utc", "observer"),
    ],
)
def test_unsupported_coordinates_retained_but_not_predicted(scale, position):
    ephemeris = make_ephemeris(coordinate=TimeCoordinate("jd", scale, position, "source"))
    with pytest.raises(TransitTimingError, match="unsupported_time_coordinate"):
        predict_coordinate_transit(ephemeris, 0)


def test_observer_tai_arithmetic_does_not_enable_utc_export():
    ephemeris = make_ephemeris(
        coordinate=TimeCoordinate("jd", "tai", "observer", "observer JD TAI"),
        duration_basis="observer_elapsed",
    )
    result = predict_coordinate_transit(ephemeris, 0)
    assert Decimal(result.midpoint_jd_decimal) == Decimal("2451545")
    with pytest.raises(TransitTimingError, match="arrival_resolution_unavailable"):
        require_observing_eligibility(result)
    with pytest.raises(TransitTimingError, match="duration_basis_mismatch"):
        predict_coordinate_transit(replace(ephemeris, duration_basis="ephemeris_coordinate"), 0)


def test_source_and_validity_contracts_are_explicit_and_immutable():
    with pytest.raises(TransitTimingError):
        EphemerisProvenance("", "fit", "epoch", "period", "v1", True)
    ephemeris = make_ephemeris(valid_cycle_start=-2, valid_cycle_end=2)
    assert (
        predict_coordinate_transit(ephemeris, -2).validity_status
        == "within_supplied_cycle_interval"
    )
    with pytest.raises(TransitTimingError, match="outside_model_validity"):
        predict_coordinate_transit(ephemeris, 3)
    with pytest.raises(TransitTimingError, match="incomplete_validity"):
        make_ephemeris(valid_cycle_start=0)
    with pytest.raises(FrozenInstanceError):
        ephemeris.period_days = "3"
    with pytest.raises(FrozenInstanceError):
        ephemeris.provenance.source_id = "changed"


@pytest.mark.parametrize("cycle", [-3, 0, 3])
def test_unknown_is_not_zero(cycle):
    unknown = propagate_uncertainty(make_ephemeris(), cycle)
    assert unknown.status == "unknown"
    assert unknown.value_days is None
    known = propagate_uncertainty(
        make_ephemeris(
            uncertainty=EphemerisUncertainty(
                component("0"), component("0"), "0", "analytic covariance"
            )
        ),
        cycle,
    )
    assert known.status == "known"
    assert Decimal(known.value_days) == 0


def test_cycle_zero_does_not_need_period_covariance_or_joint_fit():
    ephemeris = make_ephemeris(uncertainty=EphemerisUncertainty(component("0.003")))
    ephemeris = replace(ephemeris, provenance=replace(ephemeris.provenance, joint_fit=False))
    result = propagate_uncertainty(ephemeris, 0)
    assert result.value_days == "0.003"
    nonzero = propagate_uncertainty(ephemeris, 1)
    assert set(nonzero.reasons) == {
        "period_unknown",
        "covariance_unknown",
        "unrelated_parameter_sets",
    }


def test_missing_epoch_is_unknown_even_when_period_is_known():
    ephemeris = make_ephemeris(
        uncertainty=EphemerisUncertainty(
            period=component("0.001"), zero_covariance_assumption="explicit synthetic independence"
        )
    )
    assert propagate_uncertainty(ephemeris, 0).value_days is None
    assert propagate_uncertainty(ephemeris, 10).value_days is None


@pytest.mark.parametrize(
    ("cycle", "covariance", "expected"),
    [
        (2, "0.000006", "0.007"),
        (-2, "0.000006", "0.001"),
        (2, "-0.000006", "0.001"),
        (-2, "-0.000006", "0.007"),
    ],
)
def test_signed_covariance_against_perfect_square_cases(cycle, covariance, expected):
    # sigma_epoch=0.003 days, sigma_period=0.002 days; perfect +/- correlation.
    ephemeris = make_ephemeris(
        uncertainty=EphemerisUncertainty(
            component("0.003"), component("0.002"), covariance, "synthetic analytic covariance"
        )
    )
    assert Decimal(propagate_uncertainty(ephemeris, cycle).value_days) == Decimal(expected)


def test_zero_covariance_requires_explicit_assumption():
    errors = EphemerisUncertainty(component("0.003"), component("0.004"))
    assert propagate_uncertainty(make_ephemeris(uncertainty=errors), 1).value_days is None
    errors = replace(errors, zero_covariance_assumption="synthetic independence")
    result = propagate_uncertainty(make_ephemeris(uncertainty=errors), 1)
    assert Decimal(result.value_days) == Decimal("0.005")
    assert result.assumptions == ("synthetic independence",)


@pytest.mark.parametrize("covariance", ["0.000006000000000001", "-0.000006000000000001", "NaN"])
def test_non_psd_and_nonfinite_covariance_rejected_without_clamping(covariance):
    with pytest.raises(TransitTimingError):
        EphemerisUncertainty(component("0.003"), component("0.002"), covariance, "synthetic")


@pytest.mark.parametrize("kind", ["asymmetric", "limit", "unknown_confidence"])
def test_unsupported_uncertainty_semantics_preserved(kind):
    error = UncertaintyComponent("0.001", "source", kind, "+0.001 / -0.002; original units days")
    ephemeris = make_ephemeris(uncertainty=EphemerisUncertainty(epoch=error))
    prediction = predict_coordinate_transit(ephemeris, 0)
    assert prediction.timing_uncertainty.value_days is None
    payload = json.loads(coordinate_prediction_to_json(prediction))
    assert payload["prediction"]["ephemeris"]["uncertainty"]["epoch"]["kind"] == kind
    assert (
        "-0.002"
        in payload["prediction"]["ephemeris"]["uncertainty"]["epoch"]["original_description"]
    )


def test_independent_decimal_context_and_tiny_source_values():
    with localcontext() as context:
        context.prec = 5
        ephemeris = make_ephemeris(
            uncertainty=EphemerisUncertainty(component("0.000000000000000000000001"))
        )
        result = predict_coordinate_transit(ephemeris, 10000)
    assert result.midpoint_jd_decimal == "2472795.000"
    assert result.timing_uncertainty.value_days is None


def test_unknown_padding_and_serialized_null_are_explicit():
    prediction = predict_coordinate_transit(make_ephemeris(), 1)
    require_quantified_padding(prediction, "0")
    with pytest.raises(TransitTimingError, match="unknown_timing_uncertainty"):
        require_quantified_padding(prediction, "1")
    with pytest.raises(TransitTimingError, match="negative_padding"):
        require_quantified_padding(prediction, "-1")
    payload = json.loads(coordinate_prediction_to_json(prediction))
    assert payload["prediction"]["timing_uncertainty"]["value_days"] is None
    assert payload["observing_eligible"] is False
    assert payload["record_kind"] == "unresolved_coordinate_prediction"
    assert not any(key.endswith("_utc") for key in payload["prediction"])


def test_explicit_legacy_constructor_requires_acknowledgement():
    from astroscope.transit_scheduler import calculate_mid_transit_jd

    values = dict(
        planet_name="legacy",
        orbital_period_days=2.0,
        reference_mid_transit_jd=2451545.0,
        transit_duration_hours=2.0,
    )
    with pytest.raises(TransitTimingError, match="legacy_acknowledgement_required"):
        legacy_arithmetic_ephemeris(acknowledge_unvalidated=False, **values)
    legacy = legacy_arithmetic_ephemeris(acknowledge_unvalidated=True, **values)
    assert calculate_mid_transit_jd(legacy, 1) == 2451547.0
    with pytest.raises(TransitTimingError, match="strict_prediction_required"):
        require_observing_eligibility(legacy)
    with pytest.raises(TransitTimingError, match="strict_prediction_required"):
        coordinate_prediction_to_json(legacy)


@pytest.mark.parametrize(
    "route",
    [
        "schedule",
        "visibility",
        "sample",
        "rank",
        "timing_score",
        "csv",
        "json",
        "ics",
        "timeline",
        "altitude",
        "score_plot",
        "export_datetime",
        "visual_datetime",
        "dashboard_exports",
        "rows",
    ],
)
def test_direct_unresolved_consumer_bypasses_reject(route):
    from astroscope import transit_ranking as rank
    from astroscope import transit_schedule as schedule
    from astroscope import transit_schedule_dashboard as dashboard
    from astroscope import transit_schedule_exports as exports
    from astroscope import transit_schedule_visuals as visuals
    from astroscope import transit_visibility as visibility

    prediction = predict_coordinate_transit(make_ephemeris(), 0)
    candidate = SimpleNamespace(event=prediction)
    ranked = SimpleNamespace(candidate=candidate)
    result = SimpleNamespace(ranked_transits=(ranked,))
    calls = {
        "schedule": lambda: schedule.generate_transit_schedule(
            (SimpleNamespace(ephemeris=make_ephemeris()),), None, None
        ),
        "visibility": lambda: visibility.analyze_transit_visibility(prediction, None, None),
        "sample": lambda: visibility.sample_transit_visibility(None, None, prediction),
        "rank": lambda: rank.score_transit_candidate(candidate),
        "timing_score": lambda: rank.score_timing_confidence(prediction.timing_uncertainty),
        "csv": lambda: exports.transit_schedule_to_csv(result),
        "json": lambda: exports.transit_schedule_to_json(result),
        "ics": lambda: exports.transit_schedule_to_ics(result),
        "timeline": lambda: visuals.create_schedule_timeline_figure(result),
        "altitude": lambda: visuals.create_transit_altitude_figure(ranked),
        "score_plot": lambda: visuals.create_transit_score_figure(ranked),
        "export_datetime": lambda: exports._utc_datetime_from_julian_date(prediction),
        "visual_datetime": lambda: visuals.julian_date_to_utc_datetime(prediction),
        "dashboard_exports": lambda: dashboard.build_dashboard_exports(result),
        "rows": lambda: dashboard.ranked_schedule_rows(result),
    }
    with pytest.raises(TransitTimingError, match="unresolved_timing_input"):
        calls[route]()


def test_none_cannot_enter_timing_score():
    from astroscope.transit_ranking import score_timing_confidence

    with pytest.raises(TransitTimingError, match="unknown_timing_uncertainty"):
        score_timing_confidence(None)


def test_observer_context_round_trips_but_never_enables_arrival_resolution():
    from astroscope.transit_timing import ObserverTimingContext

    context = ObserverTimingContext(
        "Synthetic site",
        "35",
        "135",
        "10",
        "120",
        "30",
        "J2000.0",
        "fixed ICRS direction; no proper motion correction",
    )
    prediction = predict_coordinate_transit(make_ephemeris(observer_context=context), 0)
    payload = json.loads(coordinate_prediction_to_json(prediction))
    retained = payload["prediction"]["ephemeris"]["observer_context"]
    assert retained["geodetic_datum"] == "WGS84"
    assert retained["coordinate_reference_epoch"] == "J2000.0"
    assert retained["target_ra_icrs_degrees"] == "120"
    with pytest.raises(TransitTimingError, match="arrival_resolution_unavailable"):
        require_observing_eligibility(prediction)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude_degrees", "91"),
        ("longitude_degrees", "-181"),
        ("target_ra_icrs_degrees", "360"),
        ("target_dec_icrs_degrees", "-91"),
        ("geodetic_datum", "unknown"),
        ("motion_assumption", ""),
    ],
)
def test_invalid_observer_context_is_rejected(field, value):
    from astroscope.transit_timing import ObserverTimingContext

    values = dict(
        site_name="site",
        latitude_degrees="35",
        longitude_degrees="135",
        elevation_meters="10",
        target_ra_icrs_degrees="120",
        target_dec_icrs_degrees="30",
        coordinate_reference_epoch="J2000.0",
        motion_assumption="fixed direction",
    )
    values[field] = value
    with pytest.raises(TransitTimingError):
        ObserverTimingContext(**values)


@pytest.mark.parametrize(("representation", "offset"), [("offset", None), ("jd", "2400000.5")])
def test_zero_point_cannot_be_inferred_or_changed(representation, offset):
    with pytest.raises(TransitTimingError):
        TimeCoordinate(representation, "tdb", "barycentric", "source label", offset)
