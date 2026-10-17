# Spike S3 — LiveKit avatar contract

| Field | Value |
|---|---|
| DAG node | S3 (parents: F0) |
| Requirements | RT-02, RT-03, RT-06, LK-01, LK-02, LK-04, NFR-L5, NFR-Q1 |
| Output | `docs/spikes/S3-results.md`, contract test suite `tests/contract/livekit_avatar/` (reused by LK1), spike worker in `spikes/s3_livekit_contract/` |
| Timebox | 5 working days |
| Status | **In progress.** Runs in CI against a self-hosted LiveKit server container. The LiveKit Cloud run needs a Cloud project key from the owner. |

## 1. Questions this spike must answer
1. Can a Visavox avatar worker built on `livekit-agents` 1.8.x (`AvatarRunner` + `DataStreamAudioReceiver` + our `VideoGenerator`) satisfy the contract a stock LiveKit agent expects? The agent side uses the unmodified `DataStreamAudioOutput` (RT-06, LK-02).
2. Does the worker join as `kind=agent` with `lk.publish_on_behalf`, using a short-lived token scoped to one room and identity (LK-04)?
3. Does the published video never freeze while the avatar is silent (RT-02, NFR-Q1)?
4. Is interruption fast enough? Measure from `clear_buffer` to `playback_finished{interrupted: true}` against the ≤ 300 ms target (RT-03, NFR-L5).
5. What latency does the transport and synchroniser add, from the first audio chunk sent by the agent to the first "speaking" frame seen by a viewer? A synthetic generator is used, so model time is zero.
6. Are RPCs from unexpected identities rejected (LK-04)?
7. Does the same suite pass unchanged on LiveKit Cloud (LK-01)?

## 2. Method
- **Server.** `livekit/livekit-server` in dev mode runs in a CI job, because the sandbox can't build or download the binary. The same tests run locally against any LiveKit URL through `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`.
- **Synthetic generator.** Frames encode state in pixels, so a viewer participant can tell idle frames from speaking frames and measure timing without any face model.
- **Participants.** Each test runs three: a stock agent (`DataStreamAudioOutput`), the avatar worker under test, and a viewer standing in for the end customer.

## 3. Exit criteria
- The contract suite passes against self-hosted LiveKit in CI, and against LiveKit Cloud once keys are provided.
- The measured numbers for questions 4 and 5 are recorded in `docs/spikes/S3-results.md`, with versions pinned (server image, `livekit`, `livekit-agents`).
- Contract deviations or LiveKit bugs found are recorded. ADR-002 is updated if anything changes the decision.

## 4. Out of scope
Face models (S1) and Connect (S2). The spike worker is throwaway; the contract tests are kept and move to LK1.
