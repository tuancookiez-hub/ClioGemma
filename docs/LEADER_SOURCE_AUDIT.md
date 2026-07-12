# Source audit: Drake3001 #1 Track 2 submission

This audit is based on the cloned repository source, not its README alone:
`https://github.com/Drake3001/Dindu-s-team---AMD-Track-2-submission`.

## Active execution path

The Dockerfile runs `python src/main.py`. The active path is:

```text
/input/tasks.json
  -> download_for_task
  -> preprocessing.preprocess_video
       -> OpenCV decode at 1 FPS
       -> resize to 512px longest edge
       -> near-duplicate pruning (mean grayscale difference >= 5)
       -> 4x4 contact-sheet JPEG grids
  -> one Qwen3.7 Plus multimodal chronological analysis request
  -> four independent DeepSeek V4 Pro text caption requests
       -> formal, sarcastic, humorous-tech, humorous-non-tech
  -> /output/results.json
```

`src/main.py` contains an older duplicate block after the active `asyncio.run`
return path. That block is unreachable and is not part of the scored execution.
The `src/pipeline_2` important-frame detector is also not called by the active
workflow; `preprocessing.preprocess_video` is the real sampler.

## Configuration that matters

From `config/pipeline.yaml`:

- VLM: Fireworks `accounts/fireworks/models/qwen3p7-plus`, temperature 0,
  max tokens 8192.
- Caption writer: Fireworks `accounts/fireworks/models/deepseek-v4-pro`,
  temperature 0.2, max tokens 2048.
- Sampling: 1 FPS, max 240 sampled frames, 512px longest edge.
- Pruning: adjacent near-duplicates removed with threshold 5.0.
- Contact sheets: 4 columns by 4 rows; all resulting grids are sent in one
  multimodal request.
- Inference: up to three concurrent model calls.

## Prompt behavior

The VLM prompt demands a chronological JSON event list with subjects, actions,
and camera movement. The style prompts are intentionally high-contrast:

- formal: documentary, chronological, camera-aware;
- sarcastic: cynical narration and jokes about basic camera movement;
- humorous-tech: heavy programming/game-engine vocabulary and deliberate
  over-engineering;
- humorous-non-tech: colorful comparisons and invented comic motivations.

This is materially different from ClioGemma's conservative short-caption gate.
The leader is optimizing style separability and temporal narrative, not merely
schema validity.

## What appears to explain the 0.92

1. A stronger vision model sees a much denser temporal record than six raw
   frames.
2. A stronger text model writes each style independently from structured events.
3. The style prompts make the requested tones unmistakable.
4. Async inference keeps the larger prompt/caption workload within the runtime.

There is no source evidence of a hidden judge, hardcoded answer table, or
special evaluator exploit. The main weaknesses are reproducibility (the old
pipeline_2 sampler uses unseeded random selection) and an unreachable duplicate
main block, but neither is required by the active path.

## Gap versus `score-max-r5`

ClioGemma currently uses Kimi evidence, six individual frames, Kimi candidate
generation, and Gemma selection/repair. It does not yet provide the leader's
multi-grid temporal coverage or DeepSeek-style high-contrast persona prompts.

## Implemented source-derived candidates

Two isolated candidates were implemented after this audit; neither mutates the
previous `score-max-r5` tag:

| Tag | Visual path | Caption path | Result |
|---|---|---|---|
| `score-max-r6-grid` | Novita Kimi K2.6, up to 16 scene-aware frames in chronological 4x4 grids | Gemma 4 verification, selection, and repair | 8/8 clips and 32/32 captions; completed within the 570-second contract |
| `score-max-r8-qwen-deepseek` | Novita Qwen3.5 multimodal, same chronological grids | Gemma 4 evidence verification/final grounding with DeepSeek V4 Pro style drafting | 8/8 clips and 32/32 captions; completed within the 570-second contract |

The r8 candidate is the closest source-derived analogue: the image model sees
the dense temporal grids, while a text model writes each style independently.
It is deliberately separate from the Gemma-only r6 control so the Gemma track
and the general Track 2 leaderboard can be evaluated independently.

## Next experiment

The implementation phase is complete. Do not run another full public-set
benchmark merely to create activity. Submit one immutable candidate, record its
digest and official score, then make the next change only from the evaluator's
result. If Gemma-track eligibility is the priority, use r6; if the broad Track
2 score is the priority and non-Gemma supporting writers are permitted, use r8.
