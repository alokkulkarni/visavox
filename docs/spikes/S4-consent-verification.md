# Spike S4 — Consent capture, liveness and verification

| Field | Value |
|---|---|
| DAG node | S4 (parents: F0) |
| Requirements | CON-01..06, CMP-01..04, NFR-S5, VOI-03 |
| Output | ADR-008, approved registry entries for chosen components, `docs/spikes/S4-results.md`, evaluation harness in `tools/bench/consent` |
| Timebox | 8 working days |
| Status | Planned — **blocked on evaluation data and GPU/CPU test infrastructure (see §5)** |

## 1. Questions this spike must answer
1. **Liveness.** Which combination of an active challenge (spoken passcode plus random head-pose prompts) and a passive presentation-attack detector meets APCER ≤ 1 % at BPCER ≤ 5 % (NFR-S5)? Every component needs a commercial licence.
2. **Managed option.** Is AWS Rekognition Face Liveness available in all three launch regions and acceptable under A-01? Self-hosting covers avatar, voice and speech models, not verification. Compare its error rates and cost with the self-hosted option.
3. **Face match.** AuraFace-v1 versus SFace for matching the consent recording to the avatar source media. What threshold gives a false accept rate ≤ 0.1 % at a false reject rate ≤ 3 % on the evaluation set?
4. **Speaker verification.** Which model with commercially licensed **weights and training data** gives the best equal error rate for matching the spoken consent to the voice sample (VOI-03)? Candidates are found and licence-checked in this spike.
5. **Passcode check.** How accurate is the transcript match of the randomised consent phrase with the chosen STT (from S1), across UK and US accents?
6. **Capture.** Can the browser capture page enforce a live camera (no virtual camera or file injection) well enough to support CMP-01? Which signals can be checked?

## 2. Method
- **Evaluation data.** Consented recordings of volunteers covering genuine attempts, plus in-house presentation attacks: printed photos, screen replays, video replays and simple masks. No public dataset is used unless its licence allows commercial evaluation.
- **Error rates.** Measured per ISO/IEC 30107-3 terminology (APCER, BPCER) for liveness, and FAR, FRR and EER for matching.
- **Infrastructure.** Every candidate component runs in an isolated container, and its weights pass `licence-gate --scan`.

## 3. Exit criteria
- The selected liveness, face-match and speaker-verification components, with thresholds, meet NFR-S5 and CON-02, or a documented gap and a proposed spec change.
- ADR-008 is accepted, and the registry entries are approved with hashes and archived licences.
- A DPIA input note on the biometric processing in consent capture (CMP-14), for counsel review G1.

## 4. Risks
- Commercially licensed speaker-verification weights are scarce, because many are trained on research-only datasets.
- Presentation-attack test sets are hard to source legally, so the in-house attack set is the fallback.

## 5. Needed from the owner
- Agreement to collect volunteer consent recordings, with a consent form and a retention plan.
- The same AWS spike account as S1 and S2, if Rekognition Face Liveness is evaluated.
