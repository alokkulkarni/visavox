"""CLI exit codes and output for the licence gate (NFR-S6, ADR-005)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from licence_gate.cli import main


def test_valid_registry_exits_zero(
    write_registry: Callable[..., Path],
    entry: Callable[..., dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(write_registry(entry()))]) == 0
    assert "1 model(s) checked, 0 violation(s)" in capsys.readouterr().out


def test_violations_exit_one_and_are_listed(
    write_registry: Callable[..., Path],
    entry: Callable[..., dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_registry(entry(weights_licence="CC-BY-NC-4.0"))
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "LG003" in out
    assert "example-model" in out


def test_schema_error_exits_two(
    write_registry: Callable[..., Path],
    entry: Callable[..., dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(write_registry(entry(status="live")))]) == 2
    assert "registry error" in capsys.readouterr().err


def test_scan_option_reports_banned_files(
    write_registry: Callable[..., Path],
    entry: Callable[..., dict[str, object]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    weights = tmp_path / "weights"
    weights.mkdir()
    (weights / "det_10g.onnx").write_bytes(b"\x00")
    assert main([str(write_registry(entry())), "--scan", str(weights)]) == 1
    assert "det_10g.onnx" in capsys.readouterr().out


def test_scan_of_missing_directory_exits_two(
    write_registry: Callable[..., Path],
    entry: Callable[..., dict[str, object]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(write_registry(entry())), "--scan", str(tmp_path / "absent")]) == 2
    assert "not a directory" in capsys.readouterr().err
