"""Registry loading and rule tests for the licence gate (NFR-S6, ADR-005)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from licence_gate.registry import RegistryError, load_registry, validate

VALID_SHA = "a" * 64


def model_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
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


def codes(registry_path: Path) -> list[str]:
    registry = load_registry(registry_path)
    return [v.code for v in validate(registry, base_dir=registry_path.parent.parent)]


def approved(tmp_path: Path, **overrides: object) -> dict[str, object]:
    """An approved entry with hashed artefacts and archived licence texts present on disk."""
    licence = tmp_path / "models" / "licences" / "example.txt"
    licence.parent.mkdir(parents=True, exist_ok=True)
    licence.write_text("Apache License 2.0 ...")
    base = model_entry(
        status="approved",
        version="1.0.0",
        artefacts=[{"file": "example.safetensors", "sha256": VALID_SHA}],
        licence_texts=["models/licences/example.txt"],
    )
    base.update(overrides)
    return base


class TestValidRegistries:
    def test_candidate_with_permissive_licences_passes(self, write_registry: Callable[..., Path]) -> None:
        assert codes(write_registry(model_entry())) == []

    def test_approved_with_hashes_and_archived_licences_passes(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        assert codes(write_registry(approved(tmp_path))) == []

    def test_conditional_licence_with_conditions_passes(self, write_registry: Callable[..., Path]) -> None:
        entry = model_entry(weights_licence="CC-BY-4.0", conditions="Attribution in product notices.")
        assert codes(write_registry(entry)) == []

    def test_retired_entries_are_not_checked_for_artefacts(self, write_registry: Callable[..., Path]) -> None:
        assert codes(write_registry(model_entry(status="retired"))) == []

    def test_empty_registry_passes(self, write_registry: Callable[..., Path]) -> None:
        assert codes(write_registry()) == []


class TestLicenceRules:
    def test_duplicate_names_are_rejected(self, write_registry: Callable[..., Path]) -> None:
        assert "LG001" in codes(write_registry(model_entry(), model_entry()))

    def test_unknown_licence_identifier_is_rejected(self, write_registry: Callable[..., Path]) -> None:
        assert "LG002" in codes(write_registry(model_entry(code_licence="Some-Custom-Licence")))

    @pytest.mark.parametrize(
        "licence",
        [
            "CC-BY-NC-4.0",
            "CC-BY-NC-SA-4.0",
            "PolyForm-Noncommercial-1.0.0",
            "Coqui-Public-Model-License",
            "Fish-Audio-Community-License",
            "NeuTTS-Open-License",
            "LicenseRef-Research-Only",
            "LicenseRef-Academic-Use",
        ],
    )
    def test_non_commercial_research_or_revenue_capped_licences_are_banned(
        self, write_registry: Callable[..., Path], licence: str
    ) -> None:
        assert "LG003" in codes(write_registry(model_entry(weights_licence=licence)))

    def test_commercial_use_false_is_rejected(self, write_registry: Callable[..., Path]) -> None:
        assert "LG004" in codes(write_registry(model_entry(commercial_use=False)))

    @pytest.mark.parametrize(
        "licence",
        ["CC-BY-4.0", "OpenMDW-1.1", "LiveKit-Model-License", "OpenRAIL-M", "LicenseRef-Vendor-Terms"],
    )
    def test_conditional_licence_without_conditions_is_rejected(
        self, write_registry: Callable[..., Path], licence: str
    ) -> None:
        assert "LG005" in codes(write_registry(model_entry(weights_licence=licence)))


class TestBannedComponents:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("name", "insightface-buffalo-l"),
            ("source_url", "https://github.com/deepinsight/insightface"),
            ("components", ["mediapipe", "79999_iter.pth"]),
            ("components", ["shape_predictor_68_face_landmarks.dat"]),
            ("components", ["CodeFormer"]),
            ("components", ["01_MorphableModel.mat (Basel Face Model 2009)"]),
            ("components", ["scrfd_10g"]),
            # Body models and motion data behind most audio-to-gesture generators (spec v1.1, issue #14).
            ("components", ["smplx"]),
            ("components", ["SMPL-X_NEUTRAL_2020.npz"]),
            ("components", ["SMPLH_male.pkl"]),
            ("components", ["amass"]),
            ("components", ["openpose body_pose_model.pth"]),
        ],
    )
    def test_banned_components_are_rejected(
        self, write_registry: Callable[..., Path], field: str, value: object
    ) -> None:
        assert "LG006" in codes(write_registry(model_entry(**{field: value})))

    @pytest.mark.parametrize("component", ["dwpose", "rtmw-x", "flame-2023-open", "simplex-noise"])
    def test_commercial_pose_and_face_components_are_not_mistaken_for_banned_ones(
        self, write_registry: Callable[..., Path], component: str
    ) -> None:
        assert "LG006" not in codes(write_registry(model_entry(components=[component])))

    def test_banned_artefact_file_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        entry = approved(tmp_path, artefacts=[{"file": "det_10g.onnx", "sha256": VALID_SHA}])
        assert "LG006" in codes(write_registry(entry))


class TestApprovedEntries:
    def test_approved_without_artefacts_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        assert "LG007" in codes(write_registry(approved(tmp_path, artefacts=[])))

    @pytest.mark.parametrize("sha", ["abc", "G" * 64, "A" * 64])
    def test_approved_with_malformed_sha256_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path, sha: str
    ) -> None:
        entry = approved(tmp_path, artefacts=[{"file": "m.safetensors", "sha256": sha}])
        assert "LG007" in codes(write_registry(entry))

    def test_approved_without_version_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        assert "LG007" in codes(write_registry(approved(tmp_path, version=None)))

    def test_approved_without_licence_texts_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        assert "LG008" in codes(write_registry(approved(tmp_path, licence_texts=[])))

    def test_approved_with_missing_licence_file_is_rejected(
        self, write_registry: Callable[..., Path], tmp_path: Path
    ) -> None:
        entry = approved(tmp_path, licence_texts=["models/licences/missing.txt"])
        assert "LG008" in codes(write_registry(entry))


class TestSchema:
    @pytest.mark.parametrize(
        "broken",
        [
            {"status": "live"},
            {"requirements": ["not-an-id"]},
            {"source_url": "ftp://example.com/model"},
            {"name": ""},
        ],
    )
    def test_invalid_fields_raise_registry_error(
        self, write_registry: Callable[..., Path], broken: dict[str, object]
    ) -> None:
        with pytest.raises(RegistryError):
            load_registry(write_registry(model_entry(**broken)))

    def test_missing_required_field_raises_registry_error(self, write_registry: Callable[..., Path]) -> None:
        entry = model_entry()
        del entry["weights_licence"]
        with pytest.raises(RegistryError):
            load_registry(write_registry(entry))

    def test_unknown_field_raises_registry_error(self, write_registry: Callable[..., Path]) -> None:
        with pytest.raises(RegistryError):
            load_registry(write_registry(model_entry(licence="MIT")))

    def test_unsupported_registry_version_raises(self, write_registry: Callable[..., Path]) -> None:
        with pytest.raises(RegistryError):
            load_registry(write_registry(model_entry(), version=2))

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "registry.yaml"
        path.write_text("version: 1\nmodels: [unclosed")
        with pytest.raises(RegistryError):
            load_registry(path)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RegistryError):
            load_registry(tmp_path / "absent.yaml")

    def test_valid_requirement_ids_are_accepted(self, write_registry: Callable[..., Path]) -> None:
        registry = load_registry(write_registry(model_entry(requirements=["RT-02", "NFR-Q3", "CMP-08"])))
        assert registry.models[0].requirements == ["RT-02", "NFR-Q3", "CMP-08"]
