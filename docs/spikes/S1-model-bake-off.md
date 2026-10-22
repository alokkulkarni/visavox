# Spike S1 — Model bake-off

| Field | Value |
|---|---|
| DAG node | S1 (parents: F0) |
| Requirements | NFR-L3, NFR-L6, NFR-Q1..Q6, RT-11, NFR-O3, NFR-S6, RT-02, AVA-01, AVA-02, VID-01, VOI-01, VOI-02, RT-04 |
| Output | ADR-006 (model selection), approved entries in `models/registry.yaml`, `docs/spikes/S1-results.md`, benchmark harness in `tools/bench` |
| Timebox | 10 working days once GPU access exists |
| Status | Planned — **blocked on GPU infrastructure (see §6)** |

## 1. Questions this spike must answer
1. **Real-time Photo avatar.** Which of Ditto (with MediaPipe/YuNet replacing InsightFace) and SoulX-FlashHead Pro meets:
   - render overhead ≤ 200 ms (NFR-L3);
   - 720p at 25 fps or more (NFR-Q1);
   - A/V sync within +45/−125 ms (NFR-Q2);
   - the lip-sync and identity baselines (NFR-Q3, NFR-Q4)?
2. **Real-time Studio avatar.** Does MuseTalk 1.5, with a commercial face parser swapped in, reach the quality tier above the Photo avatar? What does 512 px mouth-region retraining cost?
3. **Offline render.** Can InfiniteTalk or Wan2.2-S2V, plus an upscaler, produce 1080p at ≤ 2× real time when fanned out (NFR-L6)?
4. **TTS.** For Qwen3-TTS, CosyVoice3 and Chatterbox, measure:
   - time to first audio;
   - real-time factor;
   - naturalness MOS;
   - speaker similarity of 60-second clones (VOI-02);
   - language coverage (A-06).
5. **STT.** For Nemotron 3.5 Streaming and Parakeet v3, measure word error rate on UK and US accents and finalisation latency.
6. **Capacity and cost.** How many live streams fit per GPU class (g6 L4, g6e L40S, g7e RTX PRO 6000, p5 H100)? What is the GPU cost per live session-minute and per rendered minute (NFR-O3)?
7. **Head motion (RT-11, NFR-Q6, spec v1.1 #21).** For each real-time face candidate, score speech-driven head motion: the Beat Alignment Score of head-motion peaks against speech onsets, and head-pose variation (std of yaw, pitch and roll) against the band measured on real speakers. Gestures and upper-body framing are out of S1 scope; they belong to S5.
8. **Licences.** Does every chosen artefact pass `licence-gate --scan` after download? Record its SHA-256 and archive its licence texts.

## 2. Method
- **Isolation.** Each candidate is installed in its own container from pinned commits. Its downloaded weights go to a separate directory, which `licence-gate --scan` checks before first use.
- **Evaluation set.** No real customer data is used:
  - 20 synthetic, non-real-person face images and 5 studio clips from team members who have signed consent records;
  - 30 scripted utterances of 2–30 s;
  - an accent set covering UK regional and US English.
- **Latency harness (`tools/bench`).** Streams 100 ms PCM chunks at 24 kHz into each avatar model and timestamps:
  - first audio chunk in;
  - first frame out;
  - the interval between frames.
- **Density test.** Add concurrent streams until p95 frame interval exceeds 40 ms or a frame burst gap exceeds 200 ms (NFR-Q1). That point gives streams per GPU.
- **Quality metrics:**
  - LSE-C and LSE-D lip-sync scores, using a SyncNet evaluator (evaluation only, never shipped; its licence is recorded);
  - AuraFace identity similarity;
  - a 10-rater MOS panel (NFR-Q5).
- **Cost.** On-demand price × GPU-seconds per stream-minute, per region.

## 3. Exit criteria
- Each function in §1 has a **selected model and a fallback**, both meeting their thresholds, or a documented gap with a proposed spec change.
- ADR-006 is written and accepted.
- Selected artefacts are `approved` in the registry with version, SHA-256 and archived licence texts. `make licence-check` is green.
- `docs/spikes/S1-results.md` records every measurement, the hardware, the versions and the raw data location.

## 4. Risks
- Author-reported speeds come from non-AWS GPUs; real numbers may be lower (R-01).
- Training-data provenance of permissively licensed weights is unknown (R-04); this is flagged for counsel (G1).
- London has no g6e or g7. The UK benchmark runs on g7e and g6.

## 5. Harness scope in this repo
Hardware-independent parts of `tools/bench` (chunked streaming driver, timing capture, density search, metrics aggregation, report writer) are built test-first and run on CPU in CI with a synthetic generator. Model adapters run only on GPU runners.

## 6. Needed from the owner
- An AWS account (or sub-account) for spikes, with service quotas for g6 and g7e in eu-west-2, g6e in eu-central-1, and one p5.4xlarge.
- A way for the spike runner to reach it: an IAM role for a GitHub Actions self-hosted GPU runner, or credentials in a session that has AWS access.
- Agreement on the evaluation set: synthetic faces plus consented team recordings.
