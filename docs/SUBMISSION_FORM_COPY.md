# ClioGemma - submission form copy

## Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns short videos into grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions using scene-aware Kimi evidence and Gemma 4 selection in a reproducible Linux container.

### Long description

> ClioGemma is a containerized AMD Developer Hackathon ACT II Track 2 agent. It reads `/input/tasks.json`, downloads each clip, and samples six scene-aware chronological frames with FFmpeg plus optional local OCR hints. Novita-hosted Kimi K2.6 produces dense visual evidence and two candidates per requested style. Gemma 4 verifies the evidence, selects or repairs formal, sarcastic, humorous-tech, and humorous-non-tech captions, and deterministic contract checks write `/output/results.json`.

### Categories

- Video
- Summarization
- Cloud Application
- Computer Vision, if available

### Event track

`Video Captioning`

### Technologies used

- Gemma
- Kimi K2.6
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

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r5`

Digest: `sha256:b1fe388ebf6ebfd2b0d0326adecf46be82578a47679ba8931ea98894e5c97156`

### Additional information

> ClioGemma's submission image is a public `linux/amd64` container following the Track 2 contract: it reads `/input/tasks.json`, returns every requested style, writes valid `/output/results.json`, and exits cleanly. Scene-aware six-frame sampling and optional OCR feed Kimi K2.6 visual evidence and style candidates; Gemma 4 performs verification, final selection, and repairs. The exact image completed all eight retired validation clips in 351.2 seconds with 32/32 captions and passed anonymous GHCR manifest verification. No hardcoded evaluator answer or external judge is used.

### Gemma-only control

If you want the strictly Gemma-only variant, use:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

## Final checklist

- [x] Push the exact public Linux/amd64 image tag above.
- [x] Record its manifest digest.
- [x] Verify anonymous manifest access.
- [x] Run the exact published tag with mounted `/input` and `/output`.
- [x] Confirm every task ID and requested style is present and non-empty.
- [x] Push the current source and documentation to GitHub.
- [ ] Enter the public Streamlit URL.
- [x] Submit the registry reference, not the Docker Hub/GHCR web page URL.
- [ ] Record the returned leaderboard score against the image digest.
