from __future__ import annotations

import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Frame:
    path: Path
    index: int
    t_sec: float
    brightness: float = 0.0
    sharpness: float = 0.0
    motion: float = 0.0


def _pixels(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.float32)


def _metrics(pixels: np.ndarray, previous: np.ndarray | None = None) -> tuple[float, float, float]:
    brightness = float(pixels.mean() / 255.0)
    if min(pixels.shape) < 3:
        sharpness = 0.0
    else:
        lap = pixels[:-2, 1:-1] + pixels[2:, 1:-1] + pixels[1:-1, :-2] + pixels[1:-1, 2:] - 4 * pixels[1:-1, 1:-1]
        sharpness = float(lap.var() / (255.0 * 255.0))
    motion = 0.0 if previous is None else float(np.abs(pixels - previous).mean() / 255.0)
    return brightness, sharpness, motion


def probe_duration(video: Path, timeout_s: float = 20.0) -> float:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)], check=True, capture_output=True, text=True, timeout=timeout_s)
        return max(float(result.stdout.strip() or "0"), 0.0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0.0


def mine_frames(video: Path, out_dir: Path, *, count: int = 5, width: int = 896, deadline: float | None = None, strategy: str = "anchors") -> list[Frame]:
    strategy = strategy.lower().strip()
    if strategy not in {"anchors", "seek", "uniform"}:
        raise ValueError(f"unknown frame strategy: {strategy}")
    count = max(1, min(count, 16))
    width = max(160, width)
    duration = probe_duration(video, timeout_s=5.0)
    if duration <= 0:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    if count == 1:
        positions = [duration * 0.5]
    elif strategy == "anchors":
        positions = [duration * (0.05 + 0.90 * index / (count - 1)) for index in range(count)]
    else:
        positions = [min(duration * index / (count - 1), duration * 0.999) for index in range(count)]
    paths: list[tuple[Path, float]] = []
    for index, timestamp in enumerate(positions):
        if deadline is not None and deadline - time.monotonic() <= 0:
            break
        output = out_dir / f"{strategy}_{index:03d}.jpg"
        try:
            result = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{timestamp:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:{width}:force_original_aspect_ratio=decrease", str(output)], check=False, capture_output=True, text=True, timeout=15.0)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and output.exists():
            paths.append((output, round(timestamp, 3)))
    frames: list[Frame] = []
    previous: np.ndarray | None = None
    for index, (path, timestamp) in enumerate(paths):
        pixels = _pixels(path)
        brightness, sharpness, motion = _metrics(pixels, previous)
        previous = pixels
        frames.append(Frame(path, index, timestamp, brightness, sharpness, motion))
    return frames[:count]


def clean_frames(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
