# Visavox — Requirements Specification

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-10-17 |
| Status | **FROZEN 2026-10-17** (approved by the owner in PR #1). Changes need a spec-change PR per `CLAUDE.md` rule 2. |
| Owner | Alok Kulkarni |
| Companion | [`SDD.md`](SDD.md) (design), [`CLAUDE.md`](CLAUDE.md) (engineering rules) |

Keywords **MUST**, **SHOULD**, **MAY** follow RFC 2119. Every requirement has an ID that is traced into `SDD.md` §13 and into the delivery DAG. Changing a frozen requirement needs a PR that updates this file, `SDD.md` and the affected tests together.

## 1. Purpose

Visavox is a multi-tenant SaaS that turns a person's photo or short video, plus their voice, into a lip-synced digital avatar. Tenants use the avatar three ways:

1. **Real-time AI agent** — the avatar talks live with end customers over WebRTC, driven by an AI conversation pipeline.
2. **Human-voiced avatar** — the avatar fronts a live human agent, lip-synced to that person's voice in real time.
3. **Scripted video** — the tenant types a script and Visavox renders an MP4.

Real-time avatars run inside **Amazon Connect** contacts (two patterns, §6.6–6.7) and inside **LiveKit** rooms (LiveKit Cloud or self-hosted). All avatar, voice and lip-sync models run **self-hosted on Visavox-operated GPUs**; no face, voice or video data is sent to a third-party model vendor.

## 2. Decisions captured in Phase 0

| # | Question | Decision |
|---|---|---|
| D-01 | Who is it for? | Multi-tenant SaaS product |
| D-02 | What drives speech? | All three: real-time AI agent, human agent's voice, scripted text to rendered video |
| D-03 | Avatar engine | Self-hosted models on own GPUs |
| D-04 | Connect attach pattern | Both: (A) avatar answers Connect video calls, (B) avatar panel beside Connect chat/voice |
| D-05 | Avatar inputs | Single photo, short video clip, voice clone from audio, stock voices |
| D-06 | First release | All three modes in Release 1 (sequenced on one shared engine, see `SDD.md` §12) |
| D-07 | Footprint | Multi-region; tenant chooses data region; 200+ concurrent live sessions |
| D-08 | Product / repo | Visavox, `alokkulkarni/visavox` |
| D-09 | Connect pattern A mechanism | **Avatar tile** in the customer's call client via the Visavox web SDK, using supported Connect APIs only (owner, 2026-10-17). Headless virtual-agent workaround is out of scope for R1 (§4.2). |

## 3. Actors

| Actor | Description |
|---|---|
| Platform operator | Visavox staff running the service; no default access to tenant biometric data |
| Tenant admin | Manages the tenant: region, users, SSO, integrations, keys, billing |
| Creator | Tenant user who builds avatars, voices, agents and scripted videos |
| Likeness subject | The real person whose face and/or voice an avatar reproduces; may or may not be a tenant user |
| End customer | Person talking to an avatar via Connect or LiveKit |
| Human agent | Contact-centre agent who escalated contacts reach, or whose voice drives an avatar |
| Integrator | Developer wiring Visavox into Connect, LiveKit or their own app via API/SDK |

## 4. Scope

### 4.1 In scope for Release 1
- Tenant self-service console and public REST API with webhooks.
- Avatar creation from a single photo (*Photo avatar*) and from a 1–3 minute video (*Studio avatar*).
- Stock voice catalogue and voice cloning from an audio sample.
- Likeness consent, liveness and identity-match verification before any avatar or voice clone can be used.
- Real-time sessions in LiveKit rooms, Connect pattern A, Connect pattern B.
- AI-agent, human-voice and scripted-render modes.
- Region pinning (UK, EU, US at launch), metering, audit, AI disclosure, watermarking and provenance.

### 4.2 Out of scope for Release 1 (candidate backlog)
- Full-body avatars, hand gestures, multiple avatars in one scene, avatar walking or camera moves.
- Video-to-video dubbing or translation of tenant-uploaded footage.
- Native iOS/Android SDKs (Connect's own mobile SDKs receive avatar video as ordinary remote video).
- Marketplace of stock human avatars (Release 1 ships tenant-owned likenesses plus a small set of synthetic, non-real-person stock avatars).
- On-premises deployment.
- Connect "virtual agent" avatars (headless agent users injecting media through undocumented APIs); reconsider only with written AWS confirmation (D-09).

## 5. Assumptions (accepted at freeze, 2026-10-17)

| ID | Assumption | Impact if wrong |
|---|---|---|
| A-01 | **Confirmed by owner.** The LLM behind the built-in AI agent is pluggable; default is Amazon Bedrock in the tenant's region. "Self-hosted" (D-03) applies to avatar, voice, lip-sync, STT and TTS models, not the LLM. | A self-hosted LLM adds a GPU fleet and changes cost and latency budgets. |
| A-02 | Tenants may also bring their own agent (a LiveKit Agents worker, or a Connect Lex / AI agent bot); Visavox then acts only as the avatar renderer. | None — additive. |
| A-03 | Release 1 avatars are head-and-shoulders framing at 720p for live and 1080p for rendered video. | Higher resolution live video needs bigger GPUs per stream. |
| A-04 | Launch regions: UK (eu-west-2), EU (eu-central-1), US (us-east-1). | New regions are a deployment of the same regional cell. |
| A-05 | Billing is usage-metered; Release 1 exports usage to Stripe for invoicing. | Different billing provider changes only the export adapter. |
| A-06 | English (UK/US) at launch for STT/TTS/AI agent; at least 5 further languages are a Release 1 SHOULD, subject to model support. | Language list drives model selection. |

## 6. Functional requirements

### 6.1 Tenancy, identity and access (TEN)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| TEN-01 | MUST | A tenant is created with exactly one **home data region** chosen at sign-up. | AC: tenant record shows the region; it cannot be changed through the console or API after creation (migration is an operator-run, audited procedure). |
| TEN-02 | MUST | All tenant personal data, biometric data, derived avatar/voice models, media and recordings are stored and processed **only in the tenant's home region**. | AC: automated residency test creates assets for one tenant per region and asserts every object, row and GPU job ran in that region; cross-region read attempts are denied. |
| TEN-03 | MUST | Tenant isolation: no API, query, storage path, cache key or GPU worker can expose one tenant's data to another. | AC: a tenant-isolation test suite exercising every API resource with a foreign tenant's IDs returns 404 for all; database row-level security enforced and tested. |
| TEN-04 | MUST | Console sign-in via email + MFA, and per-tenant SSO via OIDC and SAML 2.0. | AC: SSO login works against a test IdP; MFA enforced for non-SSO users. |
| TEN-05 | MUST | Roles: Owner, Admin, Creator, Agent-Supervisor, Viewer, Integrator (API-only), with least-privilege permissions defined in the SDD. | AC: permission matrix tests per role per endpoint. |
| TEN-06 | MUST | Scoped API keys per tenant with expiry, rotation and revocation. | AC: revoked key rejected within 60 s in all regions. |
| TEN-07 | MUST | Immutable, tenant-visible audit log of security-relevant and consent-relevant events. | AC: audit entries are append-only, hash-chained, exportable, retained per §8. |
| TEN-08 | MUST | Per-tenant quotas: concurrent live sessions, render minutes, avatar count, storage. | AC: exceeding a quota returns a typed error and an audit event; no partial resource is created. |

### 6.2 Avatar creation (AVA)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| AVA-01 | MUST | Create a **Photo avatar** from one image (JPEG/PNG/HEIC/WebP, ≤ 20 MB). | AC: valid upload produces a usable avatar; status transitions are emitted via webhook. |
| AVA-02 | MUST | Create a **Studio avatar** from a 1–3 minute video (MP4/MOV, ≥ 720p, ≥ 25 fps, single speaker facing camera). | AC: valid upload produces an avatar whose live output scores at or above the Photo avatar baseline on the quality metrics in NFR-Q. |
| AVA-03 | MUST | Automated input quality gate: exactly one face, minimum face size, frontal pose limits, blur, exposure, occlusion, and for video: continuous presence, stable lighting. | AC: each failure returns a specific, user-readable reason; a labelled test set of good and bad inputs passes at ≥ 95 % agreement. |
| AVA-04 | MUST | An avatar cannot be previewed beyond a watermarked still, used live or rendered until its likeness consent is **Verified** (CON-01..05). | AC: API and engine refuse unverified avatars with `consent_required`. |
| AVA-05 | MUST | Avatar settings: framing/crop, background (transparent, colour, image), idle behaviour (blink, breathing, micro head motion), default voice. | AC: settings persist and apply in live and rendered output. |
| AVA-06 | MUST | Avatars are versioned; a session or render pins an avatar version. | AC: editing an avatar never changes an in-flight session. |
| AVA-07 | MUST | Deleting an avatar removes source media, derived models, caches and previews in its region. | AC: deletion completes within 24 h; verification job proves no remaining objects; audit event recorded. |
| AVA-08 | SHOULD | A small catalogue of **synthetic stock avatars** (no real person) is available to every tenant. | AC: catalogue avatars carry provenance showing they are synthetic. |

### 6.3 Voice (VOI)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| VOI-01 | MUST | Stock voice catalogue (multiple accents, genders, ages) usable by any avatar. | AC: each stock voice streams speech in the live path within the TTS latency budget (NFR-L). |
| VOI-02 | MUST | Voice clone from an audio sample (minimum length set by the selected model; target ≤ 60 s). | AC: a clone is created and is usable live and offline. |
| VOI-03 | MUST | A voice clone requires verified consent from the voice's owner, including a spoken consent phrase that matches the sample speaker. | AC: speaker-verification score below threshold blocks activation. |
| VOI-04 | MUST | Per-tenant pronunciation lexicon and an SSML subset (break, emphasis, say-as, phoneme). | AC: lexicon entries change pronunciation in live and offline output. |
| VOI-05 | MUST | All synthetic speech carries an inaudible audio watermark (TRU-03). | AC: watermark detector identifies Visavox speech in live recordings and renders at ≥ 99 % with < 0.1 % false positives on a test corpus. |

### 6.4 Likeness consent and verification (CON)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CON-01 | MUST | The likeness subject records a consent video that speaks a **randomised consent phrase** naming the tenant and the permitted uses. | AC: phrase is generated per request, expires after 24 h, and the transcript must match. |
| CON-02 | MUST | Liveness check on the consent recording, and face match between the consent recording and the avatar source media (and speaker match for voice). | AC: spoofing test set (photos of screens, replays, masks) rejected at the target rate in NFR-S; mismatches block activation. |
| CON-03 | MUST | Consent record stores scope (live agent, human-voice, scripted video, languages, channels), term/expiry, tenant, subject contact, evidence hashes. | AC: an avatar used outside its consent scope is refused by the engine. |
| CON-04 | MUST | The likeness subject can revoke consent via a link sent to them, without needing tenant permission. | AC: after revocation the avatar and voice are disabled in all sessions within 5 minutes, live sessions end gracefully, and renders are blocked. |
| CON-05 | MUST | Tenant attests it has the right to use the likeness and accepts the acceptable-use policy before submission. | AC: attestation stored with the consent record. |
| CON-06 | MUST | Block avatars whose face or voice matches a protected list (public figures, takedown requests, prior revocations). | AC: matches route to manual review; no activation without operator approval. |

### 6.5 Real-time sessions — common (RT)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| RT-01 | MUST | Session API creates a live avatar session bound to: tenant, avatar version, voice, drive mode (`ai_agent`, `human_voice`, `external_audio`), transport (`livekit`, `connect_video`, `connect_panel`), and returns join credentials. | AC: OpenAPI contract tests; session reaches `live` within NFR-L start time. |
| RT-02 | MUST | The avatar publishes synchronised audio and video; while silent it shows natural idle motion, never a frozen frame. | AC: A/V offset and idle-motion checks in NFR-Q pass in automated media tests. |
| RT-03 | MUST | **Barge-in**: when the end customer starts speaking, the avatar stops speaking within 300 ms and returns to idle or listening pose. | AC: measured in the latency harness. |
| RT-04 | MUST | **AI-agent drive**: built-in pipeline (VAD → streaming STT → turn detection → LLM → streaming TTS → lip-sync) configurable per agent: system prompt, knowledge sources, tools/webhooks, LLM model, guardrails, escalation rules. | AC: configured agent holds a multi-turn conversation in the conversation test suite. |
| RT-05 | MUST | **Human-voice drive**: a human agent's microphone audio drives the avatar in real time; the end customer hears the human's own voice and sees the avatar. Converting the human's voice into a cloned voice (speech-to-speech) is out of scope for R1. The avatar's likeness consent must include `human_voice` scope. | AC: glass-to-glass latency and A/V sync within NFR-L/NFR-Q. |
| RT-06 | MUST | **External-audio drive**: an external agent (e.g. a tenant's LiveKit Agents worker) streams its TTS audio to the avatar, which returns synchronised video; supports clear-buffer (interrupt) and playback-finished signals. | AC: LiveKit avatar contract tests (SDD §7.3). |
| RT-07 | MUST | Mandatory **AI disclosure** per CMP-05: a visible "AI avatar" indicator on video and, for `ai_agent` mode, a spoken disclosure naming the tenant before the first substantive turn and after every transfer or reconnect (wording tenant-editable, cannot be disabled). | AC: disclosure present in 100 % of sessions in e2e tests. |
| RT-08 | MUST | Session events (started, speaking, interrupted, escalated, ended, error) via webhooks and a per-session event stream. | AC: event schema contract tests. |
| RT-09 | MUST | Optional session recording (tenant setting, off by default), stored in region with C2PA manifest and watermarks. | AC: recording only exists when enabled; retention honoured. |
| RT-10 | MUST | Conversation transcript and LLM tool calls are logged per session for the tenant (PII-redaction option). | AC: transcript available via API within 60 s of session end. |

### 6.6 Amazon Connect pattern A — avatar answers Connect video calls (CNA)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CNA-01 | MUST | When an end customer starts a Connect web or in-app video contact routed by the tenant's flow, the customer sees and hears the Visavox avatar in the agent's video position during the self-service stage. Mechanism: avatar tile in the customer's call client (D-09, `SDD.md` §8.2); the customer client embeds the Visavox web SDK. | AC: e2e test in a Visavox-owned Connect test instance: customer sees and hears the avatar with A/V sync per NFR-Q2. |
| CNA-06 | MUST | The avatar's speech on a Connect contact can come from Connect's own bot (`connect_bot`) or from the Visavox AI agent as an A2A collaborator (`visavox_a2a`). | AC: e2e tests for both brains; `visavox_a2a` subject to S2 confirming A2A on WebRTC contacts. |
| CNA-02 | MUST | The avatar can escalate the same contact to a human agent queue, passing context (summary, intent, transcript link) as contact attributes; the human then appears on video as normal. | AC: e2e escalation test; attributes visible in agent workspace. |
| CNA-03 | MUST | Tenant onboarding for Connect is self-service: a CloudFormation template creates a least-privilege cross-account role and any flow modules/Lambdas in the tenant's AWS account. | AC: template deploys cleanly in a fresh account; no long-lived keys exchanged. |
| CNA-04 | MUST | Contact ID, avatar session ID and Connect instance ID are correlated in logs, events and transcripts. | AC: trace query returns the full path for a test contact. |
| CNA-05 | MUST | Human-voice drive is supported on Connect video contacts: the human agent's voice drives the avatar instead of their camera. | AC: e2e test with a test agent. |

Research on 2026-10-17 found no supported way for a bot to be the agent-side participant of a Connect WebRTC contact (`SDD.md` §8.1). The owner chose the Visavox web SDK "avatar tile" in the customer's call client (D-09). Customers on clients without the Visavox SDK (for example the hosted communications widget) do not get pattern A.

### 6.7 Amazon Connect pattern B — avatar panel beside Connect chat or voice (CNB)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CNB-01 | MUST | A drop-in web component renders the avatar video panel next to the tenant's Connect chat or voice experience. | AC: works as an Amazon Connect Touchpoint modality component (side-by-side layout) and with a custom amazon-connect-chatjs UI. The hosted communications widget cannot host custom panels and is not supported. |
| CNB-02 | MUST | For **chat** contacts, every bot or agent message is spoken by the avatar with lip-sync, in order, with the text still shown. | AC: e2e: 20-turn chat; every message spoken; no reordering. |
| CNB-03 | MUST | For **web (WebRTC) voice** self-service contacts, the customer hears exactly one voice: the avatar's synchronised audio replaces the bot's direct audio (no double playback). PSTN-only calls have no screen and are out of scope. | AC: e2e test asserts single audio source. |
| CNB-04 | MUST | When the contact transfers to a human, the panel switches to a configurable state (hide, idle avatar, or human-voice avatar if consented). | AC: e2e transfer test. |

### 6.8 LiveKit (LK)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| LK-01 | MUST | Visavox avatars join LiveKit rooms on **LiveKit Cloud** and **self-hosted LiveKit server**. | AC: e2e tests against both. |
| LK-02 | MUST | Publish a LiveKit Agents plugin (Python; Node SHOULD) implementing the LiveKit avatar contract so any LiveKit agent can add a Visavox avatar in a few lines. | AC: example agent works unchanged against both server types. |
| LK-03 | MUST | Visavox can also run the whole agent (AI-agent drive) in a tenant's LiveKit room using tenant-supplied room credentials or a Visavox-hosted room. | AC: e2e test for both. |
| LK-04 | MUST | Room tokens issued by Visavox are short-lived, scoped to one room and one identity. | AC: expired/foreign tokens rejected. |

### 6.9 Scripted video rendering (VID)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| VID-01 | MUST | Create a render from: avatar, voice, script (plain text + SSML subset), background, aspect ratio (16:9, 9:16, 1:1), resolution up to 1080p. | AC: render API contract tests. |
| VID-02 | MUST | Optional burned-in or sidecar captions (WebVTT/SRT) generated from the script and aligned to audio. | AC: caption timing within ±100 ms of speech. |
| VID-03 | MUST | Maximum script length 10 minutes of speech per render in R1. | AC: longer scripts rejected with a clear error. |
| VID-04 | MUST | Renders are asynchronous with progress, webhook on completion, signed download URL, and in-region storage. | AC: e2e test. |
| VID-05 | MUST | Scripts are moderated against the acceptable-use policy before rendering. | AC: policy test set blocked; audit event. |
| VID-06 | MUST | Every rendered file carries a C2PA manifest and invisible audio and video watermarks. | AC: C2PA validator and watermark detector pass on every render in CI samples. |

### 6.10 Console, API and SDKs (API)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| API-01 | MUST | Public REST API described by OpenAPI 3.1, versioned (`/v1`), idempotency keys on creates, cursor pagination, typed errors. | AC: contract tests generated from the spec; breaking changes fail CI. |
| API-02 | MUST | Signed webhooks (HMAC, timestamped, replay-protected) with retries and a delivery log. | AC: signature verification sample in SDK; retry tests. |
| API-03 | MUST | Web console for all tenant tasks in §6.1–6.9, WCAG 2.2 AA. | AC: automated accessibility checks plus manual audit. |
| API-04 | MUST | JavaScript/TypeScript web SDK for embedding the avatar panel (CNB) and LiveKit viewer. | AC: published package with typed API and examples. |
| API-05 | SHOULD | Python and TypeScript server SDKs generated from OpenAPI. | AC: generated, tested, published. |

### 6.11 Trust and safety (TRU)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| TRU-01 | MUST | Acceptable-use policy enforcement on scripts, AI-agent prompts and LLM outputs (impersonation, fraud, sexual content, harassment, political deception). | AC: red-team test set blocked at target rate. |
| TRU-02 | MUST | Abuse reporting and takedown workflow, including a public report form and operator tooling to disable an avatar globally within 15 minutes. | AC: drill test. |
| TRU-03 | MUST | Invisible watermark in all synthetic video and audio, live and rendered, and a detector service/API. | AC: as VOI-05 and VID-06. |
| TRU-04 | MUST | C2PA content credentials on all rendered files and recordings. | AC: validates with the reference C2PA tool. |
| TRU-05 | MUST | Operators cannot view tenant biometric data without a tenant-approved, time-boxed, audited break-glass grant. | AC: access attempt without grant denied and alerted. |

### 6.12 Metering and billing (BIL)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| BIL-01 | MUST | Meter per tenant: live avatar seconds by mode, render seconds of output, avatars created, voice clones, storage GB-month, LLM tokens. | AC: metering totals reconcile with session/render logs to ±0.5 %. |
| BIL-02 | MUST | Usage export to Stripe (A-05) and a usage API/console view. | AC: daily export job tested against Stripe test mode. |
| BIL-03 | MUST | Cost attribution of GPU time per tenant and per mode for unit economics. | AC: dashboard shows GPU-seconds per session-minute. |

## 7. Non-functional requirements

### 7.1 Latency (NFR-L) — measured in the latency harness, p95 unless stated

| ID | Requirement |
|---|---|
| NFR-L1 | Live session start: API call → first avatar frame in room ≤ 3 s (warm pool). |
| NFR-L2 | AI-agent turn: end of customer speech → first avatar audio + lip-synced video ≤ 1.5 s (p50 ≤ 1.0 s), excluding LLM time above the configured model's own budget. |
| NFR-L3 | Avatar render overhead: TTS audio chunk in → matching video frame out ≤ 200 ms. |
| NFR-L4 | Human-voice drive: agent mic → avatar audio+video at customer ≤ 500 ms glass-to-glass. |
| NFR-L5 | Barge-in stop ≤ 300 ms (RT-03). |
| NFR-L6 | Rendered video: ≤ 2× real time for 1080p on the reference GPU (a 60 s script renders in ≤ 120 s). |

### 7.2 Quality (NFR-Q)

| ID | Requirement |
|---|---|
| NFR-Q1 | Live output 720p, 25 fps minimum, no dropped-frame bursts > 200 ms under nominal load. |
| NFR-Q2 | Audio/video sync within +45 ms / −125 ms (audio leading / lagging), per ITU-R BT.1359. |
| NFR-Q3 | Lip-sync accuracy measured by SyncNet confidence/offset (LSE-C/LSE-D) at or above the chosen baseline from the model bake-off (S1). |
| NFR-Q4 | Identity preservation: face-embedding similarity between source and output above the bake-off threshold. |
| NFR-Q5 | Human panel MOS ≥ 4.0/5 for naturalness on the release evaluation set. |

### 7.3 Availability, scale, resilience (NFR-A)

| ID | Requirement |
|---|---|
| NFR-A1 | Regional data plane availability 99.9 % monthly; control-plane API 99.9 %. |
| NFR-A2 | ≥ 200 concurrent live sessions per region at launch, scaling horizontally; load test proves 2× headroom. |
| NFR-A3 | Loss of one Availability Zone causes no tenant data loss; live sessions in the failed AZ may drop and must be re-establishable within 30 s. |
| NFR-A4 | Regional DR: RPO ≤ 15 min, RTO ≤ 4 h, recovering **within the same legal jurisdiction** (no cross-jurisdiction failover of personal data). |

### 7.4 Security (NFR-S)

| ID | Requirement |
|---|---|
| NFR-S1 | OWASP ASVS 5.0 Level 2 for all web/API surfaces; annual external penetration test before GA. |
| NFR-S2 | Encryption in transit (TLS 1.2+, DTLS-SRTP for media) and at rest with per-tenant AWS KMS keys; biometric data under a separate key hierarchy. |
| NFR-S3 | No secrets in code; Secrets Manager only; secret scanning, SAST (Semgrep), SCA and container scanning block merges on high/critical findings. |
| NFR-S4 | No personal data or biometric data in logs, traces or metrics labels. |
| NFR-S5 | Presentation-attack detection on consent capture meets the target error rates defined after S1/S4 (target APCER ≤ 1 % at BPCER ≤ 5 %). |
| NFR-S6 | SBOM generated for every build; every ML model and dataset recorded in the **model licence registry** with a commercially permissive licence for code and weights; CI fails on an unregistered or non-commercial model. |

### 7.5 Operability and cost (NFR-O)

| ID | Requirement |
|---|---|
| NFR-O1 | OpenTelemetry traces across control plane, engine and integrations, correlated by session ID and Connect contact ID. |
| NFR-O2 | SLO dashboards and alerts for every NFR-L and NFR-A target. |
| NFR-O3 | GPU cost per live session-minute and per rendered minute reported daily; target set after S1. |
| NFR-O4 | All infrastructure defined as code; every region is the same cell module with region parameters. |

## 8. Compliance requirements (CMP)

Derived from regulatory research dated 2026-10-17, summarised with sources in `SDD.md` §10. This is engineering interpretation, **not legal advice**; counsel review is DAG node L1 and must complete before GA. Visavox is the AI Act *provider* (Art 50(1), 50(2)); each tenant is the *deployer* (Art 50(4)).

| ID | Pri | Requirement | Driver | Acceptance criteria |
|---|---|---|---|---|
| CMP-01 | MUST | Consent capture is **live only**: the subject records in-browser via a Visavox link; uploaded consent footage is never accepted (enterprise exception requires operator review, R2). | Industry practice; UK/EU Art 9 explicit consent; BIPA s15(b) | AC: API has no consent-upload endpoint; capture page enforces live camera + passcode. |
| CMP-02 | MUST | Consent record captures explicit consent to biometric processing, purpose, permitted uses as a "reasonably specific description", retention term, tenant, subject, timestamp, language; e-signature accepted. | UK/EU GDPR Art 9; BIPA s15(b); Cal. Lab. Code §927 | AC: record schema validated; exportable to the subject on request. |
| CMP-03 | MUST | Photo avatars use the same consent flow as Studio avatars (no photo-avatar exemption). | Consistency; misuse risk | AC: AVA-04 tests cover both avatar types. |
| CMP-04 | MUST | Block likenesses and voices of minors, deceased people and listed public figures unless rights are evidenced and operator-approved; tenant attests subject is an adult. | Cal. AB 1836; ELVIS Act; AUP | AC: age attestation required; protected-list match routes to review (CON-06). |
| CMP-05 | MUST | Spoken AI disclosure before the first substantive turn, naming the tenant on whose behalf the avatar acts; repeated after transfers and reconnects; persistent visual "AI" indicator throughout video. | EU AI Act Art 50(1) and Commission guidelines (20 Jul 2026) | AC: e2e tests assert disclosure audio precedes first agent turn and on every transfer; indicator present in every frame sample. |
| CMP-06 | MUST | A path to a human is always available on request in AI-agent mode (tenant configures the target). | FCA Consumer Duty expectations; Utah SB 226 | AC: "speak to a person" intent triggers escalation in conversation tests. |
| CMP-07 | MUST | Deployer labelling tools for tenants: visible label overlay for rendered and live video, start-and-interval audio disclaimer for long content; **on by default** for EU-region tenants. | EU AI Act Art 50(4); Code of Practice (Jun 2026) | AC: labels present in renders by default for EU tenants; tenant can configure but not remove for deepfake content. |
| CMP-08 | MUST | Rendered files carry a C2PA 2.4 manifest with AI-disclosure assertion and latent disclosure fields (provider, system/version, timestamp, unique ID), signed with a certificate eligible for the C2PA Trust List, plus an imperceptible audio and video watermark. | EU AI Act Art 50(2); Code of Practice; Cal. SB 942 | AC: C2PA validator reports valid manifest; watermark detector passes (VID-06). |
| CMP-09 | MUST | Real-time streams carry in-band imperceptible audio and video watermarks (no segment-based C2PA on WebRTC). | EU AI Act Art 50(2) | AC: detector identifies watermarks in recorded live sessions (TRU-03). |
| CMP-10 | MUST | Free public detection endpoint for Visavox watermarks and manifests; terms of service prohibit stripping provenance. | Code of Practice; SB 942 | AC: public endpoint live before GA; interoperability target 2027-02-02. |
| CMP-11 | MUST | Block generation of intimate imagery and any sexual content involving real people, and any content involving minors, at prompt, script and output stages; retain filter evidence. | EU AI Act Art 5 additions (from 2026-12-02); UK SOA 2003 ss66E–66I | AC: red-team set blocked at 100 % for the prohibited categories; filter evidence logged. |
| CMP-12 | MUST | Takedown channel removes reported intimate imagery and identical copies within 48 hours; likeness complaints handled in the same workflow. | US TAKE IT DOWN Act | AC: drill test meets 48 h; operator SLA alerting. |
| CMP-13 | MUST | Published biometric retention schedule: delete source media, avatar and voice models on purpose end or revocation, and at most 3 years after last use (≤ 1 year after purpose end for Texas subjects); deletion propagates to backups within 35 days with a deletion attestation. | BIPA s15(a); Texas CUBI; storage limitation | AC: retention job tests; attestation generated per deletion. |
| CMP-14 | MUST | DPIA per region before GA; no operator access from US-designated countries of concern; support access to tenant data is in-region or covered by a transfer risk assessment. | UK/EU GDPR Art 35; DOJ bulk data rule; ICO transfer guidance (Jan 2026) | AC: DPIA documents in repo; access-location controls enforced and tested. |
| CMP-15 | MUST | Release 1 offers no outbound calling; any future outbound AI-voice calling must check TCPA consent and opt-out before dialling. | FCC 2024 TCPA ruling | AC: no outbound dialling API exists in R1. |

## 9. Glossary

| Term | Meaning |
|---|---|
| Photo avatar | Avatar built from one still image |
| Studio avatar | Avatar built from a 1–3 minute video, higher fidelity |
| Drive mode | What makes the avatar speak: AI agent, human voice, or external audio |
| Regional cell | The full Visavox data plane deployed in one region |
| Likeness subject | The real person whose face/voice is reproduced |
