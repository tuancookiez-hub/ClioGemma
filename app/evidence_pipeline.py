"""Novita evidence-first caption generation with Gemma-owned final captions."""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.core.frames import Frame
from app.core.grids import build_timeline_grids
from app.core.parse import STYLES
from app.core.provider import NOVITA_GEMMA_MODELS, NOVITA_VISION_MODELS, ProviderConfig, provider_config


class EvidencePipelineError(RuntimeError):
    pass


def _log(message: str) -> None:
    try:
        print(message, file=sys.stderr)
    except OSError:
        pass


def _write_trace(task_id: str, payload: dict) -> None:
    root = os.environ.get("CLIO_TRACE_DIR", "").strip()
    if not root:
        return
    try:
        path = Path(root)
        path.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_id) or "task"
        (path / f"{safe}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as error:
        _log(f"trace disabled: {error}")


_EVIDENCE_PROMPT = """You are the evidence recorder for a precise video captioner.
Inspect only the chronological labelled images. Return exactly these sections:
SCENE, SUBJECTS, STABLE FACTS, TIMELINE, VISIBLE TEXT, DO NOT CLAIM.
Record only visible facts. A hand near an object does not prove writing,
drinking, opening, closing, or completion. Distinguish camera motion from
subject motion. Do not guess motives, relationships, locations, brands,
identities, exact counts, audio, or unseen events. Cite [F01] labels for each
temporal claim. Return the report only."""

_SKEPTICAL_PROMPT = """Act as an independent skeptical visual observer. Using only
the chronological labelled images, record a conservative report with exactly
SCENE, SUBJECTS, STABLE FACTS, TIMELINE, VISIBLE TEXT, DO NOT CLAIM sections.
Move ambiguous actions, counts, identities, relationships, locations, motives,
and temporal direction into DO NOT CLAIM. A likely next event is not a completed
event. Cite frame labels. Ignore audio. Return only the report."""

_CONSENSUS_PROMPT = """Create one conservative consensus evidence report from the
two reports below and the labelled images. Keep a specific claim only when the
images support it and the reports do not materially conflict. When uncertain,
use generic wording and put the detail in DO NOT CLAIM. Use exactly SCENE,
SUBJECTS, STABLE FACTS, TIMELINE, VISIBLE TEXT, DO NOT CLAIM. Return only the
report.

REPORT_A:
{report_a}

REPORT_B:
{report_b}"""

_STYLE = {
    "formal": "professional, objective, factual, and humor-free",
    "sarcastic": "dry, unmistakably ironic, lightly mocking, and deadpan",
    "humorous_tech": "funny with exactly one clear technology or programming comparison",
    "humorous_non_tech": "funny everyday comparison with no technical jargon",
}

_PAIR_PROMPT = """You are a Gemma multimodal caption writer. Use the labelled
images as the source of truth and the consensus report as a factual ceiling.
Write two different candidates for the requested style: A is safest and
literal-first; B has a different sentence shape and a sharper joke where
appropriate. Neither may add a new object, action, count, identity,
relationship, motive, location, duration, or completed event. Put the visible
anchor first. Use 18-42 words. Output exactly:
CANDIDATE_A: <caption>
CANDIDATE_B: <caption>

Requested style: {style}
Style definition: {style_definition}
Consensus report:
{evidence}"""

_SELECT_PROMPT = """You are the final Gemma caption selector. Compare the two
captions for the requested style against the labelled images and consensus
report. Choose the candidate with the best factual support and style match.
Unsupported literal facts are a hard failure. Select one candidate verbatim;
do not rewrite or combine it. Output exactly CHOICE: A or CHOICE: B.

Requested style: {style}
Style definition: {style_definition}
Evidence:
{evidence}

CANDIDATE_A:
{candidate_a}

CANDIDATE_B:
{candidate_b}"""

_FAST_PROMPT = """You are the production video-caption writer. Inspect the five
chronological images and return exactly four styled captions. Put the central
visible subject, action/state, and setting first. Never invent motives,
relationships, locations, brands, exact unstable counts, audio, duration,
future events, accidents, collisions, or completed actions not shown. Do not
describe motion blur as an event. A hand near an object does not prove that the
object was opened, closed, written on, or consumed. Use 18-42 words per
caption and keep the literal visual anchor identical across styles.

formal: one professional, objective, factual sentence; no embellishment.
sarcastic: one accurate literal sentence followed by one dry ironic observation;
do not add a new event or rhetorical question.
humorous_tech: one accurate literal sentence followed by one simple comparison;
use one concept only, with no stacked jargon, nodes, collisions, or runtime.
humorous_non_tech: one accurate literal sentence followed by one relatable
everyday comparison; never invent people, accidents, motives, or backstory.

Before returning, silently verify each caption against the full image sequence:
keep only details visible in at least one frame, remove unsupported counts or
causal claims, and check that the second sentence changes tone without adding
an event. Do not reveal this verification or any reasoning.

Return JSON only. Either use four string keys named formal, sarcastic,
humorous_tech, humorous_non_tech, or use a captions array with objects having
style and text fields. Do not include reasoning or Markdown."""

_CHAMPION_BATCH_PROMPT = """You are the final Gemma style writer for a strict
video-captioning benchmark. Use only the verified evidence and chronological
images below. Return exactly four string keys: formal, sarcastic,
humorous_tech, humorous_non_tech.

Silently draft two alternatives for each style, remove every unsupported literal
detail, then return only the strongest survivor. Keep each caption 16-30 words,
natural, complete, and specific to the visible scene.

Base all four captions on the dominant persistent scene or action across the
sequence. If a person, animal, or vehicle appears only briefly in one timeline
moment, do not make it the subject; describe the stable environment instead.

formal: objective and professional; describe only the persistent subject,
setting, main action or state, and one central object. Do not mention hairstyle,
age, ethnicity, clothing, camera movement, distant scenery, or peripheral
accessories unless they are the entire point of the clip.
sarcastic: state the literal scene first, then one dry contrast or understated
payoff. Keep it accurate and unmistakably sarcastic.
humorous_tech: state the literal scene first, then exactly one clever software
or technology analogy tied to the visible action. Avoid generic scheduler,
queue, packet, deployment, or workplace jokes unless the mapping is precise.
humorous_non_tech: state the literal scene first, then one relatable everyday
comparison with no technical jargon or invented backstory.

Useful shape patterns: sarcastic may use "Ah yes" before one dry contrast;
humorous-tech names the real subject/action and maps it directly to one familiar
technical concept; humorous-non-tech names the real subject/action and adds one
ordinary-life comparison. Never write meta phrases such as "the visible action",
"the visible scene", "the subject", or "the requested style". The caption must
sound like something a person would actually post.

Never leave a quote or sentence unfinished. Do not add names, locations,
numbers, motives, relationships, audio, or unseen outcomes. Output JSON only.
Do not prefix any value with labels such as "Caption_anchor" or "formal:".

VERIFIED EVIDENCE:
{evidence}"""

_VERIFIED_EVIDENCE_PROMPT = """You are the factual evidence stage of a video
captioning system. Inspect the three chronological labelled images. First check
the complete sequence internally, then return one conservative JSON object:
{
  "scene": "one short factual setting description",
  "subjects": ["generic visible subject descriptions"],
  "stable_facts": ["facts visibly supported by at least one image"],
  "timeline": ["beginning: ...", "middle: ...", "end: ..."],
  "visible_text": ["only large central text that is unquestionably readable"],
  "do_not_claim": ["ambiguous actions, motives, identities, counts, brands, or locations"]
}
Use generic descriptions when identity or location is uncertain. A hand near an
object does not prove writing, opening, closing, eating, drinking, or completion.
Do not infer audio, speech, motive, emotion, relationship, future action, or an
event between images. Distinguish subject motion from camera motion. Output JSON
only, without markdown or analysis."""

_VERIFIED_CAPTION_PROMPT = """Write exactly four captions from the verified
evidence below. The evidence is a hard factual ceiling: no caption may add an
object, action, identity, relationship, location, count, motive, emotion,
completed event, future event, or readable text that is absent from it.

Start every caption with the central visible subject/action/state. Keep each
caption 18-34 words and natural. The joke may change tone but may not introduce
a second event or backstory.

formal: one objective professional sentence, no humor.
sarcastic: an accurate literal clause followed by dry irony about that same
visible situation; no rhetorical question and no invented people or motive.
humorous_tech: one accurate literal clause followed by exactly one simple
software or technology analogy tied to the visible action; never discuss image
quality, cameras, JPEGs, frames, models, prompts, or computer vision.
humorous_non_tech: one accurate literal clause followed by one relatable
everyday comparison; no technology jargon, invented people, weekdays, chores,
or unseen backstory.

Return JSON only with exactly these four string keys: formal, sarcastic,
humorous_tech, humorous_non_tech.

VERIFIED EVIDENCE:
"""

_VERIFIED3_DRAFT_PROMPT = """Inspect the chronological images as one
short video. Return a conservative JSON evidence record with exactly these
keys:
{
  "scene": "specific visible setting, or a generic setting when uncertain",
  "subjects": ["generic visible subjects and objects"],
  "stable_facts": ["concrete facts directly supported by the images"],
  "timeline": ["beginning: ...", "middle: ...", "end: ..."],
  "scene_story": "two dense factual sentences covering how the clip begins, develops, and ends",
  "caption_anchor": "one complete present-tense sentence of 6-14 words stating the persistent visible subject, setting, or main state; capitalize it; prefer the scene over a transient motion or camera movement; for an animal or athlete merely passing through, describe the visible subject and setting instead of asserting a journey; do not join two actions with and",
  "visible_text": ["only large, central, unquestionably readable text"],
  "do_not_claim": ["plausible but unsupported identities, actions, counts, motives, relationships, brands, locations, audio, or outcomes"]
}
Be specific about the central visible action or state, but conservative about
what happens between images. A nearby hand does not prove writing, opening,
closing, eating, drinking, or completion. Distinguish camera motion from
subject motion. Output JSON only."""

_REFERENCE_GROUNDING_PROMPT = """Analyze the five chronological images as one
short video and return a dense factual JSON record with exactly these keys:
{
  "summary": "two concrete sentences describing the whole clip",
  "scene": "the dominant visible setting",
  "subjects": ["specific visible people, animals, vehicles, objects, and colors"],
  "primary_action": "the main visible action or persistent state",
  "stable_facts": ["5-9 concrete details supported by the images"],
  "visual_details": ["distinctive clothing, materials, foliage, architecture, weather, surfaces, or background elements"],
  "timeline": ["beginning: ...", "middle: ...", "end: ..."],
  "temporal_arc": "one sentence explaining what visibly changes or remains stable",
  "caption_anchor": "one natural present-tense sentence of 7-16 words naming the main subject, action or state, and setting",
  "visible_text": ["only unquestionably readable, central text"],
  "do_not_claim": ["uncertain identity, location, relationship, brand, count, motive, audio, or unseen outcome"]
}
Prioritize the dominant scene and main subject over a fleeting gesture or camera
movement. Compare the images before asserting motion. Be specific rather than
generic, but put uncertain details in do_not_claim instead of guessing. Do not
describe frames, image quality, sampling, or the analysis process. Output JSON
only, without markdown."""

_VERIFIED3_REVIEW_PROMPT = """Act as a strict second visual observer. Compare
the draft evidence record below against the chronological images. Remove
or correct every unsupported detail. Preserve useful specificity when it is
clearly visible. Put ambiguous identities, relationships, brands, locations,
exact counts, motives, emotions, audio, inferred actions, and unseen outcomes
in do_not_claim. Return the same exact JSON schema and nothing else.

DRAFT EVIDENCE:
"""

_VERIFIED3_STYLE_PROMPTS = {
    "formal": """Write a polished formal caption. State the persistent visible
subject, setting, and main action or state in one objective sentence. Prefer the
scene and stable objects over transient motion or camera movement. Use concrete
details from the verified evidence, with no joke, slang, flourish, or
speculation.""",
    "sarcastic": """Write with the voice of a weary, sharp observer forced to
narrate the obvious. Make the sarcasm unmistakable, dry, and genuinely witty,
not merely a formal caption with 'apparently' added. Include a concrete visible
subject, action or state, and detail. You may personify the subject or invent an
obviously comic motive in the punchline, but do not present a new object or
event as something literally shown. Build the joke from a scene-specific contrast,
understatement, or mock consequence. Never open with 'Behold', 'Witness', 'Look',
or 'Groundbreaking news'; avoid 'thrilling', 'riveting', and generic claims that
the subject is bored, heroic, or pretending.""",
    "humorous_tech": """Write like a burnt-out software engineer turning the
visible scene into a clever bug report, deployment story, stack trace, API,
queue, cache, rollback, or runtime joke. Keep at least one concrete subject,
action or state, and setting detail from the video. Bold figurative debugging
or workplace hyperbole is welcome; unsupported objects or events must not read
as literal video facts. Use technical terms naturally, never as random jargon,
and avoid empty phrases such as 'running runtime' or 'physical cache'. Map one
specific visible relationship to one apt software concept; avoid default 404,
production crash, deployment, and legacy-code jokes unless the mapping is exact.""",
    "humorous_non_tech": """Write like an observant everyday comedian. Keep at
least one concrete subject, action or state, and setting detail from the video,
then make a funny, broadly relatable comparison or mini-scenario. Weekdays,
snacks, chores, imagined attitudes, and social situations are allowed as an
obvious punchline, not as literal claims. Use no technical jargon or niche
references. Prefer a payoff uniquely suggested by the visible scene; avoid default
Monday, chores, dinner, kitchen, snack, or 'same confidence as me' formulas.""",
}

_REFERENCE_STYLE_CALIBRATION = {
    "formal": """Write a documentary-quality formal caption: one polished,
objective sentence naming the main subject, primary action or state, setting,
and two concrete visible details. Use natural language, not an inventory.
Style pattern only: "A young orange kitten sits among dense green foliage,
looking directly toward the viewer." Never copy the example's facts.""",
    "sarcastic": """Write a genuinely sarcastic caption with a factual visual
setup and one dry, lightly mocking payoff. Understatement and contrast work
better than announcing that something is exciting or ordinary. The payoff may
invent an obviously comic attitude, but must not assert a new literal event.
Style pattern only: "A city finally invested in trees, an achievement apparently
worthy of its own parade." Never copy the example's facts.""",
    "humorous_tech": """Write a funny developer-facing caption. Name the real
visible subject and action first, then map one scene-specific relationship to
exactly one coherent technical concept. The joke must land; do not merely insert
software nouns. Style pattern only: "Nature shipped its autumn update: every
leaf node changed color with no rollback required." Never copy the example's
facts.""",
    "humorous_non_tech": """Write a warm, broadly relatable everyday joke. Name
the real visible subject and action, then add one playful comparison or imagined
attitude clearly presented as humor. No technical jargon. Style pattern only:
"The trees put on the best show in town while everyone else sat in traffic."
Never copy the example's facts.""",
}

_KIMI_CANDIDATE_PROMPT = """You are the visual caption candidate generator in a
high-accuracy video-captioning system. Inspect the ordered images and the
verified evidence. Return exactly two distinct candidates for each requested
style in this JSON shape:
{{"formal":["...","..."],"sarcastic":["...","..."],"humorous_tech":["...","..."],"humorous_non_tech":["...","..."]}}

Each candidate must be 16-32 words, start from the central visible subject or
state, and include at least two concrete scene details. Formal is documentary
and literal. Sarcasm is unmistakably dry with one scene-specific contrast.
Humorous-tech uses one precise technical metaphor tied to the visible action.
Humorous-non-tech uses one warm everyday comparison with no technical jargon.
An obviously figurative punchline may invent an attitude or imagined situation,
but never present a new object, identity, location, count, or event as literal.
Do not name a city, landmark, or building unless clearly readable and central.
Do not describe camera movement, frames, models, prompts, or analysis. Avoid generic
load-balancer, Monday, oven, workplace, or empty-stadium jokes unless the
visible scene makes that comparison genuinely specific. Output JSON only.

VERIFIED EVIDENCE:
{evidence}"""

_GEMMA_CANDIDATE_PICK_PROMPT = """You are the final Gemma caption editor. For
each style, choose or minimally repair the strongest candidate below using the
ordered images and VERIFIED EVIDENCE. The final editor must emit the captions.

Accuracy is a hard gate for literal scene facts. Preserve useful concrete
details instead of genericizing them. Sarcasm must be dry and clearly funny.
Humorous-tech must contain exactly one coherent technical mapping to a visible
relationship, using at most two related technical terms. Humorous-non-tech must contain one relatable everyday payoff and
no technical jargon. Remove unsupported literal claims, especially names,
brands, exact or approximate counts, locations, camera/process language, and
inferred outcomes, but keep an obviously figurative joke when its factual setup
is true. Prefer 14-26 words for creative styles and 16-30 for formal. Use one
central subject, one setting/action detail, and one style beat; end every
sentence cleanly.

Return JSON only with exactly four string keys: formal, sarcastic,
humorous_tech, humorous_non_tech.

VERIFIED EVIDENCE:
{evidence}

CANDIDATES:
{candidates}"""

_GEMMA_REPAIR_PROMPT = """You are the last quality gate for four video captions.
Use the ordered images and VERIFIED EVIDENCE as the only factual sources.
Rewrite only captions with listed issues, while preserving concrete visible
details and the requested style. Remove unsupported names, brands, exact or
approximate counts, inferred outcomes, camera/process language, and generic
stock jokes. Do not name a city, landmark, or building unless clearly readable
and central. Avoid camera movement, frames, and inferred completion. A
figurative joke is allowed only after a true visible setup.
Return JSON only with exactly four string keys: formal, sarcastic,
humorous_tech, humorous_non_tech. Keep formal 16-32 words and each creative
style 14-26 words. Every sentence must be complete.

VERIFIED EVIDENCE:
{evidence}

CURRENT CAPTIONS:
{captions}

DETERMINISTIC ISSUES:
{issues}"""

_VERIFIED4_FINAL_PROMPT = """Perform one final image-grounded revision of the
four proposed captions. The chronological images and verified evidence are the
only factual sources. Preserve each requested tone, but remove or correct any
literal object, action, identity, relationship, setting, count, motive,
emotion, text, arrival, departure, completion, or outcome not directly
supported. The formal caption must remain literal and begin with caption_anchor.
For creative captions, preserve at least one concrete subject, action or state,
and setting detail, but keep bold sarcasm and humor. Do not remove an obviously
figurative joke merely because it mentions a motive, weekday, snack, debugging,
deployment, or imagined situation. Correct only unsupported details that read
as literal video facts. Keep each caption concise and strongly differentiated.
Return JSON only with exactly these four string keys:
formal, sarcastic, humorous_tech, humorous_non_tech.

VERIFIED EVIDENCE:
{evidence}

PROPOSED CAPTIONS:
{captions}
"""

_VERIFIED6_PICK_PROMPT = """Select the single best candidate for each style.
Judge independently on the same two axes as the external evaluator:
1. accuracy to the chronological images and verified evidence; unsupported
literal objects, actions, settings, counts, identities, or outcomes are a hard failure;
2. strength and naturalness of the requested style. Sarcasm must be unmistakably
dry; tech humor must contain a coherent joke rather than robotic substitutions;
non-tech humor should have a relatable payoff that could make a person smile.

Reject stock caption formulas. In particular, reject sarcastic openings such as
"Behold", "Witness", "Look", or "Groundbreaking news", and reject empty claims
that a scene is "thrilling" or "riveting". For tech humor, reject a generic 404,
crash, deployment, or legacy-code joke unless the software concept maps precisely
to the visible subject and action. For non-tech humor, prefer an analogy tailored
to this scene over a default Monday, chores, dinner, kitchen, or snack joke.
Do not reward invented emotions, occupations, motives, failures, or outcomes.
Reject proper names, brands, institutions, and exact wording or numbers taken
only from peripheral signs or markings. Such text is usable only when the same
fact also appears in stable_facts; visible_text by itself is not enough.

Prefer specific-and-true over vague-and-true, and prefer a clear style beat over
a weak generic sentence. Do not reward length. Return each selected candidate
verbatim; do not merge or rewrite. Return JSON only with exactly four string
keys: formal, sarcastic, humorous_tech, humorous_non_tech.

Before returning, privately score each caption on two axes: (1) accuracy to the
verified evidence and (2) strength of the requested style. Keep a caption that
already passes both axes; revise only a real factual or style failure. Do not
genericize a specific caption, and do not replace a visible action with a vague
topic summary.

VERIFIED EVIDENCE:
{evidence}

CANDIDATES:
{candidates}
"""

_TECH = {
    "algorithm", "api", "balancer", "bandwidth", "binary", "bug", "cache",
    "code", "commit", "compile", "cpu", "database", "debug", "deploy",
    "deployment", "download", "endpoint", "gpu", "hotfix", "input", "interface",
    "app", "json", "kernel", "latency", "layer", "log", "memory", "middleware", "network", "packet",
    "pipeline", "process", "program", "protocol", "queue", "regex", "render", "repo",
    "rollback", "router", "runtime", "scheduler", "script", "server", "software", "shader", "signal", "stack",
    "state", "thread", "throughput", "ui", "upload", "vertices", "wifi", "zoom", "mutex", "handshake",
    "buffer", "cache", "firmware", "boot", "simulation", "deployment", "update", "deadlock", "keystroke", "keystrokes",
}
_SPECULATIVE = re.compile(
    r"\b(probably|likely|decid(?:e|es|ed|ing)|wants?|wanted|remembers?|pretends?|"
    r"believes?|hopes?|trying to|plans? to|about to)\b",
    re.I,
)
_PROCESS = re.compile(
    r"\b(camera|sampling|model|prompt|analysis|detection|uncertain(?:ty)?|"
    r"image quality|jpe?g|pixels?|camera footage|computer vision|"
    r"visible action|visible scene|requested style)\b",
    re.I,
)
_RELATIONSHIP = re.compile(
    r"\b(famil(?:y|ies)|mothers?|fathers?|parents?|siblings?|owners?|"
    r"coworkers?|colleagues?|couples?|husbands?|wives|daughters?|sons?|kids?)\b",
    re.I,
)
_BRAND = re.compile(
    r"\b(?:adidas|apple|coca[- ]?cola|facebook|google|imac|instagram|joysound|macbook|nike|starbucks|tesla|tiktok|youtube)\b",
    re.I,
)
_AWKWARD_TECH = re.compile(r"\b(running runtime|physical cache|sign (?:as|is) an api|scheduler scheduling)\b", re.I)
_DURATION = re.compile(r"\b\d+(?:\.\d+)?\s+(?:seconds?|minutes?|hours?)\b", re.I)
_UNSTABLE_COUNT = re.compile(r"\b(?:hundreds?|thousands?|millions?)\b", re.I)


def _remaining(deadline: float | None) -> float | None:
    return None if deadline is None else deadline - time.monotonic()


def _timeout(config: ProviderConfig, deadline: float | None) -> float:
    left = _remaining(deadline)
    value = config.timeout_s if left is None else min(config.timeout_s, left - 0.5)
    if value < 1:
        raise EvidencePipelineError("clip deadline exhausted")
    return value


def _retryable_status(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if status in {408, 429, 500, 502, 503, 504}:
        return status
    name = type(error).__name__.lower()
    message = str(error).lower()
    if "timeout" in name or "timed out" in message:
        return 408
    return None


def _retry_delay(attempt: int) -> float:
    return min(1.5 * (2 ** attempt), 6.0)


def _effective_temperature(value: float) -> float:
    """Reduce provider sampling variance for an immutable release profile.

    Candidate generation remains mildly creative, while evidence, selection,
    repair, and final grounding become deterministic whenever
    ``CLIO_STABILITY_MODE`` is enabled. This cannot control a hidden judge, but
    it prevents our own output from changing unnecessarily between runs.
    """
    stable = os.environ.get("CLIO_STABILITY_MODE", "").lower() in {"1", "true", "yes"}
    if not stable:
        return value
    return 0.45 if value >= 0.55 else 0.0


def _call(config: ProviderConfig, content: list[dict], *, deadline: float | None, max_tokens: int, temperature: float) -> str:
    try:
        retries = max(0, min(int(os.environ.get("CLIO_RATE_LIMIT_RETRIES", "3")), 4))
    except ValueError:
        retries = 3
    client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=config.timeout_s, max_retries=0)
    for attempt in range(retries + 1):
        timeout = _timeout(config, deadline)
        try:
            messages: list[dict] = [{"role": "user", "content": content}]
            model_name = config.model.lower()
            if "deepseek" in model_name:
                # Novita documents DeepSeek V4's non-think mode as a
                # prompt-level instruction. Keep it in a system message as
                # well as the provider hint because some compatible routes
                # ignore the extra_body field.
                messages.insert(0, {
                    "role": "system",
                    "content": (
                        "Use non-think mode. Do not reveal analysis, planning, "
                        "or instructions. Return only the requested final "
                        "caption text or JSON object."
                    ),
                })
            request_kwargs = {
                "model": config.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "timeout": timeout,
            }
            if model_name in {item.lower() for item in NOVITA_VISION_MODELS}:
                # Kimi and Qwen are used for visual evidence.  Disabling their
                # internal reasoning keeps the response budget available for
                # the requested evidence schema.
                request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                if os.environ.get("CLIO_STABILITY_MODE", "").lower() in {"1", "true", "yes"}:
                    request_kwargs["temperature"] = 0.0
            elif "deepseek" in model_name:
                # Novita's DeepSeek V4 endpoint exposes the same thinking
                # control.  Without this, the reasoning transcript is placed
                # in message.content and JSON caption parsing fails.
                request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                request_kwargs["temperature"] = _effective_temperature(temperature)
            else:
                request_kwargs["temperature"] = _effective_temperature(temperature)
            response = client.chat.completions.create(**request_kwargs)
            break
        except Exception as error:
            status = _retryable_status(error)
            if status is None or attempt >= retries or (status == 408 and attempt >= 1):
                raise
            delay = _retry_delay(attempt)
            left = _remaining(deadline)
            if left is not None and left <= delay + 1:
                raise
            _log(f"provider status={status}; retrying in {delay:.1f}s")
            time.sleep(delay)
    message = response.choices[0].message
    text = message.content or getattr(message, "reasoning_content", "") or ""
    if not isinstance(text, str) or not text.strip():
        raise EvidencePipelineError("provider returned empty content")
    return text.strip()


def _timeline_content(frames: list[Frame], prompt: str) -> list[dict]:
    if os.environ.get("CLIO_GRID_INPUT", "").lower() in {"1", "true", "yes"}:
        return _timeline_grid_content(frames, prompt)
    if not frames:
        raise EvidencePipelineError("no frames")
    parts: list[dict] = [{"type": "text", "text": "Chronological labelled visual evidence follows."}]
    for index, frame in enumerate(frames[:8], 1):
        parts.append({"type": "text", "text": f"[F{index:02d}]"})
        data = base64.b64encode(frame.path.read_bytes()).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
    parts.append({"type": "text", "text": prompt})
    return parts


def _timeline_grid_content(frames: list[Frame], prompt: str) -> list[dict]:
    # Avoid a mostly-empty 4x4 sheet on the latency-optimized five-frame path.
    # A 3x2 sheet keeps every frame large while remaining one image request.
    if len(frames) <= 6:
        grids = build_timeline_grids(frames, cols=3, rows=2)
    elif len(frames) <= 8:
        grids = build_timeline_grids(frames, cols=4, rows=2)
    else:
        grids = build_timeline_grids(frames)
    if not grids:
        raise EvidencePipelineError("no frames")
    parts: list[dict] = [{
        "type": "text",
        "text": (
            "Chronological contact-sheet evidence follows. Each grid is ordered "
            "left-to-right, top-to-bottom; labels F01, F02, and so on are annotations. "
            "Black empty cells are padding and are not video content."
        ),
    }]
    for index, grid in enumerate(grids, 1):
        parts.append({"type": "text", "text": f"GRID {index}"})
        parts.append({"type": "image_url", "image_url": {"url": grid}})
    parts.append({"type": "text", "text": prompt})
    return parts


def _visual_content(frames: list[Frame], prompt: str) -> list[dict]:
    if os.environ.get("CLIO_GRID_INPUT", "").lower() in {"1", "true", "yes"}:
        return _timeline_grid_content(frames, prompt)
    return _timeline_content(frames, prompt)


def _caption_content(frames: list[Frame], prompt: str, config: ProviderConfig) -> list[dict]:
    """Use text-only evidence for optional text caption models."""
    if "deepseek" in config.model.lower():
        return [{"type": "text", "text": prompt}]
    return _timeline_content(frames, prompt)


def _normalize(raw: str) -> str:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:text|markdown)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    text = (
        text.replace("â€™", "'")
        .replace("â€˜", "'")
        .replace("â€œ", '"')
        .replace("â€", '"')
        .replace("â€”", "—")
        .replace("â€“", "–")
        .replace("Â", "")
    )
    text = re.sub(r"(?:\*\*|__|`)", "", text)
    text = re.sub(r"^(?:caption[_ ]?anchor|caption)\s*(?:[:\-]\s*)?", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" \t\"'")


