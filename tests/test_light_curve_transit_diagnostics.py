"""Tests for transit models and candidate diagnostics."""

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_transit_diagnostics import (
    LightCurveTransitDiagnosticError,
    build_transit_mask,
    calculate_transit_windows,
    diagnose_transit_candidate,
    generate_box_transit_model,
    transit_phase_time,
)
from astroscope.light_curve_transit_search import (
    TransitSearchCandidate,
)

TRUE_PERIOD = 2.0
TRUE_DURATION = 0.2
TRUE_TRANSIT_TIME = 0.5
TRUE_DEPTH = 0.03


def make_candidate(
    *,
    period: float = TRUE_PERIOD,
    duration: float = TRUE_DURATION,
    transit_time: float = TRUE_TRANSIT_TIME,
    depth: float = TRUE_DEPTH,
) -> TransitSearchCandidate:
    return TransitSearchCandidate(
        rank=1,
        period=period,
        power=25.0,
        duration=duration,
        transit_time=transit_time,
        depth=depth,
        depth_error=0.002,
        depth_snr=15.0,
    )


def make_flux_curve():
    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Transit Diagnostic Target",
            photometry_kind="flux",
        ),
        times=[
            0.0,
            0.45,
            0.50,
            0.55,
            1.0,
            2.0,
            2.45,
            2.50,
            2.55,
            3.0,
            4.0,
            4.50,
            4.60,
        ],
        values=[
            1.00,
            0.97,
            0.97,
            0.97,
            1.00,
            1.00,
            0.97,
            0.97,
            0.97,
            1.00,
            1.00,
            0.97,
            1.00,
        ],
        uncertainties=[0.002 for _ in range(13)],
    )


def test_transit_phase_time_is_centered_on_midpoint() -> None:
    candidate = make_candidate()

    assert transit_phase_time(
        0.5,
        candidate,
    ) == pytest.approx(0.0)

    assert transit_phase_time(
        2.5,
        candidate,
    ) == pytest.approx(0.0)

    assert transit_phase_time(
        0.45,
        candidate,
    ) == pytest.approx(-0.05)


def test_transit_mask_marks_periodic_events() -> None:
    mask = build_transit_mask(
        make_flux_curve(),
        make_candidate(),
    )

    assert mask == (
        False,
        True,
        True,
        True,
        False,
        False,
        True,
        True,
        True,
        False,
        False,
        True,
        False,
    )


def test_transit_windows_include_ingress_and_egress() -> None:
    windows = calculate_transit_windows(
        make_flux_curve(),
        make_candidate(),
    )

    assert tuple(window.cycle for window in windows) == (
        0,
        1,
        2,
    )

    assert windows[0].midpoint == pytest.approx(0.5)
    assert windows[0].ingress == pytest.approx(0.4)
    assert windows[0].egress == pytest.approx(0.6)

    assert windows[2].midpoint == pytest.approx(4.5)


def test_box_model_uses_measured_baseline() -> None:
    model = generate_box_transit_model(
        make_flux_curve(),
        make_candidate(),
    )

    assert model.baseline_flux == pytest.approx(1.0)
    assert model.in_transit_flux == pytest.approx(0.97)

    assert tuple(
        flux
        for flux, in_transit in zip(
            model.fluxes,
            model.mask,
            strict=True,
        )
        if in_transit
    ) == pytest.approx(
        (
            0.97,
            0.97,
            0.97,
            0.97,
            0.97,
            0.97,
            0.97,
        )
    )


def test_box_model_accepts_explicit_baseline() -> None:
    model = generate_box_transit_model(
        make_flux_curve(),
        make_candidate(),
        baseline_flux=1.1,
    )

    assert model.baseline_flux == pytest.approx(1.1)
    assert model.in_transit_flux == pytest.approx(1.07)


def test_diagnostics_measure_transit_depth() -> None:
    result = diagnose_transit_candidate(
        make_flux_curve(),
        make_candidate(),
    )

    assert result.measured_depth == pytest.approx(TRUE_DEPTH)
    assert result.depth_difference == pytest.approx(
        0.0,
        abs=1.0e-12,
    )

    assert result.in_transit_count == 7
    assert result.out_of_transit_count == 6


def test_perfect_box_model_has_zero_residuals() -> None:
    result = diagnose_transit_candidate(
        make_flux_curve(),
        make_candidate(),
    )

    assert result.residual_rms == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert result.in_transit_rms == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert result.out_of_transit_rms == pytest.approx(
        0.0,
        abs=1.0e-12,
    )


def test_diagnostic_points_include_phase_and_cycle() -> None:
    result = diagnose_transit_candidate(
        make_flux_curve(),
        make_candidate(),
    )

    midpoint_points = [
        point
        for point in result.points
        if point.time
        in {
            0.5,
            2.5,
            4.5,
        }
    ]

    assert tuple(point.phase for point in midpoint_points) == pytest.approx(
        (
            0.0,
            0.0,
            0.0,
        )
    )

    assert tuple(point.cycle for point in midpoint_points) == (
        0,
        1,
        2,
    )


def test_diagnostics_reject_magnitude_curve() -> None:
    curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Magnitude Target",
            photometry_kind="magnitude",
        ),
        times=[
            0.0,
            0.5,
            1.0,
        ],
        values=[
            12.0,
            12.1,
            12.0,
        ],
    )

    with pytest.raises(
        LightCurveTransitDiagnosticError,
        match="require flux",
    ):
        diagnose_transit_candidate(
            curve,
            make_candidate(),
        )


@pytest.mark.parametrize(
    ("period", "duration", "depth", "message"),
    [
        (
            0.0,
            0.2,
            0.03,
            "period",
        ),
        (
            2.0,
            0.0,
            0.03,
            "duration",
        ),
        (
            2.0,
            2.0,
            0.03,
            "shorter than",
        ),
        (
            2.0,
            0.2,
            0.0,
            "depth",
        ),
    ],
)
def test_diagnostics_reject_invalid_candidate(
    period: float,
    duration: float,
    depth: float,
    message: str,
) -> None:
    with pytest.raises(
        LightCurveTransitDiagnosticError,
        match=message,
    ):
        diagnose_transit_candidate(
            make_flux_curve(),
            make_candidate(
                period=period,
                duration=duration,
                depth=depth,
            ),
        )


def test_diagnostics_require_in_transit_observations() -> None:
    curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="No Transit Samples",
            photometry_kind="flux",
        ),
        times=[
            1.0,
            1.1,
            1.2,
        ],
        values=[
            1.0,
            1.0,
            1.0,
        ],
    )

    with pytest.raises(
        LightCurveTransitDiagnosticError,
        match="inside the predicted transit",
    ):
        diagnose_transit_candidate(
            curve,
            make_candidate(),
        )


def test_model_requires_out_of_transit_observations() -> None:
    curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Only Transit Samples",
            photometry_kind="flux",
        ),
        times=[
            0.45,
            0.50,
            0.55,
        ],
        values=[
            0.97,
            0.97,
            0.97,
        ],
    )

    with pytest.raises(
        LightCurveTransitDiagnosticError,
        match="out-of-transit observations",
    ):
        generate_box_transit_model(
            curve,
            make_candidate(),
        )
