"""Tests for telescope field-of-view visualizations."""

import pytest

from astroscope.telescope_visuals import (
    ANGULAR_SIZE_PRESETS,
    AngularSizeTarget,
    FieldOfViewLabels,
    classify_target_fit,
    create_field_of_view_figure,
)


def create_labels() -> FieldOfViewLabels:
    """Create English labels for chart tests."""

    return FieldOfViewLabels(
        title="Field of view",
        angular_distance="Angular distance",
        field_of_view="True field",
        target="Target",
        target_size="Target size",
        fit="Fit",
    )


@pytest.mark.parametrize(
    ("field_degrees", "target_degrees", "expected"),
    [
        (2.0, 1.0, "comfortable"),
        (1.1, 1.0, "tight"),
        (0.8, 1.0, "too_large"),
    ],
)
def test_target_fit_classification(
    field_degrees: float,
    target_degrees: float,
    expected: str,
) -> None:
    target = AngularSizeTarget(
        key="test",
        major_axis_degrees=target_degrees,
        minor_axis_degrees=target_degrees,
    )

    assert (
        classify_target_fit(
            true_field_degrees=field_degrees,
            target=target,
        )
        == expected
    )


def test_field_of_view_figure_contains_two_shapes() -> None:
    target = ANGULAR_SIZE_PRESETS["moon"]

    figure = create_field_of_view_figure(
        true_field_degrees=1.5,
        target=target,
        target_name="Moon",
        fit_name="Comfortable",
        labels=create_labels(),
    )

    assert len(figure.layout.shapes) == 2
    assert len(figure.data) == 1
    assert figure.layout.yaxis.scaleanchor == "x"
    assert figure.layout.yaxis.scaleratio == 1


def test_field_of_view_uses_short_margin_keys() -> None:
    figure = create_field_of_view_figure(
        true_field_degrees=1.5,
        target=ANGULAR_SIZE_PRESETS["moon"],
        target_name="Moon",
        fit_name="Comfortable",
        labels=create_labels(),
    )

    assert figure.layout.margin.l == 50
    assert figure.layout.margin.r == 50
    assert figure.layout.margin.t == 80
    assert figure.layout.margin.b == 50


def test_invalid_field_of_view_raises_error() -> None:
    with pytest.raises(ValueError):
        classify_target_fit(
            true_field_degrees=0.0,
            target=ANGULAR_SIZE_PRESETS["moon"],
        )
