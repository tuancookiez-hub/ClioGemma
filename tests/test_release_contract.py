from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.parse import STYLES, parse_styles
from app.core.provider import ProviderError, provider_config
from app.evidence_pipeline import (
    _caption_batch_issues,
    _caption_model_config,
    _candidate_quality_issues,
    _deterministic_verified_caption,
    _eight_anchor_frames,
    _five_anchor_frames,
    _four_anchor_frames,
    _parse_verified_evidence,
    _normalize,
    _retry_delay,
    _retryable_status,
    _three_anchor_frames,
    _vision_model_config,
    _verify_model_config,
)
from app.core.frames import Frame
from app.core.provider import ProviderConfig
from app.visual import run


def test_parser_requires_exact_four_style_keys() -> None:
    raw = json.dumps({style: style for style in STYLES})
    assert parse_styles(raw, recover=False) == {style: style for style in STYLES}
    assert parse_styles(json.dumps({"formal": "only one"}), recover=False) == {}


def test_novita_lock_rejects_other_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLIO_ENFORCE_NOVITA", "1")
    monkeypatch.setenv("CLIO_API_KEY", "test")
    monkeypatch.setenv("CLIO_BASE_URL", "https://api.pioneer.ai/v1")
    monkeypatch.setenv("CLIO_MODEL", "claude-sonnet-4-5")
    with pytest.raises(ProviderError, match="Novita"):
        provider_config()


def test_runner_writes_schema_when_task_has_no_url(tmp_path: Path) -> None:
    input_path = tmp_path / "tasks.json"
    output_path = tmp_path / "results.json"
    input_path.write_text(json.dumps([{"task_id": "t1", "styles": list(STYLES)}]), encoding="utf-8")
    assert run(input_path, output_path) == 0
    rows = json.loads(output_path.read_text(encoding="utf-8"))
    assert rows[0]["task_id"] == "t1"
    assert set(rows[0]["captions"]) == set(STYLES)


def test_provider_retry_policy_is_bounded() -> None:
    class RateLimitError(Exception):
        status_code = 429

    class BadRequestError(Exception):
        status_code = 400

    class RequestTimeout(Exception):
        pass

    assert _retryable_status(RateLimitError()) == 429
    assert _retryable_status(BadRequestError()) is None
    assert _retryable_status(RequestTimeout("request timed out")) == 408
    assert [_retry_delay(index) for index in range(5)] == [1.5, 3.0, 6.0, 6.0, 6.0]


def test_verified_evidence_parser_and_style_guard() -> None:
    assert _normalize("**deployment** via `queue`") == "deployment via queue"
    assert _normalize("thatâ€™s ready") == "that's ready"
    assert "stock style formula" in _candidate_quality_issues(
        "sarcastic",
        "Behold the thrilling spectacle of cars moving through a city road past yellow trees and tall apartment buildings in the background.",
    )
    assert "stock style formula" not in _candidate_quality_issues(
        "sarcastic",
        "Cars file past yellow trees and apartment towers, maintaining the solemn urban tradition of moving three metres before reconsidering every life choice.",
    )
    evidence = _parse_verified_evidence(
        '```json\n{"scene":"street","subjects":["train"],'
        '"stable_facts":["a train is visible","tracks are visible"],'
        '"timeline":["beginning: train approaches"],'
        '"caption_anchor":"A train is beside a platform",'
        '"visible_text":[],"do_not_claim":[]}\n```'
    )
    assert evidence["scene"] == "street"
    captions = {
        "formal": "A train travels beside a platform while trees line the railway in the background.",
        "sarcastic": "A train travels beside a platform, because apparently rails remain its preferred route today.",
        "humorous_tech": "A train travels beside a platform like a data packet moving through a network route.",
        "humorous_non_tech": "A train travels beside a platform like a JPEG captured from several video frames.",
    }
    issues = _caption_batch_issues(captions)
    assert "humorous_non_tech" in issues
    assert "stock style formula" in _caption_batch_issues({
        "formal": "A train travels beside a platform while trees line the railway in the background.",
        "sarcastic": "A train travels beside a platform, because apparently rails remain its preferred route today.",
        "humorous_tech": "A train travels beside a platform, like a software task waiting on one visible input.",
        "humorous_non_tech": "A train travels beside a platform with an unexpectedly dramatic sense of purpose.",
    })["humorous_tech"]
    assert "stock style formula" in _caption_batch_issues({
        "formal": "A train travels beside a platform while trees line the railway in the background.",
        "sarcastic": "A train travels beside a platform, because apparently rails remain popular today.",
        "humorous_tech": "A train travels beside a platform like a packet following a stable network route.",
        "humorous_non_tech": "A train races past the platform like someone who remembered they left the oven on.",
    })["humorous_non_tech"]
    assert "unsupported brand claim" in _caption_batch_issues({
        "formal": "A woman types on an iMac at a white desk inside a modern office.",
        "sarcastic": "A woman types at a desktop computer, clearly saving civilization one email at a time.",
        "humorous_tech": "A woman types at a desktop computer like a user feeding requests into a server.",
        "humorous_non_tech": "A woman types at a desktop computer like someone finishing the final item on a long list.",
    })["formal"]
    fallback = _deterministic_verified_caption(
        "humorous_tech",
        {"caption_anchor": "A train travels beside a platform"},
    )
    assert "train" in fallback.lower() and "software operation" in fallback.lower()


