"""Tests for astronomical light-curve import and export."""

import json

import pytest

from astroscope.light_curve import LightCurveMetadata
from astroscope.light_curve_io import (
    LightCurveColumnMap,
    LightCurveIOError,
    detect_light_curve_csv_columns,
    export_light_curve_csv,
    export_light_curve_json,
    import_light_curve_csv,
)
from astroscope.light_curve_period import (
    LombScargleResult,
    PeriodCandidate,
    PeriodogramPoint,
)
from astroscope.light_curve_phase import (
    bin_phase_fold,
    fold_light_curve,
)
from astroscope.light_curve_transit_search import (
    BoxLeastSquaresSearchResult,
    TransitPeriodogramPoint,
    TransitSearchCandidate,
)


def make_metadata() -> LightCurveMetadata:
    return LightCurveMetadata(
        object_name="WASP-12 b",
        photometry_kind="flux",
    )


def make_columns() -> LightCurveColumnMap:
    return LightCurveColumnMap(
        time="bjd",
        value="flux",
        uncertainty="flux_error",
    )


def test_import_csv_orders_observations() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n2460002.0,0.99,0.01\n2460000.0,1.00,0.01\n2460001.0,0.98,0.02\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.imported_rows == 3
    assert result.skipped_rows == 0
    assert result.original_was_sorted is False

    assert tuple(point.time for point in result.light_curve.points) == (
        2460000.0,
        2460001.0,
        2460002.0,
    )


def test_import_csv_skips_invalid_rows() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n"
            "2460000.0,1.00,0.01\n"
            "invalid,0.99,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.total_rows == 4
    assert result.imported_rows == 3
    assert result.skipped_rows == 1


def test_import_csv_accepts_blank_uncertainty() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n2460000.0,1.00,0.01\n2460001.0,0.98,\n2460002.0,1.01,0.02\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.light_curve.has_uncertainties is False
    assert result.light_curve.points[1].uncertainty is None


def test_import_csv_rejects_duplicate_time() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="Duplicate observation time",
    ):
        import_light_curve_csv(
            csv_text=(
                "bjd,flux,flux_error\n"
                "2460000.0,1.00,0.01\n"
                "2460000.0,0.99,0.01\n"
                "2460001.0,0.98,0.02\n"
                "2460002.0,1.01,0.01\n"
            ),
            metadata=make_metadata(),
            columns=make_columns(),
        )


def test_import_csv_can_keep_first_duplicate() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd,flux,flux_error\n"
            "2460000.0,1.00,0.01\n"
            "2460000.0,0.99,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
        duplicate_policy="keep-first",
    )

    assert result.imported_rows == 3
    assert result.duplicate_rows == 1
    assert result.skipped_rows == 1
    assert result.light_curve.points[0].value == pytest.approx(1.0)


def test_import_csv_rejects_missing_column() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="missing mapped columns",
    ):
        import_light_curve_csv(
            csv_text=("bjd,brightness\n2460000.0,1.00\n2460001.0,0.99\n2460002.0,1.01\n"),
            metadata=make_metadata(),
            columns=make_columns(),
        )


def test_column_mapping_requires_distinct_columns() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="distinct columns",
    ):
        LightCurveColumnMap(
            time="flux",
            value="flux",
        )


def test_import_csv_accepts_padded_header_names() -> None:
    result = import_light_curve_csv(
        csv_text=(
            "bjd   , flux   , flux_error\n"
            "2460000.0,1.00,0.01\n"
            "2460001.0,0.98,0.02\n"
            "2460002.0,1.01,0.01\n"
        ),
        metadata=make_metadata(),
        columns=make_columns(),
    )

    assert result.imported_rows == 3


def test_export_csv_round_trips_flux_light_curve() -> None:
    original = import_light_curve_csv(
        csv_text=("time,flux,uncertainty\n0.0,1.0,0.01\n1.0,0.98,0.02\n2.0,1.01,0.01\n"),
        metadata=make_metadata(),
        columns=LightCurveColumnMap(
            time="time",
            value="flux",
            uncertainty="uncertainty",
        ),
    ).light_curve

    exported_csv = export_light_curve_csv(original)

    assert exported_csv.splitlines()[0] == ("time,flux,uncertainty")

    detection = detect_light_curve_csv_columns(exported_csv)
    round_trip = import_light_curve_csv(
        csv_text=exported_csv,
        metadata=original.metadata,
        columns=detection.columns,
    ).light_curve

    assert round_trip.metadata == original.metadata
    assert round_trip.points == original.points


def test_export_csv_uses_magnitude_header() -> None:
    metadata = LightCurveMetadata(
        object_name="RR Lyrae",
        photometry_kind="magnitude",
    )
    light_curve = import_light_curve_csv(
        csv_text=("time,magnitude,uncertainty\n0.0,12.4,0.02\n1.0,12.2,0.03\n2.0,12.5,0.02\n"),
        metadata=metadata,
        columns=LightCurveColumnMap(
            time="time",
            value="magnitude",
            uncertainty="uncertainty",
        ),
    ).light_curve

    exported_csv = export_light_curve_csv(light_curve)

    assert exported_csv.splitlines()[0] == ("time,magnitude,uncertainty")


def test_export_csv_rejects_non_light_curve() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="LightCurve instance",
    ):
        export_light_curve_csv("not-a-light-curve")


