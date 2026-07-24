"""Tests for scientific light-curve analysis visualizations."""

from dataclasses import dataclass

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_analysis_visuals import (
    LightCurveAnalysisVisualLabels,
    build_bls_periodogram_figure,
    build_lomb_scargle_periodogram_figure,
    build_phase_folded_figure,
    build_transit_model_figure,
    build_transit_residual_figure,
)
from astroscope.light_curve_phase import (
    bin_phase_fold,
    fold_light_curve,
)
from astroscope.light_curve_transit_diagnostics import (
    diagnose_transit_candidate,
)
from astroscope.light_curve_transit_search import (
    BoxLeastSquaresSearchResult,
    TransitPeriodogramPoint,
    TransitSearchCandidate,
)
from astroscope.light_curve_visuals import (
    LightCurveVisualError,
)


@dataclass(frozen=True, slots=True)
class FakePeriodogramPoint:
    period: float
    power: float


@dataclass(frozen=True, slots=True)
class FakePeriodCandidate:
    rank: int
    period: float
    power: float


@dataclass(frozen=True, slots=True)
class FakePeriodogramResult:
    samples: tuple[FakePeriodogramPoint, ...]
    candidates: tuple[FakePeriodCandidate, ...]


def make_periodogram_result() -> FakePeriodogramResult:
    return FakePeriodogramResult(
        samples=(
            FakePeriodogramPoint(
                period=3.0,
                power=0.2,
            ),
            FakePeriodogramPoint(
                period=1.0,
                power=0.1,
            ),
            FakePeriodogramPoint(
                period=2.0,
                power=0.8,
            ),
        ),
        candidates=(
            FakePeriodCandidate(
                rank=1,
                period=2.0,
                power=0.8,
            ),
        ),
    )


def make_phase_results(
    *,
    photometry_kind: str = "flux",
):
    values = (
        [
            1.0,
            0.9,
            1.0,
            0.9,
        ]
        if photometry_kind == "flux"
        else [
            12.0,
            12.1,
            12.0,
            12.1,
        ]
    )

    curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Phase Visual Target",
            photometry_kind=photometry_kind,
        ),
        times=[
            0.0,
            0.5,
            1.0,
            1.5,
        ],
        values=values,
        uncertainties=[
            0.01,
            0.01,
            0.01,
            0.01,
        ],
    )

    phase_fold = fold_light_curve(
        curve,
        period=1.0,
        epoch=0.0,
    )

    phase_binning = bin_phase_fold(
        phase_fold,
        bin_count=2,
    )

    return phase_fold, phase_binning


def make_bls_result() -> BoxLeastSquaresSearchResult:
    candidate = TransitSearchCandidate(
        rank=1,
        period=2.0,
        power=20.0,
        duration=0.2,
        transit_time=0.5,
        depth=0.03,
        depth_error=0.002,
        depth_snr=15.0,
    )

    return BoxLeastSquaresSearchResult(
        minimum_period=1.0,
        maximum_period=3.0,
        durations=(0.2,),
        objective="snr",
        observation_baseline=10.0,
        weighted=True,
        samples=(
            TransitPeriodogramPoint(
                period=1.5,
                power=4.0,
                duration=0.2,
                transit_time=0.4,
                depth=0.01,
                depth_error=0.003,
                depth_snr=3.0,
            ),
            TransitPeriodogramPoint(
                period=2.0,
                power=20.0,
                duration=0.2,
                transit_time=0.5,
                depth=0.03,
                depth_error=0.002,
                depth_snr=15.0,
            ),
            TransitPeriodogramPoint(
                period=2.5,
                power=5.0,
                duration=0.2,
                transit_time=0.6,
                depth=0.012,
                depth_error=0.003,
                depth_snr=4.0,
            ),
        ),
        candidates=(candidate,),
    )


def make_transit_diagnostics():
    curve = build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Transit Visual Target",
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
        ],
        values=[
            1.0,
            0.97,
            0.97,
            0.97,
            1.0,
            1.0,
            0.97,
            0.97,
            0.97,
            1.0,
        ],
        uncertainties=[0.002 for _ in range(10)],
    )

    candidate = TransitSearchCandidate(
        rank=1,
        period=2.0,
        power=20.0,
        duration=0.2,
        transit_time=0.5,
        depth=0.03,
        depth_error=0.002,
        depth_snr=15.0,
    )

    return diagnose_transit_candidate(
        curve,
        candidate,
    )


