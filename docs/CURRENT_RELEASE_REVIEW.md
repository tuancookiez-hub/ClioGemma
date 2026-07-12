# Current release review - source-derived R6/R8 candidates

**Updated:** 2026-07-13

**Track:** AMD Developer Hackathon ACT II, Track 2 - Video Captioning

**Production policy:** Novita provider; immutable, separately tagged candidates; no separate external judge

## Executive decision

There are two separately tagged candidates:

Gemma-track control: `ghcr.io/tuancookiez-hub/cliogemma:score-max-r6-grid`

Digest: `sha256:2d7eac8954a5a8831608886f6398084086d82ac8016c228e8cc5d51f4f1154e8`

Source-derived broad Track 2 candidate: `ghcr.io/tuancookiez-hub/cliogemma:score-max-r8-qwen-deepseek`

Digest: `sha256:e10362b03f5527a6a32e31119331f2a3ecee78bf60cbc8c04cb7e04775b19418`

The latest confirmed ClioGemma score is **0.77**. The strongest confirmed
control is **0.85**, earned by the older four-frame `verified5` architecture.
The eight-frame pairs/selector experiment scored **0.59** and the concise
four-frame follow-up scored **0.72**. Local testing establishes contract,
runtime, and qualitative readiness; it does not prove a score above 0.92.
The score-max r5 image completed all eight retired clips in 351.2 seconds,
with 32/32 captions and anonymous GHCR manifest HTTP 200 verification.

## Official score history

| Image | Material configuration | Official score |
|---|---|---:|
| `gemma3-5frames` | Gemma 3, five frames, one call | 0.66 |
| `gemma3-5frames-p2-r1` | Same caption path with bounded retries and parallelism two | 0.68 |
| `gemma4-4f-verified5-p2-r1` | Four-frame evidence, verification, direct personas, final revision | 0.85 |
| `gemma4-4f-verified5-p2-r2` | Sarcasm cleanup variant | Result not recorded in this repository |
| `gemma4-8f-pairs-picker-p2-r1` | Eight-frame evidence, two candidates per style, visual selection | **0.59** |
| `gemma4-4f-verified5-concise-p2-r1` | Four-frame verified5 path, concise style calibration, final revision | **0.72** |
| `gemma4-4f-verified5-balanced-p2-r2` | Four-frame verified5 path, restored detail/temperature, style quality guard | Pending |
| `gemma4-4f-kimi-grounded-p2-r3` | Kimi K2.6 evidence, Gemma writers/final revision | Pending |
| `gemma4-champion-r1` | Gemma-only four-frame path with internal best-of-two drafting, stock rejection, anchor-preserving fallbacks, and final accuracy/style revision | Pending |
| `gemma4-champion-r6` | Gemma-only four-frame batch writer with label normalization | Pending |
| `gemma4-kimi-batch-r1` | Kimi eight-frame evidence, Gemma verification, Gemma batch writing and final revision | Pending |
| `gemma4-reference-r3` | Kimi five-frame dense evidence, dedicated reference-calibrated Gemma writers, targeted deterministic gates, no global rewrite | **0.77** |
| `score-max-r5` | Scene-aware six frames, OCR hints, Kimi evidence plus two candidates per style, Gemma verification/selection/repair | Pending |
| `score-max-r6-grid` | Up-to-16-frame chronological 4x4 grids, Kimi evidence, Gemma verification/selection/repair | Not yet scored |
| `score-max-r8-qwen-deepseek` | Qwen3.5 chronological grids, Gemma verification/final grounding, DeepSeek V4 Pro style drafting | Not yet scored |

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

## Failed 0.59 experiment

The eight-frame pairs/selector branch changed too many variables at once:
more frames, two candidates per style, a visual selector, higher creative
temperature, and removal of the proven final grounding revision. Its local
outputs were valid, but the official **0.59** score shows that local contract
success is not enough. The likely failure mode is verbose or over-clever prose
that missed the hidden judge's preference for short, directly visible captions.

## Source-derived candidate architecture

```text
/input/tasks.json
  -> download, ffprobe, and chronological scene-aware sampling
  -> up to 16 frames are packed into labelled 4x4 contact sheets
  -> Kimi K2.6 (r6) or Qwen3.5 (r8) records scene, subjects, facts, timeline,
     visible text, and a do-not-claim ledger
  -> Gemma 4 verifies evidence and performs final grounding
  -> r6 keeps Gemma for selection and repair; r8 uses DeepSeek V4 Pro for
     independent style drafting before Gemma's final grounding pass
  -> deterministic schema, length, style, and hallucination guard
  -> atomic /output/results.json after every completed task
```

All provider calls use Novita. r6 is the Gemma-track control; r8 is the
source-derived broad Track 2 candidate. There is no Claude, audio model,
external scoring judge, or hardcoded evaluator answer.

