# ClioGemma - AMD Developer Hackathon ACT II, Track 2

ClioGemma is a Dockerized video-captioning agent. It reads
`/input/tasks.json`, downloads each video, and writes `/output/results.json`
with the requested `formal`, `sarcastic`, `humorous_tech`, and
`humorous_non_tech` captions.

The latest confirmed leaderboard score is **0.75**. The strongest confirmed
control remains **0.85** from the older four-frame `verified5` image. The
eight-frame pairs/selector experiment scored **0.59**, and the concise
four-frame candidate scored **0.72**. The current work is a new measured
Gemma-only recovery candidate; it is not being presented as a guaranteed 0.93.

## Current candidate

The next release candidate is Novita-only and Gemma-only (`verified5-champion`):

```text
video
  -> four chronological visual anchors
  -> Gemma 4 factual evidence record with an explicit do-not-claim ledger
  -> second Gemma 4 visual verification pass
  -> one direct multimodal writer per style; Gemma internally drafts two angles
     and keeps the sharper grounded survivor
  -> Gemma 4 final accuracy/style revision
  -> deterministic schema, length, cliché, and style validation
  -> /output/results.json
```

There is no Claude, Kimi, Gemini, external judge, or provider fallback in the
image. The observer, verifier, persona writers, and final revision all use
`google/gemma-4-31b-it` through Novita.

This architecture keeps the proven evidence/verification path and restores the
original detail and creative range that produced the 0.85 control score. It
adds evaluator-aligned style checks, rejects stock formulas before fallback,
and preserves the verified anchor in every deterministic fallback.

## Build the leaderboard candidate

PowerShell:

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_PIPELINE=verified5-champion `
  --build-arg SWIFTCLIP_FRAME_COUNT=4 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r1 `
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

The source changes for this candidate are documented in
[docs/CHAMPION_R1_PLAN.md](docs/CHAMPION_R1_PLAN.md). The public image must be
built and pushed with the user's revocable Novita key before submission.

See [docs/CURRENT_RELEASE_REVIEW.md](docs/CURRENT_RELEASE_REVIEW.md) for the
score diagnosis, competitor evidence, provenance caveats, and experiment plan.

## Highest-scoring local candidate

The Track 2 guide permits any model. The strongest local retired-set proxy is
the Kimi-grounded Gemma batch profile:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-kimi-batch-r1`

Digest: `sha256:a66cd000cfb8d416e0c23574801839ee7957affa2ab93cd47621e4be7e19eb14`

Kimi is used only for eight-frame visual evidence; Gemma performs evidence
verification, all caption writing, internal selection, and final revision. The
strict local proxy measured 0.759, while the Gemma proxy was much more lenient;
only AMD can decide the official score. The strictly Gemma-only control remains
`gemma4-champion-r6`.

See [docs/MODEL_AB_COMPARISON.md](docs/MODEL_AB_COMPARISON.md) and
[docs/CHAMPION_R1_PLAN.md](docs/CHAMPION_R1_PLAN.md) for the A/B evidence.

## Streamlit demo

The human-facing demo is `streamlit_app.py`. It is separate from the evaluator
entrypoint. See [docs/STREAMLIT_DEPLOYMENT.md](docs/STREAMLIT_DEPLOYMENT.md).
