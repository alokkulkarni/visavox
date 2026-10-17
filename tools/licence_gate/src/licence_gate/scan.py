"""Scan a directory of downloaded model artefacts for banned components (ADR-005, NFR-S6)."""

from __future__ import annotations

from pathlib import Path

from licence_gate.registry import Violation
from licence_gate.rules import is_banned_component


def scan_artefacts(root: Path) -> list[Violation]:
    """Return one LG006 violation per file whose relative path names a banned component."""
    violations: list[Violation] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if is_banned_component(relative):
            violations.append(
                Violation("LG006", relative, "artefact path matches a banned non-commercial component")
            )
    return violations
