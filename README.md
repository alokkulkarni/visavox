# Visavox

Self-hosted, real-time, lip-synced AI video avatars for Amazon Connect and LiveKit, plus scripted video rendering. Multi-tenant SaaS with tenant-chosen data regions.

- **Specification:** [`REQUIREMENTS.md`](REQUIREMENTS.md) — frozen v1.0
- **Design:** [`SDD.md`](SDD.md) and [`docs/adr/`](docs/adr/)
- **Engineering rules:** [`CLAUDE.md`](CLAUDE.md)
- **Model licence registry:** [`models/registry.yaml`](models/registry.yaml)

## Develop

```bash
make setup          # uv sync --all-packages
make lint typecheck test licence-check
```

Every change follows spec-driven and test-driven development on its own branch with a pull request; nothing is committed to `main` directly.
