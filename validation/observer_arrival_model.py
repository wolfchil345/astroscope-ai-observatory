"""Research-only timing candidate. Never grants production observing eligibility.

The context owns process-global astronomy tables and is for serial benchmark use.
Geometric timing here deliberately omits several relativistic/finite-distance terms.
"""

from __future__ import annotations

import hashlib
import json
import math
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from unittest.mock import patch

import astropy.units as u
import erfa
import numpy as np
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.table import QTable
from astropy.time import Time, TimeDelta
from astropy.utils import iers

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation/manifests/observer_arrival_v1.json"
POLICY = ROOT / "validation/manifests/observer_arrival_policy_v1.json"
EOP = ROOT / "validation/fixtures/solar_lunar_eop_v1.json"
LEAPS = ROOT / "validation/fixtures/observer_arrival_leaps_v1.json"
FIXTURE = ROOT / "validation/fixtures/observer_arrival_v1.json"
EXPECTED_MANIFEST_SHA256 = "6509f789568eb7df8642bb7a3ef0be719027fcd6b07583ca0946f5876533fb1e"


class ArrivalError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs() -> tuple[dict, dict]:
    if sha(MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise ArrivalError("manifest_checksum")
    manifest = json.loads(MANIFEST.read_text())
    for name, digest in manifest["files"].items():
        if sha(ROOT / name) != digest:
            raise ArrivalError("input_checksum")
    policy, fixture = json.loads(POLICY.read_text()), json.loads(FIXTURE.read_text())
    for key, count in [("cases", 288), ("leap_cases", 5)]:
        if len(fixture[key]) != count or len({r["id"] for r in fixture[key]}) != count:
            raise ArrivalError("fixture_denominator")
    return policy, fixture


def split_jd(value: str) -> tuple[float, float]:
    if not isinstance(value, str) or len(value) > 100:
        raise ArrivalError("decimal_jd_required")
    try:
        with localcontext() as ctx:
            ctx.prec = 80
            number = Decimal(value)
            if not number.is_finite() or not Decimal(2400000) <= number <= Decimal(2500000):
                raise ArrivalError("invalid_jd")
            whole = int(number)
            return float(whole), float(number - whole)
    except InvalidOperation as exc:
        raise ArrivalError("invalid_jd") from exc


def time_from_jd(value: str, scale: str, location=None) -> Time:
    return Time(*split_jd(value), format="jd", scale=scale, location=location)


def finite_number(value: object, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArrivalError("invalid_context_number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ArrivalError("invalid_context_number")
    return float(value)


def context_coordinates(site: dict, target: dict) -> tuple[EarthLocation, SkyCoord]:
    if not isinstance(site, dict) or not isinstance(target, dict):
        raise ArrivalError("context_required")
    if site.get("datum") != "WGS84" or target.get("frame") != "ICRS":
        raise ArrivalError("unsupported_frame")
    if (
        target.get("coordinate_epoch") != "J2000"
        or target.get("motion_assumption") != "fixed_icrs_direction_at_infinity"
    ):
        raise ArrivalError("unsupported_motion")
    loc = EarthLocation.from_geodetic(
        finite_number(site.get("longitude_deg"), -180, 180) * u.deg,
        finite_number(site.get("latitude_deg"), -90, 90) * u.deg,
        finite_number(site.get("elevation_m"), -500, 9000) * u.m,
    )
    coord = SkyCoord(
        ra=finite_number(target.get("ra_deg"), 0, 360) * u.deg,
        dec=finite_number(target.get("dec_deg"), -90, 90) * u.deg,
        frame="icrs",
    )
    return loc, coord


@dataclass(frozen=True)
class ResearchArrival:
    tai: Time
    iterations: int
    residual_seconds: float
    model_id: str = "geometric-plane-wave-tdb-v1"
    observing_eligible: bool = False


class ResearchConverter:
    """Finite historical study domain, not an operational timing service."""

    def __init__(self, policy: dict):
        self.policy = policy
        self.active = False

    def _active(self):
        if not self.active:
            raise ArrivalError("research_context_closed")

    def _geometric_domain(self, t: Time):
        self._active()
        if not t.isscalar or not math.isfinite(t.jd1) or not math.isfinite(t.jd2):
            raise ArrivalError("finite_scalar_required")
        start, end = self.policy["geometric_guard_utc_interval"]
        if not Time(start, scale="utc") <= t < Time(end, scale="utc"):
            raise ArrivalError("outside_frozen_domain")

    def _correction(self, t: Time, coord: SkyCoord) -> TimeDelta:
        return t.light_travel_time(coord, kind="barycentric", ephemeris="builtin")

    def forward(self, tai: Time, site: dict, target: dict) -> Time:
        if not isinstance(tai, Time) or tai.scale != "tai":
            raise ArrivalError("observer_tai_required")
        self._geometric_domain(tai)
        loc, coord = context_coordinates(site, target)
        t = Time(tai.jd1, tai.jd2, format="jd", scale="tai", location=loc)
        return t.tdb + self._correction(t, coord)

    def inverse(
        self,
        coordinate_jd: str,
        site: dict,
        target: dict,
        *,
        model_id: str = "geometric-plane-wave-tdb-v1",
        scale: str = "tdb",
        reference_position: str = "barycentric",
        input_state: str = "source_coordinate",
    ) -> ResearchArrival:
        self._active()
        if model_id != self.policy["model_id"]:
            raise ArrivalError("unsupported_correction_model")
        if scale != "tdb" or reference_position != "barycentric":
            raise ArrivalError("unsupported_coordinate")
        if input_state != "source_coordinate":
            raise ArrivalError("already_resolved_or_unknown_state")
        loc, coord = context_coordinates(site, target)
        b = time_from_jd(coordinate_jd, "tdb", loc)
        t = b
        for iteration in range(1, self.policy["solver"]["max_iterations"] + 1):
            self._geometric_domain(t)
            correction = self._correction(t, coord)
            residual = float(((t + correction) - b).to_value(u.s))
            if not math.isfinite(residual):
                raise ArrivalError("nonfinite_solver_residual")
            if abs(residual) <= self.policy["solver"]["stopping_residual_seconds"]:
                return ResearchArrival(t.tai, iteration, residual)
            t = t - TimeDelta(residual, format="sec", scale="tdb")
        raise ArrivalError("solver_nonconvergence")

    def observer_utc(self, tai_jd: str) -> Time:
        self._active()
        t = time_from_jd(tai_jd, "tai")
        a, b = self.policy["leap_guard_tai_interval"]
        leap_domain = Time(a, scale="tai") <= t <= Time(b, scale="tai")
        a, b = self.policy["geometric_guard_utc_interval"]
        geometric_domain = Time(a, scale="utc") <= t < Time(b, scale="utc")
        if not (leap_domain or geometric_domain):
            raise ArrivalError("outside_frozen_domain")
        t.precision = 9
        return t.utc

    def datetime_export(self, tai_jd: str):
        try:
            return self.observer_utc(tai_jd).to_datetime(leap_second_strict="raise")
        except ValueError as exc:
            if isinstance(exc, ArrivalError):
                raise
            raise ArrivalError("unrepresentable_utc_datetime") from exc


def deny_network(*args, **kwargs):
    raise RuntimeError("Observer-arrival validation must be offline")


@contextmanager
def frozen_converter():
    """Verify inputs, pin data, block sockets, and restore state even after failure."""
    policy, _ = load_inputs()
    rows = json.loads(EOP.read_text())["rows"]
    table = QTable()
    for key, unit in [("MJD", u.day), ("UT1_UTC", u.s), ("PM_x", u.arcsec), ("PM_y", u.arcsec)]:
        table[key] = [r[key] for r in rows] * unit
    leap_rows = json.loads(LEAPS.read_text())["rows"]
    pinned = np.array(
        [(r["year"], r["month"], r["tai_utc"]) for r in leap_rows],
        dtype=[("year", "i4"), ("month", "i4"), ("tai_utc", "f8")],
    )
    previous = erfa.leap_seconds.get().copy()
    converter = ResearchConverter(policy)
    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket, "create_connection", deny_network),
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("iers_degraded_accuracy", "error"),
        iers.earth_orientation_table.set(iers.IERS(table)),
    ):
        try:
            # Let Astropy finish its lazy leap-table initialization before replacing it.
            _ = Time("2024-01-01", scale="tai").utc
            erfa.leap_seconds.set(pinned)
            converter.active = True
            yield converter
        finally:
            converter.active = False
            erfa.leap_seconds.set(previous)
