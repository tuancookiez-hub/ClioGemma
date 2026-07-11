# ClioGemma - submission form copy

## Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns short videos into grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions using an evidence-first Gemma 4 pipeline in a reproducible Linux container.

### Long description

> ClioGemma is a containerized video-captioning agent for AMD Developer Hackathon ACT II, Track 2. It reads `/input/tasks.json`, downloads each clip, and samples four chronological visual anchors with FFmpeg. Novita-hosted Gemma 4 creates and independently verifies a structured scene story, stable facts, timeline, and claims to avoid. Four direct multimodal persona writers each produce one concise grounded caption for formal, sarcastic, humorous-tech, and humorous-non-tech output. A final Gemma 4 visual grounding revision checks the captions against the evidence before deterministic validation writes exact-schema `/output/results.json`. The public `linux/amd64` image uses only Novita and Gemma, with no separate judge, non-Gemma writer, audio model, or hardcoded evaluator answers.

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

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-concise-p2-r1`

Verified public digest:

`sha256:8b27cbaeffd98489ce318ebc227b5a150e07b68cd3b972b76302eeade9412c24`

### Additional information

> ClioGemma's submission image is a public `linux/amd64` container that follows the Track 2 contract: it reads `/input/tasks.json`, returns every requested caption style, writes valid `/output/results.json`, and exits cleanly. The production path uses four chronological FFmpeg anchors and Novita-hosted Google Gemma 4 for factual observation, independent visual verification, one concise persona-specific writer per style, and a final grounding revision. It uses no external judge, non-Gemma caption writer, audio model, or hardcoded evaluator answer. The exact source completed all eight retired validation videos with 32/32 captions, and the pulled public artifact passed a separate mounted input/output run with 2/2 tasks and 8/8 captions. The public Streamlit application is a human-facing demo; the AMD evaluator runs the Docker entrypoint. The restricted, revocable Track 2 credential is not stored in GitHub.

## Final checklist

- [x] Push the exact public Linux/amd64 image tag above.
- [x] Record its manifest digest.
- [x] Pull it and verify anonymous manifest access.
- [x] Run the exact published tag with mounted `/input` and `/output`.
- [x] Confirm every task ID and requested style is present and non-empty.
- [x] Push the current source and documentation to GitHub.
- [ ] Enter the public Streamlit URL.
- [ ] Submit the registry reference, not the Docker Hub/GHCR web page URL.
- [ ] Record the returned leaderboard score against the image digest.
