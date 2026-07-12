# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each clip, and writes `/output/results.json`
with formal, sarcastic, humorous-tech, and humorous-non-tech captions.

## Current score candidate

Submit this exact public Linux/amd64 image:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-reference-r3`

Digest: `sha256:c4d26f321471cff72685c519b952a0854331a9dcd8a608b533b5c84059e6587e`

This is a new, unscored candidate. The latest recorded leaderboard score is
**0.75**, and the strongest previously confirmed ClioGemma control is **0.85**.
The new image is not presented as a guaranteed 0.93; only AMD's hidden
evaluation can establish its official score.

## Architecture

```text
video
  -> five chronological 768px frames
  -> Kimi K2.6 dense factual grounding through Novita
     (summary, setting, subjects, primary action, 5-9 stable details,
      timeline, visible text, uncertainty ledger)
  -> four dedicated Gemma 4 31B multimodal style writers through Novita
     (one call per requested style, public-guide style calibration,
      internal two-angle drafting)
  -> deterministic hallucination, brand, count, cliché, encoding,
     length, style, and schema validation
  -> atomic /output/results.json
```

Kimi supplies visual evidence only. Google Gemma 4 writes every caption. The
reference-calibrated profile deliberately skips the old global rewrite stage,
which frequently flattened strong jokes into safe generic captions.

## Validation

The exact published r3 image completed the eight retired AMD validation clips:

- 8/8 tasks and 32/32 requested captions
- exit code zero in 140.4 seconds at parallelism two
- valid schema and no deterministic quality-gate failures
- no empty captions, malformed encoding, or unsupported brand leakage
- blind comparison against the previous Kimi/Gemma batch candidate: **31 of
  32 captions preferred**, with one loss on mountain tech humor
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
  --build-arg CLIO_PIPELINE=hybrid-kimi-reference `
  --build-arg SWIFTCLIP_FRAME_COUNT=5 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-reference-r3 `
  --push .
```

Track 2 does not inject a provider key. Use a restricted, revocable credential
for the scoring image, never commit it to Git, and rotate it after judging.

## Gemma-only control

The strictly Gemma-only control remains:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

Use r3 when the primary objective is the Track 2 leaderboard. Keep r6 only for
a comparison where every model role must be Gemma.

## Supporting documents

- [Current release review](docs/CURRENT_RELEASE_REVIEW.md)
- [Candidate validation history](docs/CHAMPION_R1_PLAN.md)
- [Submission form copy](docs/SUBMISSION_FORM_COPY.md)
- [Local dashboard](docs/LOCAL_DASHBOARD.md)
- [Streamlit deployment](docs/STREAMLIT_DEPLOYMENT.md)