def test_export_json_contains_metadata_summary_and_observations() -> None:
    light_curve = import_light_curve_csv(
        csv_text=("time,flux,uncertainty\n0.0,1.0,0.01\n1.0,0.98,0.02\n2.0,1.01,0.01\n"),
        metadata=make_metadata(),
        columns=LightCurveColumnMap(
            time="time",
            value="flux",
            uncertainty="uncertainty",
        ),
    ).light_curve

    report = json.loads(export_light_curve_json(light_curve))

    assert report["schema_version"] == 1
    assert report["metadata"] == {
        "object_name": "WASP-12 b",
        "photometry_kind": "flux",
        "time_standard": "BJD_TDB",
        "filter_name": None,
        "observatory_name": None,
        "telescope_name": None,
    }
    assert report["summary"] == {
        "observation_count": 3,
        "start_time": 0.0,
        "end_time": 2.0,
        "duration": 2.0,
        "has_uncertainties": True,
    }
    assert report["observations"] == [
        {
            "time": 0.0,
            "value": 1.0,
            "uncertainty": 0.01,
        },
        {
            "time": 1.0,
            "value": 0.98,
            "uncertainty": 0.02,
        },
        {
            "time": 2.0,
            "value": 1.01,
            "uncertainty": 0.01,
        },
    ]


def test_export_json_rejects_non_light_curve() -> None:
    with pytest.raises(
        LightCurveIOError,
        match="LightCurve instance",
    ):
        export_light_curve_json({"not": "a light curve"})


def test_export_json_includes_period_and_transit_analyses() -> None:
    light_curve = import_light_curve_csv(
        csv_text=("time,flux,uncertainty\n0.0,1.0,0.01\n1.0,0.98,0.02\n2.0,1.01,0.01\n"),
        metadata=make_metadata(),
        columns=LightCurveColumnMap(
            time="time",
            value="flux",
            uncertainty="uncertainty",
        ),
    ).light_curve

    period_result = LombScargleResult(
        minimum_period=1.0,
        maximum_period=5.0,
        observation_baseline=2.0,
        weighted=True,
        samples=(
            PeriodogramPoint(
                frequency=0.25,
                period=4.0,
                power=0.9,
            ),
        ),
        candidates=(
            PeriodCandidate(
                rank=1,
                frequency=0.25,
                period=4.0,
                power=0.9,
                false_alarm_probability=0.001,
            ),
        ),
    )

    transit_result = BoxLeastSquaresSearchResult(
        minimum_period=1.0,
        maximum_period=5.0,
        durations=(0.5,),
        objective="snr",
        observation_baseline=2.0,
        weighted=True,
        samples=(
            TransitPeriodogramPoint(
                period=4.0,
                power=12.0,
                duration=0.5,
                transit_time=1.0,
                depth=0.05,
                depth_error=0.005,
                depth_snr=10.0,
            ),
        ),
        candidates=(
            TransitSearchCandidate(
                rank=1,
                period=4.0,
                power=12.0,
                duration=0.5,
                transit_time=1.0,
                depth=0.05,
                depth_error=0.005,
                depth_snr=10.0,
            ),
        ),
    )

    report = json.loads(
        export_light_curve_json(
            light_curve,
            period_result=period_result,
            transit_result=transit_result,
        )
    )

    assert report["period_analysis"]["weighted"] is True
    assert report["period_analysis"]["candidates"][0] == {
        "rank": 1,
        "frequency": 0.25,
        "period": 4.0,
        "power": 0.9,
        "false_alarm_probability": 0.001,
    }

    assert report["transit_analysis"]["objective"] == "snr"
    assert report["transit_analysis"]["candidates"][0] == {
        "rank": 1,
        "period": 4.0,
        "power": 12.0,
        "duration": 0.5,
        "transit_time": 1.0,
        "depth": 0.05,
        "depth_error": 0.005,
        "depth_snr": 10.0,
    }


def test_export_json_includes_phase_fold_and_binning() -> None:
    light_curve = import_light_curve_csv(
        csv_text=("time,flux,uncertainty\n0.0,1.0,0.01\n1.0,0.98,0.02\n2.0,1.01,0.01\n"),
        metadata=make_metadata(),
        columns=LightCurveColumnMap(
            time="time",
            value="flux",
            uncertainty="uncertainty",
        ),
    ).light_curve

    phase_fold = fold_light_curve(
        light_curve,
        period=2.0,
    )
    phase_binning = bin_phase_fold(
        phase_fold,
        bin_count=2,
    )

    report = json.loads(
        export_light_curve_json(
            light_curve,
            phase_fold=phase_fold,
            phase_binning=phase_binning,
        )
    )

    phase_analysis = report["phase_analysis"]

    assert phase_analysis["period"] == pytest.approx(2.0)
    assert phase_analysis["epoch"] == pytest.approx(0.0)
    assert phase_analysis["observation_count"] == 3
    assert len(phase_analysis["points"]) == 3
    assert "light_curve" not in phase_analysis

    assert phase_analysis["points"][0] == {
        "time": 0.0,
        "phase": 0.0,
        "cycle": 0,
        "value": 1.0,
        "uncertainty": 0.01,
    }

    binning = phase_analysis["binning"]

    assert binning["bin_count"] == 2
    assert binning["minimum_points"] == 1
    assert binning["weighted"] is True
    assert binning["populated_bin_count"] == 2
    assert len(binning["bins"]) == 2
