# ADR-007: Connect pattern A via an avatar tile in the customer's call client

| Field | Value |
|---|---|
| Status | Accepted (owner decision D-09, 2026-10-17); mechanism details to be confirmed in S2 |
| Date | 2026-10-17 |
| Requirements | CNA-01..06, CNB-03, NFR-Q2 |
| DAG node | S2, CA1–CA3 |

## Context
- `CreateParticipant` allows only `CUSTOM_BOT` (chat) and `CUSTOMER` (WebRTC, and only after a human agent has connected).
- Chime media pipelines cannot inject media into Connect meetings.
- A headless virtual-agent user could send video through the documented `startVideoInput`, but replacing its audio needs undocumented connect-rtc-js internals, and the AWS service-terms position is unconfirmed.
- A2A collaboration (GA 2026-09-23) lets an external agent exchange PCM audio with a voice contact.

## Decision
- During self-service on a Connect web or in-app video contact, the customer's call client, which embeds the Visavox web SDK, shows the avatar **in the agent's video tile**.
- The avatar's media comes from a Visavox LiveKit room in the tenant's cell.
- Speech comes from either:
  - Connect's own bot (`connect_bot`): its meeting audio is tapped in the browser and lip-synced; or
  - the Visavox agent as an A2A collaborator (`visavox_a2a`).
- The SDK mutes the direct bot audio so the customer hears one synchronised voice.
- On escalation, the human agent's Chime video replaces the tile on the same contact.

## Consequences
- Only supported Connect APIs are used.
- Pattern A needs a Visavox-enabled customer client; the hosted communications widget cannot show the tile.
- The `connect_bot` path adds about 300 ms to bot speech. S2 must measure it against NFR-L2 and NFR-Q2.
- `visavox_a2a` depends on A2A covering WebRTC contacts, which is unverified and is S2's first check.

## Alternatives considered
- **Headless virtual-agent users.** Rejected for R1: undocumented APIs, one agent user and one headless browser per concurrent call, and an unconfirmed service-terms position. Reconsider only with written AWS confirmation.
- **Avatar joins as a `CUSTOMER` participant.** Only possible after a human agent connects, so it cannot serve self-service.
