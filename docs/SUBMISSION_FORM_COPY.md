# ClioGemma - submission form copy

## Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns short videos into grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions using an evidence-first Gemma 4 pipeline in a reproducible Linux container.

### Long description

> ClioGemma is a containerized video-captioning agent for AMD Developer Hackathon ACT II, Track 2. It reads `/input/tasks.json`, downloads each clip, and samples four chronological visual anchors with FFmpeg. Novita-hosted Gemma 4 creates and independently verifies a structured evidence record, including visible facts and claims to avoid. Four direct multimodal persona writers then produce formal, sarcastic, humorous-tech, and humorous-non-tech captions. Literal details remain grounded while creative styles may use clearly figurative humor, matching AMD's public validation guidance. A final Gemma 4 revision checks accuracy and style against the original images before the runner writes exact-schema `/output/results.json`. The `linux/amd64` image uses only Novita and Gemma, with no separate judge, non-Gemma writer, audio model, or hardcoded evaluator answers.

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

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-verified5-p2-r1`

Use this exact value only after the tag has been pushed and anonymously pulled.

### Additional information

> ClioGemma's submission image is a public `linux/amd64` container that follows the Track 2 contract: it reads `/input/tasks.json`, returns every requested caption style, writes valid `/output/results.json`, and exits cleanly. The production path uses four chronological FFmpeg anchors and Novita-hosted Google Gemma 4 for factual observation, visual verification, direct multimodal persona writing, and a final frame-grounded revision. It uses no external judge, non-Gemma caption writer, audio model, or hardcoded evaluator answer. The public Streamlit application is a human-facing demo; the AMD evaluator runs the Docker entrypoint. The credential embedded for Track 2 is restricted and revocable and is not stored in GitHub.

## Final checklist

- [ ] Push the current source to GitHub.
- [ ] Push the exact public Linux/amd64 image tag above.
- [ ] Record its manifest digest.
- [ ] Pull it anonymously.
- [ ] Run the exact published tag with mounted `/input` and `/output`.
- [ ] Confirm every task ID and requested style is present and non-empty.
- [ ] Enter the public Streamlit URL.
- [ ] Submit the registry reference, not the Docker Hub/GHCR web page URL.
- [ ] Record the returned leaderboard score against the image digest.
