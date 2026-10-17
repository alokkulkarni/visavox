# ADR-002: LiveKit as the internal media backbone

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Requirements | RT-01..10, LK-01..04, CNA-01, CNB-01..04, NFR-L1..L5 |
| DAG node | F1, LK1–LK4 |

## Context
Avatars must run in LiveKit rooms (LiveKit Cloud and self-hosted) and in Amazon Connect contacts. Connect offers no supported way for a bot to be the agent-side media of a WebRTC contact (ADR-007). LiveKit Cloud has no UK media region. LiveKit Agents 1.8.x defines a virtual-avatar contract (`lk.audio_stream`, `lk.clear_buffer`, `lk.playback_finished`), with the worker side in Python.

## Decision
Every live Visavox session runs as participants in a LiveKit room: either the tenant's room or a Visavox-hosted room on **self-hosted LiveKit server in the tenant's cell**. The avatar worker implements the LiveKit avatar contract. Connect integrations deliver the avatar to the customer through a Visavox room joined by the Visavox web SDK.

## Consequences
- One media stack to build, test and operate; Connect and LiveKit differ only at the edges.
- We own LiveKit operations per cell (Redis, TURN on 443, egress sizing).
- We depend on an avatar contract whose reference example LiveKit removed in July 2026, so we pin versions and keep our own contract tests.

## Alternatives considered
- **A separate Chime-based media path for Connect.** Duplicates the stack, and Chime media pipelines cannot inject media into Connect meetings.
- **LiveKit Cloud only.** Has no UK media region, and region pinning needs the Scale plan and does not fail over.
