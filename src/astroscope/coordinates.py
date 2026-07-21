"""Celestial-coordinate parsing and transformation utilities."""

import warnings
from dataclasses import dataclass
from typing import Final

import astropy.units as u
from astropy.coordinates import Angle, IllegalHourWarning, SkyCoord


@dataclass(frozen=True, slots=True)
class CelestialPreset:
    """A predefined celestial object's ICRS coordinates."""

    right_ascension: str
    declination: str


@dataclass(frozen=True, slots=True)
class CoordinateResult:
    """Calculated representations of one celestial coordinate."""

    right_ascension_hms: str
    right_ascension_hours: float
    right_ascension_degrees: float
    declination_dms: str
    declination_degrees: float
    galactic_longitude_degrees: float
    galactic_latitude_degrees: float
    cartesian_x: float
    cartesian_y: float
    cartesian_z: float


CELESTIAL_PRESETS: Final[dict[str, CelestialPreset]] = {
    "sirius": CelestialPreset(
        right_ascension="06h45m08.91728s",
        declination="-16d42m58.0171s",
    ),
    "betelgeuse": CelestialPreset(
        right_ascension="05h55m10.30536s",
        declination="+07d24m25.4304s",
    ),
    "vega": CelestialPreset(
        right_ascension="18h36m56.33635s",
        declination="+38d47m01.2802s",
    ),
    "polaris": CelestialPreset(
        right_ascension="02h31m49.09456s",
        declination="+89d15m50.7923s",
    ),
    "m31": CelestialPreset(
        right_ascension="00h42m44.330s",
        declination="+41d16m07.50s",
    ),
}


def parse_right_ascension(right_ascension: str) -> Angle:
    """Parse and validate right ascension expressed as an hour angle."""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", IllegalHourWarning)
            angle = Angle(
                right_ascension.strip(),
                unit=u.hourangle,
            )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Right ascension must use a format such as '06h45m08.9s' or '06:45:08.9'."
        ) from error

    hours = float(angle.to_value(u.hourangle))

    if not 0.0 <= hours < 24.0:
        raise ValueError(
            "Right ascension must be greater than or equal to 0 hours and less than 24 hours."
        )

    return angle


def parse_declination(declination: str) -> Angle:
    """Parse and validate declination expressed in degrees."""

    try:
        angle = Angle(declination.strip(), unit=u.deg)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Declination must use a format such as '-16d42m58s' or '-16:42:58'."
        ) from error

    degrees = float(angle.to_value(u.deg))

    if not -90.0 <= degrees <= 90.0:
        raise ValueError("Declination must be between -90 and +90 degrees.")

    return angle


def create_icrs_coordinate(
    right_ascension: str,
    declination: str,
) -> SkyCoord:
    """Create an ICRS SkyCoord from right ascension and declination."""

    ra_angle = parse_right_ascension(right_ascension)
    dec_angle = parse_declination(declination)

    return SkyCoord(
        ra=ra_angle,
        dec=dec_angle,
        frame="icrs",
    )


def calculate_coordinate_details(
    right_ascension: str,
    declination: str,
) -> CoordinateResult:
    """Calculate formatted ICRS, Galactic, and Cartesian coordinates."""

    coordinate = create_icrs_coordinate(
        right_ascension=right_ascension,
        declination=declination,
    )

    galactic = coordinate.galactic
    cartesian = coordinate.cartesian

    right_ascension_hms = coordinate.ra.to_string(
        unit=u.hourangle,
        sep=":",
        precision=3,
        pad=True,
    )

    declination_dms = coordinate.dec.to_string(
        unit=u.deg,
        sep=":",
        precision=2,
        alwayssign=True,
        pad=True,
    )

    return CoordinateResult(
        right_ascension_hms=right_ascension_hms,
        right_ascension_hours=float(coordinate.ra.to_value(u.hourangle)),
        right_ascension_degrees=float(coordinate.ra.to_value(u.deg)),
        declination_dms=declination_dms,
        declination_degrees=float(coordinate.dec.to_value(u.deg)),
        galactic_longitude_degrees=float(galactic.l.to_value(u.deg)),
        galactic_latitude_degrees=float(galactic.b.to_value(u.deg)),
        cartesian_x=float(cartesian.x.value),
        cartesian_y=float(cartesian.y.value),
        cartesian_z=float(cartesian.z.value),
    )
