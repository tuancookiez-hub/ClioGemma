# Current release review - verified7 candidate

**Updated:** 2026-07-12

**Track:** AMD Developer Hackathon ACT II, Track 2 - Video Captioning

**Production policy:** Novita provider; Gemma family only; no non-Gemma writer or separate judge

## Executive decision

Submit this exact immutable image next:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-8f-pairs-picker-p2-r1`

Manifest digest:

`sha256:b0f2f7040b94b0cb7a994c5ebea5ff08d85e8addc759d494009581765ef7d026`

The confirmed ClioGemma score is **0.85**, earned by the older four-frame
`verified5` architecture. The new `verified7` artifact is materially different
and has not yet been measured by AMD. Local testing establishes contract,
runtime, and qualitative readiness; it does not prove a score above 0.92.

## Official score history

| Image | Material configuration | Official score |
|---|---|---:|
| `gemma3-5frames` | Gemma 3, five frames, one call | 0.66 |
| `gemma3-5frames-p2-r1` | Same caption path with bounded retries and parallelism two | 0.68 |
| `gemma4-4f-verified5-p2-r1` | Four-frame evidence, verification, direct personas, final revision | 0.85 |
| `gemma4-4f-verified5-p2-r2` | Sarcasm cleanup variant | Result not recorded in this repository |
| `gemma4-8f-pairs-picker-p2-r1` | Eight-frame evidence, two candidates per style, visual selection | Pending |

The jump from 0.68 to 0.85 proves that caption architecture and style identity
matter much more than retry tuning alone. The remaining target is at least 0.93.

## Evidence from public high-scoring systems

The findings below are architectural observations, not code copied into
ClioGemma. GitHub branches and mutable container tags are not guaranteed to be
the exact historical leaderboard artifacts.

| System | Reported score | Useful production lesson |
|---|---:|---|
| [Stryvo Vision](https://github.com/StrvyoLabs/Stryvo-Vision) | 0.88 | Dense visual grounding followed by independent style generation |
| [Raccoon Vision Translator](https://github.com/Showraiser/Raccoon-Vision-Translator) | 0.88 | Visual verification and sequential persona writers |
| [Yash video captioner](https://github.com/yash-kumarx/amd-hackathon-video-captioning) | 0.91 | Eight-frame chronological story, candidate pools, frame-aware selection; inspected image used mixed providers, so only structural ideas were transferred |
| [ProVision V2](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/meowvision/provision-v2) | 0.92 | Three-frame description, verification, then separate style writers |
| [Quiptionary](https://github.com/praneethd2007-a11y/video-caption-agent-epso) | 0.92 | Direct visual generation per style with strong, unmistakable persona prompts |

Repeated signal: accuracy requires chronological visual facts, while the style
score requires each requested tone to be generated independently rather than
as four compromises in one response.

## Verified7 architecture

```text
/input/tasks.json
  -> download, ffprobe, and chronological FFmpeg sampling
  -> eight 768px anchors
  -> Gemma 4 observer: scene, subjects, stable facts, timeline, scene story,
     conservative caption anchor, visible text, and do-not-claim ledger
  -> Gemma 4 second visual observer removes unsupported evidence
  -> four independent Gemma 4 persona calls
       -> Candidate A: polished, literal-first, reliable
       -> Candidate B: different construction, sharper but still grounded
  -> Gemma 4 visual selector compares all candidates against six anchors
  -> deterministic exact-candidate, schema, length, style, and stock-phrase guard
  -> atomic /output/results.json after every completed task
```

Every model role is `google/gemma-4-31b-it` through Novita. There is no Claude,
Kimi, Gemini, audio model, external scoring judge, hardcoded evaluator answer,
or provider fallback in the image.

## Improvements beyond the 0.85 image

1. **Temporal coverage:** eight anchors replace four and produce a two-sentence
   beginning-to-end scene story.
2. **Candidate diversity:** each style receives two alternatives instead of one,
   allowing the system to trade off accuracy and creative strength.
3. **Frame-aware selection:** the selector sees six chronological images and the
   verified evidence rather than judging prose alone.
4. **Less repetitive humor:** stock openings and generic 404, legacy-code,
   Monday, chores, dinner, kitchen, and snack formulas are discouraged and
   mechanically penalized during tie-breaking.
5. **Peripheral-text protection:** proper names and exact sign text cannot enter
   a caption merely because OCR placed them in `visible_text`. This was added
   after a real frame check caught an incorrect background business name.
6. **Partial-result resilience:** valid results are written atomically after
   each task, so a later timeout does not erase earlier captions.
7. **Reproducible image settings:** model roles, pipeline, frame count, frame
   width, task parallelism, request timeout, and clip timeout are embedded in
   the published image.

## Exact validation evidence

Repository validation:

- `python -m pytest tests -q`: 6 passed
- `python -m compileall -q app tests`: passed
- `git diff --check`: passed

Exact final source on all eight retired AMD videos:

- 8/8 tasks
- 32/32 requested captions
- valid style keys and non-empty values
- exit code 0
- 218.4 seconds at task parallelism two
- no provider, selector, or schema failures

Published artifact validation:

- public Linux/amd64 OCI manifest
- anonymous registry request: HTTP 200
- pulled digest: `sha256:b0f2f7040b94b0cb7a994c5ebea5ff08d85e8addc759d494009581765ef7d026`
- judge-style run with no source mount and no environment override
- 2/2 retired tasks, 8/8 captions, valid schema, exit code 0
- 103.3 seconds

## Score assessment

The new image is a credible attempt to move from 0.85 into the 0.90-plus range,
because it directly addresses the largest observed weaknesses: limited temporal
coverage, single-shot persona writing, generic repeated jokes, and prose-only
selection. It also retains a large runtime margin.

There is still no defensible way to simulate the hidden AMD score exactly. The
hidden clips, reference expectations, judge prompt, weighting, and stochastic
provider behavior are unavailable. A reasonable pre-submission expectation is
roughly **0.88-0.93**, with a real but not high-confidence chance of exceeding
0.92. A 0.95 claim would be speculation until an official score demonstrates it.

## Next experiment policy

1. Submit only `gemma4-8f-pairs-picker-p2-r1` and record its digest and score.
2. Do not mutate this tag. Every later experiment gets a new tag.
3. If the score is below 0.90, inspect whether the failure is accuracy, style,
   or incomplete outputs before changing architecture.
4. If the score is 0.90-0.92, preserve evidence and runtime; vary one creative
   factor at a time, starting with the sarcasm and non-tech candidate prompts.
5. If it exceeds 0.92, keep it as the control and make only evidence-backed
   attempts at 0.93-plus.
6. Record tag, digest, Git commit, model, frame settings, parallelism, timestamp,
   official score, and evaluator error for every submission.

## Release checklist

- [x] Track 2 input/output contract preserved.
- [x] Linux/amd64 entrypoint and exact requested style keys preserved.
- [x] Novita-only and Gemma-only production roles enforced.
- [x] Repository tests and compilation pass.
- [x] All eight retired validation clips pass within the 570-second budget.
- [x] Immutable public tag pushed.
- [x] Anonymous pull access and manifest digest verified.
- [x] Exact published image passes a mounted input/output smoke test.
- [ ] Submit the exact tag and record the official score.
