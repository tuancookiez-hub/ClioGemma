"""Optional local OCR for large, readable on-screen text."""
from __future__ import annotations

import re

from app.core.frames import Frame


def extract_visible_text(frames: list[Frame], *, max_chars: int = 1200) -> list[str]:
    """Return conservative OCR lines; an unavailable OCR engine is non-fatal."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return []
    seen: set[str] = set()
    lines: list[str] = []
    for frame in frames:
        try:
            with Image.open(frame.path) as image:
                text = pytesseract.image_to_string(image.convert("RGB"), config="--psm 6")
        except Exception:
            continue
        for raw in re.split(r"[\r\n]+", text):
            value = re.sub(r"\s+", " ", raw).strip(" |\t")
            if len(value) < 3 or value.casefold() in seen:
                continue
            seen.add(value.casefold())
            lines.append(value)
            if sum(len(item) + 1 for item in lines) >= max_chars:
                return lines
    return lines