def _normalize_anchor(raw: str) -> str:
    anchor = _normalize(raw).strip()
    if not anchor:
        return ""
    anchor = anchor.rstrip(".?!")
    if anchor.isupper():
        anchor = anchor.lower()
    if anchor and anchor[0].isalpha():
        anchor = anchor[0].upper() + anchor[1:]
    return anchor


_ANCHOR_STOP = {
    "a", "an", "and", "are", "at", "by", "for", "from", "in", "is",
    "of", "on", "the", "through", "to", "with",
}


def _anchor_style_issues(style: str, caption: str, anchor: str) -> list[str]:
    anchor = _normalize_anchor(anchor)
    if not anchor:
        return []
    normalized_caption = _normalize(caption)
    if style == "formal":
        if not normalized_caption.casefold().startswith(anchor.casefold()):
            return ["formal caption must begin with the verified factual anchor"]
        return []
    anchor_tokens = {
        token.rstrip("s")
        for token in re.findall(r"[a-z]+", anchor.casefold())
        if token not in _ANCHOR_STOP and len(token) > 2
    }
    caption_tokens = {token.rstrip("s") for token in re.findall(r"[a-z]+", normalized_caption.casefold())}
    if anchor_tokens and not anchor_tokens & caption_tokens:
        return ["creative caption must retain a concrete detail from the verified anchor"]
    return []


