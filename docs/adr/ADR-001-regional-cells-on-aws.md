# ADR-001: AWS regional cells on EKS

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Requirements | TEN-01, TEN-02, NFR-A1..A4, NFR-O4, CMP-14 |
| DAG node | F1, M1 |

## Context
Tenants choose a data region (D-07) and all biometric data must stay there (TEN-02). Amazon Connect integration is AWS-native, and Connect video calling is available in us-east-1, eu-west-2 and eu-central-1. GPU instance families differ by region (no g6e or g7 in London; no p5 in Frankfurt).

## Decision
Deploy Visavox as identical, independent **regional cells** on AWS (UK eu-west-2, EU eu-central-1, US us-east-1 at launch), each with its own EKS cluster, Karpenter-managed GPU node pools defined per cell, data stores and LiveKit. A thin global layer holds only routing metadata (tenant slug to cell) and operational artefacts.

## Consequences
- Residency is enforced by topology rather than by policy alone.
- Cross-cell features (global search, global analytics over tenant data) are not possible by design.
- Each cell's GPU pool profiles must be benchmarked separately (S1).
- DR stays in-jurisdiction (NFR-A4); the UK cell has no second UK region, so DR uses multi-AZ and in-region backups.

## Alternatives considered
- **Single global data plane with row-level region tags.** Simpler to operate, but it cannot prove residency and fails TEN-02.
- **Kubernetes on multiple clouds.** Portable, but it loses Connect proximity and in-region Bedrock, for no requirement gain.
