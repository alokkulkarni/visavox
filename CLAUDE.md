# CLAUDE.md — Visavox engineering rules (absolute)

Visavox is a multi-tenant SaaS for self-hosted, real-time lip-synced video avatars on Amazon Connect and LiveKit, plus scripted video rendering. The spec is `REQUIREMENTS.md`; the design is `SDD.md`. These rules are not optional.

## Source of truth
1. `REQUIREMENTS.md` and `SDD.md` are frozen once approved. Never implement anything they do not require.
2. If code and spec disagree, stop and propose a spec change PR first. Spec, design and tests change in the same PR.
3. Every commit, test and PR cites requirement IDs (e.g. `RT-03`, `CMP-05`).
4. If a requirement is ambiguous, ask the owner. Never guess data structures, API contracts or compliance behaviour.

## Git workflow
5. Never commit or push to `main`. One branch per DAG node: `feature/<node-id>-<slug>` or `bugfix/<issue-id>-<slug>`.
6. Semantic commits: `type(scope): summary` (feat, fix, test, docs, refactor, chore, ci, perf, build).
7. Open PRs with `gh pr create` against `main`. The body includes the requirement IDs, test results and Security/Validator reports.
8. Merge only when all CI gates are green: `gh pr merge --squash --delete-branch`.

## Test-driven development
9. Write the failing test first and commit it (`test(...)`) before the implementation.
10. No production code without a test that fails without it. No skipped or xfail tests on `main`.
11. Test layers: unit, contract (OpenAPI, LiveKit avatar contract, Connect events), integration (testcontainers), media quality (`tests/media`), e2e, load. Use the layer the requirement's acceptance criteria demand.
12. Coverage at least 90 % lines on changed code; media and latency acceptance criteria are asserted numerically, never eyeballed.

## Architecture guardrails
13. Python 3.12 for services, engine and ML; TypeScript for console and web SDK; Terraform plus Helm for infrastructure.
14. Tenant data never leaves its home region cell. No cross-region calls carrying tenant data.
15. Every tenant table has `tenant_id` and row-level security. Every query runs with the tenant context set.
16. Biometric data (source media, consent evidence, avatar and voice artefacts) uses the tenant biometric KMS key only.
17. The engine refuses any avatar or voice without a valid, in-scope, unrevoked consent token. Never add a bypass, even for tests: use test fixtures that issue real tokens.
18. All synthetic audio and video is watermarked at source; renders carry C2PA manifests; AI disclosure cannot be disabled.

## Models and licences
19. Only models listed in `models/registry.yaml` with commercial-use code and weight licences may be loaded.
20. Banned: InsightFace pretrained models, CelebAMask-HQ-trained parsers, dlib landmarks, CodeFormer, Basel Face Model, and any NC, research-only or revenue-capped licence.
21. Weights are pinned by SHA-256; the licence text is archived alongside the registry entry.

## Security and data handling
22. No secrets in code or config. Use AWS Secrets Manager and IRSA.
23. No personal or biometric data in logs, traces, metric labels, test snapshots or fixtures committed to git. Use synthetic faces and voices only.
24. Semgrep, gitleaks, Trivy, SBOM and the licence gate must pass; high or critical findings block merge.

## Commands (use `uv` for Python and `pnpm` for TypeScript)
- `make lint` · `make test` · `make test-contract` · `make test-media` · `make security` · `make licence-check`

## Definition of done
Tests green · requirement IDs cited · Security-Agent clean · Validator-Agent confirms spec match · docs and ADRs updated · PR squash-merged.
