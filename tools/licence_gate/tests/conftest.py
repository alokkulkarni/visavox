"""Shared fixtures for licence-gate tests (NFR-S6, ADR-005)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

VALID_SHA = "a" * 64


def model_entry(**overrides: Any) -> dict[str, Any]:
    """A minimal valid candidate entry; tests override fields to break one rule at a time."""
    entry: dict[str, Any] = {
        "name": "example-model",
        "purpose": "realtime_photo_avatar",
        "status": "candidate",
        "source_url": "https://example.com/example-model",
        "code_licence": "Apache-2.0",
        "weights_licence": "MIT",
        "commercial_use": True,
        "requirements": ["RT-02"],
    }
    entry.update(overrides)
    return entry


@pytest.fixture
def valid_sha() -> str:
    return VALID_SHA


@pytest.fixture
def entry() -> Callable[..., dict[str, Any]]:
    """Factory for a minimal valid candidate entry; override fields to break one rule at a time."""
    return model_entry


@pytest.fixture
def write_registry(tmp_path: Path) -> Callable[..., Path]:
    def _write(*entries: dict[str, Any], version: int = 1) -> Path:
        path = tmp_path / "models" / "registry.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"version": version, "models": list(entries)}))
        return path

    return _write
