# Champion R1: evidence-based score recovery

**Updated:** 2026-07-12  
**Track:** AMD Developer Hackathon ACT II, Track 2

> Current release: `score-max-r5`. This document retains earlier champion
> experiments as score history; the scene-aware Kimi/Gemma ensemble at the end
> is the active submission candidate.

## Why the previous candidate failed

The official score sequence is more informative than any single model claim:

| Candidate family | Official score | Interpretation |
|---|---:|---|
| Gemma 3, five frames | 0.66–0.68 | Basic generation and retries were not enough. |
| Gemma 4, four-frame verified path | 0.85 | The strongest confirmed control. |
| Gemma 4, eight-frame pairs/selector | 0.59 | More frames and a selector can hurt when captions become verbose or generic. |
| Gemma 4 concise variant | 0.72 | Over-compression removed useful scene detail. |
| Latest submitted candidate | 0.77 | The reference-calibrated Kimi/Gemma image remained below the 0.85 control. |

The strict self-check proxy also found two concrete failure modes in the current
outputs: generic `humorous_tech` fallbacks for traffic/cooking and formal captions
that sometimes lost the verified subject/action anchor. Those are high-leverage
because the official score averages all four styles.

## Research-derived design decision

The public [Yash video-captioning repository](https://github.com/yash-kumarx/amd-hackathon-video-captioning)
describes a useful pattern: visual grounding, then Gemma-owned styled generation,
internal best-of-N selection, judge-style reranking, and critique/repair. The
repository keeps Gemma as the load-bearing language model even when Kimi performs
visual grounding. We apply the safe part of that pattern while preserving our
proven Gemma-only four-frame control.

The score-max profile is now the active submission. The Gemma-only four-frame
profile remains a control, while `hybrid-kimi8` and earlier aliases are retained
only for historical A/B comparison.

## Implemented changes

1. `verified5-champion` aliases preserve the four chronological Gemma evidence
   frames, second observer, independent style writers, and final revision.
2. Balanced writer prompts now instruct Gemma to draft two internal angles and
   return the sharper grounded survivor; no extra candidate text is emitted.
3. The final revision prompt privately scores accuracy and style, preserving a
   specific caption instead of genericizing it.
4. Stock phrases are rejected during the normal style checks, not only during
   experimental pair selection.
5. Deterministic fallbacks retain the verified anchor and use a scene-grounded
   technical or everyday comparison rather than the old generic formulas.
6. Final captions are normalized for leading capitalization.
7. `hybrid-kimi8` uses eight chronological frames for Kimi evidence and a Gemma
   verification pass, so it can be tested separately without changing the
   Gemma-only profile.

## Build candidate

```powershell
docker buildx build --platform linux/amd64 `
  --provenance=false --sbom=false `
  --build-arg CLIO_API_KEY="$env:NOVITA_API_KEY" `
  --build-arg CLIO_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_VERIFY_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_CAPTION_MODEL=google/gemma-4-31b-it `
  --build-arg CLIO_PIPELINE=verified5-champion `
  --build-arg SWIFTCLIP_FRAME_COUNT=4 `
  --build-arg SWIFTCLIP_FRAME_WIDTH=768 `
  --build-arg SWIFTCLIP_PARALLEL=2 `
  --tag ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r1 `
  --push .
```

For the optional A/B image, change only the pipeline to `hybrid-kimi8`, frame
count to `8`, and use `CLIO_VISION_MODEL=moonshotai/kimi-k2.6`.

The checked-in PowerShell wrapper performs the same build without multiline
escaping mistakes:

```powershell
.\scripts\build_champion.ps1 -Push
```

## Verification status

- Repository tests: 7 passed.
- Python compilation and diff check: passed.
- Local Docker contract smoke: 8 tasks, 8 non-empty four-style result objects.
- The smoke used a deliberately invalid key, so it validates container and
  fallback behavior only; it is not a quality score.
- A real quality smoke requires the user-supplied Novita key in the shell and
  should be run on all eight retired examples before submission.

## Score expectation

This is a measured recovery candidate, not a guaranteed 0.93. The previous 0.77
means the hidden judge is stricter than a lenient Gemma proxy. The immediate goal
is to recover and exceed the confirmed 0.85 control; only an official submission
can establish whether the additional style selection is enough to approach 0.93.

## Live self-check results

The exact published variants completed all eight retired clips with valid output:

| Tag | Frames | Runtime | Strict Kimi proxy | Notes |
|---|---:|---:|---:|---|
| `gemma4-champion-r1` | 4 | 309.5 s | 0.708 (earlier proxy) | Generic tech fallbacks remained. |
| `gemma4-champion-r2` | 4 | 191.6 s | 0.728 | Cleaner fallbacks; style remained conservative. |
| `gemma4-champion-r3` | 8 | 326.7 s | not used as final control | More temporal detail, but transient-action drift appeared. |
| `gemma4-champion-r6` | 4 | 247.2 s | 0.723 | Gemma batch writer; label leakage fixed. |
| `gemma4-kimi-batch-r1` | 8 | 269.8 s | **0.759** | Kimi evidence plus Gemma batch writer/final revision; strongest local candidate. |
| `gemma4-reference-r3` | 5 | **140.4 s** | official **0.77** | Dense Kimi facts, dedicated Gemma style writers, reference-calibrated prompts, no flattening global rewrite. |
| `score-max-r5` | 6 scene-aware | **351.2 s** | Pending official | OCR hints, Kimi evidence plus two candidates per style, Gemma verification/selection/repair, full eight-clip contract pass. |

The Gemma proxy gave much higher values (0.96+), so proxy judges are not
calibrated to AMD's hidden evaluator. The strongest candidate to test officially
is `score-max-r5`; retain `gemma4-champion-r6` as the Gemma-only control. Local
retired-set results are regression evidence, not an AMD score prediction.
