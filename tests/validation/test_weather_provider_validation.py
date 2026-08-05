"""Offline checks for Mission 31 Open-Meteo provider-contract evidence."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from validation.weather_provider import (
    load_verified_inputs,
    run_validation,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation/manifests/weather_provider_contract_v1.json"


def test_manifest_fixture_integrity_hashes_verify() -> None:
    """The committed evidence inputs verify before use."""

    manifest, fixture = load_verified_inputs(MANIFEST)
    assert manifest["schema_version"] == fixture["schema_version"] == "1.0"


def test_normalized_transition_evidence_has_expected_categories() -> None:
    """The six normalized response scenarios remain discoverable."""

    _, fixture = load_verified_inputs(MANIFEST)
    assert [scenario["id"] for scenario in fixture["scenarios"]] == [
        "tokyo-ordinary",
        "new-york-spring-gap",
        "new-york-fall-fold",
        "london-fall-fold",
        "lord-howe-fall-fold",
        "lord-howe-spring-gap",
    ]


def test_canonical_offline_validation_run_is_reproducible() -> None:
    """The offline validator produces the committed result contract."""

    assert run_validation(MANIFEST)["aggregate_status"] == "passed"


def test_validation_performs_no_network_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal evidence verification never opens a socket."""

    monkeypatch.setattr(
        socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network"))
    )
    assert run_validation(MANIFEST)["scenario_count"] == 6
