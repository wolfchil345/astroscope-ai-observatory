"""Verify committed Open-Meteo timestamp-contract evidence without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class WeatherProviderValidationError(ValueError):
    """Raised when committed provider-contract inputs fail verification."""


def _path(value: str | Path) -> Path:
    """Resolve a repository-relative validation path."""

    candidate = Path(value)
    return candidate if candidate.is_absolute() else REPOSITORY_ROOT / candidate


def _sha256(path: Path) -> str:
    """Return one file digest."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified_inputs(manifest_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a manifest and fixture after deterministic integrity checks."""

    manifest = json.loads(_path(manifest_path).read_text(encoding="utf-8"))
    fixture_path = _path(manifest["fixture_path"])
    if _sha256(fixture_path) != manifest["fixture_sha256"]:
        raise WeatherProviderValidationError(
            "Weather provider fixture SHA-256 verification failed."
        )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != manifest.get("schema_version"):
        raise WeatherProviderValidationError("Weather provider schema versions do not match.")
    return manifest, fixture


def run_validation(manifest_path: str | Path) -> dict[str, Any]:
    """Validate normalized archived response evidence fully offline."""

    manifest, fixture = load_verified_inputs(manifest_path)
    scenarios = fixture.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 6:
        raise WeatherProviderValidationError("Expected exactly six provider evidence scenarios.")
    for scenario in scenarios:
        if scenario["named_iso"]["offset_free"] is not True:
            raise WeatherProviderValidationError("Expected offset-free named-zone ISO evidence.")
        if scenario["named_unix"]["step_seconds"] != [3600]:
            raise WeatherProviderValidationError("Expected hourly Unix timestamp steps.")
    return {
        "schema_version": "1.0",
        "benchmark_id": "weather-provider-contract-v1",
        "aggregate_status": "passed",
        "scenario_count": len(scenarios),
        "fixture_sha256": manifest["fixture_sha256"],
        "claim_boundary": fixture["claim_boundary"],
    }


def main() -> int:
    """Run the offline validator and write a deterministic JSON record."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    record = run_validation(arguments.manifest)
    Path(arguments.output).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
