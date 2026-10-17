"""Artefact directory scan tests: banned weight files are found by name (NFR-S6, ADR-005)."""

from __future__ import annotations

from pathlib import Path

from licence_gate.scan import scan_artefacts


def make_files(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00")


def test_clean_directory_has_no_violations(tmp_path: Path) -> None:
    make_files(tmp_path, "ditto/blaze_face.tflite", "ditto/decoder.onnx", "tts/model.safetensors")
    assert scan_artefacts(tmp_path) == []


def test_banned_weight_files_are_reported_with_their_paths(tmp_path: Path) -> None:
    make_files(
        tmp_path,
        "ditto/insightface_det.onnx",
        "ditto/models/2d106det.onnx",
        "musetalk/face-parse-bisent/79999_iter.pth",
        "landmarks/shape_predictor_68_face_landmarks.dat",
        "ok/model.onnx",
    )
    violations = scan_artefacts(tmp_path)
    assert {v.code for v in violations} == {"LG006"}
    reported = sorted(v.entry for v in violations)
    assert reported == sorted(
        [
            "ditto/insightface_det.onnx",
            "ditto/models/2d106det.onnx",
            "landmarks/shape_predictor_68_face_landmarks.dat",
            "musetalk/face-parse-bisent/79999_iter.pth",
        ]
    )


def test_banned_directory_names_are_reported(tmp_path: Path) -> None:
    make_files(tmp_path, "vendor/buffalo_l/w600k_r50.onnx")
    assert [v.code for v in scan_artefacts(tmp_path)] == ["LG006"]
