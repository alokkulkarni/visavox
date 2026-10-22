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

### Local cell (NFR-O5)
Everything runs on your machine in Docker before it goes near the cloud. Only synthetic data is used.

```bash
make up             # start the cell and wait until every container is healthy
make test-local     # smoke tests against the running cell
make test-contract  # LiveKit avatar contract suite against the same LiveKit
make down           # stop and delete the cell, including its data
```

| Container | Stands in for | Reach it at |
|---|---|---|
| `livekit` | LiveKit server (same version as CI) | `ws://localhost:7880`, key `devkey` / secret `secret` |
| `avatar` | Avatar engine, `cpu` profile: synthetic stand-in from spike S3 | joins room `local-demo` for agent identity `local-agent` |
| `postgres` | Aurora PostgreSQL (ADR-004) | `localhost:55432`, database `visavox`, roles `visavox_owner` and `visavox_app` (non-owner, no RLS bypass) |
| `valkey` | ElastiCache (Valkey engine) | `localhost:56379` |
| `aws` | S3, SQS, KMS, Secrets Manager (Moto) | `AWS_ENDPOINT_URL=http://localhost:55000`, any credentials |
| `oidc` | Cognito as OIDC provider (mock-oauth2-server) | issuer `http://localhost:58080/visavox` |

- **Every new service must run here.** `make local-check`, also run in CI and by `make up`, fails if a `services/<name>` folder lacks a Dockerfile, a compose entry built from it, or a healthcheck.
- **Media networking.** `make up` passes this machine's network address to LiveKit, so containers and your browser reach the same WebRTC media port. If it can't find one (for example, offline), run `make up LIVEKIT_NODE_IP=<your IP>`. Only UDP 7882 is reachable from your network; everything else listens on loopback.
- **GPU models.** Docker on macOS has no NVIDIA GPU, so the real avatar models run only on a Linux host with an NVIDIA GPU and the NVIDIA Container Toolkit. `make gpu-check` verifies that host. Everywhere else, the `cpu` stand-in keeps every non-quality test runnable.
- **Amazon Connect** runs only in AWS. Local Connect tests reach this cell through an authenticated tunnel. The tunnel tool is chosen in spike S2 (SDD §14) and adds a compose profile here.

Every change follows spec-driven and test-driven development on its own branch with a pull request; nothing is committed to `main` directly.
