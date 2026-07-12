from __future__ import annotations

import os
from dataclasses import dataclass

NOVITA_BASE_URL = "https://api.novita.ai/openai"
NOVITA_GEMMA_MODELS = frozenset({"google/gemma-4-31b-it", "google/gemma-3-27b-it"})
NOVITA_VISION_MODELS = frozenset({"moonshotai/kimi-k2.6"})


class ProviderError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    base_url: str
    model: str
    timeout_s: float


def provider_config() -> ProviderConfig:
    key = os.environ.get("CLIO_API_KEY", "").strip() or os.environ.get("NOVITA_API_KEY", "").strip()
    if not key:
        raise ProviderError("Novita API key missing; set CLIO_API_KEY or NOVITA_API_KEY")
    base_url = os.environ.get("CLIO_BASE_URL", "").strip() or os.environ.get("NOVITA_BASE_URL", "").strip() or NOVITA_BASE_URL
    model = os.environ.get("CLIO_MODEL", "").strip() or os.environ.get("NOVITA_MODEL", "").strip() or "google/gemma-3-27b-it"
    try:
        timeout_s = float(os.environ.get("CLIO_REQUEST_TIMEOUT", "25"))
    except ValueError as error:
        raise ProviderError("CLIO_REQUEST_TIMEOUT must be numeric") from error
    if timeout_s <= 0:
        raise ProviderError("CLIO_REQUEST_TIMEOUT must be positive")
    if os.environ.get("CLIO_ENFORCE_NOVITA", "").lower() in {"1", "true", "yes"}:
        if "novita.ai" not in base_url.lower():
            raise ProviderError("Novita-only mode requires the Novita endpoint")
        if model.lower() not in {item.lower() for item in NOVITA_GEMMA_MODELS}:
            raise ProviderError("Novita-only mode permits Gemma 4 31B or Gemma 3 27B")
    return ProviderConfig(key, base_url, model, timeout_s)
