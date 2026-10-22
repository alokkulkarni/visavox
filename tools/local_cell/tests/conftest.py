"""Fixture repositories for the local-cell guard (NFR-O5)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def repo(tmp_path: Path) -> Callable[..., Path]:
    """Write a repo with `deploy/local/compose.yaml` and the given `services/<name>` folders."""

    def _repo(
        compose_services: dict[str, dict[str, Any]] | None,
        service_dirs: dict[str, bool] | None = None,
    ) -> Path:
        for name, has_dockerfile in (service_dirs or {}).items():
            folder = tmp_path / "services" / name
            folder.mkdir(parents=True)
            if has_dockerfile:
                (folder / "Dockerfile").write_text("FROM scratch\n")
        if compose_services is not None:
            compose = tmp_path / "deploy" / "local" / "compose.yaml"
            compose.parent.mkdir(parents=True)
            compose.write_text(yaml.safe_dump({"services": compose_services}))
        return tmp_path

    return _repo
