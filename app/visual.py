"""Track 2 Docker entrypoint and bounded batch runner."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.core.frames import mine_frames
from app.core.parse import STYLES

FALLBACK = "The video clip could not be captioned."


def _fallback(styles: list[str]) -> dict[str, str]:
    return {style: FALLBACK for style in styles}


def _download(url: str, destination: Path, deadline: float | None) -> Path:
    if url.startswith("file://"):
        path = Path(url[7:])
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    if Path(url).exists():
        return Path(url)
    request = urllib.request.Request(url, headers={"User-Agent": "ClioGemma/1.0"})
    timeout = 20.0 if deadline is None else max(1.0, min(20.0, deadline - time.monotonic()))
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as stream:
        while True:
            if deadline is not None and deadline - time.monotonic() <= 0:
                raise TimeoutError("download deadline exceeded")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            stream.write(chunk)
    return destination


def run_task_combined(video_url: str, task_id: str, styles: list[str], out_dir: Path, deadline: float | None = None) -> dict[str, str]:
    from app.evidence_pipeline import caption_clip_evidence

    work = out_dir / task_id
    work.mkdir(parents=True, exist_ok=True)
    video = _download(video_url, work / "video.mp4", deadline)
    strategy = os.environ.get("SWIFTCLIP_FRAME_STRATEGY", "anchors")
    count = int(os.environ.get("SWIFTCLIP_FRAME_COUNT", "5"))
    width = int(os.environ.get("SWIFTCLIP_FRAME_WIDTH", "896"))
    frames = mine_frames(video, work / "frames", count=count, width=width, strategy=strategy, deadline=deadline)
    if not frames:
        raise RuntimeError("frame extraction failed")
    timeout = None if deadline is None else max(1.0, deadline - time.monotonic())
    captions = caption_clip_evidence(frames, task_id, timeout_s=timeout)
    return {style: captions.get(style, "") for style in styles}


def runtime_config() -> tuple[float, float, int]:
    hard = min(float(os.environ.get("SWIFTCLIP_DEADLINE_S", "570")), 570.0)
    per_clip = min(float(os.environ.get("SWIFTCLIP_CLIP_TIMEOUT", "125")), hard)
    parallel = min(int(os.environ.get("SWIFTCLIP_PARALLEL", "2")), 8)
    if hard <= 0 or per_clip <= 0 or parallel <= 0:
        raise ValueError("runtime values must be positive")
    return hard, per_clip, parallel


def run(input_path: Path, output_path: Path) -> int:
    try:
        tasks = json.loads(input_path.read_text(encoding="utf-8-sig"))
        if not isinstance(tasks, list):
            raise ValueError("tasks.json must be a list")
    except Exception as error:
        print(f"invalid tasks.json: {error}", file=sys.stderr)
        return 2
    try:
        hard, per_clip, parallel = runtime_config()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    root = Path(os.environ.get("SWIFTCLIP_WORK", "/tmp/swiftclip"))
    root.mkdir(parents=True, exist_ok=True)
    global_end = time.monotonic() + hard - min(30.0, hard * 0.1)

    def process(index: int) -> dict:
        task = tasks[index] if isinstance(tasks[index], dict) else {}
        task_id = str(task.get("task_id", f"t{index}"))
        styles = [str(style) for style in (task.get("styles") or STYLES)]
        url = str(task.get("video_url") or task.get("video") or "")
        if not url:
            return {"task_id": task_id, "captions": _fallback(styles)}
        deadline = min(time.monotonic() + per_clip, global_end)
        try:
            captions = run_task_combined(url, task_id, styles, root, deadline)
            return {"task_id": task_id, "captions": captions}
        except Exception as error:
            print(f"task {task_id} failed: {error}", file=sys.stderr)
            return {"task_id": task_id, "captions": _fallback(styles)}

    results: list[dict | None] = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(process, index): index for index in range(len(tasks))}
        try:
            for future in as_completed(futures, timeout=max(1.0, global_end - time.monotonic())):
                results[futures[future]] = future.result()
        except TimeoutError:
            print("global timeout; filling incomplete tasks", file=sys.stderr)
    for index, result in enumerate(results):
        if result is None:
            task = tasks[index] if isinstance(tasks[index], dict) else {}
            styles = [str(style) for style in (task.get("styles") or STYLES)]
            results[index] = {"task_id": str(task.get("task_id", f"t{index}")), "captions": _fallback(styles)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(Path(sys.argv[1] if len(sys.argv) > 1 else "/input/tasks.json"), Path(sys.argv[2] if len(sys.argv) > 2 else "/output/results.json")))
