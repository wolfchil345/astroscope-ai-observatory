"""Independent optical corpus, reference integrity and policy-boundary controls."""

import ast
import json
import math
import shutil
import socket
from pathlib import Path

import pytest

from astroscope import imaging, telescope
from validation import telescope_imaging as audit
from validation.reference_generation import telescope_imaging as reference

MANIFEST, FIXTURE = audit.load_inputs()


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["id"])
def test_frozen_reference(case):
    assert audit.compare_case(case, MANIFEST["policy"])["passed"]


def test_offline_reference_regenerates_exactly(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket, "socket", deny)
    assert reference.encoded_fixture() == (audit.ROOT / audit.FIXTURE).read_text()
    assert audit.run_benchmark()["overall_passed"]


def test_reference_has_no_production_or_binary_trig_imports():
    tree = ast.parse(Path(reference.__file__).read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(n.name.split(".")[0] for n in node.names)
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module.split(".")[0])
    assert set(modules) <= {
        "__future__",
        "argparse",
        "json",
        "decimal",
        "fractions",
        "itertools",
        "pathlib",
    }


@pytest.mark.parametrize("path", [audit.MANIFEST, *MANIFEST["files"]])
def test_corrupted_reference_is_rejected(tmp_path, path):
    for name in [audit.MANIFEST, *MANIFEST["files"]]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(audit.ROOT / name, destination)
    with (tmp_path / path).open("a") as file:
        file.write(" ")
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit.load_inputs(tmp_path)


def test_old_diagonal_regression_is_detected(monkeypatch):
    original = imaging.calculate_astrophotography_setup

    def old(*args, **kwargs):
        from dataclasses import replace

        result = original(*args, **kwargs)
        return replace(
            result,
            field_diagonal_degrees=math.hypot(
                result.field_width_degrees, result.field_height_degrees
            ),
        )

    monkeypatch.setattr(imaging, "calculate_astrophotography_setup", old)
    case = next(c for c in FIXTURE["cases"] if c["id"] == "imaging-100")
    result = audit.compare_case(case, MANIFEST["policy"])
    assert not result["passed"]
    assert not result["metrics"]["field_diagonal_degrees"]["passed"]


def test_unit_error_is_detected(monkeypatch):
    monkeypatch.setattr(imaging, "PLATE_SCALE_CONSTANT", 206265)
    case = next(c for c in FIXTURE["cases"] if c["kind"] == "imaging")
    assert not audit.compare_case(case, MANIFEST["policy"])["passed"]


def test_missing_overlap_is_detected(monkeypatch):
    original = imaging.calculate_target_framing

    def no_overlap(**kwargs):
        kwargs["overlap_percent"] = 0
        return original(**kwargs)

    monkeypatch.setattr(imaging, "calculate_target_framing", no_overlap)
    case = next(
        c
        for c in FIXTURE["cases"]
        if c["kind"] == "mosaic"
        and c["inputs"]["overlap"] == "50"
        and c["inputs"]["target_width"] == "2.5"
    )
    assert not audit.compare_case(case, MANIFEST["policy"])["passed"]


@pytest.mark.parametrize(
    "scale,expected",
    [
        (math.nextafter(1, 0), "oversampled"),
        (1, "well_sampled"),
        (1.5, "well_sampled"),
        (math.nextafter(1.5, math.inf), "undersampled"),
        (3, "undersampled"),
        (math.nextafter(3, math.inf), "severely_undersampled"),
    ],
)
def test_sampling_policy_boundaries(scale, expected):
    assert (
        imaging.classify_sampling(image_scale_arcsec_per_pixel=scale, seeing_arcseconds=3)
        == expected
    )


@pytest.mark.parametrize(
    "pupil,magnification,expected",
    [
        (math.nextafter(0.5, 0), 100, "excessive_magnification"),
        (0.5, 100, "high_power"),
        (math.nextafter(1, 0), 100, "high_power"),
        (1, 100, "general_purpose"),
        (math.nextafter(2, 0), 100, "general_purpose"),
        (2, 100, "wide_field"),
        (7, 100, "wide_field"),
        (math.nextafter(7, math.inf), 100, "excessive_exit_pupil"),
        (2, 200, "wide_field"),
        (2, math.nextafter(200, math.inf), "excessive_magnification"),
        (8, 201, "excessive_magnification"),
    ],
)
def test_optical_policy_boundaries(pupil, magnification, expected):
    assert (
        telescope.classify_optical_setup(
            exit_pupil_mm=pupil, magnification=magnification, maximum_useful_magnification=200
        )
        == expected
    )


