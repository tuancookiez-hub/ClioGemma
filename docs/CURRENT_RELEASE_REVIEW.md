# Current release review - score recovery plan

**Updated:** 2026-07-12

**Track:** AMD Developer Hackathon ACT II, Track 2 - Video Captioning

**Production policy:** Novita provider; Gemma family only; no separate judge

## Executive decision

Do not resubmit the old fast image. Its official score moved from **0.66** to
only **0.68** after concurrency and 429 handling were fixed. The +0.02 gain
shows that rate limiting was real but not the dominant cause. The large
remaining gap is architectural: one multimodal call was being asked to both
understand the video and write four conflicting tones.

The next submission should be the `verified5` Gemma 4 candidate documented
below. It is contract-valid and has passed real-video Docker-style tests, but a
score above 0.92 is not a fact until the AMD evaluator measures the exact
published digest.

## Official score history

| Image | Material configuration | Official score |
|---|---|---:|
| `gemma3-5frames` | Gemma 3, five frames, one call, higher concurrency | 0.66 |
| `gemma3-5frames-p2-r1` | Same quality path, parallelism two, bounded 429/5xx retry | 0.68 |
| `gemma4-4f-verified5-p2-r1` | Verified evidence plus direct multimodal personas | Pending |

The first two rows prove that operational reliability alone cannot close a
0.24 gap to the 0.92 leader.

## What the public competitors actually do

The GitHub repositories are not always the submitted artifacts. The findings
below come from both public source and the public Docker images.

