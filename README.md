# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each video, and writes `/output/results.json`
with the requested `formal`, `sarcastic`, `humorous_tech`, and
`humorous_non_tech` captions.

The current confirmed leaderboard score is **0.85**. That score belongs to the
older four-frame `verified5` image. The eight-frame pairs/selector experiment
was submitted separately and scored **0.59**, so it is retained only as a
failed experiment. The concise four-frame candidate scored **0.72**. The
balanced four-frame candidate below is the current release candidate.

## Current candidate

The next release candidate is Novita-only and Gemma-only:

```text
video
  -> four chronological visual anchors
  -> Gemma 4 factual evidence record with an explicit do-not-claim ledger
  -> second Gemma 4 visual verification pass
  -> one direct multimodal writer per style with balanced style calibration
  -> Gemma 4 final visual grounding revision
  -> deterministic schema, length, cliché, and style validation
  -> /output/results.json
```

There is no Claude, Kimi, Gemini, external judge, or provider fallback in the
image. The observer, verifier, persona writers, and final revision all use
`google/gemma-4-31b-it` through Novita.

This architecture keeps the proven evidence/verification path and restores the
original detail and creative range that produced the 0.85 control score. It
adds evaluator-aligned style checks and rejects invented numbers, durations,
names, locations, and literal unseen outcomes.

## Build the leaderboard candidate

PowerShell:

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_PIPELINE=verified5-balanced `
  --build-arg SWIFTCLIP_FRAME_COUNT=4 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-balanced-p2-r2 `
  --push .
```

Track 2 does not inject a provider key. Use a restricted, revocable key and
rotate it after judging; never commit it to Git.

## Verification status

- Six repository tests pass.
- Python compilation passes.
- The exact balanced source completed all eight retired validation videos: 8/8
  tasks, 32/32 captions, exit code zero in 218.4 seconds at parallelism two.
- The pulled balanced public image completed a judge-style test with only
  `/input` and `/output` mounted: 2/2 tasks, 8/8 captions, valid schema, and
  exit zero.
- Anonymous GHCR manifest access returned HTTP 200.

These are reliability and qualitative checks, not a substitute for the hidden
AMD score. Only the leaderboard can confirm a score above 0.92.

Published candidate:
`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-balanced-p2-r2`

Digest: `sha256:9dcc777f1e80256fecee64fbfa3f105f549e5b0e38c3f9100098ec21fefe824f`

See [docs/CURRENT_RELEASE_REVIEW.md](docs/CURRENT_RELEASE_REVIEW.md) for the
score diagnosis, competitor evidence, provenance caveats, and experiment plan.

## Hybrid diagnostic candidate

The Track 2 guide permits any model, so a separately published diagnostic uses
Kimi K2.6 only for visual evidence and keeps Gemma 4 for every caption writer
and final revision:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-kimi-grounded-p2-r3`

Digest: `sha256:dbae1f1d3420c7394704a3ca4bee466951ef214818c42bd6eae86e0c2533b201`

See [docs/MODEL_AB_COMPARISON.md](docs/MODEL_AB_COMPARISON.md) before choosing
between the Gemma-only control and this hybrid experiment.

## Streamlit demo

The human-facing demo is `streamlit_app.py`. It is separate from the evaluator
entrypoint. See [docs/STREAMLIT_DEPLOYMENT.md](docs/STREAMLIT_DEPLOYMENT.md).
