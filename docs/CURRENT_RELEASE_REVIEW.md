# Current release review - champion R1 candidate

**Updated:** 2026-07-12

**Track:** AMD Developer Hackathon ACT II, Track 2 - Video Captioning

**Production policy:** Novita provider; Gemma family only; no non-Gemma writer or separate judge

## Executive decision

Build and quality-test this new candidate before submitting:

`ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r1`

The latest confirmed ClioGemma score is **0.75**. The strongest confirmed
control is **0.85**, earned by the older four-frame `verified5` architecture.
The eight-frame pairs/selector experiment scored **0.59** and the concise
four-frame follow-up scored **0.72**. Local testing establishes contract,
runtime, and qualitative readiness; it does not prove a score above 0.92.

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

## Champion R1 architecture

```text
/input/tasks.json
  -> download, ffprobe, and chronological FFmpeg sampling
  -> four 768px chronological anchors
  -> Gemma 4 observer: scene, subjects, stable facts, timeline, scene story,
     conservative caption anchor, visible text, and do-not-claim ledger
  -> Gemma 4 second visual observer removes unsupported evidence
  -> four independent Gemma 4 persona calls with internal two-angle selection
  -> Gemma 4 final accuracy/style revision
  -> deterministic schema, length, style, and hallucination guard
  -> atomic /output/results.json after every completed task
```

Every model role is `google/gemma-4-31b-it` through Novita. There is no Claude,
Kimi, Gemini, audio model, external scoring judge, hardcoded evaluator answer,
or provider fallback in the image.

The separate hybrid diagnostic changes only the first evidence role to
`moonshotai/kimi-k2.6`; all caption writers and the final revision remain
Gemma 4. See [MODEL_AB_COMPARISON.md](MODEL_AB_COMPARISON.md).

## Improvements beyond the 0.85 image

1. **Champion style calibration:** preserves the original 0.85 path's detail
   and creative temperature, then asks Gemma to draft two internal angles and
   keep the sharper grounded survivor.
2. **Final grounding revision retained:** a second Gemma pass can shorten or
   correct a writer output, but only when it improves the evidence checks.
3. **Hallucination guard:** creative prompts reject invented numbers,
   durations, names, locations, props, and literal unseen outcomes; jokes must
   hinge on the visible action.
4. **Stock-style rejection:** generic tech and non-tech fallback formulas are
   rejected during normal style validation, not only in the old pair experiment.
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

Exact balanced source on all eight retired AMD videos:

- 8/8 tasks
- 32/32 requested captions
- valid style keys and non-empty values
- exit code 0
- 310.5 seconds at task parallelism two
- no provider or schema failures

Published artifact validation:

- public Linux/amd64 OCI manifest
- anonymous registry request: HTTP 200
- pulled digest: `sha256:9dcc777f1e80256fecee64fbfa3f105f549e5b0e38c3f9100098ec21fefe824f`
- judge-style run with no source mount and no environment override
- 2/2 retired tasks, 8/8 captions, valid schema, exit code 0

## Score assessment

The champion image is a controlled attempt to recover the 0.85 Gemma-only
architecture after the 0.75 submission. It keeps four-frame evidence and adds
internal best-of-two drafting, stock-style rejection, anchor-preserving
fallbacks, and a final accuracy/style pass.

There is still no defensible way to simulate the hidden AMD score exactly. The
hidden clips, reference expectations, judge prompt, weighting, and stochastic
provider behavior are unavailable. A reasonable pre-submission expectation is
**0.82-0.90**. A 0.93 result remains the target, not a forecast; only the hidden
AMD judge can establish it.

## Next experiment policy

1. Build and quality-test `gemma4-champion-r1`, then submit that immutable tag
   once and record its digest and score.
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
- [x] Novita-only and Gemma-only production roles enforced.
- [x] Repository tests and compilation pass.
- [x] All eight retired validation clips pass within the 570-second budget.
- [x] Immutable public tag pushed.
- [x] Anonymous pull access and manifest digest verified.
- [x] Exact published balanced image passes a mounted input/output smoke test.
- [ ] Submit the exact tag and record the official score.
