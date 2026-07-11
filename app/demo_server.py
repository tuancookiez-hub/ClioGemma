"""Local ClioGemma dashboard server.

This is a developer demo only. It is intentionally excluded from the Track 2
submission image by .dockerignore. The evaluator still uses app.visual and the
/input/tasks.json -> /output/results.json contract.
"""
from __future__ import annotations

import cgi
import json
import os
import shutil
import tempfile
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from app.core.frames import mine_frames
from app.evidence_pipeline import caption_clip_evidence
from app.core.parse import STYLES
from app.visual import _download

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
JOBS: dict[str, dict] = {}
JOBS_LOCK = Lock()


def _json(handler: SimpleHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _remember(job: dict) -> None:
    with JOBS_LOCK:
        JOBS[job["job_id"]] = job
        while len(JOBS) > 10:
            JOBS.pop(next(iter(JOBS)))


def _caption(video: Path, task_id: str, selected_style: str) -> dict:
    started = time.monotonic()
    work = Path(tempfile.mkdtemp(prefix="cliogemma-demo-"))
    try:
        os.environ.setdefault("CLIO_ENFORCE_NOVITA", "1")
        os.environ.setdefault("CLIO_FAST_MODE", "1")
        frames = mine_frames(video, work / "frames", count=5, width=896, strategy="anchors")
        if len(frames) < 1:
            raise RuntimeError("no frames could be extracted")
        captions = caption_clip_evidence(frames, task_id, timeout_s=125)
        if selected_style in STYLES:
            captions = {selected_style: captions[selected_style]}
        return {
            "captions": captions,
            "elapsed_s": round(time.monotonic() - started, 3),
            "frame_count": len(frames),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[demo] {format % args}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            configured = bool(os.environ.get("CLIO_API_KEY", "").strip() or os.environ.get("NOVITA_API_KEY", "").strip())
            _json(self, {"ok": True, "configured": configured, "model": os.environ.get("CLIO_MODEL", "google/gemma-3-27b-it")})
            return
        if path == "/api/jobs":
            with JOBS_LOCK:
                jobs = list(reversed(list(JOBS.values())))
            _json(self, {"jobs": jobs})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/caption":
            _json(self, {"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            _json(self, {"error": "upload is empty or exceeds 512 MB"}, 413)
            return
        if not (os.environ.get("CLIO_API_KEY", "").strip() or os.environ.get("NOVITA_API_KEY", "").strip()):
            _json(self, {"error": "Set CLIO_API_KEY or NOVITA_API_KEY before generating captions."}, 503)
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": str(length),
        })
        selected_style = str(form.getfirst("style", "all"))
        video_url = str(form.getfirst("video_url", "")).strip()
        job_id = uuid.uuid4().hex[:10]
        try:
            with tempfile.TemporaryDirectory(prefix="cliogemma-upload-") as temp:
                root = Path(temp)
                upload = form["video"] if "video" in form else None
                if upload is not None and getattr(upload, "filename", ""):
                    video = root / Path(upload.filename).name
                    with video.open("wb") as stream:
                        shutil.copyfileobj(upload.file, stream)
                elif video_url:
                    video = _download(video_url, root / "video.mp4", time.monotonic() + 125)
                else:
                    raise ValueError("choose a video file or provide a video URL")
                result = _caption(video, job_id, selected_style)
            job = {"job_id": job_id, "status": "complete", "source": video_url or "uploaded video", **result}
            _remember(job)
            _json(self, job)
        except Exception as error:
            job = {"job_id": job_id, "status": "error", "error": str(error)}
            _remember(job)
            _json(self, job, 500)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the local ClioGemma dashboard")
    parser.add_argument("port", nargs="?", type=int, default=8787)
    args = parser.parse_args()
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    print(f"ClioGemma dashboard: http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
