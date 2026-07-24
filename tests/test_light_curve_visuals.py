"""Tests for astronomical light-curve visualizations."""

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_visuals import (
    LightCurveVisualError,
    LightCurveVisualLabels,
    build_light_curve_comparison_figure,
    build_light_curve_figure,
)


def make_curve(
    *,
    object_name: str = "Visual Test Target",
    photometry_kind: str = "flux",
    values: list[float] | None = None,
    uncertainties: list[float] | None = None,
):
    resolved_values = (
        values
        if values is not None
        else [
            1.0,
            0.98,
            1.01,
        ]
    )

    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name=object_name,
            photometry_kind=photometry_kind,
        ),
        times=[
            0.0,
            1.0,
            2.0,
        ],
        values=resolved_values,
        uncertainties=uncertainties,
    )


def test_single_light_curve_figure_contains_points() -> None:
    figure = build_light_curve_figure(make_curve())

    assert len(figure.data) == 1

    trace = figure.data[0]

    assert trace.type == "scatter"
    assert trace.mode == "markers"

    assert tuple(trace.x) == pytest.approx(
        (
            0.0,
            1.0,
            2.0,
        )
    )

    assert tuple(trace.y) == pytest.approx(
        (
            1.0,
            0.98,
            1.01,
        )
    )


def test_single_figure_uses_object_name() -> None:
    figure = build_light_curve_figure(
        make_curve(
            object_name="Kepler Test Star",
        )
    )

    assert figure.layout.title.text == "Kepler Test Star light curve"
    assert figure.data[0].name == "Kepler Test Star"


def test_figure_can_connect_points() -> None:
    figure = build_light_curve_figure(
        make_curve(),
        connect_points=True,
    )

    assert figure.data[0].mode == "lines+markers"


def test_flux_figure_uses_flux_axis() -> None:
    figure = build_light_curve_figure(
        make_curve(
            photometry_kind="flux",
        )
    )

    assert figure.layout.yaxis.title.text == "Flux"
    assert figure.layout.yaxis.autorange != "reversed"


def test_magnitude_figure_reverses_vertical_axis() -> None:
    figure = build_light_curve_figure(
        make_curve(
            photometry_kind="magnitude",
            values=[
                12.1,
                11.9,
                12.0,
            ],
        )
    )

    assert figure.layout.yaxis.title.text == "Magnitude"
    assert figure.layout.yaxis.autorange == "reversed"


def test_uncertainties_create_error_bars() -> None:
    figure = build_light_curve_figure(
        make_curve(
            uncertainties=[
                0.01,
                0.02,
                0.03,
            ],
        )
    )

    error_y = figure.data[0].error_y

    assert error_y.visible is True
    assert tuple(error_y.array) == pytest.approx(
        (
            0.01,
            0.02,
            0.03,
        )
    )


def test_curve_without_uncertainties_has_no_error_array() -> None:
    figure = build_light_curve_figure(make_curve())

    error_y = figure.data[0].error_y

    assert error_y.visible is not True
    assert error_y.array is None


def test_comparison_figure_contains_two_series() -> None:
    raw_curve = make_curve(
        values=[
            1.02,
            0.97,
            1.01,
        ],
    )
    processed_curve = make_curve(
        values=[
            1.01,
            0.99,
            1.00,
        ],
    )

    figure = build_light_curve_comparison_figure(
        raw_curve,
        processed_curve,
    )

    assert len(figure.data) == 2

    assert tuple(trace.name for trace in figure.data) == (
        "Raw",
        "Processed",
    )

    assert figure.layout.showlegend is True


def test_comparison_accepts_custom_series_names() -> None:
    figure = build_light_curve_comparison_figure(
        make_curve(),
        make_curve(),
        raw_name="Imported observations",
        processed_name="Detrended observations",
    )

    assert tuple(trace.name for trace in figure.data) == (
        "Imported observations",
        "Detrended observations",
    )


def test_custom_labels_support_future_i18n() -> None:
    labels = LightCurveVisualLabels(
        time_axis="Zeit",
        flux_axis="Fluss",
        magnitude_axis="Magnitude",
        raw_series="Rohdaten",
        processed_series="Verarbeitet",
    )

    figure = build_light_curve_comparison_figure(
        make_curve(),
        make_curve(),
        labels=labels,
    )

    assert figure.layout.xaxis.title.text == "Zeit"
    assert figure.layout.yaxis.title.text == "Fluss"

    assert tuple(trace.name for trace in figure.data) == (
        "Rohdaten",
        "Verarbeitet",
    )


def test_comparison_rejects_mixed_photometry_kinds() -> None:
    with pytest.raises(
        LightCurveVisualError,
        match="same photometry kind",
    ):
        build_light_curve_comparison_figure(
            make_curve(
                photometry_kind="flux",
            ),
            make_curve(
                photometry_kind="magnitude",
                values=[
                    12.0,
                    12.1,
                    12.0,
                ],
            ),
        )


@pytest.mark.parametrize(
    "connect_points",
    [
        1,
        "yes",
        None,
    ],
)
def test_visuals_reject_non_boolean_connect_setting(
    connect_points,
) -> None:
    with pytest.raises(
        LightCurveVisualError,
        match="boolean",
    ):
        build_light_curve_figure(
            make_curve(),
            connect_points=connect_points,
        )
