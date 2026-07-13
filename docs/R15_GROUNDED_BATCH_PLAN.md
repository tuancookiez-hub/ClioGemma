# r15 grounded batch candidate

**Status:** r15 implemented and smoke-tested; r16 visual-override follow-up is the current candidate

## Why r14 stalled at 0.70

The r14 image used a fast two-call path:

1. Kimi K2.6 inspected a four-frame chronological contact sheet and returned
   structured evidence.
2. Gemma 4 wrote all four captions from the text evidence only.

That kept runtime low, but the final Gemma writer could not re-check the
images. Its local outputs show broad, interchangeable captions and lost
distinctive details. This is a concrete regression from the 0.85 control,
where Gemma had image access while writing.

## r15 change

`score-max-r15-grounded` keeps the same Kimi evidence stage and the same
four-style single Gemma call, but sends Gemma the labelled chronological
contact sheet plus the evidence JSON. The writer prompt now follows the public
Track 2 rubric: concrete subject/setting details first, one scene-specific
style beat, and no suppression of a briefly visible main subject.

There is no extra selector or repair call. This is intentional: the failed
0.10 candidate chained too many calls and timed out, while the r14 two-call
profile completed its local contract. r15 changes the information available to
the writer without widening the latency budget.

## Build

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VISION_MODEL=moonshotai/kimi-k2.6 `
  --build-arg CLIO_PIPELINE=score-max-r15-grounded `
  --build-arg SWIFTCLIP_FRAME_STRATEGY=anchors `
  --build-arg SWIFTCLIP_FRAME_COUNT=4 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg CLIO_GRID_INPUT=1 `
  --build-arg CLIO_STABILITY_MODE=1 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --build-arg SWIFTCLIP_CLIP_TIMEOUT=65 `
  --build-arg SWIFTCLIP_OCR=0 `
  --build-arg CLIO_REQUEST_TIMEOUT=20 `
  --build-arg CLIO_RATE_LIMIT_RETRIES=0 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:score-max-r15-grounded `
  --push .
```

Do not overwrite the r14 tag. Record the resulting digest and the official
score separately. A local contract pass can establish schema/runtime health,
but only the AMD judge can establish the score.

## Validation

- `python -m pytest tests -q`: 11 passed
- `python -m compileall -q app tests`: passed
- `git diff --check`: passed
- New regression test confirms Kimi and Gemma each receive the chronological
  contact sheet and that Gemma remains the emitting model.

## r16 visual-override follow-up

The eight-clip r15 smoke completed in 99 seconds with 8/8 valid task results,
but the trace showed Kimi mislabeling a zucchini as cucumber and the bleacher
colors. r16 keeps the same runtime and model roles and adds an explicit rule:
Gemma must resolve any evidence/image conflict from the pixels, instead of
mechanically copying the Kimi noun. It also requires each technical joke to map
to the visible action rather than merely naming an object.

Build r16 with the same script:

```powershell
.\scripts\build_r15_grounded.ps1 `
  -Pipeline score-max-r16-visual-override `
  -Tag ghcr.io/tuancookiez-hub/cliogemma:score-max-r16-visual-override `
  -Push
```