@pytest.mark.parametrize(
    "size,expected",
    [
        (4, "comfortable"),
        (math.nextafter(4, math.inf), "tight"),
        (5, "tight"),
        (math.nextafter(5, math.inf), "mosaic_required"),
    ],
)
def test_framing_policy_boundaries(size, expected):
    result = imaging.calculate_target_framing(
        field_width_degrees=5,
        field_height_degrees=5,
        target=imaging.ImagingTargetSpec("test", size, size),
        overlap_percent=0,
    )
    assert result.status == expected


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize(
    "factory",
    [
        lambda x: telescope.TelescopeSpec(x, 650),
        lambda x: telescope.TelescopeSpec(130, x),
        lambda x: telescope.EyepieceSpec(x, 50),
        lambda x: telescope.EyepieceSpec(25, x),
        lambda x: imaging.CameraSensorSpec(100, 100, x),
        lambda x: imaging.calculate_sensor_field_degrees(x, 650),
        lambda x: imaging.calculate_sensor_field_degrees(24, x),
        lambda x: imaging.calculate_astrophotography_setup(
            telescope.TelescopeSpec(130, 650),
            imaging.CameraSensorSpec(100, 100, 4),
            seeing_arcseconds=x,
        ),
    ],
)
def test_nonpositive_nonfinite_rejected(factory, bad):
    with pytest.raises(ValueError):
        factory(bad)


@pytest.mark.parametrize("bad", [True, 1.5, 0, -1])
@pytest.mark.parametrize("axis", ["width", "height"])
def test_pixel_counts_are_positive_integers(bad, axis):
    with pytest.raises(ValueError):
        imaging.CameraSensorSpec(
            bad if axis == "width" else 100, bad if axis == "height" else 100, 4
        )


@pytest.mark.parametrize(
    "option,value",
    [
        ("barlow_factor", 0.99),
        ("barlow_factor", 0),
        ("barlow_factor", math.inf),
        ("reducer_factor", 1.01),
        ("reducer_factor", 0),
        ("reducer_factor", math.nan),
    ],
)
@pytest.mark.parametrize("kind", ["optical", "imaging"])
def test_accessory_contracts(kind, option, value):
    scope = telescope.TelescopeSpec(130, 650)
    with pytest.raises(ValueError):
        if kind == "optical":
            telescope.calculate_optical_simulation(
                scope, telescope.EyepieceSpec(25, 50), **{option: value}
            )
        else:
            imaging.calculate_astrophotography_setup(
                scope, imaging.CameraSensorSpec(100, 100, 4), **{option: value}
            )


@pytest.mark.parametrize("overlap", [-1, 100, 101, math.nan, math.inf])
def test_invalid_overlap(overlap):
    with pytest.raises(ValueError):
        imaging.calculate_target_framing(
            field_width_degrees=1,
            field_height_degrees=1,
            target=imaging.ImagingTargetSpec("test", 2, 2),
            overlap_percent=overlap,
        )


def test_exact_pi_and_constant_approximation():
    assert FIXTURE["pi"].startswith("3.14159265358979323846264338327950288419716939937510")
    # This bounds the rounded coefficient only, not physical image quality.
    assert abs(206.265 / float(FIXTURE["exact_plate_scale_constant"]) - 1) < 1e-6


def test_baseline_failure_record_preserved():
    result = json.loads(
        (audit.ROOT / "validation/results/telescope_imaging_baseline_run.json").read_text()
    )
    assert result["case_count"] == 307 and result["failed_cases"] == 35
    assert not result["overall_passed"]
    assert not result["environment"]["git_dirty"]
    assert {r["field"] for r in result["failure_metrics"]} == {"field_diagonal_degrees"}
