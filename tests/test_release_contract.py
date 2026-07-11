from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.parse import STYLES, parse_styles
from app.core.provider import ProviderError, provider_config
from app.evidence_pipeline import _retry_delay, _retryable_status
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

    assert _retryable_status(RateLimitError()) == 429
    assert _retryable_status(BadRequestError()) is None
    assert [_retry_delay(index) for index in range(5)] == [1.5, 3.0, 6.0, 6.0, 6.0]