def _style_issues(style: str, caption: str) -> list[str]:
    words = re.findall(r"\b[\w'-]+\b", caption)
    issues: list[str] = []
    if not 12 <= len(words) <= 50:
        issues.append("word count must be 12-50")
    if _PROCESS.search(caption):
        issues.append("process leakage")
    if style == "formal" and _SPECULATIVE.search(caption):
        issues.append("speculative intent")
    if style == "formal" and _RELATIONSHIP.search(caption):
        issues.append("inferred relationship")
    if _BRAND.search(caption):
        issues.append("unsupported brand claim")
    if style == "formal" and _DURATION.search(caption):
        issues.append("precise duration")
    if _UNSTABLE_COUNT.search(caption):
        issues.append("unsupported approximate count")
    hits = {word for word in _TECH if re.search(rf"\b{re.escape(word)}s?\b", caption, re.I)}
    if style == "humorous_tech" and not hits:
        issues.append("missing tech comparison")
    if style == "humorous_tech" and _AWKWARD_TECH.search(caption):
        issues.append("awkward or incorrect tech analogy")
    if style == "humorous_tech" and len(hits) > 3:
        issues.append("stacked tech jargon")
    if style == "humorous_non_tech" and hits:
        issues.append("technical jargon")
    if caption.count('"') % 2 or caption.count("“") != caption.count("”"):
        issues.append("unbalanced quotation")
    stock = _STOCK_STYLE.get(style)
    if stock and stock.search(caption):
        issues.append("stock style formula")
    if style == "formal" and ("!" in caption or "?" in caption):
        issues.append("formal punctuation")
    return issues