def test_verified3_uses_first_middle_last_and_gemma_caption_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = [Frame(tmp_path / f"{index}.jpg", index, float(index)) for index in range(5)]
    assert [frame.index for frame in _three_anchor_frames(frames)] == [0, 2, 4]
    assert [frame.index for frame in _four_anchor_frames(frames)] == [0, 1, 3, 4]
    assert [frame.index for frame in _five_anchor_frames(frames)] == [0, 1, 2, 3, 4]
    assert [frame.index for frame in _eight_anchor_frames(frames)] == [0, 1, 2, 3, 4]
    monkeypatch.setenv("CLIO_ENFORCE_NOVITA", "1")
    monkeypatch.setenv("CLIO_CAPTION_MODEL", "google/gemma-4-31b-it")
    monkeypatch.setenv("CLIO_VERIFY_MODEL", "google/gemma-4-31b-it")
    config = ProviderConfig("test", "https://api.novita.ai/openai", "google/gemma-3-27b-it", 25.0)
    assert _caption_model_config(config).model == "google/gemma-4-31b-it"
    assert _verify_model_config(config).model == "google/gemma-4-31b-it"
    monkeypatch.setenv("CLIO_VISION_MODEL", "moonshotai/kimi-k2.6")
    assert _vision_model_config(config).model == "moonshotai/kimi-k2.6"


