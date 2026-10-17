# ADR-003: Python backend and engine, TypeScript front end

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Requirements | API-01..05, LK-02, RT-04 |
| DAG node | F0 |

## Context
The avatar, voice and STT models are PyTorch. The LiveKit avatar worker API and the most complete LiveKit Agents framework are Python. The console and web SDK run in browsers, and Connect customer SDKs (Touchpoint, ChatJS, Chime JS) are TypeScript/JavaScript.

## Decision
- Python 3.12 for all services, the engine, ML and tooling. Use FastAPI, Pydantic v2, SQLAlchemy 2 and `uv`.
- TypeScript for the console, the web SDK and the Node `AvatarSession`, built with `pnpm`.
- Terraform and Helm for infrastructure.

## Consequences
- One backend language keeps model code, engine and services in one toolchain.
- Python service throughput must be watched; hot paths (frame generation) run on GPU and use TensorRT where models allow it.

## Alternatives considered
- **Go or TypeScript services.** These would split the backend from the ML and LiveKit worker code, with no requirement gain.