| System | Reported score | Production pattern | Main limitation |
|---|---:|---|---|
| [Stryvo Vision](https://github.com/StrvyoLabs/Stryvo-Vision) | 0.88 | 12 frames, one dense visual description, four independent style rewrites with few-shots | No second visual verification |
| [Raccoon Vision Translator](https://github.com/Showraiser/Raccoon-Vision-Translator) | 0.88 | 4-6 frames, Gemma 4 description, visual verification, separate sequential style writers, text-only QC | QC does not recheck frames; many calls and optional audio add failure surface |
| [ProVision V2](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-ii/meowvision/provision-v2) | 0.92 | Three frames, Kimi K2P6 description, visual verification, sequential style writers with prior-caption diversity | Public tag provenance is not cryptographically bound to the score |
| [Quiptionary](https://github.com/praneethd2007-a11y/video-caption-agent-epso) | 0.92 | Four frames sent directly to Qwen3.7 Plus once per style, strong persona prompts, temperature 0.7 | Minimal grounding and sequential runtime, but excellent style identity |

The consistent signal is **one generation per style with a strong voice**.
Verification helps accuracy, but Quiptionary proves that distinctive persona
prompts plus concrete visual details can reach 0.92 without a separate evidence
stage. The new candidate combines both lessons.

## ProVision image legitimacy

The public Docker Hub tag
[`track2-provision-kimi-3frames-cleanup-beta`](https://hub.docker.com/r/somnuskai/amd-track2-captioner/tags?name=track2-provision-kimi-3frames-cleanup-beta)
is a real, pullable, unobfuscated Linux image. The source contains a normal
Track 2 harness and no hardcoded evaluator answers.

Live metadata checked on 2026-07-11:

- Tag digest: `sha256:f747f459e5631b0c2c381d6436e9003971aa21eeddc3a472687b919738e1b633`
- Linux/amd64 manifest: `sha256:806fbc48ca2e81a3e0b6ba39cce3b0f617178de0bf61240bae126c7feed8656e`
- Last pushed: `2026-07-10T22:28:22Z`
- Image source/defaults: Kimi K2P6, three frames, visual draft then visual verification, four sequential style calls, checks disabled

There is no evidence that the owner replaced the image to sabotage copying.
The digest remained stable during this review. However, Docker tags are
mutable and the leaderboard does not publish the evaluated digest, so no one
outside the organizer can prove that the current tag is byte-for-byte the
artifact that earned 0.92. The README inside the image still mentions 0.91 and
an older tag, which is consistent with stale documentation but is not proof of
tampering.

The public project page labels Gemini 3 Flash while the image defaults to Kimi
K2P6. Treat the image configuration as evidence of runtime behavior and the
project-page technology label as presentation metadata.

## New ClioGemma architecture

```text
/input/tasks.json
  -> download and ffprobe
  -> four chronological FFmpeg anchors (896px)
  -> Gemma 4 observer: structured scene, subjects, facts, timeline,
     caption anchor, visible text, and do-not-claim ledger
  -> Gemma 4 second visual observer: correct unsupported evidence
  -> four direct multimodal persona writers, each seeing the frames and
     verified evidence; formal uses low temperature and creative styles 0.82
  -> deterministic style checks and one bounded repair when needed
  -> one final Gemma 4 revision against the original images and verified facts
  -> exact requested keys in /output/results.json
```

What is new beyond the public 0.92 pattern:

1. A structured negative-evidence ledger tells every writer what not to claim.
2. Each creative caption retains a real video detail but may use the bold,
   clearly figurative motives and mini-scenarios rewarded by AMD's examples.
3. The final revision sees the original frames; Raccoon's QC sees only prose,
   and ProVision's shipped `RUN_CHECKS=false` path has no active final gate.
4. Mechanical checks reject process leakage, missing sarcasm cues, missing or
   awkward tech analogies, and technical terms in the non-tech style without
   suppressing obvious figurative humor.
5. A slow individual call no longer erases every caption for that clip. Timeouts
   are retried once within the clip deadline, and completed evidence is retained.

The new official FAQ supersedes the earlier hidden-count and per-request
wording. It publishes eight retired validation clips but does not disclose the
new hidden-set count. Provider calls use a 40-second timeout inside a 570-second
container budget.

All model roles remain Gemma 4 on Novita. No separate judge or non-Gemma writer
is introduced.

## Current test evidence

The current source passed:

- `python -m pytest tests -q`: 6 passed
- `python -m compileall -q app tests`
- `git diff --check`
- Gemma 4 text probe: 3.6 seconds
- Gemma 4 image probe: 5.4 seconds
- All eight AMD retired validation clips: 8/8 tasks, 32/32 captions, exit 0,
  367.7 seconds at parallelism two, including one recovered provider timeout

The official-example outputs contained specific visible details and much
stronger personas than the 0.68 path. Markdown emphasis and a weak rare
sarcasm recovery were corrected before the final run.

## Can this exceed 0.92?

It is possible, but not yet measurable with high confidence. The strongest
evidence in favor is that the candidate now contains every repeated structural
feature of the 0.88-0.92 systems and adds frame-aware final correction. The
strongest evidence against certainty is that ProVision uses Kimi K2P6, and the
AMD judge and hidden clips are unavailable locally.

A reasonable pre-submission assessment is:

- High confidence the candidate beats the old 0.68 path if the public key and
  endpoint remain healthy.
- Moderate confidence it reaches the high 0.80s or low 0.90s.
- Low-to-moderate confidence it exceeds 0.92 on the first submission.
- No honest basis yet for claiming 0.95.

The official score is the only calibration signal that can turn those ranges
into evidence.

## Submission experiment order

Do not mutate tags. Publish a new immutable tag for every experiment and record
its manifest digest.

1. `gemma4-4f-verified5-p2-r1` - full candidate; submit first.
2. If accuracy is high but style appears weak, change only creative temperature
   or the humorous-tech prompt.
3. If temporal facts are wrong, test five anchors while keeping the model and
   prompts fixed.
4. If timeouts/fallbacks appear, lower parallelism from two to one without
   changing prompts.
5. Keep the best official score; do not infer gains from local prose alone.

For every submission record: tag, digest, Git commit, frame count, model roles,
parallelism, timestamp, score, and observed evaluator error.

## Release checklist

- [x] Required `/input/tasks.json` to `/output/results.json` contract preserved.
- [x] Linux/amd64 entrypoint preserved.
- [x] Requested style keys preserved exactly.
- [x] Six repository tests pass.
- [x] Real Gemma 4 text and image calls pass.
- [x] All eight official retired validation clips pass within 570 seconds.
- [ ] Commit and push this candidate source.
- [ ] Build and push the exact public `gemma4-4f-verified5-p2-r1` image.
- [ ] Pull anonymously and verify its linux/amd64 digest.
- [ ] Run the exact published image against mounted input/output.
- [ ] Submit the exact registry reference and record the official score.
