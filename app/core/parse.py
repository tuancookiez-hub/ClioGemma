from __future__ import annotations

import json
import re

STYLES = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")


def parse_styles(raw: str, *, recover: bool = True) -> dict[str, str]:
    text = (raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if not recover:
            return {}
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict) or set(data) != set(STYLES):
        return {}
    if not all(isinstance(data[key], str) and data[key].strip() for key in STYLES):
        return {}
    return {key: " ".join(data[key].split()) for key in STYLES}
