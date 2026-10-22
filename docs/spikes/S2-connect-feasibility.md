# Spike S2 — Amazon Connect feasibility

| Field | Value |
|---|---|
| DAG node | S2 (parents: F0, LC1 — the local cell, per spec v1.1 #21) |
| Requirements | CNA-01..06, CNB-01..04, NFR-L2, NFR-Q2, NFR-O5 |
| Output | `docs/spikes/S2-results.md`, ADR-007 updated from "Accepted" to "Confirmed" (or a spec-change PR), test-instance IaC in `infra/test-connect/`, local-cell Connect wiring (tunnel and test flows) reused by CA1–CB2 e2e tests |
| Timebox | 8 working days once a Connect test instance exists |
| Status | Planned — **blocked on AWS test account (see §5)** |

## 1. Questions this spike must answer

| # | Question | Requirement | Pass condition |
|---|---|---|---|
| Q1 | Does A2A external-agent collaboration work on **WebRTC** (in-app/web) contacts, in eu-west-2, eu-central-1 and us-east-1? | CNA-06 (`visavox_a2a`) | Our test agent receives caller PCM and its audio reaches the caller on a WebRTC contact |
| Q2 | Can the customer client tap Connect meeting audio (`getCurrentMeetingAudioStream()`), publish it to a Visavox room, and mute Connect's direct playback without harming the contact? | CNA-06 (`connect_bot`), CNB-03 | Single voice heard; contact stays healthy for 10 minutes; added latency measured |
| Q3 | Can a Touchpoint modality component render the avatar in the agent video position (pattern A) and in a side-by-side panel (pattern B)? | CNA-01, CNB-01 | Working prototype in both layouts |
| Q4 | On escalation, does the same contact switch cleanly from avatar tile to the human agent's Chime video, with context attributes visible? Does video survive agent-to-agent transfer? | CNA-02, CNA-04 | Contact ID unchanged; attributes visible; transfer outcome recorded |
| Q5 | Human-voice extension: does a custom CCP sending avatar video via `startVideoInput(MediaStream)` keep A/V sync within NFR-Q2 at the customer? If not, does delaying agent audio in the Visavox customer SDK fix it? | CNA-05, NFR-Q2 | Measured skew with and without SDK re-alignment |
| Q6 | Chat: can streamed AI-agent chunks (ChatJS ≥ 5.3, Touchpoint) be assembled into sentences in order? Can Lex full messages be voiced without reordering? | CNB-02 | 20-turn chat test, no reordering |
| Q7 | Which Chime video resolution and frame rate do Connect meetings use for agent video? | NFR-Q1 | Recorded from WebRTC stats |
| Q8 | Is everything above available in all three launch regions? | TEN-02 | Region matrix completed |
| Q9 | Which authenticated TLS tunnel lets the Connect flow Lambda and the A2A collaborator reach the local cell, and what latency does it add? | NFR-O5, CNA-06 | Lambda calls and A2A `wss://` work through the tunnel; tunnel is authenticated, short-lived and closed after tests; added latency recorded |

## 2. Method
- Use a Visavox-owned AWS test account, separate from any tenant or employer estate.
- Create one Connect instance per launch region with web, in-app and video calling enabled, the Customer tier for A2A, and test flows built from the Visavox flow module.
- **Local first (NFR-O5).** The Visavox side runs in the local Docker cell (LC1) on a developer machine: LiveKit, the stub avatar worker (synthetic audio-reactive video, `cpu` profile) and a minimal session endpoint. S2 tests integration, not models.
- Connect exists only in AWS. Its flow Lambda and the A2A collaborator reach the local cell through an authenticated TLS tunnel (Q9). The customer client (Touchpoint or a custom Chime client with the Visavox web SDK) and the agent workspace run in a browser on the same machine, joining Connect in the cloud and LiveKit locally.
- Only synthetic content crosses the tunnel. The tunnel is opened for a test run and closed afterwards.
- Measure latency and A/V skew with WebRTC `getStats()` and audio-visual clap markers recorded at the customer client.
- Every experiment is scripted, so results can be re-run before CA1 starts.

## 3. Exit criteria
- Q1–Q8 each have a yes/no answer with evidence (logs, stats, recordings of synthetic content only).
- ADR-007 is confirmed, or a spec-change PR records any requirement that cannot be met, with options.
- Infrastructure code for the test instances is merged, so CA1–CA3 e2e tests can reuse it.

## 4. Risks
- If Q1 fails, `visavox_a2a` drops to "Visavox agent via LiveKit, Connect at escalation" or waits for AWS. This needs an owner decision.
- If Q5 fails without SDK re-alignment, CNA-05 holds only for customers using the Visavox SDK. This needs to be documented.

## 5. Needed from the owner
- An AWS account for spikes, with permission to create Connect instances in eu-west-2, eu-central-1 and us-east-1.
- Confirmation that the account is not linked to any employer Connect estate.
- A quota request for A2A if required.