_STOCK_STYLE = {
    "sarcastic": re.compile(
        r"^(?:behold|witness|look\b)|groundbreaking news|\b(?:thrilling|riveting)\b|"
        r"apparently this (?:perfectly )?ordinary scene",
        re.I,
    ),
    "humorous_tech": re.compile(
        r"\b404\b|motivation not found|legacy (?:codebase|process)|total system crash|"
        r"software task waiting on one visible input|software task waiting on input|"
        r"scheduler managing one very visible queue|scheduler keeping one visible sequence moving",
        re.I,
    ),
    "humorous_non_tech": re.compile(
        r"\b(?:on a |every )?monday\b|what (?:to|i should) (?:eat|have) for dinner|"
        r"walked into the kitchen|finish all my chores|three different snacks|same confidence as me|"
        r"unexpectedly dramatic sense of purpose|left the oven on",
        re.I,
    ),
}


def _candidate_quality_issues(style: str, caption: str) -> list[str]:
    issues = _style_issues(style, caption)
    words = re.findall(r"\b[\w'-]+\b", caption)
    if not 22 <= len(words) <= 45:
        issues.append("candidate word count must be 22-45")
    stock = _STOCK_STYLE.get(style)
    if stock and stock.search(caption):
        issues.append("stock style formula")
    return issues


def _parse_pair(raw: str) -> tuple[str, str]:
    match = re.search(r"CANDIDATE[_\s-]*A\s*:\s*(.*?)\s*CANDIDATE[_\s-]*B\s*:\s*(.*)$", raw, re.I | re.S)
    if not match:
        raise EvidencePipelineError("candidate writer returned no A/B markers")
    first, second = _normalize(match.group(1)), _normalize(match.group(2))
    if not first or not second or first.casefold() == second.casefold():
        raise EvidencePipelineError("candidate pair was empty or duplicated")
    return first, second


def _candidate_pair(style: str, frames: list[Frame], evidence: str, config: ProviderConfig, deadline: float | None) -> tuple[str, str]:
    prompt = _PAIR_PROMPT.format(style=style, style_definition=_STYLE[style], evidence=evidence)
    return _parse_pair(_call(config, _timeline_content(frames, prompt), deadline=deadline, max_tokens=1800, temperature=0.35 if style == "formal" else 0.6))


def _select(style: str, candidates: tuple[str, str], frames: list[Frame], evidence: str, config: ProviderConfig, deadline: float | None) -> str:
    prompt = _SELECT_PROMPT.format(style=style, style_definition=_STYLE[style], evidence=evidence, candidate_a=candidates[0], candidate_b=candidates[1])
    raw = _call(config, _timeline_content(frames, prompt), deadline=deadline, max_tokens=80, temperature=0)
    match = re.fullmatch(r"\s*CHOICE\s*:\s*([AB])\s*\.?\s*", raw, re.I)
    if not match:
        raise EvidencePipelineError(f"selector returned invalid choice for {style}")
    choice = 0 if match.group(1).upper() == "A" else 1
    other = 1 - choice
    if _style_issues(style, candidates[choice]) and not _style_issues(style, candidates[other]):
        choice = other
    return candidates[choice]


def _decode_json_object(raw: str, label: str) -> dict:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise EvidencePipelineError(f"{label} returned no JSON object")


def _parse_fast(raw: str) -> dict[str, str]:
    data = _decode_json_object(raw, "fast Gemma call")
    if isinstance(data, dict) and isinstance(data.get("captions"), list):
        out = {}
        for item in data["captions"]:
            if isinstance(item, dict) and str(item.get("style")) in STYLES and isinstance(item.get("text"), str):
                out[str(item["style"])] = _normalize(str(item["text"]))
        if set(out) == set(STYLES):
            return out
    if isinstance(data, dict) and set(data) == set(STYLES):
        out = {style: _normalize(str(data[style])) for style in STYLES}
        if all(out.values()):
            return out
    raise EvidencePipelineError("fast Gemma call returned the wrong caption schema")


def _parse_candidate_sets(raw: str) -> dict[str, list[str]]:
    data = _decode_json_object(raw, "candidate call")
    result: dict[str, list[str]] = {}
    for style in STYLES:
        value = data.get(style)
        if isinstance(value, str):
            values = [_normalize(value)]
        elif isinstance(value, list):
            values = [_normalize(str(item)) for item in value if str(item).strip()]
        else:
            values = []
        values = [item for item in values if item]
        if len(values) < 2:
            raise EvidencePipelineError(f"candidate output lacks two {style} candidates")
        result[style] = values[:2]
    return result


def _kimi_style_candidates(
    frames: list[Frame],
    evidence: dict,
    config: ProviderConfig,
    deadline: float | None,
) -> dict[str, list[str]]:
    prompt = _KIMI_CANDIDATE_PROMPT.format(
        evidence=json.dumps(evidence, ensure_ascii=False, indent=2)
    )
    raw = _call(
        config,
        _timeline_content(frames, prompt),
        deadline=deadline,
        max_tokens=1600,
        temperature=0.7,
    )
    return _parse_candidate_sets(raw)


