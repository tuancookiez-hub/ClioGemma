# Current release review

**Track:** AMD Developer Hackathon ACT II, Track 2 - Video Captioning  
**Model policy:** Novita + Gemma 4 31B or Gemma 3 27B only  
**Judge policy:** no local or external judge in the production image

## Decision

The reconstructed release is packageable after a Novita one-clip smoke and a
linux/amd64 Docker smoke. A `0.92+` score is plausible but not proven by the
current tree. Historical local development evidence was approximately `0.871`
for the old Gemma single-call baseline; previous `0.900`/`0.905` diagnostics
used a non-Gemma writer/rewriter and cannot be claimed as production scores.
The leaderboard submission is the decisive measurement.

## Participant-guide contract

The attached guide requires a public Docker image, startup reading
`/input/tasks.json`, valid `/output/results.json`, every requested style, exit
code zero, a 10-minute total runtime, a public `linux/amd64` image, and no
hardcoded answers. The hidden set is about 12 clips, roughly 30 seconds to two
minutes each. General rules state that startup must be under 60 seconds and a
request must stay under 30 seconds. Submissions are limited to 10 per hour.
Track 2 permits any model/provider, but this release intentionally narrows the
provider to Novita and the two verified Gemma IDs above.
The guide also says no API key or model restriction is injected for Track 2,
which is why the submission build accepts a credential as a build argument;
use a restricted key and rotate it after the run.

There is a documentation discrepancy to resolve before publishing: the
current public event page describes Track 2 as using Fireworks credits and an
LLM judge, while the attached Participant Guide is the local contract used for
this package and does not impose that provider restriction. Treat the guide
and the platform's live submission validator as authoritative for eligibility.
The image contains no judge; the AMD/lablab evaluator remains external.

## Production flow

```text
Dockerfile -> app.visual.run -> download -> ffprobe/ffmpeg
  -> five anchors at 5%, 27.5%, 50%, 72.5%, 95%
  -> one structured Novita Gemma request for all four styles
  -> /output/results.json
```

Every model call uses the same Novita Gemma model. The release path has no
post-selection rewrite or external judge. The only operational fallback is a
deterministic schema-preserving caption if an individual clip cannot be
processed; this prevents malformed output from scoring zero while never
introducing another provider.

The default release model is now Gemma 3 27B because a live one-call smoke
returned in about 10 seconds; Gemma 4 31B remained an explicit A/B variant but
hit repeated 25-second read timeouts during the same check. The release image
therefore uses one structured Gemma call per clip for reliability. The former
evidence/candidate path remains in the source only for later A/B
testing; it is not selected by the Docker image. The default request timeout
is 25 seconds. Three clips run concurrently and
each clip has a 125-second budget, giving approximately four waves for the
guide's 12-clip hidden set. If measured tail latency fails the 10-minute gate,
the first rollback is a single structured Gemma call per clip.

### Latest no-judge smoke

On 2026-07-11, the default fast path generated all four non-empty style strings
for the official urban example clip using `google/gemma-3-27b-it` through
Novita in 7.3 seconds. The same 11-call evidence path reached its parallel
reports but timed out during consensus for both Gemma 4 31B and Gemma 3 27B;
it is therefore not the release default. This is a generation/contract smoke,
not a quality score. The same 27B fast path was then run inside the built
linux/amd64 Docker image with a mounted `/input` and `/output`; it exited zero
and produced all four non-empty keys. The container run used a real Novita key
locally; the key is not present in the tree or this document.

## Competitor comparison

The public [ClipTone repository](https://github.com/gulsherx11/Video-Captioning-Agent)
uses the same required `/input` to `/output` Docker contract, three concurrent
clips, evenly spaced frames, one structured vision call for all four styles,
and a self-evaluation/regeneration loop. It also documents a primary/fallback
Fireworks chain and Groq Whisper audio. Its README build command targets a
public `linux/amd64` image. The current release adopts its packaging discipline
and single-structured-output principle, while staying inside the requested
Novita/Gemma-only policy and avoiding external audio/judge models.

## Score history and limitations

The earlier 32-clip holdout was a development proxy repeatedly inspected while
changing prompts, so it is not an untouched test set. The official guide says
the final score is a weighted average of accuracy and style, but does not
publish the weights. Local means are directional only.

| Evidence | Score | Compliant with this release? |
|---|---:|---|
| Old Gemma-only single-call baseline | 0.8711 | Yes, historical |
| Claude-assisted r3 diagnostic | 0.9000 | No |
| Claude style-gate r4 diagnostic | 0.9055 | No |
| Current reconstructed pipeline | not measured | Pending Novita smoke/leaderboard |

Known remaining errors are unsupported temporal direction, completed actions
inferred from hand position, unstable counts/posture, proper names, motives,
and weak creative jokes. The evidence ceiling and immutable selector target
those errors, but no local judge can certify a hidden score.

## Release checklist

- [ ] Set `NOVITA_API_KEY` to a restricted/revocable key (rotate the keys
      previously shared in chat first).
- [x] Run one-clip generation smoke; inspect all four captions.
- [x] Run `python -m pytest -q` (`3 passed`).
- [x] Build `linux/amd64` with Docker (`cliogemma-release-audit:latest`) and
      inspect the image as `linux/amd64`.
- [x] Run a mounted input/output container smoke with the real Novita key;
      exit code zero and all four non-empty style keys were observed.
- [ ] Run a final mounted input/output smoke after publishing the exact public
      image tag.
- [x] Confirm output JSON count, task ID, requested style keys, and non-empty
      strings on the one-task smoke.
- [ ] Push the exact public registry tag; submit a registry reference, not a
  web URL.
- [ ] Record each of the 10 hourly submissions with model, frames, tag,
  timestamp, and returned leaderboard score. Change one variable at a time.

Suggested submission ladder: start with the verified Gemma 3 27B/5-frame
release; then test a separate Gemma 3 27B/3-frame tag inspired by the public
ProVision image, followed by 4 and 8 anchors. Test Gemma 4 31B only as
a single-call A/B image and keep it only if its measured request latency stays
under the guide's 30-second request limit. Do not submit the timed-out
multi-pass evidence path.

## Repository state

This tree was reconstructed after a local working-tree deletion. The old
benchmark JSON, holdout media, and Git metadata must be restored from the
user's backup before a third-party review that depends on exact historical
artifacts. Do not present reconstructed scores as fresh measurements. The
production source is now intentionally small: `Dockerfile`, `app/visual.py`,
`app/core/`, and `app/evidence_pipeline.py`.

## Win assessment

Beating `0.91` remains possible, but `0.92+` cannot be promised before the
leaderboard tests this exact image. The project is release-ready only after the
two smoke gates above; then the ten-submission ladder provides the fastest
truthful path to a winning variant.
