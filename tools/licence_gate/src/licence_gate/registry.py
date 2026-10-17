"""Load and validate models/registry.yaml (ADR-005, NFR-S6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from licence_gate.rules import LicenceClass, classify_licence, is_banned_component

REQUIREMENT_ID = r"^([A-Z]{2,4}-\d{2}|NFR-[A-Z]\d)$"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RegistryError(Exception):
    """The registry file is missing, unreadable or does not match the schema."""


@dataclass(frozen=True)
class Violation:
    code: str
    entry: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.entry}: {self.message}"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Artefact(_Strict):
    file: Annotated[str, Field(min_length=1)]
    sha256: str


class ModelEntry(_Strict):
    name: Annotated[str, Field(min_length=1)]
    purpose: Annotated[str, Field(min_length=1)]
    status: Literal["candidate", "approved", "retired"]
    source_url: Annotated[str, Field(pattern=r"^https://\S+$")]
    version: str | None = None
    code_licence: Annotated[str, Field(min_length=1)]
    weights_licence: Annotated[str, Field(min_length=1)]
    commercial_use: bool
    conditions: str | None = None
    components: list[str] = Field(default_factory=list)
    artefacts: list[Artefact] = Field(default_factory=list)
    licence_texts: list[str] = Field(default_factory=list)
    requirements: Annotated[list[Annotated[str, Field(pattern=REQUIREMENT_ID)]], Field(min_length=1)]


class Registry(_Strict):
    version: Literal[1]
    models: list[ModelEntry] = Field(default_factory=list)


def load_registry(path: Path) -> Registry:
    try:
        raw = yaml.safe_load(path.read_text())
    except OSError as exc:
        raise RegistryError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"invalid YAML in {path}: {exc}") from exc
    try:
        return Registry.model_validate(raw)
    except ValidationError as exc:
        raise RegistryError(f"schema error in {path}: {exc}") from exc


def validate(registry: Registry, base_dir: Path) -> list[Violation]:
    violations: list[Violation] = []
    seen: set[str] = set()
    for model in registry.models:
        if model.name in seen:
            violations.append(Violation("LG001", model.name, "duplicate model name"))
        seen.add(model.name)
        if model.status == "retired":
            continue
        violations.extend(_licence_violations(model))
        violations.extend(_component_violations(model))
        if model.status == "approved":
            violations.extend(_approval_violations(model, base_dir))
    return violations


def _licence_violations(model: ModelEntry) -> list[Violation]:
    found: list[Violation] = []
    for kind, identifier in (("code", model.code_licence), ("weights", model.weights_licence)):
        match classify_licence(identifier):
            case LicenceClass.BANNED:
                found.append(
                    Violation(
                        "LG003",
                        model.name,
                        f"{kind} licence {identifier} is non-commercial, research-only or revenue-capped",
                    )
                )
            case LicenceClass.UNKNOWN:
                found.append(
                    Violation("LG002", model.name, f"{kind} licence {identifier} is not on the allowlist")
                )
            case LicenceClass.CONDITIONAL if not (model.conditions and model.conditions.strip()):
                found.append(
                    Violation(
                        "LG005", model.name, f"{kind} licence {identifier} requires recorded conditions"
                    )
                )
            case _:
                pass
    if not model.commercial_use:
        found.append(Violation("LG004", model.name, "commercial_use must be true"))
    return found


def _component_violations(model: ModelEntry) -> list[Violation]:
    texts = [model.name, model.source_url, *model.components, *(a.file for a in model.artefacts)]
    return [
        Violation("LG006", model.name, f"banned non-commercial component referenced: {text}")
        for text in texts
        if is_banned_component(text)
    ]


def _approval_violations(model: ModelEntry, base_dir: Path) -> list[Violation]:
    found: list[Violation] = []
    if not model.version:
        found.append(Violation("LG007", model.name, "approved entries must pin a version"))
    if not model.artefacts:
        found.append(Violation("LG007", model.name, "approved entries must list artefacts with SHA-256"))
    found.extend(
        Violation("LG007", model.name, f"artefact {a.file} has a malformed SHA-256")
        for a in model.artefacts
        if not SHA256.match(a.sha256)
    )
    if not model.licence_texts:
        found.append(Violation("LG008", model.name, "approved entries must archive licence texts"))
    found.extend(
        Violation("LG008", model.name, f"archived licence text not found: {text}")
        for text in model.licence_texts
        if not (base_dir / text).is_file()
    )
    return found
