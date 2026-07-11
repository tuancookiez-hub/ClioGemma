# ClioGemma - AMD Developer Hackathon ACT II, Track 2

This is the production Docker submission for video captioning. It reads
`/input/tasks.json` and writes `/output/results.json` with the requested
`formal`, `sarcastic`, `humorous_tech`, and `humorous_non_tech` captions.

Production inference is Novita-only and Gemma-only:

- `google/gemma-3-27b-it` (default, lower-latency release candidate)
- `google/gemma-4-31b-it` (explicit A/B variant)

The image has no external judge, Claude/Gemini fallback, audio model, or
text-only provider. The release path makes one structured multimodal Gemma
request per clip. If a clip fails, the runner emits a deterministic
schema-preserving placeholder so the submission remains valid; this is not a
second model/provider fallback.

## Build for submission

```bash
docker buildx build --platform linux/amd64 \
  --build-arg CLIO_API_KEY="$NOVITA_API_KEY" \
  --build-arg CLIO_MODEL=google/gemma-3-27b-it \
  --tag <public-registry>/<user>/cliogemma:release-1 \
  --push .
```

Track 2 permits credentials inside the image because no key is injected by the
harness. Use a restricted, revocable key and rotate it after submission. Never
commit the key or put it in documentation.

The attached Participant Guide is the release contract for this package. The
public event page has broader Fireworks/LLM-judge wording; verify the live
submission validator before publishing. “No judge” here means no judge is
bundled in this image—the platform evaluator remains external.

## Review document

See [docs/CURRENT_RELEASE_REVIEW.md](docs/CURRENT_RELEASE_REVIEW.md) for the
participant-guide contract, architecture, competitor comparison, score
history, release checklist, and the honest `0.92+` assessment.
