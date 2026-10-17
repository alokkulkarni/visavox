"""Command line entry point: `licence-gate models/registry.yaml [--scan DIR]` (ADR-005, NFR-S6).

Exit codes: 0 clean, 1 violations found, 2 registry or input error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from licence_gate.registry import RegistryError, load_registry, validate
from licence_gate.scan import scan_artefacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="licence-gate", description=__doc__)
    parser.add_argument("registry", type=Path, help="path to models/registry.yaml")
    parser.add_argument(
        "--base-dir", type=Path, default=None, help="repository root for licence text paths (default: ../..)"
    )
    parser.add_argument("--scan", type=Path, default=None, help="directory of downloaded artefacts to scan")
    args = parser.parse_args(argv)

    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 2
    if args.scan is not None and not args.scan.is_dir():
        print(f"scan path is not a directory: {args.scan}", file=sys.stderr)
        return 2

    base_dir = args.base_dir or args.registry.resolve().parent.parent
    violations = validate(registry, base_dir=base_dir)
    if args.scan is not None:
        violations.extend(scan_artefacts(args.scan))

    for violation in violations:
        print(violation)
    print(f"{len(registry.models)} model(s) checked, {len(violations)} violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
