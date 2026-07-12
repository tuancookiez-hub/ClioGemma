# ClioGemma - slide deck brief

Create a polished 7-8 slide deck about how the project works. Focus on the
problem, user value, architecture, and reproducibility. Do not make the deck a
leaderboard-results report.

## Core message

**ClioGemma separates seeing from writing: Kimi builds visual candidates, while
Gemma verifies and expresses the same evidence in four distinct voices.**

## Slide plan

### 1. Title

- ClioGemma
- Evidence-first video captioning with Gemma
- AMD Developer Hackathon ACT II - Track 2

Visual: one video strip branching into four caption cards.

### 2. The challenge

One clip must produce four tones without changing the facts:

- formal
- sarcastic
- humorous-tech
- humorous-non-tech

Emphasize that style creativity and factual grounding pull in opposite
directions.

### 3. Product flow

1. Receive a video task.
2. Sample six scene-aware chronological moments and optional OCR hints.
3. Build a factual record and verify it with Gemma.
4. Generate two Kimi candidates for each requested style.
5. Let Gemma select or repair the final four captions.
6. Return evaluator-ready JSON.

### 4. Architecture

```mermaid
flowchart LR
    A["/input/tasks.json"] --> B["Download + FFmpeg"]
    B --> C["6 scene-aware frames + OCR"]
    C --> D["Kimi K2.6 evidence"]
    D --> E["Gemma 4 verification"]
    E --> F["Kimi two candidates/style"]
    F --> G["Gemma select + repair"]
    G --> H["Schema validation"]
    H --> I["/output/results.json"]
```

Callouts: Novita-only, Gemma-owned final captions, no separate judge, Linux/amd64, bounded
runtime.

### 5. Grounding design

Show the structured evidence fields:

- scene
- subjects
- stable facts
- beginning / middle / end
- caption anchor
- clearly readable text
- do-not-claim ledger

Explain that the negative ledger is as important as the visible facts because
it blocks inferred motives, identities, locations, counts, and unseen outcomes.

### 6. Four voices, one event

Use one real example and show four short caption cards. The literal subject and
action should remain recognizable in all four while the sentence shape and
tone change.

### 7. Built for the evaluator

- public Linux/amd64 Docker image
- exact `/input/tasks.json` to `/output/results.json` contract
- requested keys only
- two concurrent clips
- bounded provider calls and 570-second global limit
- no hardcoded test-video answers
- public Streamlit demo is separate from the scoring entrypoint

### 8. Close

Headline: **See carefully. Verify twice. Write with personality.**

Include the GitHub repository, demo URL, and public image reference.

## Design direction

- Use the existing black, ivory, and gold ClioGemma visual identity.
- Keep body text short; prefer diagrams, caption cards, and frame strips.
- Use gold for evidence/verification and distinct restrained colors for the
  four style cards.
- Use monospace only for paths, model IDs, and JSON keys.
- Keep the emblem small and crisp; do not place decorative artifacts in the
  top-left corner.

## Claims to avoid

- Do not claim a score above 0.92 unless the exact image digest receives it.
- Do not describe the older 0.85 image as the current architecture.
- Do not claim Claude, Gemini, Fireworks, Whisper, or an external judge is used
  in production.
- Do not expose credentials.

## Source files

- `README.md`
- `docs/CURRENT_RELEASE_REVIEW.md`
- `docs/SUBMISSION_FORM_COPY.md`
- `Dockerfile`
- `app/visual.py`
- `app/evidence_pipeline.py`