def _gemma_select_candidates(
    frames: list[Frame],
    evidence: dict,
    candidates: dict[str, list[str]],
    config: ProviderConfig,
    deadline: float | None,
) -> dict[str, str]:
    prompt = _GEMMA_CANDIDATE_PICK_PROMPT.format(
        evidence=json.dumps(evidence, ensure_ascii=False, indent=2),
        candidates=json.dumps(candidates, ensure_ascii=False, indent=2),
    )
    raw = _call(
        config,
        _caption_content(frames, prompt, config),
        deadline=deadline,
        max_tokens=1100,
        temperature=0.15,
    )
    return _parse_fast(raw)


def _gemma_repair_captions(
    frames: list[Frame],
    evidence: dict,
    captions: dict[str, str],
    issues: dict[str, list[str]],
    config: ProviderConfig,
    deadline: float | None,
) -> dict[str, str]:
    prompt = _GEMMA_REPAIR_PROMPT.format(
        evidence=json.dumps(evidence, ensure_ascii=False, indent=2),
        captions=json.dumps(captions, ensure_ascii=False, indent=2),
        issues=json.dumps(issues, ensure_ascii=False, indent=2),
    )
    raw = _call(
        config,
        _caption_content(frames, prompt, config),
        deadline=deadline,
        max_tokens=1100,
        temperature=0.1,
    )
    return _parse_fast(raw)


def _parse_verified_evidence(raw: str) -> dict:
    data = _decode_json_object(raw, "verified evidence call")
    stable = data.get("stable_facts")
    timeline = data.get("timeline")
    if not isinstance(stable, list) or not stable:
        raise EvidencePipelineError("verified evidence lacks stable facts")
    if not isinstance(timeline, list) or not timeline:
        raise EvidencePipelineError("verified evidence lacks a timeline")
    anchor = _normalize_anchor(str(data.get("caption_anchor", "")))
    if anchor:
        data["caption_anchor"] = anchor + "."
    return data


def _caption_batch_issues(captions: dict[str, str], anchor: str = "") -> dict[str, list[str]]:
    issues = {style: _style_issues(style, captions.get(style, "")) for style in STYLES}
    anchor = _normalize_anchor(anchor)
    if anchor:
        for style in STYLES:
            issues[style].extend(_anchor_style_issues(style, captions.get(style, ""), anchor))
    normalized = [re.sub(r"\W+", " ", captions.get(style, "").lower()).strip() for style in STYLES]
    if len(set(normalized)) != len(normalized):
        for style in STYLES:
            issues[style].append("caption duplicates another style")
    return {style: values for style, values in issues.items() if values}


def _issue_count(issues: dict[str, list[str]]) -> int:
    return sum(len(values) for values in issues.values())


def _caption_clip_fast(frames: list[Frame], task_id: str, config: ProviderConfig, deadline: float | None) -> dict[str, str]:
    raw = _call(config, _timeline_content(frames, _FAST_PROMPT), deadline=deadline, max_tokens=1200, temperature=0.25)
    captions = _parse_fast(raw)
    _write_trace(task_id, {"mode": "fast", "captions": captions})
    return captions


def _caption_clip_verified2(frames: list[Frame], task_id: str, config: ProviderConfig, deadline: float | None) -> dict[str, str]:
    evidence_raw = _call(
        config,
        _timeline_content(frames[:3], _VERIFIED_EVIDENCE_PROMPT),
        deadline=deadline,
        max_tokens=700,
        temperature=0.1,
    )
    evidence = _parse_verified_evidence(evidence_raw)
    caption_prompt = _VERIFIED_CAPTION_PROMPT + json.dumps(evidence, ensure_ascii=False, indent=2)
    caption_raw = _call(
        config,
        [{"type": "text", "text": caption_prompt}],
        deadline=deadline,
        max_tokens=900,
        temperature=0.4,
    )
    captions = _parse_fast(caption_raw)
    issues = _caption_batch_issues(captions)
    if issues:
        repair_prompt = (
            caption_prompt
            + "\n\nThe previous captions failed deterministic checks:\n"
            + json.dumps(issues, ensure_ascii=False)
            + "\nRewrite all four captions. Correct only the listed failures while preserving the verified facts. "
            "Return the same exact four-key JSON object.\n\nPREVIOUS CAPTIONS:\n"
            + json.dumps(captions, ensure_ascii=False, indent=2)
        )
        try:
            repaired_raw = _call(
                config,
                [{"type": "text", "text": repair_prompt}],
                deadline=deadline,
                max_tokens=900,
                temperature=0.25,
            )
            repaired = _parse_fast(repaired_raw)
            if len(_caption_batch_issues(repaired)) <= len(issues):
                captions = repaired
        except Exception as error:
            _log(f"verified2 repair skipped: {error}")
    _write_trace(task_id, {"mode": "verified2", "evidence": evidence, "captions": captions})
    return captions