def test_lomb_scargle_figure_sorts_periods() -> None:
    figure = build_lomb_scargle_periodogram_figure(make_periodogram_result())

    assert len(figure.data) == 2

    assert tuple(figure.data[0].x) == pytest.approx(
        (
            1.0,
            2.0,
            3.0,
        )
    )

    assert tuple(figure.data[0].y) == pytest.approx(
        (
            0.1,
            0.8,
            0.2,
        )
    )


def test_lomb_scargle_figure_marks_candidates() -> None:
    figure = build_lomb_scargle_periodogram_figure(make_periodogram_result())

    candidate_trace = figure.data[1]

    assert candidate_trace.name == "Period candidates"
    assert candidate_trace.mode == "markers"
    assert tuple(candidate_trace.x) == pytest.approx((2.0,))


def test_periodogram_rejects_empty_samples() -> None:
    with pytest.raises(
        LightCurveVisualError,
        match="at least one value",
    ):
        build_lomb_scargle_periodogram_figure(
            FakePeriodogramResult(
                samples=(),
                candidates=(),
            )
        )


def test_phase_figure_contains_observations_and_bins() -> None:
    phase_fold, phase_binning = make_phase_results()

    figure = build_phase_folded_figure(
        phase_fold,
        phase_binning=phase_binning,
    )

    assert len(figure.data) == 2

    assert tuple(trace.name for trace in figure.data) == (
        "Folded observations",
        "Phase bins",
    )

    assert figure.data[0].error_y.visible is True
    assert figure.layout.xaxis.title.text == "Phase"
    assert figure.layout.yaxis.title.text == "Flux"


def test_phase_magnitude_axis_is_reversed() -> None:
    phase_fold, _ = make_phase_results(
        photometry_kind="magnitude",
    )

    figure = build_phase_folded_figure(phase_fold)

    assert figure.layout.yaxis.title.text == "Magnitude"
    assert figure.layout.yaxis.autorange == "reversed"


def test_bls_figure_contains_power_and_candidate() -> None:
    figure = build_bls_periodogram_figure(make_bls_result())

    assert len(figure.data) == 2
    assert figure.data[0].name == "BLS power"
    assert figure.data[1].name == "Transit candidates"

    assert tuple(figure.data[1].x) == pytest.approx((2.0,))


def test_transit_model_figure_contains_two_series() -> None:
    figure = build_transit_model_figure(make_transit_diagnostics())

    assert len(figure.data) == 2

    assert tuple(trace.name for trace in figure.data) == (
        "Observed",
        "Box transit model",
    )

    assert figure.data[0].error_y.visible is True
    assert figure.layout.xaxis.title.text == "Time from transit midpoint"


def test_transit_model_points_are_sorted_by_phase_time() -> None:
    figure = build_transit_model_figure(make_transit_diagnostics())

    phase_times = tuple(figure.data[0].x)

    assert phase_times == tuple(sorted(phase_times))


def test_residual_figure_contains_zero_reference() -> None:
    figure = build_transit_residual_figure(make_transit_diagnostics())

    assert len(figure.data) == 1
    assert figure.data[0].name == "Residual"
    assert len(figure.layout.shapes) == 1

    reference = figure.layout.shapes[0]

    assert reference.y0 == pytest.approx(0.0)
    assert reference.y1 == pytest.approx(0.0)


def test_analysis_visuals_accept_custom_labels() -> None:
    labels = LightCurveAnalysisVisualLabels(
        period_axis="Periodo",
        power_axis="Potenza",
        lomb_scargle_series="Potenza Lomb-Scargle",
        period_candidates="Candidati",
    )

    figure = build_lomb_scargle_periodogram_figure(
        make_periodogram_result(),
        labels=labels,
    )

    assert figure.layout.xaxis.title.text == "Periodo"
    assert figure.layout.yaxis.title.text == "Potenza"
    assert figure.data[0].name == "Potenza Lomb-Scargle"
