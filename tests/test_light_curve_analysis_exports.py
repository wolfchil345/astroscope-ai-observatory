"""Tests for scientific light-curve analysis exports."""

import csv
import json
from dataclasses import dataclass
from io import StringIO

import pytest

from astroscope.light_curve import (
    LightCurveMetadata,
    build_light_curve,
)
from astroscope.light_curve_analysis_exports import (
    analysis_report_to_json,
    build_analysis_report,
    period_candidates_to_csv,
    transit_candidates_to_csv,
    transit_diagnostics_to_csv,
)
from astroscope.light_curve_exports import (
    LightCurveExportError,
)
from astroscope.light_curve_transit_diagnostics import (
    diagnose_transit_candidate,
)
from astroscope.light_curve_transit_search import (
    BoxLeastSquaresSearchResult,
    TransitPeriodogramPoint,
    TransitSearchCandidate,
)


@dataclass(frozen=True, slots=True)
class FakePeriodCandidate:
    rank: int
    period: float
    power: float


@dataclass(frozen=True, slots=True)
class FakePeriodResult:
    candidates: tuple[FakePeriodCandidate, ...]


def read_csv_rows(
    content: str,
) -> list[dict[str, str]]:
    """Parse CSV text into dictionaries."""

    return list(csv.DictReader(StringIO(content)))


def make_curve(
    *,
    object_name: str = "星-A",
    with_uncertainties: bool = True,
):
    uncertainties = [0.002 for _ in range(10)] if with_uncertainties else None

    return build_light_curve(
        metadata=LightCurveMetadata(
            object_name=object_name,
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
        uncertainties=uncertainties,
    )


def make_period_result() -> FakePeriodResult:
    return FakePeriodResult(
        candidates=(
            FakePeriodCandidate(
                rank=1,
                period=2.0,
                power=0.9,
            ),
            FakePeriodCandidate(
                rank=2,
                period=1.0,
                power=0.6,
            ),
        )
    )


def make_transit_candidate() -> TransitSearchCandidate:
    return TransitSearchCandidate(
        rank=1,
        period=2.0,
        power=20.0,
        duration=0.2,
        transit_time=0.5,
        depth=0.03,
        depth_error=0.002,
        depth_snr=15.0,
    )


def make_bls_result() -> BoxLeastSquaresSearchResult:
    candidate = make_transit_candidate()

    return BoxLeastSquaresSearchResult(
        minimum_period=1.0,
        maximum_period=3.0,
        durations=(0.2,),
        objective="snr",
        observation_baseline=3.0,
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
        ),
        candidates=(candidate,),
    )


def make_diagnostics(
    *,
    with_uncertainties: bool = True,
):
    return diagnose_transit_candidate(
        make_curve(
            with_uncertainties=with_uncertainties,
        ),
        make_transit_candidate(),
    )


def test_period_candidates_csv_contains_ranked_results() -> None:
    rows = read_csv_rows(period_candidates_to_csv(make_period_result()))

    assert len(rows) == 2

    assert tuple(int(row["rank"]) for row in rows) == (
        1,
        2,
    )

    assert tuple(float(row["period"]) for row in rows) == pytest.approx(
        (
            2.0,
            1.0,
        )
    )


def test_empty_period_candidates_export_header_only() -> None:
    content = period_candidates_to_csv(
        FakePeriodResult(
            candidates=(),
        )
    )

    rows = read_csv_rows(content)

    assert rows == []
    assert content.startswith("rank,period,power\n")


def test_transit_candidates_csv_contains_bls_values() -> None:
    rows = read_csv_rows(transit_candidates_to_csv(make_bls_result()))

    assert len(rows) == 1

    row = rows[0]

    assert row["rank"] == "1"
    assert float(row["period"]) == pytest.approx(2.0)
    assert float(row["duration"]) == pytest.approx(0.2)
    assert float(row["depth"]) == pytest.approx(0.03)
    assert float(row["depth_snr"]) == pytest.approx(15.0)


def test_transit_diagnostics_csv_contains_points() -> None:
    diagnostics = make_diagnostics()

    rows = read_csv_rows(transit_diagnostics_to_csv(diagnostics))

    assert len(rows) == len(diagnostics.points)

    assert all(float(row["measured_depth"]) == pytest.approx(0.03) for row in rows)

    assert {row["in_transit"] for row in rows} == {
        "True",
        "False",
    }


def test_diagnostics_csv_uses_blank_missing_uncertainties() -> None:
    rows = read_csv_rows(
        transit_diagnostics_to_csv(
            make_diagnostics(
                with_uncertainties=False,
            )
        )
    )

    assert all(row["uncertainty"] == "" for row in rows)


def test_analysis_report_contains_dataset_summary() -> None:
    report = build_analysis_report(make_curve())

    dataset = report["dataset"]

    assert isinstance(dataset, dict)
    assert dataset["object_name"] == "星-A"
    assert dataset["photometry_kind"] == "flux"
    assert dataset["observation_count"] == 10
    assert dataset["time_start"] == pytest.approx(0.0)
    assert dataset["time_end"] == pytest.approx(3.0)
    assert dataset["time_span"] == pytest.approx(3.0)
    assert dataset["has_uncertainties"] is True


def test_complete_json_report_contains_all_sections() -> None:
    content = analysis_report_to_json(
        make_curve(),
        period_result=make_period_result(),
        transit_result=make_bls_result(),
        transit_diagnostics=make_diagnostics(),
    )

    report = json.loads(content)

    assert report["schema_version"] == "1.0"
    assert "period_search" in report
    assert "transit_search" in report
    assert "transit_diagnostics" in report

    assert report["period_search"]["candidates"][0]["period"] == pytest.approx(2.0)

    assert report["transit_search"]["candidates"][0]["depth"] == pytest.approx(0.03)

    assert report["transit_diagnostics"]["measured_depth"] == pytest.approx(0.03)


def test_json_report_preserves_unicode() -> None:
    content = analysis_report_to_json(
        make_curve(
            object_name="ケプラー星",
        )
    )

    assert "ケプラー星" in content
    assert "\\u30b1" not in content


def test_json_report_is_deterministic_and_newline_terminated() -> None:
    first = analysis_report_to_json(
        make_curve(),
        period_result=make_period_result(),
    )
    second = analysis_report_to_json(
        make_curve(),
        period_result=make_period_result(),
    )

    assert first == second
    assert first.endswith("\n")


@pytest.mark.parametrize(
    "function",
    [
        period_candidates_to_csv,
        transit_candidates_to_csv,
        transit_diagnostics_to_csv,
    ],
)
def test_analysis_exports_reject_wrong_result_types(
    function,
) -> None:
    with pytest.raises(
        LightCurveExportError,
    ):
        function(object())


def test_json_report_rejects_invalid_indentation() -> None:
    with pytest.raises(
        LightCurveExportError,
        match="indentation",
    ):
        analysis_report_to_json(
            make_curve(),
            indent=-1,
        )
