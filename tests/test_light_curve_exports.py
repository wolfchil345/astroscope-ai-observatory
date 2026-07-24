"""Tests for astronomical light-curve CSV exports."""

import csv
from io import StringIO

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_exports import (
    LightCurveExportError,
    light_curve_to_csv,
    phase_bins_to_csv,
    phase_fold_to_csv,
)
from astroscope.light_curve_phase import (
    bin_phase_fold,
    fold_light_curve,
)


def read_csv_rows(
    content: str,
) -> list[dict[str, str]]:
    """Parse exported CSV text into dictionaries."""

    return list(csv.DictReader(StringIO(content)))


def make_curve(
    *,
    with_uncertainties: bool = True,
):
    uncertainties = (
        [
            0.01,
            0.02,
            0.03,
            0.04,
        ]
        if with_uncertainties
        else None
    )

    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name="Target, Alpha",
            photometry_kind="flux",
        ),
        times=[
            0.0,
            0.25,
            0.50,
            0.75,
        ],
        values=[
            1.0,
            0.9,
            1.1,
            0.8,
        ],
        uncertainties=uncertainties,
    )


def make_phase_results():
    phase_fold = fold_light_curve(
        make_curve(),
        period=1.0,
        epoch=0.0,
    )

    phase_binning = bin_phase_fold(
        phase_fold,
        bin_count=2,
        minimum_points=1,
    )

    return phase_fold, phase_binning


def test_light_curve_csv_contains_metadata() -> None:
    rows = read_csv_rows(light_curve_to_csv(make_curve()))

    assert len(rows) == 4
    assert rows[0]["object_name"] == "Target, Alpha"
    assert rows[0]["photometry_kind"] == "flux"

    assert float(rows[0]["time"]) == pytest.approx(0.0)

    assert float(rows[0]["value"]) == pytest.approx(1.0)

    assert float(rows[0]["uncertainty"]) == pytest.approx(0.01)


def test_light_curve_csv_preserves_order() -> None:
    rows = read_csv_rows(light_curve_to_csv(make_curve()))

    assert tuple(float(row["time"]) for row in rows) == pytest.approx(
        (
            0.0,
            0.25,
            0.50,
            0.75,
        )
    )


def test_missing_uncertainties_are_blank() -> None:
    rows = read_csv_rows(
        light_curve_to_csv(
            make_curve(
                with_uncertainties=False,
            )
        )
    )

    assert all(row["uncertainty"] == "" for row in rows)


def test_phase_fold_csv_contains_analysis_values() -> None:
    phase_fold, _ = make_phase_results()

    rows = read_csv_rows(phase_fold_to_csv(phase_fold))

    assert len(rows) == 4

    assert all(float(row["period"]) == pytest.approx(1.0) for row in rows)

    assert all(float(row["epoch"]) == pytest.approx(0.0) for row in rows)

    assert tuple(float(row["phase"]) for row in rows) == pytest.approx(
        (
            0.0,
            0.25,
            0.50,
            0.75,
        )
    )

    assert tuple(int(row["cycle"]) for row in rows) == (
        0,
        0,
        0,
        0,
    )


def test_phase_bins_csv_contains_bin_settings() -> None:
    _, phase_binning = make_phase_results()

    rows = read_csv_rows(phase_bins_to_csv(phase_binning))

    assert len(rows) == 2

    assert all(row["bin_count"] == "2" for row in rows)

    assert all(row["minimum_points"] == "1" for row in rows)

    assert all(row["weighted"] == "True" for row in rows)

    assert tuple(int(row["observation_count"]) for row in rows) == (
        2,
        2,
    )


def test_phase_bins_csv_contains_bin_boundaries() -> None:
    _, phase_binning = make_phase_results()

    rows = read_csv_rows(phase_bins_to_csv(phase_binning))

    assert float(rows[0]["phase_start"]) == pytest.approx(0.0)

    assert float(rows[0]["phase_end"]) == pytest.approx(0.5)

    assert float(rows[0]["phase_center"]) == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("function", "value"),
    [
        (
            light_curve_to_csv,
            object(),
        ),
        (
            phase_fold_to_csv,
            object(),
        ),
        (
            phase_bins_to_csv,
            object(),
        ),
    ],
)
def test_exports_reject_wrong_result_type(
    function,
    value,
) -> None:
    with pytest.raises(
        LightCurveExportError,
        match="requires",
    ):
        function(value)


def test_exports_use_unix_line_endings() -> None:
    content = light_curve_to_csv(make_curve())

    assert "\r\n" not in content
    assert content.endswith("\n")
