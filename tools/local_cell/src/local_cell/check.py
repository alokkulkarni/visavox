"""Check that every Visavox service runs in the local Docker cell (NFR-O5, SDD §14).

`local-cell-check [--root DIR]` reads deploy/local/compose.yaml and the services/ folder.
Exit codes: 0 clean, 1 violations found, 2 compose file unreadable.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

COMPOSE = Path("deploy/local/compose.yaml")
# The only port the local cell may expose beyond loopback: LiveKit's WebRTC media port, which clients in
# containers and in the host browser both reach through the host's network address.
MEDIA_PORTS = frozenset({"7882:7882/udp"})


class ComposeError(Exception):
    """deploy/local/compose.yaml is not valid YAML or not a compose mapping."""


@dataclass(frozen=True)
class Violation:
    code: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.subject}: {self.message}"


def check(root: Path) -> list[Violation]:
    compose_path = root / COMPOSE
    if not compose_path.is_file():
        return [Violation("LC001", str(COMPOSE), "local cell compose file is missing")]
    services = _load_services(compose_path)
    violations: list[Violation] = []
    violations.extend(_service_folder_violations(root, services))
    for name, service in services.items():
        violations.extend(_compose_service_violations(name, service))
    return violations


def _load_services(path: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ComposeError(f"invalid YAML in {path}: {exc}") from exc
    services = raw.get("services") if isinstance(raw, dict) else None
    if not isinstance(services, dict):
        raise ComposeError(f"{path} has no `services` mapping")
    return {str(name): service or {} for name, service in services.items()}


def _service_folder_violations(root: Path, services: dict[str, dict[str, Any]]) -> list[Violation]:
    found: list[Violation] = []
    folders = sorted(p for p in (root / "services").glob("*") if p.is_dir())
    for folder in folders:
        name, dockerfile = folder.name, f"services/{folder.name}/Dockerfile"
        if not (folder / "Dockerfile").is_file():
            found.append(Violation("LC002", name, f"{dockerfile} is missing"))
        service = services.get(name)
        if service is None:
            found.append(Violation("LC003", name, f"no `{name}` service in {COMPOSE}"))
            continue
        build = service.get("build")
        if not isinstance(build, dict) or build.get("dockerfile") != dockerfile:
            found.append(Violation("LC007", name, f"compose service must build from {dockerfile}"))
    return found


def _compose_service_violations(name: str, service: dict[str, Any]) -> list[Violation]:
    found: list[Violation] = []
    healthcheck = service.get("healthcheck")
    if not service.get("profiles") and (not healthcheck or healthcheck.get("disable")):
        found.append(Violation("LC004", name, "default services need a healthcheck so `make up` can wait"))
    image = service.get("image")
    if "build" not in service and (not isinstance(image, str) or "@sha256:" not in image):
        found.append(Violation("LC005", name, f"image must be pinned by digest: {image}"))
    for port in service.get("ports", []):
        if not (isinstance(port, str) and (port.startswith("127.0.0.1:") or port in MEDIA_PORTS)):
            found.append(Violation("LC006", name, f"port {port} is reachable from the network"))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="local-cell-check", description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    args = parser.parse_args(argv)
    try:
        violations = check(args.root)
    except ComposeError as exc:
        print(f"compose error: {exc}", file=sys.stderr)
        return 2
    for violation in violations:
        print(violation)
    print(f"local cell checked, {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
