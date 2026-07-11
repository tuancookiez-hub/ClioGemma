"""Novita + Gemma-only evidence-first caption generation."""
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
from app.core.parse import STYLES
from app.core.provider import NOVITA_GEMMA_MODELS, ProviderConfig, provider_config


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

_TECH = {
    "algorithm", "api", "bandwidth", "binary", "cache", "code", "commit",
    "compile", "cpu", "database", "debug", "deploy", "download", "gpu",
    "json", "kernel", "latency", "network", "packet", "program", "regex",
    "render", "repo", "runtime", "script", "server", "software", "upload",
    "wifi",
}
_SPECULATIVE = re.compile(
    r"\b(probably|likely|decides?|wants?|remembers?|pretends?|believes?|hopes?|trying to|plans? to|about to)\b",
    re.I,
)
_PROCESS = re.compile(r"\b(frames?|sampling|model|prompt|analysis|detection|uncertain(?:ty)?)\b", re.I)
_RELATIONSHIP = re.compile(r"\b(family|mother|father|parent|sibling|owner|coworker|colleague|couple|husband|wife|daughter|son)\b", re.I)
_DURATION = re.compile(r"\b\d+(?:\.\d+)?\s+(?:seconds?|minutes?|hours?)\b", re.I)


def _remaining(deadline: float | None) -> float | None:
    return None if deadline is None else deadline - time.monotonic()


def _timeout(config: ProviderConfig, deadline: float | None) -> float:
    left = _remaining(deadline)
    value = config.timeout_s if left is None else min(config.timeout_s, left - 0.5)
    if value < 1:
        raise EvidencePipelineError("clip deadline exhausted")
    return value


def _call(config: ProviderConfig, content: list[dict], *, deadline: float | None, max_tokens: int, temperature: float) -> str:
    timeout = _timeout(config, deadline)
    client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=timeout, max_retries=1)
    response = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    message = response.choices[0].message
    text = message.content or getattr(message, "reasoning_content", "") or ""
    if not isinstance(text, str) or not text.strip():
        raise EvidencePipelineError("provider returned empty content")
    return text.strip()


def _timeline_content(frames: list[Frame], prompt: str) -> list[dict]:
    if not frames:
        raise EvidencePipelineError("no frames")
    parts: list[dict] = [{"type": "text", "text": "Chronological labelled visual evidence follows."}]
    for index, frame in enumerate(frames[:8], 1):
        parts.append({"type": "text", "text": f"[F{index:02d}]"})
        data = base64.b64encode(frame.path.read_bytes()).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
    parts.append({"type": "text", "text": prompt})
    return parts


def _normalize(raw: str) -> str:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:text|markdown)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    return re.sub(r"\s+", " ", text).strip(" \t\"'")


def _style_issues(style: str, caption: str) -> list[str]:
    words = re.findall(r"\b[\w'-]+\b", caption)
    issues: list[str] = []
    if not 18 <= len(words) <= 42:
        issues.append("word count must be 18-42")
    if _PROCESS.search(caption):
        issues.append("process leakage")
    if _SPECULATIVE.search(caption):
        issues.append("speculative intent")
    if _RELATIONSHIP.search(caption):
        issues.append("inferred relationship")
    if _DURATION.search(caption):
        issues.append("precise duration")
    hits = {word for word in _TECH if re.search(rf"\b{re.escape(word)}s?\b", caption, re.I)}
    if style == "humorous_tech" and not hits:
        issues.append("missing tech comparison")
    if style == "humorous_non_tech" and hits:
        issues.append("technical jargon")
    if style == "formal" and ("!" in caption or "?" in caption):
        issues.append("formal punctuation")
    if style == "sarcastic" and "!" in caption:
        issues.append("sarcasm exclamation")
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


def _parse_fast(raw: str) -> dict[str, str]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise EvidencePipelineError("fast Gemma call returned no JSON")
    data = json.loads(match.group(0))
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


def _caption_clip_fast(frames: list[Frame], task_id: str, config: ProviderConfig, deadline: float | None) -> dict[str, str]:
    raw = _call(config, _timeline_content(frames, _FAST_PROMPT), deadline=deadline, max_tokens=1200, temperature=0.25)
    captions = _parse_fast(raw)
    _write_trace(task_id, {"mode": "fast", "captions": captions})
    return captions


def caption_clip_evidence(frames: list[Frame], task_id: str, model: Optional[str] = None, timeout_s: Optional[float] = None) -> dict[str, str]:
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
