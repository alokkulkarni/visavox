# ADR-005: Model licence registry gate in CI

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Requirements | NFR-S6, CMP-13 |
| DAG node | F0 |

## Context
Research on 2026-10-17 found that many popular talking-head pipelines quietly include non-commercial components: InsightFace pretrained models, CelebAMask-HQ-trained face parsers, dlib landmarks, CodeFormer and the Basel Face Model. Several TTS licences also changed during 2025–26. A licence label on a repository does not cover every weight file it downloads.

## Decision
- Every model or weight file the platform loads must have an entry in `models/registry.yaml` with:
  - source URL;
  - version;
  - SHA-256;
  - code licence and weights licence;
  - commercial-use flag;
  - path to an archived copy of the licence text.
- `tools/licence_gate` validates the registry in CI and fails the build on any of:
  - a banned component or licence;
  - a non-commercial or revenue-capped licence;
  - an approved entry without a hash or archived licence.
- Candidate entries (pre-S1) may omit hashes but can never be loaded.

## Consequences
- Adding a model is a reviewed change with evidence attached.
- The engine's model loader must refuse any artefact whose hash is not an approved registry entry. That check is built in E1.

## Alternatives considered
- **Manual review only.** It does not scale, and it misses transitive weight downloads.
