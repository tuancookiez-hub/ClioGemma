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

`ghcr.io/tuancookiez-hub/cliogemma:score-max-r20-qwen-gemma-reliable`

Digest: `sha256:1562851f5271a5a0dfa34ffacc12bcde78c3467acb2585c7809684fe65ae2c41`

### Additional information

> ClioGemma's submission image is a `linux/amd64` container following the Track 2 contract: it reads `/input/tasks.json`, returns every requested style, writes valid `/output/results.json`, and exits cleanly. Scene-aware chronological frames feed Qwen3.5 visual evidence; Gemma 4 verifies the evidence and emits all final captions. The exact image completed all eight retired validation clips in 146.0 seconds with 32/32 captions. No hardcoded evaluator answer or external judge is used. Make the GHCR package public before submitting.

### Gemma-only control

If you want the strictly Gemma-only variant, use:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r6`

## Final checklist

- [x] Push the exact Linux/amd64 image tag above.
- [x] Record its manifest digest.
- [ ] Verify anonymous manifest access after changing package visibility to Public.
- [x] Run the exact published tag with mounted `/input` and `/output`.
- [x] Confirm every task ID and requested style is present and non-empty.
- [x] Push the current source and documentation to GitHub.
- [ ] Enter the public Streamlit URL.
- [x] Submit the registry reference, not the Docker Hub/GHCR web page URL.
- [ ] Record the returned leaderboard score against the image digest.
