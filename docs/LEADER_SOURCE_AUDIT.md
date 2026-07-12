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

## Cross-reference audit: what the other repositories actually run

This section is based on executable Docker entrypoints and imported modules,
not on claimed README architecture.

| Repository | Active scored path | Genuine lesson | What was not adopted |
|---|---|---|---|
| [Yash](https://github.com/yash-kumarx/amd-hackathon-video-captioning) | `main.py` → `pipeline.run`; Kimi grounding with optional OCR/audio, Gemma style generation, Kimi/Flash fallback races, atomic prefilled output | Grounding/style separation, failure ladder, evidence enrichment, and candidate/critique hooks | Multiple external keys/providers and the default `BEST_OF_N=1` path are not a score guarantee |
| [Raccoon](https://github.com/Showraiser/Raccoon-Vision-Translator) | `app.py`; five evenly spaced frames, Gemma 4 description, Gemma visual verification, then one sequential writer per style | A second visual verification pass and clearly separated personas | Five-frame spacing alone does not explain the higher score; no Docker Track 2 runtime path is present in the repo |
| [Stryvo](https://github.com/StrvyoLabs/Stryvo-Vision) | `main.py`; up to 12 frames, one Kimi neutral description, four concurrent GLM-5.2 style calls | Dense evenly spread evidence and independent style calls | It has no evidence verifier or candidate selector; optional README claims are not active code |
| [Quiptionary](https://github.com/praneethd2007-a11y/video-caption-agent-epso) | `main.py`; ten extracted frames, four-frame per-style Qwen3.7 Plus calls, no shared description in the Docker path | Direct visual style prompts with one concrete anchor | Sequential calls, no cross-style consistency check, and no repair stage |
| [TheSkyGold](https://github.com/TheSkyGold/track2-captioner) | Docker pins `CAPTION_ENGINE=pipeline`: Qwen2.5-VL description plus Gemma-3 style generation over eight frames | Evidence lock, optional audio/OCR, deterministic formal lane, and atomic output | The GPT/Gemini/Claude ensemble in `app/ensemble.py` is opt-in and not the default scored image |
| [Thoha](https://github.com/iiTzThoha/video-caption-agent) | `pipeline.py`; direct MiniMax video description followed by one JSON style call | Native video input can simplify temporal coverage | Three-to-four sentence outputs, single pass, and weak fallbacks are not robust enough for this contract |
| [DescribeX](https://github.com/Anushiv7/DescribeX) | `docker/entrypoint.py` → `CaptionEngine`; up to 16 uniformly sampled frames, one scene description, one multi-style text call | Clean engine/entrypoint separation and formatters | The Docker image has no pinned model IDs or baked API configuration, so it is not a directly reproducible leaderboard artifact |

The repeated pattern is therefore not “copy the current number one.” It is:
dense chronological evidence, an evidence lock/verification pass, independent
style writing, and a deterministic final quality gate. ClioGemma's r6/r8
candidates implement that common core while keeping provider roles explicit.

## Nondeterministic-score analysis

The supplied FAQ does not disclose the internal judge prompt or state that
repeated scoring of an identical output is random. The large swings in
ClioGemma's history cannot be attributed to judge randomness alone because
each submission also changed models, prompts, frame counts, temperatures, or
even the published image. A same-digest repeat would be the only clean way to
measure judge variance.

The practical defense is variance reduction, not blind resubmission:

1. Keep frame selection deterministic: fixed timestamps and deterministic scene
   metric tie-breaks, with no random sampling.
2. Make evidence and final selection temperature-zero or near-zero.
3. Generate style diversity before selection, then choose with a factual/style
   gate instead of shipping one high-temperature answer.
4. Keep captions short, concrete, and reference-shaped so a judge has a large
   margin to recognize the intended scene and tone.
5. Submit immutable digests and record the exact output configuration; never
   compare mutable `latest` tags.

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
| `score-max-r9-stable` | r8 architecture with deterministic stability profile | Near-zero evidence/final sampling; bounded creative temperature | Published immutable candidate; intended to reduce output variance, not a guaranteed score increase |
| `score-max-r10-gemma-stable` | Kimi K2.6 chronological grids with the same stability profile | Gemma 4 generates, selects, verifies, repairs, and emits every caption | Published single-submission candidate; no DeepSeek writer in the emitted path |

The r8 candidate is the closest source-derived analogue: the image model sees
the dense temporal grids, while a text model writes each style independently.
The r9 tag keeps that architecture but clamps evidence and final sampling to
near-zero and creative sampling to a bounded level. It targets our output
variance; it does not claim the hidden judge itself is deterministic.
For the single Track 2 submission, r10 is the recommended compromise: it keeps
Gemma as the load-bearing caption model while retaining the dense-grid and
Kimi-grounding improvements.

## Next experiment

The implementation phase is complete. Do not run another full public-set
benchmark merely to create activity. Submit the immutable r10 digest and record
the official score, then make the next change only from the evaluator's result.
