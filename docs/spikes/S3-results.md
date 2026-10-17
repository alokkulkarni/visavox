# Spike S3 — Results: LiveKit avatar contract

| Field | Value |
|---|---|
| Run | GitHub Actions run 39033015248 (2026-10-17), job `contract · LiveKit avatar` |
| Server | `livekit/livekit-server:v1.13.10`, dev mode, host network, ubuntu-24.04 runner |
| Client libraries | `livekit-agents` 1.8.6, `livekit` (rtc) 1.1.20, `livekit-api` 1.2.1 |
| Avatar | Synthetic generator (no model), 640×360 RGBA at 25 fps, 24 kHz mono audio |
| Suite | `tests/contract/livekit_avatar` — 7 tests, all passing |

## Answers to the spike questions

| # | Question (plan §1) | Result | Evidence |
|---|---|---|---|
| 1 | Does a worker on the public `AvatarRunner` + `DataStreamAudioReceiver` API satisfy a stock `DataStreamAudioOutput` agent? | **Yes** | `test_segment_reports_playback_finished_with_its_duration` passes: position 1.0 s ± 0.15 s, not interrupted |
| 2 | Joins as `kind=agent` with `lk.publish_on_behalf`, using a scoped, short-lived token? | **Yes** | `test_avatar_joins_as_agent_publishing_on_behalf_of_the_agent`. Token unit tests: one room, no admin grants, TTL ≤ 10 min |
| 3 | Video never freezes while silent? | **Yes, 25.0 fps** at the viewer during silence | `test_video_keeps_flowing_while_the_avatar_is_silent` |
| 4 | Interruption fast enough (RT-03, NFR-L5 ≤ 300 ms)? | **Yes, 18.4 ms** from `clear_buffer` to `playback_finished{interrupted: true}` at the agent | `test_clear_buffer_interrupts_within_300_ms` |
| 5 | Transport and synchroniser latency? | **240.9 ms**, from the agent's first audio chunk to the first speaking frame decoded by the viewer | `test_first_speaking_frame_reaches_the_viewer_quickly` |
| 6 | RPCs from unexpected identities rejected? | **Yes** | `test_clear_buffer_from_an_unexpected_identity_is_rejected` |
| 7 | Same suite on LiveKit Cloud? | **Not yet run.** Needs a LiveKit Cloud project key from the owner | — |

Single-run figures. The suite runs on every PR, so the numbers will build a distribution over time.

## Findings that affect the design

1. **The latency budget needs revisiting (NFR-L2).** With zero model time, the path from agent to viewer already takes about 240 ms. That includes:
   - the 100 ms queues in `AVSynchronizer` and `AudioSource`;
   - the byte stream;
   - WebRTC encoding and decoding.

   SDD §7.2 budgeted the avatar at ≤ 200 ms plus 50–100 ms of network. The real fixed cost is higher. The p50 ≤ 1.0 s turn target is therefore tight, and S1 must measure the end-to-end turn with real models.

   Possible mitigation: the queue sizes are adjustable only through the private `AvatarRunner(_queue_size_ms=...)` argument. That is a stability risk (R-05), so any tuning needs a version guard and an upstream feature request.
2. **TokenVerifier gap.** `livekit-api` 1.2.1's `TokenVerifier` does not parse the `kind` claim, although the signed token carries it. Our tests assert `kind` on the verified payload. A newer `livekit-api` parses it; upgrade once the 7-day cooldown allows.
3. **Version pinning works as intended.** The 7-day supply-chain cooldown held back `livekit-agents` 1.8.8, so the spike used 1.8.6. The avatar contract is identical across these versions: same RPC names, same byte-stream topic.
4. **Self-hosted LiveKit runs cleanly in CI** as a container. LK1 and later suites can rely on it for contract and e2e tests without a cloud dependency.

## Exit criteria status
- [x] Contract suite passes against self-hosted LiveKit in CI
- [x] Measurements recorded with versions pinned
- [ ] LiveKit Cloud run (blocked on owner-provided Cloud project key)
- [x] No change to ADR-002; finding 1 is recorded as risk R-07 in `SDD.md` §16
