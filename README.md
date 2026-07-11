# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each video, and writes `/output/results.json`
with the requested `formal`, `sarcastic`, `humorous_tech`, and
`humorous_non_tech` captions.

The current confirmed leaderboard score is **0.85**. That score belongs to the
older four-frame `verified5` image, not the eight-frame candidate in this source
tree. The new image has not yet received an AMD score.

## Current candidate

The next release candidate is Novita-only and Gemma-only:

```text
video
  -> eight chronological visual anchors
  -> Gemma 4 factual evidence record with an explicit do-not-claim ledger
  -> second Gemma 4 visual verification pass
  -> one direct multimodal writer per style, producing two alternatives
  -> Gemma 4 visual selector compares both alternatives against six anchors
  -> deterministic schema, length, cliché, and style validation
  -> /output/results.json
```

There is no Claude, Kimi, Gemini, external judge, or provider fallback in the
image. The observer, verifier, persona writers, and visual selector all use
`google/gemma-4-31b-it` through Novita. The selector is part of caption
generation, not a separate scoring model or provider.

This architecture combines verified evidence with the strongest lesson from
the public 0.91-0.92 systems and AMD's retired validation examples: every
creative style needs a distinctive voice, bold figurative humor, and concrete
visible details. ClioGemma adds pairwise alternatives, a frame-aware selector,
stock-phrase rejection, and a rule that prevents uncertain peripheral text
from becoming a literal caption claim.

## Build the leaderboard candidate

PowerShell:

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_PIPELINE=verified7 `
  --build-arg SWIFTCLIP_FRAME_COUNT=8 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-8f-pairs-picker-p2-r1 `
  --push .
```

Track 2 does not inject a provider key. Use a restricted, revocable key and
rotate it after judging; never commit it to Git.

## Verification status

- Six repository tests pass.
- Python compilation passes.
- The exact final source completed all eight retired validation videos: 8/8
  tasks, 32/32 captions, exit code zero in 218.4 seconds at parallelism two.
- The pulled public image completed a judge-style test with only `/input` and
  `/output` mounted: 2/2 tasks, 8/8 captions, valid schema, exit zero in 103.3
  seconds.
- Anonymous GHCR manifest access returned HTTP 200.

These are reliability and qualitative checks, not a substitute for the hidden
AMD score. Only the leaderboard can confirm a score above 0.92.

Published candidate:
`ghcr.io/tuancookiez-hub/cliogemma:gemma4-8f-pairs-picker-p2-r1`

Digest: `sha256:b0f2f7040b94b0cb7a994c5ebea5ff08d85e8addc759d494009581765ef7d026`

See [docs/CURRENT_RELEASE_REVIEW.md](docs/CURRENT_RELEASE_REVIEW.md) for the
score diagnosis, competitor evidence, provenance caveats, and experiment plan.

## Streamlit demo

The human-facing demo is `streamlit_app.py`. It is separate from the evaluator
entrypoint. See [docs/STREAMLIT_DEPLOYMENT.md](docs/STREAMLIT_DEPLOYMENT.md).
