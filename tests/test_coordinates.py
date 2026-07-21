"""Tests for celestial-coordinate parsing and transformations."""

import pytest

from astroscope.coordinates import (
    CELESTIAL_PRESETS,
    calculate_coordinate_details,
    create_icrs_coordinate,
    parse_declination,
    parse_right_ascension,
)


def test_every_celestial_preset_can_be_parsed() -> None:
    for preset in CELESTIAL_PRESETS.values():
        coordinate = create_icrs_coordinate(
            right_ascension=preset.right_ascension,
            declination=preset.declination,
        )

        assert coordinate.frame.name == "icrs"


def test_sirius_coordinate_values() -> None:
    result = calculate_coordinate_details(
        right_ascension="06h45m08.91728s",
        declination="-16d42m58.0171s",
    )

    assert result.right_ascension_hours == pytest.approx(
        6.752477,
        abs=0.000001,
    )

    assert result.right_ascension_degrees == pytest.approx(
        result.right_ascension_hours * 15.0,
    )

    assert result.declination_degrees == pytest.approx(
        -16.716116,
        abs=0.000001,
    )


def test_polaris_is_close_to_north_celestial_pole() -> None:
    preset = CELESTIAL_PRESETS["polaris"]

    result = calculate_coordinate_details(
        right_ascension=preset.right_ascension,
        declination=preset.declination,
    )

    assert result.declination_degrees > 89.0


def test_galactic_coordinates_have_valid_ranges() -> None:
    result = calculate_coordinate_details(
        right_ascension="18h36m56.33635s",
        declination="+38d47m01.2802s",
    )

    assert 0.0 <= result.galactic_longitude_degrees < 360.0
    assert -90.0 <= result.galactic_latitude_degrees <= 90.0


def test_cartesian_direction_is_unit_length() -> None:
    result = calculate_coordinate_details(
        right_ascension="00h42m44.330s",
        declination="+41d16m07.50s",
    )

    vector_length_squared = result.cartesian_x**2 + result.cartesian_y**2 + result.cartesian_z**2

    assert vector_length_squared == pytest.approx(1.0)


@pytest.mark.parametrize(
    "right_ascension",
    [
        "-01h00m00s",
        "24h00m00s",
        "25h00m00s",
        "not-a-coordinate",
    ],
)
def test_invalid_right_ascension_raises_error(
    right_ascension: str,
) -> None:
    with pytest.raises(ValueError):
        parse_right_ascension(right_ascension)


@pytest.mark.parametrize(
    "declination",
    [
        "-91d00m00s",
        "+91d00m00s",
        "not-a-coordinate",
    ],
)
def test_invalid_declination_raises_error(
    declination: str,
) -> None:
    with pytest.raises(ValueError):
        parse_declination(declination)


def test_formatted_coordinate_strings_exist() -> None:
    result = calculate_coordinate_details(
        right_ascension="05h55m10.30536s",
        declination="+07d24m25.4304s",
    )

    assert result.right_ascension_hms.count(":") == 2
    assert result.declination_dms.count(":") == 2
