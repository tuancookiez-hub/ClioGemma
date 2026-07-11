# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each video, and writes `/output/results.json`
with the requested `formal`, `sarcastic`, `humorous_tech`, and
`humorous_non_tech` captions.

The current leaderboard score is **0.68**. That score belongs to the older
Gemma 3 fast image, not the stronger candidate in this source tree.

## Current candidate

The next release candidate is Novita-only and Gemma-only:

```text
video
  -> four chronological visual anchors
  -> Gemma 4 factual evidence record with an explicit do-not-claim ledger
  -> second Gemma 4 visual verification pass
  -> four direct multimodal persona writers with style-specific temperatures
  -> final Gemma 4 revision against the original images
  -> deterministic schema/style validation
  -> /output/results.json
```

There is no Claude, Kimi, Gemini, external judge, or provider fallback in the
image. The observer, verifier, writer, and final grounding revision all use
`google/gemma-4-31b-it` through Novita. The final revision is part of caption
generation, not a scoring model.

This architecture combines verified evidence with the strongest lesson from
the current 0.92 Quiptionary image and AMD's retired validation examples:
every creative style needs a distinctive voice, bold figurative humor, and at
least one concrete visible detail. ClioGemma adds a do-not-claim ledger and a
final frame-aware revision without flattening obvious jokes.

## Build the leaderboard candidate

PowerShell:

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_PIPELINE=verified5 `
  --build-arg SWIFTCLIP_FRAME_COUNT=4 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-p2-r1 `
  --push .
```

Track 2 does not inject a provider key. Use a restricted, revocable key and
rotate it after judging; never commit it to Git.

## Verification status

- Six repository tests pass.
- Python compilation passes.
- One real Gemma 4 image request completed in 5.4 seconds.
- All eight official retired validation videos completed 8/8 tasks and 32/32
  captions with exit code zero in 367.7 seconds at parallelism two, inside the
  570-second budget. Outputs retained specific details and strong personas.

These are reliability and qualitative checks, not a substitute for the hidden
AMD score. Only the leaderboard can confirm a score above 0.92.

Published candidate:
`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-p2-r1`  
Digest: `sha256:42b6db6e6438d1adbb34f3d4120d02a0f24b7c5616fb24df51f1a21ce63a97b5`

See [docs/CURRENT_RELEASE_REVIEW.md](docs/CURRENT_RELEASE_REVIEW.md) for the
score diagnosis, competitor evidence, provenance caveats, and experiment plan.

## Streamlit demo

The human-facing demo is `streamlit_app.py`. It is separate from the evaluator
entrypoint. See [docs/STREAMLIT_DEPLOYMENT.md](docs/STREAMLIT_DEPLOYMENT.md).
