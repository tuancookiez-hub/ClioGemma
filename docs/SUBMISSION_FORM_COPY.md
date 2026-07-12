# ClioGemma - submission form copy

## Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns short videos into grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions using an evidence-first Gemma 4 pipeline in a reproducible Linux container.

### Long description

> ClioGemma is a containerized video-captioning agent for AMD Developer Hackathon ACT II, Track 2. It reads `/input/tasks.json`, downloads each clip, and samples four chronological visual anchors with FFmpeg. Novita-hosted Gemma 4 creates and independently verifies a structured scene story, stable facts, timeline, and claims to avoid. Four direct multimodal persona writers produce grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions with evaluator-aligned style guidance. A final Gemma 4 visual grounding revision checks the captions against the evidence before deterministic validation writes exact-schema `/output/results.json`. The public `linux/amd64` image uses only Novita and Gemma, with no separate judge, non-Gemma writer, audio model, or hardcoded evaluator answers.

### Categories

- Video
- Summarization
- Cloud Application
- Computer Vision, if available

### Event track

`Video Captioning`

### Technologies used

- Gemma
- AI/ML API
- Python
- Docker
- FFmpeg

## Application

### GitHub repository

`https://github.com/tuancookiez-hub/ClioGemma`

### Demo platform

`Streamlit`

### Demo URL

Use the final public `.streamlit.app` URL after deployment. Do not enter a
localhost URL.

### Docker image

`ghcr.io/tuancookiez-hub/cliogemma:track2-final-r1`

Digest: `sha256:a66cd000cfb8d416e0c23574801839ee7957affa2ab93cd47621e4be7e19eb14`

### Additional information

> ClioGemma's submission image is a public `linux/amd64` container that follows the Track 2 contract: it reads `/input/tasks.json`, returns every requested caption style, writes valid `/output/results.json`, and exits cleanly. Kimi K2.6 is used only for chronological visual evidence; Google Gemma 4 performs the evidence verification, all four-style caption writing, internal selection, and final accuracy/style revision. The image uses no non-Gemma caption writer, audio model, or hardcoded evaluator answer. The public Streamlit application is a human-facing demo; the AMD evaluator runs the Docker entrypoint. The restricted, revocable Track 2 credential is not stored in GitHub.

### Gemma-only control

If you want the strictly Gemma-only variant, use:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

The public guide permits any Track 2 model, but this control keeps every model
role on Gemma and is useful for a Gemma-specific prize entry.

## Final checklist

- [ ] Push the exact public Linux/amd64 image tag above.
- [ ] Record its manifest digest.
- [ ] Pull it and verify anonymous manifest access.
- [ ] Run the exact published tag with mounted `/input` and `/output`.
- [x] Confirm every task ID and requested style is present and non-empty.
- [x] Push the current source and documentation to GitHub.
- [ ] Enter the public Streamlit URL.
- [ ] Submit the registry reference, not the Docker Hub/GHCR web page URL.
- [ ] Record the returned leaderboard score against the image digest.
