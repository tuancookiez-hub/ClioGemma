from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image, ImageDraw

from app.core.frames import Frame


def build_timeline_grids(
    frames: list[Frame],
    *,
    cell_size: int = 480,
    cols: int = 4,
    rows: int = 4,
    quality: int = 85,
) -> list[str]:
    """Encode chronological frames as labelled contact-sheet JPEG data URLs.

    A grid lets a vision model inspect many more temporal states in one request
    than sending only a handful of individual images. Labels are annotations,
    not video content, and empty cells are black.
    """
    if not frames:
        return []
    cell_size = max(160, int(cell_size))
    cols = max(1, int(cols))
    rows = max(1, int(rows))
    capacity = cols * rows
    grids: list[str] = []
    for start in range(0, len(frames), capacity):
        canvas = Image.new("RGB", (cell_size * cols, cell_size * rows), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        for slot, frame in enumerate(frames[start : start + capacity]):
            try:
                with Image.open(frame.path) as source:
                    image = source.convert("RGB")
                    image.thumbnail((cell_size - 12, cell_size - 12), Image.Resampling.LANCZOS)
                    x = (slot % cols) * cell_size + (cell_size - image.width) // 2
                    y = (slot // cols) * cell_size + (cell_size - image.height) // 2
                    canvas.paste(image, (x, y))
            except (OSError, ValueError):
                continue
            label = f"F{frame.index + 1:02d}"
            x0 = (slot % cols) * cell_size + 5
            y0 = (slot // cols) * cell_size + 5
            draw.rectangle((x0 - 2, y0 - 2, x0 + 28, y0 + 14), fill=(0, 0, 0))
            draw.text((x0, y0), label, fill=(255, 220, 80))
        output = BytesIO()
        canvas.save(output, format="JPEG", quality=max(50, min(95, quality)), optimize=True)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        grids.append(f"data:image/jpeg;base64,{encoded}")
    return grids
