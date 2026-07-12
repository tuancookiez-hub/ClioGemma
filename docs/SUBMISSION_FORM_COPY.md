# ClioGemma - submission form copy

## Basic information

### Submission title

`ClioGemma`

### Short description

> ClioGemma turns short videos into grounded formal, sarcastic, humorous-tech, and humorous-non-tech captions using Kimi visual evidence and Gemma 4 caption generation in a reproducible Linux container.

### Long description

> ClioGemma is a containerized video-captioning agent for AMD Developer Hackathon ACT II, Track 2. It reads `/input/tasks.json`, downloads each clip, and samples five chronological visual anchors with FFmpeg. Novita-hosted Kimi K2.6 converts those frames into dense factual evidence: a scene summary, subjects, primary action, stable details, timeline, visible text, and claims to avoid. Four dedicated multimodal Gemma 4 writers then produce formal, sarcastic, humorous-tech, and humorous-non-tech captions with public-guide-aligned style calibration and internal two-angle drafting. Deterministic hallucination, brand, count, cliché, encoding, length, style, and schema checks write exact-contract `/output/results.json`. Kimi provides visual evidence only; Gemma writes every emitted caption.

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

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-reference-r3`

Digest: `sha256:c4d26f321471cff72685c519b952a0854331a9dcd8a608b533b5c84059e6587e`

### Additional information

> ClioGemma's submission image is a public `linux/amd64` container that follows the Track 2 contract: it reads `/input/tasks.json`, returns every requested caption style, writes valid `/output/results.json`, and exits cleanly. Kimi K2.6 is used only for five-frame chronological visual evidence; Google Gemma 4 performs all four dedicated caption-writing roles and internal style selection. Deterministic quality gates prevent malformed encoding, unsupported brands or counts, stock jokes, and invalid output. The image uses no non-Gemma caption writer, audio model, or hardcoded evaluator answer. The exact published image completed all eight retired validation clips in 140.4 seconds with 32/32 captions and passed anonymous pull verification.

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
