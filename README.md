# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each clip, and writes `/output/results.json`
with formal, sarcastic, humorous-tech, and humorous-non-tech captions.

## Recommended Track 2 submission

Track 2 has one submission; Gemma recognition is an award within that track.

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r10-gemma-stable`

Digest: `sha256:70a03959943645e979e724a7ebdb6cae5981dfc0c7bb385aa5d3464eb33c08aa`

This image uses Kimi K2.6 for dense visual evidence and Gemma 4 for caption
generation, selection, verification, repair, and emitted captions.

## Earlier research candidates

Gemma-track control:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r6-grid`

Digest: `sha256:2d7eac8954a5a8831608886f6398084086d82ac8016c228e8cc5d51f4f1154e8`

Source-derived broad Track 2 candidate:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r8-qwen-deepseek`

Digest: `sha256:e10362b03f5527a6a32e31119331f2a3ecee78bf60cbc8c04cb7e04775b19418`

Variance-controlled broad candidate:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r9-stable`

Digest: `sha256:9d2cd8fa19a82dc5e5caecb4eb71c88863665a125e273433003608317b296152`

The latest recorded leaderboard score is **0.77**, and the strongest previously
confirmed ClioGemma control is **0.85**. No candidate is presented as a
guaranteed 0.93; only AMD's hidden evaluation can establish the official score.
The r8/r9 images remain research branches and should not replace r10 for this
single-entry competition.

## Architecture

```text
video
  -> scene-aware sampling of up to 16 chronological frames plus optional OCR hints
  -> labelled 4x4 temporal grids preserve the leader's dense evidence pattern
  -> Kimi K2.6 (r6) or Qwen3.5 (r8) dense factual grounding through Novita
     (summary, setting, subjects, primary action, 5-9 stable details,
      timeline, visible text, uncertainty ledger)
  -> Gemma 4 31B visual verification and final grounding
  -> r6 uses Gemma for caption selection/repair; r8 uses DeepSeek V4 Pro for
     independent style drafting before Gemma's final grounding pass
     (public-guide style calibration and concrete-detail preservation)
  -> deterministic hallucination, brand, count, cliché, encoding,
     length, style, and schema validation
  -> atomic /output/results.json
```

Kimi supplies visual evidence and candidate diversity. Google Gemma 4 owns
verification, final grounding, and every emitted caption in the recommended
r10 image. The r8/r9 DeepSeek writer branch is retained only as research.

## Validation

The published r6 and r8 images completed the eight retired AMD validation clips;
r10 preserves the same contract with the stability profile enabled:

- 8/8 tasks and 32/32 requested captions
- r6 completed within the 570-second contract; r8 completed in 272.3 seconds at parallelism three
- valid schema, non-empty values, and bounded runtime under the 570-second budget
- anonymous GHCR manifest request: HTTP 200
- clean `docker pull` and Linux/amd64 manifest inspection: passed

The blind comparison is a directional public-set regression test, not AMD's
hidden scoring model.

## Build profiles

The immutable recommended image is already published. Its build profile is:

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VISION_MODEL=moonshotai/kimi-k2.6 `
  --build-arg CLIO_PIPELINE=score-max-r1 `
  --build-arg SWIFTCLIP_FRAME_STRATEGY=scene `
  --build-arg SWIFTCLIP_FRAME_COUNT=16 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg CLIO_GRID_INPUT=1 `
  --build-arg CLIO_STABILITY_MODE=1 `
  --build-arg SWIFTCLIP_PARALLEL=3 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:score-max-r10-gemma-stable `
  --push .
```

The broad Track 2 source-derived profile changes only the visual model and
style writer: `CLIO_VISION_MODEL=qwen/qwen3.5-397b-a17b`,
`CLIO_CAPTION_MODEL=deepseek/deepseek-v4-pro`, and
`CLIO_ALLOW_NON_GEMMA_CAPTION=1`, with the same grid settings.

Track 2 does not inject a provider key. Use a restricted, revocable credential
for the scoring image, never commit it to Git, and rotate it after judging.

## Supporting documents

- [Current release review](docs/CURRENT_RELEASE_REVIEW.md)
- [Candidate validation history](docs/CHAMPION_R1_PLAN.md)
- [Submission form copy](docs/SUBMISSION_FORM_COPY.md)
- [Local dashboard](docs/LOCAL_DASHBOARD.md)
- [Streamlit deployment](docs/STREAMLIT_DEPLOYMENT.md)