def _three_anchor_frames(frames: list[Frame]) -> list[Frame]:
    if len(frames) <= 3:
        return frames
    return [frames[0], frames[len(frames) // 2], frames[-1]]


def _four_anchor_frames(frames: list[Frame]) -> list[Frame]:
    if len(frames) <= 4:
        return frames
    last = len(frames) - 1
    return [frames[round(last * index / 3)] for index in range(4)]


def _five_anchor_frames(frames: list[Frame]) -> list[Frame]:
    if len(frames) <= 5:
        return frames
    last = len(frames) - 1
    return [frames[round(last * index / 4)] for index in range(5)]


def _eight_anchor_frames(frames: list[Frame]) -> list[Frame]:
    if len(frames) <= 8:
        return frames
    last = len(frames) - 1
    return [frames[round(last * index / 7)] for index in range(8)]


def _role_model_config(config: ProviderConfig, env_name: str, role: str) -> ProviderConfig:
    model = os.environ.get(env_name, "").strip() or config.model
    if "gemma" not in model.lower():
        raise EvidencePipelineError(f"{role} model must be Gemma-family")
    enforce = os.environ.get("CLIO_ENFORCE_NOVITA", "").lower() in {"1", "true", "yes"}
    if enforce and model.lower() not in {item.lower() for item in NOVITA_GEMMA_MODELS}:
        raise EvidencePipelineError(f"Novita-only {role} model must be an allowed Gemma model")
    return replace(config, model=model)


def _caption_model_config(config: ProviderConfig) -> ProviderConfig:
    model = os.environ.get("CLIO_CAPTION_MODEL", "").strip()
    if "deepseek" in model.lower() and os.environ.get("CLIO_ALLOW_NON_GEMMA_CAPTION", "").lower() in {"1", "true", "yes"}:
        return replace(config, model=model)
    return _role_model_config(config, "CLIO_CAPTION_MODEL", "caption")


def _verify_model_config(config: ProviderConfig) -> ProviderConfig:
    return _role_model_config(config, "CLIO_VERIFY_MODEL", "verification")


def _vision_model_config(config: ProviderConfig) -> ProviderConfig:
    model = os.environ.get("CLIO_VISION_MODEL", "").strip() or config.model
    if "gemma" in model.lower():
        return replace(config, model=model)
    if model.lower() not in {item.lower() for item in NOVITA_VISION_MODELS}:
        raise EvidencePipelineError(f"Novita vision model must be Gemma or an allowed multimodal model: {model}")
    return replace(config, model=model)


def _write_verified3_style(
    style: str,
    evidence: dict,
    prior_captions: list[str],
    config: ProviderConfig,
    deadline: float | None,
    frames: list[Frame] | None = None,
    concise: bool = False,
    balanced: bool = False,
    champion: bool = False,
    reference_calibrated: bool = False,
) -> str:
    anchor = _normalize_anchor(str(evidence.get("caption_anchor", "")))
    prior_note = ""
    if prior_captions:
        prior_note = (
            "\n\nCaptions already written for this clip:\n- "
            + "\n- ".join(prior_captions)
            + "\nUse a different sentence shape and comedic angle while preserving the same visible facts."
        )
    anchor_note = ""
    if anchor and style == "formal" and not reference_calibrated:
        anchor_note = (
            "\n\nBegin with this exact verified factual clause, unchanged: "
            + anchor
            + "."
        )
    elif anchor:
        anchor_note = (
            "\n\nNaturally retain the central visual fact in this verified anchor: "
            + anchor
            + ". Do not copy the formal sentence word for word."
        )
    creative_rule = (
        "The verified evidence is a hard ceiling for literal claims. An obviously figurative creative punchline may "
        "invent an attitude or relatable scenario, but the caption must still name a real visible detail. "
        if style != "formal"
        else "The verified evidence is a hard ceiling; every statement must be literal and supported. "
    )
    internal_selection = (
        " Before answering, silently draft two different angles, delete any detail not in VERIFIED EVIDENCE, "
        "and return only the sharper, more natural survivor."
        if balanced or reference_calibrated
        else ""
    )
    length_rule = (
        "Aim for 22-32 words, hard bounds 16-38, with one polished sentence or two short sentences"
    ) if reference_calibrated else (
        "Aim for 18-28 words, hard bounds 14-32, with one crisp factual sentence"
        if style == "formal"
        else "Aim for 15-28 words, hard bounds 12-32, with one crisp sentence or two short sentences"
    ) if champion else (
        "Aim for 18-30 words, hard bounds 14-34, with one crisp factual sentence"
        if style == "formal"
        else "Aim for 16-28 words, hard bounds 12-32, with one crisp sentence or two short sentences"
    ) if concise else ("Write 18-48 words" if style == "formal" else "Write 12-40 words")
    calibration = ""
    if reference_calibrated:
        calibration = (
            "\n\nREFERENCE-CALIBRATED STYLE RUBRIC:\n"
            + _REFERENCE_STYLE_CALIBRATION[style]
            + "\nKeep at least two concrete scene details. A creative punchline may contain an "
            "obviously figurative motive, comparison, or imagined consequence; that is style, not a literal claim. "
            "The factual setup must remain true. Avoid generic jokes that could fit any clip."
        )
    elif concise:
        calibration = (
            "\n\nSTYLE CALIBRATION EXAMPLES — style patterns only; never copy their facts:\n"
            "formal: A city boulevard lined with autumn trees carries steady traffic beneath apartment towers.\n"
            "sarcastic: The city decorated the commute, apparently hoping traffic would count as sightseeing.\n"
            "humorous_tech: Nature's annual deployment updates the leaf nodes to yellow while the traffic queue keeps processing.\n"
            "humorous_non_tech: The trees planned a better show than the people stuck underneath them.\n"
            "Prefer a precise visible detail and one clean style beat over a long inventory. Avoid filler, invented names, and explanations."
        )
    elif balanced:
        calibration = (
            "\n\nEVALUATOR-ALIGNED STYLE CHECK — use these as style patterns only; never copy their facts:\n"
            "formal: lead with the visible subject, action or state, and setting; add one or two concrete details. Keep it objective and professional.\n"
            "sarcastic: state the visible situation first, then add one dry contrast, understatement, or mock consequence.\n"
            "humorous_tech: state the visible situation first, then use exactly one coherent software or technology analogy tied to that action.\n"
            "humorous_non_tech: state the visible situation first, then use one relatable everyday comparison suggested by the scene.\n"
            "Prefer a complete, natural caption with concrete detail over a compressed fragment or a stack of jokes. Make the punchline hinge on the visible action, not just the topic. Never invent numeric quantities, durations, names, locations, or literal unseen outcomes, even in a joke."
        )
    if balanced:
        calibration += (
            "\nUse these shape patterns only; never copy their facts: "
            "formal = visible subject/action + setting + one detail; "
            "sarcastic = literal scene + one dry contrast; "
            "humorous_tech = literal scene + one apt software analogy; "
            "humorous_non_tech = literal scene + one everyday comparison."
        )
    if champion:
        calibration += (
            "\nCHAMPION PRECISION RULES: For formal, mention only the central subject, action/state, setting, "
            "and one or two unmistakable details; omit peripheral accessories, distant structures, and camera language. "
            "For creative styles, state the visible scene first, then add exactly one scene-specific style beat. "
            "Do not use a generic scheduler, queue, packet, or workplace joke unless it maps to the visible action. "
            "Never leave a quotation, sentence, or thought unfinished."
        )
    prompt = (
        _VERIFIED3_STYLE_PROMPTS[style]
        + calibration
        + "\n\n"
        + creative_rule
        + length_rule
        + ", use one or two concise sentences, never mention frames or analysis, and output only the caption text."
        + internal_selection
        + anchor_note
        + prior_note
        + "\n\nVERIFIED EVIDENCE:\n"
        + json.dumps(evidence, ensure_ascii=False, indent=2)
    )
    persona_mode = bool(frames)
    temperature = 0.12 if style == "formal" else (
        0.78 if reference_calibrated else (0.65 if concise else (0.70 if champion else (0.82 if persona_mode else 0.7)))
    )
    content = _caption_content(frames, prompt, config) if frames else [{"type": "text", "text": prompt}]
    caption = _normalize(
        _call(
            config,
            content,
            deadline=deadline,
            max_tokens=210 if concise else 240,
            temperature=temperature,
        )
    )
    issues = _style_issues(style, caption)
    anchor_check_style = "sarcastic" if reference_calibrated else style
    issues.extend(_anchor_style_issues(anchor_check_style, caption, anchor))
    if not issues:
        return caption
    repair_prompt = (
        prompt
        + "\n\nYour previous caption failed these mechanical checks: "
        + "; ".join(issues)
        + ". Rewrite it without adding facts. Keep the verified anchor's subject/action in the sentence, and keep the requested style unmistakable. Output only the corrected caption.\n\nPREVIOUS CAPTION:\n"
        + caption
    )
    try:
        repaired = _normalize(
            _call(
                config,
                _caption_content(frames, repair_prompt, config) if frames else [{"type": "text", "text": repair_prompt}],
                deadline=deadline,
                max_tokens=240,
                temperature=0.25,
            )
        )
        repaired_issues = _style_issues(style, repaired)
        repaired_issues.extend(_anchor_style_issues(anchor_check_style, repaired, anchor))
        if len(repaired_issues) < len(issues):
            return repaired
    except Exception as error:
        _log(f"verified3 {style} repair skipped: {error}")
    if style == "sarcastic":
        return caption
    return _deterministic_verified_caption(style, evidence)


def _write_verified7_pair(
    style: str,
    evidence: dict,
    frames: list[Frame],
    config: ProviderConfig,
    deadline: float | None,
) -> tuple[str, str]:
    creative = style != "formal"
    prompt = (
        _VERIFIED3_STYLE_PROMPTS[style]
        + "\n\nCreate TWO excellent alternatives for this one style. Candidate A should be polished, "
        "literal-first, and highly reliable. Candidate B should use a different sentence shape and a sharper, "
        "more original angle while remaining equally grounded. Both must retell the real clip: name the main "
        "subject, setting, primary action or state, how it develops when supported, and at least two concrete "
        "visible details. Aim for 30-38 words; hard bounds 22-45. "
        + (
            "An obviously figurative punchline may invent an attitude or relatable scenario, but no new object or event may read as literally shown. "
            if creative
            else "Every statement must remain objective, professional, and literally supported. "
        )
        + "Never mention frames, analysis, models, prompts, or captioning. "
        "Never include proper names, brands, institutions, or exact wording or numbers from background signs and markings unless that same fact is explicitly present in stable_facts. "
        "Output exactly:\nCANDIDATE_A: <caption>\nCANDIDATE_B: <caption>\n\nVERIFIED EVIDENCE:\n"
        + json.dumps(evidence, ensure_ascii=False, indent=2)
    )
    raw = _call(
        config,
        _timeline_content(frames, prompt),
        deadline=deadline,
        max_tokens=520,
        temperature=0.3 if style == "formal" else 0.88,
    )
    return _parse_pair(raw)


def _deterministic_verified_caption(style: str, evidence: dict) -> str:
    anchor = _normalize_anchor(str(evidence.get("caption_anchor", "")))
    if not anchor:
        anchor = _normalize(str(evidence.get("scene", "The main subject remains visible"))).rstrip(".?!")
    if style == "formal":
        stable_facts = evidence.get("stable_facts")
        if isinstance(stable_facts, list):
            for fact in stable_facts:
                detail = _normalize(str(fact)).rstrip(".?!")
                if detail and detail.casefold() not in anchor.casefold():
                    return f"{anchor.rstrip('.?!')}. {detail}."
        return f"{anchor.rstrip('.?!')}."
    anchor_lower = anchor.casefold()
    if style == "humorous_tech":
        if any(token in anchor_lower for token in ("traffic", "pedestrian", "vehicle", "intersection")):
            ending = "like a scheduler coordinating competing requests at one shared endpoint."
        elif any(token in anchor_lower for token in ("chop", "dice", "vegetable", "knife")):
            ending = "like a batch job splitting one input into smaller chunks."
        elif any(token in anchor_lower for token in ("mountain", "camera", "landscape", "ridge")):
            ending = "like a zoom operation revealing another nested layer."
        elif any(token in anchor_lower for token in ("wave", "ocean", "beach", "shore")):
            ending = "like a retry loop repeatedly hitting the same shoreline endpoint."
        else:
            ending = "like one clean software operation tied to the visible action."
    elif style == "humorous_non_tech":
        if any(token in anchor_lower for token in ("kitten", "cat")):
            ending = "like a tiny explorer claiming every patch of ground."
        elif any(token in anchor_lower for token in ("wave", "ocean", "beach", "shore")):
            ending = "like a toddler asking the same question on repeat."
        elif any(token in anchor_lower for token in ("runner", "track", "athlete")):
            ending = "like someone suddenly late for an appointment."
        else:
            ending = "with the determined focus of someone handling an oddly important errand."
    else:
        ending = "and apparently this ordinary scene has decided to become today's main event."
    return f"{anchor}, {ending}"


def _caption_clip_verified3(
    frames: list[Frame],
    task_id: str,
    config: ProviderConfig,
    deadline: float | None,
    ocr_text: list[str] | None = None,
) -> dict[str, str]:
    pipeline = os.environ.get("CLIO_PIPELINE", "").strip().lower()
    fast_batch_mode = pipeline in {"fast-kimi-gemma", "kimi-gemma-fast"}
    score_max_mode = pipeline in {"score-max-r1", "kimi-gemma-ensemble", "ensemble-r1"}
    reference_mode = pipeline in {"hybrid-kimi-reference", "reference-r1", "score-r1", "gemma-reference", "reference-gemma-r1", "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1", "fast-kimi-gemma", "kimi-gemma-fast"}
    gemma_reference_mode = pipeline in {"gemma-reference", "reference-gemma-r1"}
    concise_mode = pipeline in {"verified5-concise", "verified-5-concise", "precision", "concise"}
    champion_mode = pipeline in {"verified5-champion", "verified-5-champion", "champion-r3", "gemma-champion", "champion-r2"}
    batch_mode = fast_batch_mode or pipeline in {"champion-batch", "gemma-champion-batch", "champion-r4", "hybrid-kimi-batch", "kimi-grounded-batch"}
    hybrid_mode = fast_batch_mode or pipeline in {"verified5-kimi", "verified-5-kimi", "kimi-grounded", "hybrid-kimi", "hybrid-kimi8", "kimi-grounded8", "hybrid-kimi-batch", "kimi-grounded-batch", "hybrid-kimi-reference", "reference-r1", "score-r1", "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1"}
    hybrid_verified_mode = pipeline in {"hybrid-kimi8", "kimi-grounded8", "hybrid-kimi-batch", "kimi-grounded-batch", "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1"}
    balanced_mode = pipeline in {
        "verified5-balanced", "verified-5-balanced", "stylecal", "rebalanced",
        "verified5-kimi", "verified-5-kimi", "kimi-grounded", "hybrid-kimi",
        "hybrid-kimi8", "kimi-grounded8", "verified5-champion", "verified-5-champion",
        "champion-r3", "champion-r2", "gemma-champion", "champion-batch", "gemma-champion-batch", "champion-r4",
        "hybrid-kimi-batch", "kimi-grounded-batch",
        "hybrid-kimi-reference", "reference-r1", "score-r1", "gemma-reference", "reference-gemma-r1",
        "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1",
        "fast-kimi-gemma", "kimi-gemma-fast",
    }
    persona_mode = pipeline in {
        "verified5", "verified-5", "verified5-concise", "verified-5-concise", "precision", "concise",
        "verified5-balanced", "verified-5-balanced", "stylecal", "rebalanced",
        "verified5-kimi", "verified-5-kimi", "kimi-grounded", "hybrid-kimi", "hybrid-kimi8", "kimi-grounded8",
        "verified5-champion", "verified-5-champion", "champion-r3", "gemma-champion",
        "champion-r2", "champion-batch", "gemma-champion-batch", "champion-r4",
        "hybrid-kimi-batch", "kimi-grounded-batch",
        "hybrid-kimi-reference", "reference-r1", "score-r1", "gemma-reference", "reference-gemma-r1",
        "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1",
        "fast-kimi-gemma", "kimi-gemma-fast",
        "persona", "persona-grounded",
    }
    eight_frame_mode = pipeline in {"hybrid-kimi8", "kimi-grounded8", "champion-r3", "hybrid-kimi-batch", "kimi-grounded-batch"}
    anchors = frames if (score_max_mode or fast_batch_mode) else (_five_anchor_frames(frames) if reference_mode and not gemma_reference_mode else (
        _eight_anchor_frames(frames) if eight_frame_mode else (_four_anchor_frames(frames) if persona_mode else _three_anchor_frames(frames))
    ))
    draft_config = _vision_model_config(config) if hybrid_mode else config
    # The latency-optimized path should prefer the conservative evidence schema.
    # Dense reference evidence encouraged peripheral details that the simple
    # caption judge does not reward.
    grounding_prompt = _VERIFIED3_DRAFT_PROMPT if fast_batch_mode else (
        _REFERENCE_GROUNDING_PROMPT if reference_mode else _VERIFIED3_DRAFT_PROMPT
    )
    if ocr_text and reference_mode:
        grounding_prompt += "\n\nLOCAL OCR HINTS (use only when visibly corroborated):\n" + " | ".join(ocr_text[:12])
    try:
        draft_raw = _call(
            draft_config,
            _timeline_content(anchors, grounding_prompt),
            deadline=deadline,
            max_tokens=650,
            temperature=0.15,
        )
        draft = _parse_verified_evidence(draft_raw)
    except Exception as error:
        _log(f"verified3 evidence stage failed; using direct grounded generation: {error}")
        return _caption_clip_fast(anchors, task_id, config, deadline)
    verify_config = _verify_model_config(config)
    if hybrid_mode and not hybrid_verified_mode:
        evidence = draft
    else:
        review_prompt = _VERIFIED3_REVIEW_PROMPT + json.dumps(draft, ensure_ascii=False, indent=2)
        try:
            verified_raw = _call(
                verify_config,
                _timeline_content(anchors, review_prompt),
                deadline=deadline,
                max_tokens=900,
                temperature=0.05,
            )
            evidence = _parse_verified_evidence(verified_raw)
        except Exception as error:
            _log(f"verified3 second observer unavailable; retaining first evidence record: {error}")
            evidence = draft
    caption_config = _caption_model_config(config)
    captions: dict[str, str] = {}
    candidate_sets: dict[str, list[str]] | None = None
    if score_max_mode:
        try:
            candidate_sets = _kimi_style_candidates(anchors, evidence, draft_config, deadline)
            captions = _gemma_select_candidates(anchors, evidence, candidate_sets, caption_config, deadline)
        except Exception as error:
            _log(f"score-max candidate/rerank stage unavailable; using Gemma writers: {error}")
            captions = {}
    if batch_mode:
        batch_prompt = _CHAMPION_BATCH_PROMPT.format(
            evidence=json.dumps(evidence, ensure_ascii=False, indent=2)
        )
        try:
            captions = _parse_fast(
                _call(
                    caption_config,
                    ([{"type": "text", "text": batch_prompt}] if fast_batch_mode else _timeline_content(anchors, batch_prompt)),
                    deadline=deadline,
                    max_tokens=750 if fast_batch_mode else 1100,
                    temperature=0.55,
                )
            )
        except Exception as error:
            _log(f"champion batch writer unavailable; using per-style writers: {error}")
    if set(captions) != set(STYLES):
        if fast_batch_mode:
            captions = {
                style: _deterministic_verified_caption(style, evidence)
                for style in STYLES
            }
            _write_trace(
                task_id,
                {
                    "mode": pipeline,
                    "draft_model": draft_config.model,
                    "caption_model": caption_config.model,
                    "evidence": evidence,
                    "captions": captions,
                    "fallback": "deterministic-fast-batch",
                },
            )
            return captions
        captions = {}
        prior: list[str] = []
        for style in STYLES:
            try:
                caption = _write_verified3_style(
                    style,
                    evidence,
                    prior,
                    caption_config,
                    deadline,
                    anchors if persona_mode else None,
                    concise_mode,
                    balanced_mode,
                    champion_mode,
                    reference_mode,
                )
            except Exception as error:
                _log(f"verified3 {style} writer unavailable; using evidence-bound local caption: {error}")
                caption = _deterministic_verified_caption(style, evidence)
            captions[style] = caption
            prior.append(caption)
    if score_max_mode and set(captions) == set(STYLES):
        issues = _caption_batch_issues(captions, str(evidence.get("caption_anchor", "")))
        if issues:
            try:
                repaired = _gemma_repair_captions(anchors, evidence, captions, issues, caption_config, deadline)
                repaired_issues = _caption_batch_issues(repaired, str(evidence.get("caption_anchor", "")))
                if _issue_count(repaired_issues) <= _issue_count(issues):
                    captions = repaired
            except Exception as repair_error:
                _log(f"score-max deterministic repair unavailable; retaining selected captions: {repair_error}")
    if pipeline in {"verified4", "verified-4", "champion", "verified5", "verified-5", "verified5-concise", "verified-5-concise", "precision", "concise", "verified5-balanced", "verified-5-balanced", "stylecal", "rebalanced", "verified5-kimi", "verified-5-kimi", "kimi-grounded", "hybrid-kimi", "hybrid-kimi8", "kimi-grounded8", "hybrid-kimi-batch", "kimi-grounded-batch", "verified5-champion", "verified-5-champion", "champion-r3", "champion-r2", "gemma-champion", "champion-batch", "gemma-champion-batch", "champion-r4", "persona", "persona-grounded"}:
        final_prompt = _VERIFIED4_FINAL_PROMPT.format(
            evidence=json.dumps(evidence, ensure_ascii=False, indent=2),
            captions=json.dumps(captions, ensure_ascii=False, indent=2),
        ) + (
            "\nKeep every caption compact: formal 14-34 words; each creative style 12-32 words. "
            "Prefer one sentence or two short sentences, preserving one concrete visible detail and one clear style beat."
            if concise_mode else ""
        )
        if balanced_mode:
            final_prompt += (
                "\nFor this balanced profile, retain useful concrete detail and natural sentence length. "
                "Remove unsupported numbers, durations, names, locations, props, or literal unseen outcomes even when they appear inside a joke. "
                "Keep each creative punchline tied to the specific visible action or transformation. "
                "Reject generic legacy-process, weekday-task, empty-bleachers, or other stock formulas; rewrite the joke around the clip-specific detail."
            )
        if champion_mode:
            final_prompt += (
                "\nFor the champion profile, keep formal captions to the central subject/action/setting plus one or two "
                "unmistakable details; remove peripheral accessories, distant structures, and camera movement. "
                "Every creative caption must contain the visible subject/action before one scene-specific style beat. "
                "Reject generic scheduler/queue jokes, unfinished quotations, and malformed sentences."
            )
        try:
            reviewed_raw = _call(
                verify_config,
                _timeline_content(anchors, final_prompt),
                deadline=deadline,
                max_tokens=900,
                temperature=0.1,
            )
            reviewed = {style: _normalize(text) for style, text in _parse_fast(reviewed_raw).items()}
            reviewed = {
                style: (text[:1].upper() + text[1:] if text and text[0].islower() else text)
                for style, text in reviewed.items()
            }
            anchor = str(evidence.get("caption_anchor", ""))
            concise_ok = all(
                14 <= len(text.split()) <= (34 if style == "formal" else 32)
                for style, text in reviewed.items()
            ) if concise_mode else True
            champion_ok = all(
                14 <= len(text.split()) <= (32 if style == "formal" else 30)
                for style, text in reviewed.items()
            ) if champion_mode else True
            reviewed_issues = _caption_batch_issues(reviewed, anchor)
            has_malformed_quote = any(
                "unbalanced quotation" in issues
                for issues in reviewed_issues.values()
            )
            if concise_ok and champion_ok and not has_malformed_quote and _issue_count(reviewed_issues) <= _issue_count(_caption_batch_issues(captions, anchor)):
                captions = reviewed
        except Exception as error:
            _log(f"verified4 final grounding revision skipped: {error}")
    _write_trace(
        task_id,
        {
            "mode": pipeline or "verified3",
            "vision_model": config.model,
            "draft_model": draft_config.model,
            "verification_model": verify_config.model,
            "caption_model": caption_config.model,
            "candidate_sets": candidate_sets,
            "draft": draft,
            "evidence": evidence,
            "captions": captions,
            "issues": _caption_batch_issues(captions, str(evidence.get("caption_anchor", ""))),
        },
    )
    return captions


def _caption_clip_verified7(frames: list[Frame], task_id: str, config: ProviderConfig, deadline: float | None) -> dict[str, str]:
    anchors = _eight_anchor_frames(frames)
    try:
        draft_raw = _call(
            config,
            _timeline_content(anchors, _VERIFIED3_DRAFT_PROMPT),
            deadline=deadline,
            max_tokens=800,
            temperature=0.1,
        )
        draft = _parse_verified_evidence(draft_raw)
    except Exception as error:
        _log(f"verified7 evidence stage failed; using direct grounded generation: {error}")
        return _caption_clip_fast(_four_anchor_frames(anchors), task_id, config, deadline)
    verify_config = _verify_model_config(config)
    evidence = draft
    try:
        review_prompt = _VERIFIED3_REVIEW_PROMPT + json.dumps(draft, ensure_ascii=False, indent=2)
        verified_raw = _call(
            verify_config,
            _timeline_content(anchors[:6], review_prompt),
            deadline=deadline,
            max_tokens=800,
            temperature=0.05,
        )
        evidence = _parse_verified_evidence(verified_raw)
    except Exception as error:
        _log(f"verified7 evidence review skipped: {error}")

    caption_config = _caption_model_config(config)
    style_frames = _four_anchor_frames(anchors)
    candidates: dict[str, list[str]] = {}
    for style in STYLES:
        try:
            pair = _write_verified7_pair(style, evidence, style_frames, caption_config, deadline)
            candidates[style] = [pair[0], pair[1]]
        except Exception as error:
            _log(f"verified7 {style} pair unavailable: {error}")
            try:
                single = _write_verified3_style(style, evidence, [], caption_config, deadline, style_frames)
            except Exception as fallback_error:
                _log(f"verified7 {style} single fallback unavailable: {fallback_error}")
                single = _deterministic_verified_caption(style, evidence)
            backup = _deterministic_verified_caption(style, evidence)
            candidates[style] = [single, backup if backup.casefold() != single.casefold() else single]

    pick_prompt = _VERIFIED6_PICK_PROMPT.format(
        evidence=json.dumps(evidence, ensure_ascii=False, indent=2),
        candidates=json.dumps(candidates, ensure_ascii=False, indent=2),
    )
    try:
        picked_raw = _call(
            verify_config,
            _timeline_content(anchors[:6], pick_prompt),
            deadline=deadline,
            max_tokens=900,
            temperature=0.0,
        )
        picked = _parse_fast(picked_raw)
        captions: dict[str, str] = {}
        for style in STYLES:
            matches = [
                index for index, candidate in enumerate(candidates[style])
                if candidate.casefold() == picked[style].casefold()
            ]
            if not matches:
                raise EvidencePipelineError(f"verified7 picker rewrote the {style} candidate")
            chosen = matches[0]
            alternate = 1 - chosen
            if len(_candidate_quality_issues(style, candidates[style][alternate])) < len(
                _candidate_quality_issues(style, candidates[style][chosen])
            ):
                chosen = alternate
            captions[style] = candidates[style][chosen]
    except Exception as error:
        _log(f"verified7 visual picker skipped: {type(error).__name__}: {error!r}")
        captions = {
            style: min(candidates[style], key=lambda value: len(_candidate_quality_issues(style, value)))
            for style in STYLES
        }
    _write_trace(
        task_id,
        {
            "mode": "verified7-pairs-picker",
            "evidence": evidence,
            "candidates": candidates,
            "captions": captions,
            "issues": _caption_batch_issues(captions),
        },
    )
    return captions


def caption_clip_evidence(
    frames: list[Frame],
    task_id: str,
    model: Optional[str] = None,
    timeout_s: Optional[float] = None,
    ocr_text: list[str] | None = None,
) -> dict[str, str]:
    if not frames:
        raise EvidencePipelineError(f"no frames available for {task_id}")
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    config = provider_config()
    if model:
        config = replace(config, model=model)
    enforce = os.environ.get("CLIO_ENFORCE_NOVITA", "").lower() in {"1", "true", "yes"}
    if "gemma" not in config.model.lower():
        raise EvidencePipelineError("production generation model must be Gemma-family")
    if enforce and ("novita.ai" not in config.base_url.lower() or config.model.lower() not in {m.lower() for m in NOVITA_GEMMA_MODELS}):
        raise EvidencePipelineError("Novita-only mode requires an allowed Gemma 4 31B or Gemma 3 27B model")
    _log(f"evidence: Gemma model={config.model} task={task_id}")
    pipeline = os.environ.get("CLIO_PIPELINE", "").strip().lower()
    if pipeline in {"verified7", "verified-7", "pairs-picker"}:
        return _caption_clip_verified7(frames, task_id, config, deadline)
    if pipeline in {
        "verified3", "verified-3", "verified-sequential",
        "verified4", "verified-4", "champion",
        "verified5", "verified-5", "verified5-concise", "verified-5-concise",
        "precision", "concise", "verified5-balanced", "verified-5-balanced",
        "stylecal", "rebalanced", "verified5-kimi", "verified-5-kimi",
        "kimi-grounded", "hybrid-kimi", "hybrid-kimi8", "kimi-grounded8",
        "verified5-champion", "verified-5-champion", "champion-r3", "champion-r2", "gemma-champion",
        "champion-batch", "gemma-champion-batch", "champion-r4",
        "hybrid-kimi-batch", "kimi-grounded-batch",
        "hybrid-kimi-reference", "reference-r1", "score-r1", "gemma-reference", "reference-gemma-r1",
        "score-max-r1", "kimi-gemma-ensemble", "ensemble-r1",
        "fast-kimi-gemma", "kimi-gemma-fast",
        "persona", "persona-grounded",
    }:
        return _caption_clip_verified3(frames, task_id, config, deadline, ocr_text=ocr_text)
    if pipeline in {"verified2", "verified-2", "two-stage"}:
        return _caption_clip_verified2(frames, task_id, config, deadline)
    if os.environ.get("CLIO_FAST_MODE", "").lower() in {"1", "true", "yes"}:
        return _caption_clip_fast(frames, task_id, config, deadline)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_call, config, _timeline_content(frames, _EVIDENCE_PROMPT), deadline=deadline, max_tokens=5000, temperature=0.1),
            pool.submit(_call, config, _timeline_content(frames, _SKEPTICAL_PROMPT), deadline=deadline, max_tokens=5000, temperature=0.1),
        ]
        report_a, report_b = [future.result() for future in futures]
    if min(len(report_a.split()), len(report_b.split())) < 12:
        raise EvidencePipelineError("evidence report too short")
    evidence = _call(config, _timeline_content(frames, _CONSENSUS_PROMPT.format(report_a=report_a, report_b=report_b)), deadline=deadline, max_tokens=5000, temperature=0.05)
    if len(evidence.split()) < 12:
        raise EvidencePipelineError("consensus report too short")

    pairs: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=len(STYLES)) as pool:
        futures = {pool.submit(_candidate_pair, style, frames, evidence, config, deadline): style for style in STYLES}
        for future in as_completed(futures):
            pairs[futures[future]] = future.result()
    selected: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(STYLES)) as pool:
        futures = {pool.submit(_select, style, pairs[style], frames, evidence, config, deadline): style for style in STYLES}
        for future in as_completed(futures):
            selected[futures[future]] = future.result()
    if set(selected) != set(STYLES) or not all(selected[style].strip() for style in STYLES):
        raise EvidencePipelineError("caption schema incomplete")
    result = {style: selected[style].strip() for style in STYLES}
    _write_trace(task_id, {"report_a": report_a, "report_b": report_b, "consensus": evidence, "candidates": pairs, "selected": result})
    return result
