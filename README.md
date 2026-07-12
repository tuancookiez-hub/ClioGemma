# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each clip, and writes `/output/results.json`
with formal, sarcastic, humorous-tech, and humorous-non-tech captions.

## Current score candidate

Submit this exact public Linux/amd64 image:

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r5`

Digest: `sha256:b1fe388ebf6ebfd2b0d0326adecf46be82578a47679ba8931ea98894e5c97156`

This is a new, unscored candidate. The latest recorded leaderboard score is
**0.77**, and the strongest previously confirmed ClioGemma control is **0.85**.
The new image is not presented as a guaranteed 0.93; only AMD's hidden
evaluation can establish its official score.

## Architecture

```text
video
  -> scene-aware sampling of six chronological 768px frames plus optional OCR hints
  -> Kimi K2.6 dense factual grounding through Novita
     (summary, setting, subjects, primary action, 5-9 stable details,
      timeline, visible text, uncertainty ledger)
  -> Gemma 4 31B visual verification, then Kimi K2.6 generates two candidates
     per requested style
  -> Gemma 4 31B selects and repairs the four final style captions
     (public-guide style calibration and concrete-detail preservation)
  -> deterministic hallucination, brand, count, cliché, encoding,
     length, style, and schema validation
  -> atomic /output/results.json
```

Kimi supplies visual evidence and candidate diversity. Google Gemma 4 owns
verification, final caption selection, and repairs. The score-max profile keeps
the richer candidate stage while preserving the exact Track 2 contract.

## Validation

The exact published r5 image completed the eight retired AMD validation clips:

- 8/8 tasks and 32/32 requested captions
- exit code zero in 351.2 seconds at parallelism two
- valid schema, non-empty values, and bounded runtime under the 570-second budget
- anonymous GHCR manifest request: HTTP 200
- clean `docker pull` and Linux/amd64 manifest inspection: passed

The blind comparison is a directional public-set regression test, not AMD's
hidden scoring model.

## Build

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
  --build-arg SWIFTCLIP_FRAME_COUNT=6 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:score-max-r5 `
  --push .
```

Track 2 does not inject a provider key. Use a restricted, revocable credential
for the scoring image, never commit it to Git, and rotate it after judging.

## Gemma-only control

The strictly Gemma-only control remains:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

Use r5 when the primary objective is the Track 2 leaderboard. Keep r6 only for
a comparison where every model role must be Gemma.

## Supporting documents

- [Current release review](docs/CURRENT_RELEASE_REVIEW.md)
- [Candidate validation history](docs/CHAMPION_R1_PLAN.md)
- [Submission form copy](docs/SUBMISSION_FORM_COPY.md)
- [Local dashboard](docs/LOCAL_DASHBOARD.md)
- [Streamlit deployment](docs/STREAMLIT_DEPLOYMENT.md)
