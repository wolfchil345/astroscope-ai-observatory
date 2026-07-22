"""Tests for astrophotography frame visualizations."""

import pytest

from astroscope.imaging import (
    ImagingTargetSpec,
    calculate_target_framing,
)
from astroscope.imaging_visuals import (
    ImagingFrameLabels,
    create_imaging_frame_figure,
    rectangle_vertices,
)


def create_labels() -> ImagingFrameLabels:
    """Create English labels for chart tests."""

    return ImagingFrameLabels(
        title="Imaging frame",
        horizontal_axis="Horizontal angle",
        vertical_axis="Vertical angle",
        target="Target",
        sensor_panel="Sensor panel",
        rotation="Rotation",
        mosaic="Mosaic",
    )


def test_rectangle_vertices_close_the_shape() -> None:
    x_values, y_values = rectangle_vertices(
        width_degrees=2.0,
        height_degrees=1.0,
    )

    assert len(x_values) == 5
    assert len(y_values) == 5
    assert x_values[0] == x_values[-1]
    assert y_values[0] == y_values[-1]


def test_rotation_changes_rectangle_coordinates() -> None:
    normal_x, normal_y = rectangle_vertices(
        width_degrees=2.0,
        height_degrees=1.0,
        rotation_degrees=0.0,
    )

    rotated_x, rotated_y = rectangle_vertices(
        width_degrees=2.0,
        height_degrees=1.0,
        rotation_degrees=45.0,
    )

    assert normal_x != rotated_x
    assert normal_y != rotated_y


def test_single_panel_figure_has_two_traces() -> None:
    target = ImagingTargetSpec(
        key="moon",
        width_degrees=0.5,
        height_degrees=0.5,
    )

    framing = calculate_target_framing(
        field_width_degrees=2.0,
        field_height_degrees=1.5,
        target=target,
    )

    figure = create_imaging_frame_figure(
        field_width_degrees=2.0,
        field_height_degrees=1.5,
        target=target,
        framing=framing,
        rotation_degrees=0.0,
        target_name="Moon",
        labels=create_labels(),
    )

    assert framing.total_panels == 1
    assert len(figure.data) == 2
    assert figure.layout.yaxis.scaleanchor == "x"
    assert figure.layout.yaxis.scaleratio == 1


def test_mosaic_figure_has_one_trace_per_panel() -> None:
    target = ImagingTargetSpec(
        key="large_target",
        width_degrees=5.0,
        height_degrees=2.0,
    )

    framing = calculate_target_framing(
        field_width_degrees=2.0,
        field_height_degrees=1.0,
        target=target,
        overlap_percent=20.0,
    )

    figure = create_imaging_frame_figure(
        field_width_degrees=2.0,
        field_height_degrees=1.0,
        target=target,
        framing=framing,
        rotation_degrees=25.0,
        target_name="Large target",
        labels=create_labels(),
    )

    assert framing.total_panels == 9

    assert len(figure.data) == (framing.total_panels + 1)


def test_imaging_figure_uses_short_margin_keys() -> None:
    target = ImagingTargetSpec(
        key="moon",
        width_degrees=0.5,
        height_degrees=0.5,
    )

    framing = calculate_target_framing(
        field_width_degrees=2.0,
        field_height_degrees=1.5,
        target=target,
    )

    figure = create_imaging_frame_figure(
        field_width_degrees=2.0,
        field_height_degrees=1.5,
        target=target,
        framing=framing,
        rotation_degrees=0.0,
        target_name="Moon",
        labels=create_labels(),
    )

    assert figure.layout.margin.l == 50
    assert figure.layout.margin.r == 50
    assert figure.layout.margin.t == 85
    assert figure.layout.margin.b == 50


def test_non_finite_rotation_raises_error() -> None:
    with pytest.raises(ValueError):
        rectangle_vertices(
            width_degrees=2.0,
            height_degrees=1.0,
            rotation_degrees=float("inf"),
        )
