# ClioGemma — Submission Form Copy

This is copy-ready text for the AMD Developer Hackathon ACT II Track 2 form.
It is based on the attached Participant Guide and the current release tree.
Replace angle-bracket placeholders only after the public repository and image
exist.

## Step 1 — Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns each short video into four grounded captions—formal, sarcastic, humorous-tech, and humorous-non-tech—using Novita-hosted Gemma vision inference in a reproducible AMD-compatible Docker pipeline.

This is under the 255-character limit and over the 50-character minimum.

### Long description

> ClioGemma is a containerized video-captioning agent for AMD Developer Hackathon ACT II, Track 2. It reads the evaluator's `/input/tasks.json`, downloads each clip, extracts five chronological anchor frames with FFmpeg, and sends the visual timeline to a Novita-hosted Gemma multimodal model. One structured request produces all four required styles: formal, sarcastic, humorous-tech, and humorous-non-tech. The prompt forces the model to preserve visible evidence, avoid unsupported identities, locations, counts, motives, audio claims, and completed actions, and silently verify each caption before returning JSON. The runner validates the response, preserves the exact requested style schema, handles clips concurrently, enforces bounded per-clip and total runtime, and writes `/output/results.json`. The default release uses Google Gemma 3 27B for reliable latency; Gemma 4 31B is supported as a measured A/B variant. The image is built for `linux/amd64` and contains no external judge or non-Gemma provider. A deterministic schema-preserving placeholder is used only when a clip cannot be processed, preventing malformed output from invalidating the submission. The result is a small, reproducible Docker artifact designed for hidden clips rather than hardcoded examples.

### Categories

Recommended selections:

- Video
- Summarization
- Cloud Application

If available, add Computer Vision or Generative AI; do not add unrelated categories.

### Event track

`Video Captioning`

### Technologies used

Recommended selections:

- Gemma
- AI/ML API
- Python
- Docker
- FFmpeg

## Step 2 — Submission artifacts

### Public GitHub repository

`https://github.com/<your-account>/cliogemma`

The repository must contain the current release tree, a README with build/run
instructions, and no API keys. The current local tree is intentionally
uncommitted after reconstruction; commit and review it before submitting.

### Public Docker image

Recommended tag:

`ghcr.io/<your-account>/cliogemma:release-1`

Build command:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg CLIO_API_KEY="$NOVITA_API_KEY" \
  --build-arg CLIO_MODEL=google/gemma-3-27b-it \
  --tag ghcr.io/<your-account>/cliogemma:release-1 \
  --push .
```

Use a dedicated, restricted, revocable Novita key. The Participant Guide says
Track 2 does not receive an injected key, so the submitted image needs its own
credential. Rotate the key after the submission window. Never commit it to the
repository or paste it into the project description.

### Demo/application URL

Use a publicly reachable demo URL only if one exists. If the form accepts a
container reference instead, provide the public registry image above. Do not
claim that a local Docker tag is publicly runnable.

### Cover image, video, and slides

Use the slide brief in `docs/PPT_SLIDE_BRIEF.md`. The presentation should show
the problem, four-style output, architecture, Docker contract, Gemma choice,
and verified smoke evidence. Do not state an unmeasured leaderboard score.

## Final pre-submit checklist

- [ ] Rotate the keys previously shared in chat; create a dedicated Novita key.
- [ ] Commit the current release tree after restoring any desired historical
      Git/benchmark artifacts from backup.
- [ ] Push the public GitHub repository.
- [ ] Build and push the `linux/amd64` image.
- [ ] Pull the image on a clean machine and run the official example clips.
- [ ] Confirm `/output/results.json` contains every task ID and all four style
      keys with non-empty strings.
- [ ] Confirm the image does not include source files outside the intended
      release tree or any literal key.
- [ ] Complete the platform form, then record each leaderboard submission,
      model, frame count, image tag, timestamp, and returned score.

## Verified claims only

- Local contract tests: `3 passed`.
- `linux/amd64` image build: passed locally.
- Novita Gemma 3 27B one-clip generation smoke: all four styles in about
  7.3 seconds.
- Historical Gemma-only proxy baseline: approximately `0.871`; this is not a
  current leaderboard score.
- Current `0.92+` performance: not yet measured by the AMD evaluator.
