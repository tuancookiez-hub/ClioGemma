# Gemma vs Kimi vision A/B comparison

**Updated:** 2026-07-12

## Why this test exists

ClioGemma's Gemma-only candidates scored 0.85, 0.59, and 0.72. Public
0.91-class repositories use a stronger vision/evidence model before Gemma
styles the captions. This test isolates that variable instead of replacing the
whole application with an unmeasured model.

## Public architecture evidence

- [Yash's AMD Track 2 repository](https://github.com/yash-kumarx/amd-hackathon-video-captioning)
  describes Kimi K2.6 as the vision-grounding stage and Gemma 4 as the styling,
  selection, and critique stage.
- [TheSkyGold's Track 2 repository](https://github.com/TheSkyGold/track2-captioner)
  describes Qwen3-VL-8B scene understanding followed by Gemma styling in its
  default submission profile.
- [Novita's Kimi K2.6 model page](https://novita.ai/models/model-detail/moonshotai-kimi-k2.6)
  lists `moonshotai/kimi-k2.6` with image and video input support.

The participant guide permits any model/API/framework for Track 2, so a Kimi
vision stage with Gemma caption writers is eligible for the general Track 2
submission. The Gemma-only tag remains available for a Gemma-specific entry.

## Controlled A/B method

- Same v3 and v8 AMD reference videos.
- Same four chronological 768px frames per clip.
- Same prompt, output schema, temperature target, and Novita endpoint.
- Only the multimodal model changed: `google/gemma-4-31b-it` versus
  `moonshotai/kimi-k2.6`.
- Kimi reasoning was disabled for the JSON probe; otherwise its reasoning can
  consume the output budget without returning visible JSON.

## Observed output difference

Gemma's direct captions were valid and stylistically coherent, but its visual
descriptions were often broad: “a woman works at a computer” or “a man runs on
a red track.” Kimi more consistently surfaced useful evidence such as the
wired mouse, potted plants, lane/bleacher structure, and the runner entering
and exiting the frame. Kimi also produced stronger scene-specific analogies.

Kimi is not automatically correct: one evidence draft contradicted the
runner's direction, so the hybrid keeps a final Gemma image-grounded revision.
The conclusion is “Kimi is a better evidence candidate on these probes,” not
“Kimi should write the final captions without review.”

## Hybrid implementation

```text
4 chronological frames
  -> Kimi K2.6 evidence JSON (thinking disabled)
  -> Gemma 4 persona writers for all four requested styles
  -> Gemma 4 final image-grounded revision
  -> schema and style validation
```

Published diagnostic candidate:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-4f-kimi-grounded-p2-r3`

Digest:

`sha256:dbae1f1d3420c7394704a3ca4bee466951ef214818c42bd6eae86e0c2533b201`

Exact published-image validation:

- 2/2 reference tasks, 8/8 captions, exit code 0
- Full eight-clip set: 8/8 tasks, 32/32 captions, exit code 0
- Full eight-clip wall time: approximately 161 seconds

No official AMD score exists for this tag yet. Submit it only as a separately
measured experiment; keep the Gemma-only balanced tag as the control.
