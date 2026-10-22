"""Every service runs in the local cell, pinned, health-checked and private (NFR-O5, SDD §14)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from local_cell.check import check, main

DIGEST = "sha256:" + "a" * 64


def healthy(**overrides: Any) -> dict[str, Any]:
    service: dict[str, Any] = {
        "image": f"example/infra:1.0@{DIGEST}",
        "healthcheck": {"test": ["CMD", "true"]},
    }
    service.update(overrides)
    return service


def built(name: str, **overrides: Any) -> dict[str, Any]:
    service: dict[str, Any] = {
        "build": {"context": "../..", "dockerfile": f"services/{name}/Dockerfile"},
        "healthcheck": {"test": ["CMD", "true"]},
    }
    service.update(overrides)
    return service


Repo = Callable[..., Path]


def codes(root: Path) -> list[str]:
    return [v.code for v in check(root)]


def test_infrastructure_only_cell_is_clean(repo: Repo) -> None:
    assert check(repo({"livekit": healthy(), "postgres": healthy()})) == []


def test_missing_compose_file_is_reported(repo: Repo) -> None:
    assert codes(repo(None)) == ["LC001"]


class TestServices:
    def test_service_with_dockerfile_and_compose_entry_is_clean(self, repo: Repo) -> None:
        root = repo({"session": built("session")}, {"session": True})
        assert check(root) == []

    def test_service_without_dockerfile_is_reported(self, repo: Repo) -> None:
        assert "LC002" in codes(repo({"session": built("session")}, {"session": False}))

    def test_service_missing_from_compose_is_reported(self, repo: Repo) -> None:
        assert "LC003" in codes(repo({"livekit": healthy()}, {"control-plane": True}))

    def test_compose_entry_must_build_the_services_own_dockerfile(self, repo: Repo) -> None:
        root = repo({"session": healthy()}, {"session": True})
        assert "LC007" in codes(root)


class TestHealthchecks:
    def test_default_service_without_healthcheck_is_reported(self, repo: Repo) -> None:
        service = healthy()
        del service["healthcheck"]
        assert "LC004" in codes(repo({"livekit": service}))

    def test_disabled_healthcheck_is_reported(self, repo: Repo) -> None:
        assert "LC004" in codes(repo({"livekit": healthy(healthcheck={"disable": True})}))

    def test_profiled_one_shot_service_needs_no_healthcheck(self, repo: Repo) -> None:
        service = healthy(profiles=["gpu"])
        del service["healthcheck"]
        assert check(repo({"gpu-check": service})) == []


class TestImages:
    @pytest.mark.parametrize("image", ["postgres:17", "postgres:latest", "postgres"])
    def test_image_without_digest_is_reported(self, repo: Repo, image: str) -> None:
        assert "LC005" in codes(repo({"postgres": healthy(image=image)}))


class TestPorts:
    @pytest.mark.parametrize("port", ["127.0.0.1:5432:5432", "127.0.0.1:7880:7880", "7882:7882/udp"])
    def test_loopback_ports_and_the_media_port_are_allowed(self, repo: Repo, port: str) -> None:
        assert check(repo({"livekit": healthy(ports=[port])})) == []

    @pytest.mark.parametrize("port", ["5432:5432", "0.0.0.0:7880:7880", "7881:7881", "7883:7883/udp", 5432])
    def test_ports_reachable_from_the_network_are_reported(self, repo: Repo, port: object) -> None:
        assert "LC006" in codes(repo({"livekit": healthy(ports=[port])}))


class TestCli:
    def test_clean_cell_exits_zero(self, repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--root", str(repo({"livekit": healthy()}))]) == 0
        assert "0 violation(s)" in capsys.readouterr().out

    def test_violations_exit_one_and_are_listed(self, repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--root", str(repo({"livekit": healthy(image="livekit")}))]) == 1
        out = capsys.readouterr().out
        assert "LC005 livekit" in out

    def test_unreadable_compose_exits_two(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        compose = tmp_path / "deploy" / "local" / "compose.yaml"
        compose.parent.mkdir(parents=True)
        compose.write_text("services: [unclosed\n")
        assert main(["--root", str(tmp_path)]) == 2
        assert "compose error" in capsys.readouterr().err
