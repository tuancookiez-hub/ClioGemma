# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each clip, and writes `/output/results.json`
with formal, sarcastic, humorous-tech, and humorous-non-tech captions.

## Current release candidates

Gemma-track control:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r6-grid`

Digest: `sha256:2d7eac8954a5a8831608886f6398084086d82ac8016c228e8cc5d51f4f1154e8`

Source-derived broad Track 2 candidate:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r8-qwen-deepseek`

Digest: `sha256:e10362b03f5527a6a32e31119331f2a3ecee78bf60cbc8c04cb7e04775b19418`

This is a new, unscored candidate. The latest recorded leaderboard score is
**0.77**, and the strongest previously confirmed ClioGemma control is **0.85**.
Neither image is presented as a guaranteed 0.93; only AMD's hidden evaluation
can establish the official score. Use r6 when Gemma-track eligibility is the
priority; use r8 when the broad Track 2 score is the priority and supporting
non-Gemma writers are permitted.

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

Kimi/Qwen supplies visual evidence and candidate diversity. Google Gemma 4 owns
verification and final grounding in both candidates. r6 preserves Gemma-only
caption roles for the Gemma track; r8 follows the source-derived independent
style-writer split.

## Validation

The published r6 and r8 images completed the eight retired AMD validation clips:

- 8/8 tasks and 32/32 requested captions
- r6 completed within the 570-second contract; r8 completed in 272.3 seconds at parallelism three
- valid schema, non-empty values, and bounded runtime under the 570-second budget
- anonymous GHCR manifest request: HTTP 200
- clean `docker pull` and Linux/amd64 manifest inspection: passed

The blind comparison is a directional public-set regression test, not AMD's
hidden scoring model.

## Build profiles

The immutable images are already published. The Gemma-track build profile is:

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
  --build-arg SWIFTCLIP_PARALLEL=3 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:score-max-r6-grid `
  --push .
```

The broad Track 2 source-derived profile changes only the visual model and
style writer: `CLIO_VISION_MODEL=qwen/qwen3.5-397b-a17b`,
`CLIO_CAPTION_MODEL=deepseek/deepseek-v4-pro`, and
`CLIO_ALLOW_NON_GEMMA_CAPTION=1`, with the same grid settings.

Track 2 does not inject a provider key. Use a restricted, revocable credential
for the scoring image, never commit it to Git, and rotate it after judging.

## Gemma-only control

The strictly Gemma-only control remains:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

Use r6 when Gemma-track eligibility is the priority. Use r8 when the broad
Track 2 score is the priority and non-Gemma supporting writers are permitted.

## Supporting documents

- [Current release review](docs/CURRENT_RELEASE_REVIEW.md)
- [Candidate validation history](docs/CHAMPION_R1_PLAN.md)
- [Submission form copy](docs/SUBMISSION_FORM_COPY.md)
- [Local dashboard](docs/LOCAL_DASHBOARD.md)
- [Streamlit deployment](docs/STREAMLIT_DEPLOYMENT.md)
