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
    _eight_anchor_frames,
    _four_anchor_frames,
    _parse_verified_evidence,
    _normalize,
    _retry_delay,
    _retryable_status,
    _three_anchor_frames,
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


def test_verified3_uses_first_middle_last_and_gemma_caption_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = [Frame(tmp_path / f"{index}.jpg", index, float(index)) for index in range(5)]
    assert [frame.index for frame in _three_anchor_frames(frames)] == [0, 2, 4]
    assert [frame.index for frame in _four_anchor_frames(frames)] == [0, 1, 3, 4]
    assert [frame.index for frame in _eight_anchor_frames(frames)] == [0, 1, 2, 3, 4]
    monkeypatch.setenv("CLIO_ENFORCE_NOVITA", "1")
    monkeypatch.setenv("CLIO_CAPTION_MODEL", "google/gemma-4-31b-it")
    monkeypatch.setenv("CLIO_VERIFY_MODEL", "google/gemma-4-31b-it")
    config = ProviderConfig("test", "https://api.novita.ai/openai", "google/gemma-3-27b-it", 25.0)
    assert _caption_model_config(config).model == "google/gemma-4-31b-it"
    assert _verify_model_config(config).model == "google/gemma-4-31b-it"