def test_champion_profile_keeps_anchor_and_normalizes_final_caption(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import app.evidence_pipeline as pipeline

    frames = []
    for index in range(4):
        path = tmp_path / f"{index}.jpg"
        path.write_bytes(b"frame")
        frames.append(Frame(path, index, float(index)))

    evidence = {
        "scene": "street",
        "subjects": ["train"],
        "stable_facts": ["a train is visible", "a platform is visible"],
        "timeline": ["beginning: train beside platform"],
        "scene_story": "A train remains beside a platform.",
        "caption_anchor": "A train travels beside a platform",
        "visible_text": [],
        "do_not_claim": [],
    }

    def fake_call(config, content, *, deadline, max_tokens, temperature):
        prompt = " ".join(str(part.get("text", "")) for part in content if part.get("type") == "text")
        if "Perform one final image-grounded revision" in prompt:
            return json.dumps({
                "formal": "a train travels beside a platform at a visible station structure in an outdoor setting.",
                "sarcastic": "A train travels beside a platform, because apparently rails remain popular today.",
                "humorous_tech": "A train travels beside a platform, like a packet following a stable network route.",
                "humorous_non_tech": "A train travels beside a platform, like someone taking the long way home on purpose.",
            })
        if "Return a conservative JSON evidence record" in prompt:
            return json.dumps(evidence)
        if "Act as a strict second visual observer" in prompt:
            return json.dumps(evidence)
        if "Write like a burnt-out software engineer" in prompt:
            return "A train travels beside a platform, like a packet following a stable network route."
        if "Write like an observant everyday comedian" in prompt:
            return "A train travels beside a platform, like someone taking the long way home on purpose."
        if "Write with the voice of a weary" in prompt:
            return "A train travels beside a platform, because apparently rails remain popular today."
        return "A train travels beside a platform at a visible station structure in an outdoor setting."

    monkeypatch.setattr(pipeline, "_call", fake_call)
    monkeypatch.setenv("CLIO_PIPELINE", "verified5-champion")
    monkeypatch.setenv("CLIO_ENFORCE_NOVITA", "1")
    config = ProviderConfig("test", "https://api.novita.ai/openai", "google/gemma-4-31b-it", 25.0)
    result = pipeline._caption_clip_verified3(frames, "champion-test", config, None)
    assert result["formal"].startswith("A train travels")
    assert "packet" in result["humorous_tech"]
    assert not pipeline._caption_batch_issues(result)


def test_reference_profile_uses_kimi_grounding_and_skips_global_rewrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import app.evidence_pipeline as pipeline

    frames = []
    for index in range(5):
        path = tmp_path / f"reference-{index}.jpg"
        path.write_bytes(b"frame")
        frames.append(Frame(path, index, float(index)))

    evidence = {
        "summary": "A train moves beside a platform. Trees line the railway.",
        "scene": "outdoor railway platform",
        "subjects": ["train", "platform", "trees"],
        "primary_action": "the train moves beside the platform",
        "stable_facts": ["a train is visible", "a platform is visible", "trees line the railway"],
        "visual_details": ["metal train", "outdoor platform", "green trees"],
        "timeline": ["beginning: train approaches", "middle: train passes", "end: train remains visible"],
        "temporal_arc": "The train changes position beside the platform.",
        "caption_anchor": "A train moves beside an outdoor platform",
        "visible_text": [],
        "do_not_claim": [],
    }
    calls: list[tuple[str, str]] = []

    def fake_call(config, content, *, deadline, max_tokens, temperature):
        prompt = " ".join(str(part.get("text", "")) for part in content if part.get("type") == "text")
        calls.append((config.model, prompt))
        if "five chronological images" in prompt:
            return json.dumps(evidence)
        if "documentary-quality formal caption" in prompt:
            return "A train moves beside an outdoor platform as green trees line the railway behind it."
        if "genuinely sarcastic caption" in prompt:
            return "A train moves beside a leafy outdoor platform, naturally choosing the one route where getting lost would require genuine effort."
        if "developer-facing caption" in prompt:
            return "A train moves beside a tree-lined platform like one well-routed packet following a very visible physical network path."
        if "broadly relatable everyday joke" in prompt:
            return "A train moves beside a leafy platform with the confidence of someone who has finally remembered exactly where they parked."
        raise AssertionError("reference profile unexpectedly invoked another model stage")

    monkeypatch.setattr(pipeline, "_call", fake_call)
    monkeypatch.setenv("CLIO_PIPELINE", "hybrid-kimi-reference")
    monkeypatch.setenv("CLIO_VISION_MODEL", "moonshotai/kimi-k2.6")
    monkeypatch.setenv("CLIO_CAPTION_MODEL", "google/gemma-4-31b-it")
    monkeypatch.setenv("CLIO_VERIFY_MODEL", "google/gemma-4-31b-it")
    monkeypatch.setenv("CLIO_ENFORCE_NOVITA", "1")
    config = ProviderConfig("test", "https://api.novita.ai/openai", "google/gemma-4-31b-it", 25.0)
    result = pipeline._caption_clip_verified3(frames, "reference-test", config, None)
    assert set(result) == set(STYLES)
    assert calls[0][0] == "moonshotai/kimi-k2.6"
    assert all(model == "google/gemma-4-31b-it" for model, _ in calls[1:])
    assert not any("Perform one final image-grounded revision" in prompt for _, prompt in calls)
    assert "well-routed packet" in result["humorous_tech"]
