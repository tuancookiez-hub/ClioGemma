"""One-clip generation smoke; deliberately does not call a judge."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.frames import mine_frames  # noqa: E402
from app.core.parse import STYLES  # noqa: E402
from app.evidence_pipeline import caption_clip_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", default="google/gemma-3-27b-it")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    os.environ.setdefault("CLIO_ENFORCE_NOVITA", "1")
    os.environ.setdefault("CLIO_FAST_MODE", "1")
    frames = mine_frames(args.video, ROOT / ".smoke_frames", count=5, width=896, strategy="anchors")
    if len(frames) != 5:
        raise SystemExit(f"expected 5 frames, got {len(frames)}")
    started = time.monotonic()
    captions = caption_clip_evidence(frames, args.video.stem, model=args.model, timeout_s=125)
    if set(captions) != set(STYLES) or not all(captions[style].strip() for style in STYLES):
        raise SystemExit("caption schema failed")
    report = {"model": args.model, "video": str(args.video), "elapsed_s": round(time.monotonic() - started, 3), "captions": captions}
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"model": args.model, "elapsed_s": report["elapsed_s"], "styles": list(captions)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