## Improvements beyond the 0.85 image

1. **Score-max candidate architecture:** Kimi supplies two visual candidates
   per style, while Gemma 4 makes the final evidence-grounded choice.
2. **Scene-aware sampling and OCR:** six frames are chosen from stable anchors
   plus high-motion transitions; optional local OCR supplies corroborating text
   without making text alone a factual claim.
3. **Issue-triggered repair:** deterministic checks for unsupported counts,
   brands, process leakage, stock jokes, and style failures trigger one Gemma
   repair pass instead of silently shipping a weak caption.
4. **Resilient JSON parsing:** provider responses with explanatory text or
   fenced JSON are decoded without losing the valid object.
5. **Champion style calibration:** preserves the original 0.85 path's detail
   and creative temperature, then asks Gemma to draft two internal angles and
   keep the sharper grounded survivor.
6. **Final grounding revision retained:** a second Gemma pass can shorten or
   correct a writer output, but only when it improves the evidence checks.
7. **Hallucination guard:** creative prompts reject invented numbers,
   durations, names, locations, props, and literal unseen outcomes; jokes must
   hinge on the visible action.
8. **Stock-style rejection:** generic tech and non-tech fallback formulas are
   rejected during normal style validation, not only in the old pair experiment.
9. **Peripheral-text protection:** proper names and exact sign text cannot enter
   a caption merely because OCR placed them in `visible_text`. This was added
   after a real frame check caught an incorrect background business name.
10. **Partial-result resilience:** valid results are written atomically after
   each task, so a later timeout does not erase earlier captions.
11. **Reproducible image settings:** model roles, pipeline, frame count, frame
   width, task parallelism, request timeout, and clip timeout are embedded in
   the published image.

## Exact validation evidence

Repository validation:

- `python -m pytest tests -q`: 9 passed
- `python -m compileall -q app tests`: passed
- `git diff --check`: passed

Source-derived candidate runs on all eight retired AMD videos:

- 8/8 tasks
- 32/32 requested captions
- valid style keys and non-empty values
- exit code 0
- r5 baseline: 351.2 seconds at task parallelism two
- r6 grid: 8/8 and 32/32 within the 570-second contract
- r8 Qwen/DeepSeek: 8/8 and 32/32 in 272.3 seconds at task parallelism three
- no empty outputs or schema failures

Published artifact validation:

- public Linux/amd64 OCI manifest
- anonymous registry request: HTTP 200
- r6 digest: `sha256:2d7eac8954a5a8831608886f6398084086d82ac8016c228e8cc5d51f4f1154e8`
- r8 digest: `sha256:e10362b03f5527a6a32e31119331f2a3ecee78bf60cbc8c04cb7e04775b19418`
- judge-style run with no source mount and no environment override
- 8/8 retired tasks, 32/32 captions, valid schema, exit code 0

## Score assessment

The source-derived r6/r8 candidates address the leader's two largest gaps:
dense chronological contact sheets and independent style writers. This is
architectural evidence, not a forecast of the hidden score. The exact AMD
judge remains the only source of an official 0.93+ result.

There is still no defensible way to simulate the hidden AMD score exactly. The
hidden clips, reference expectations, judge prompt, weighting, and stochastic
provider behavior are unavailable. The 31/32 public-set advantage is meaningful
regression evidence, but it is not a calibrated numerical forecast. A 0.93 result
remains the target; only the hidden AMD judge can establish it.

## Next experiment policy

1. Pick one immutable tag: r6 for Gemma-track eligibility, or r8 for the
   source-derived broad Track 2 route, and record its digest and official score.
2. Do not mutate this tag. Every later experiment gets a new tag.
3. If the score is below 0.90, inspect whether the failure is accuracy, style,
   or incomplete outputs before changing architecture. Do not resubmit the same
   tag hoping the score changes.
4. If the score is 0.90-0.92, preserve evidence and runtime; vary one creative
   factor at a time, starting with the sarcasm and non-tech candidate prompts.
5. If it exceeds 0.92, keep it as the control and make only evidence-backed
   attempts at 0.93-plus.
6. Record tag, digest, Git commit, model, frame settings, parallelism, timestamp,
   official score, and evaluator error for every submission.

## Release checklist

- [x] Track 2 input/output contract preserved.
- [x] Linux/amd64 entrypoint and exact requested style keys preserved.
- [x] Novita-only provider and separate Gemma-track versus broad Track 2 roles documented.
- [x] Repository tests and compilation pass.
- [x] All eight retired validation clips pass within the 570-second budget.
- [x] Immutable public tag pushed.
- [x] Anonymous pull access and manifest digest verified.
- [x] Published r6 and r8 images pass the full eight-clip mounted input/output test.
- [ ] Submit the exact tag and record the official score.
