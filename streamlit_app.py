"""Public Streamlit demo for the ClioGemma release.

The hackathon evaluator still uses ``app.visual`` and the Docker I/O contract.
This file is only the human-facing demo entry point for Streamlit Community
Cloud. It calls the same five-frame, Novita + Gemma fast path as the release.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path

import streamlit as st

from app.core.parse import STYLES
from app.visual import run_task_combined


ROOT = Path(__file__).resolve().parent
MODEL = "google/gemma-3-27b-it"
STYLE_LABELS = {
    "formal": "Formal",
    "sarcastic": "Sarcastic",
    "humorous_tech": "Humorous tech",
    "humorous_non_tech": "Humorous non-tech",
}


def _load_streamlit_secrets() -> None:
    """Copy deployment secrets into the environment without displaying them."""
    for name in ("CLIO_API_KEY", "NOVITA_API_KEY", "CLIO_BASE_URL", "CLIO_MODEL"):
        try:
            value = st.secrets.get(name, "")
        except Exception:
            value = ""
        if value:
            os.environ[name] = str(value)


def _configure_release_defaults() -> None:
    _load_streamlit_secrets()
    os.environ.setdefault("CLIO_ENFORCE_NOVITA", "1")
    os.environ.setdefault("CLIO_FAST_MODE", "1")
    os.environ.setdefault("CLIO_MODEL", MODEL)
    os.environ.setdefault("CLIO_BASE_URL", "https://api.novita.ai/openai")
    os.environ.setdefault("SWIFTCLIP_FRAME_STRATEGY", "anchors")
    os.environ.setdefault("SWIFTCLIP_FRAME_COUNT", "5")
    os.environ.setdefault("SWIFTCLIP_FRAME_WIDTH", "896")


def _has_key() -> bool:
    return bool((os.environ.get("CLIO_API_KEY", "").strip()) or (os.environ.get("NOVITA_API_KEY", "").strip()))


def _render_brand() -> None:
    left, right = st.columns([1, 8], vertical_alignment="center")
    with left:
        logo = ROOT / "demo" / "clio-emblem.png"
        if logo.exists():
            st.image(str(logo), width=64)
    with right:
        st.markdown("# ClioGemma")
        st.caption("Grounded video captioning · Novita + Gemma · AMD Track 2")


def _render_result(result: dict[str, str]) -> None:
    st.subheader("Generated captions")
    for style in STYLES:
        caption = result.get(style)
        if not caption:
            continue
        with st.container(border=True):
            st.markdown(f"**{STYLE_LABELS[style]}**")
            st.write(caption)
    payload = json.dumps({"task_id": "streamlit-demo", "captions": result}, ensure_ascii=False, indent=2)
    st.download_button(
        "Download captions.json",
        data=payload,
        file_name="cliogemma-captions.json",
        mime="application/json",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="ClioGemma", page_icon="✨", layout="wide")
    _configure_release_defaults()

    st.markdown(
        """
        <style>
        .stApp { background: #0d0d0e; color: #f7f2e8; }
        [data-testid="stHeader"] { background: rgba(13,13,14,0); }
        .block-container { max-width: 1180px; padding-top: 2.2rem; }
        h1, h2, h3 { color: #f4c35a; }
        .stButton > button, .stDownloadButton > button { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _render_brand()

    if not _has_key():
        st.info(
            "The demo is deployed, but caption generation is not configured yet. "
            "Add CLIO_API_KEY (a restricted Novita key) in Streamlit Cloud → Settings → Secrets."
        )

    upload_col, settings_col = st.columns([1.45, 1], gap="large")
    with upload_col:
        st.subheader("Upload video")
        uploaded = st.file_uploader(
            "MP4, MOV, or WEBM",
            type=["mp4", "mov", "webm", "m4v", "avi"],
            help="The public demo samples five chronological frames before calling Gemma.",
        )
        if uploaded is not None:
            st.video(uploaded.getvalue())

    with settings_col:
        st.subheader("Caption settings")
        selected = st.multiselect(
            "Styles",
            options=list(STYLES),
            default=list(STYLES),
            format_func=lambda style: STYLE_LABELS[style],
        )
        st.caption(f"Model: `{os.environ.get('CLIO_MODEL', MODEL)}`")
        generate = st.button("✨ Generate captions", type="primary", use_container_width=True)

    if generate:
        if uploaded is None:
            st.warning("Upload a video first.")
        elif not selected:
            st.warning("Choose at least one caption style.")
        elif not _has_key():
            st.error("Caption generation is unavailable until a Novita key is added to Streamlit Secrets.")
        else:
            suffix = Path(uploaded.name).suffix.lower() or ".mp4"
            run_id = f"streamlit-{uuid.uuid4().hex[:8]}"
            with tempfile.TemporaryDirectory(prefix="cliogemma-") as temp_dir:
                root = Path(temp_dir)
                video_path = root / f"input{suffix}"
                video_path.write_bytes(uploaded.getvalue())
                with st.spinner("Sampling the video and asking Gemma for grounded captions…"):
                    try:
                        result = run_task_combined(
                            str(video_path),
                            run_id,
                            selected,
                            root / "work",
                            deadline=time.monotonic() + 125,
                        )
                    except Exception as error:
                        st.error(f"Caption generation failed: {error}")
                    else:
                        _render_result(result)


if __name__ == "__main__":
    main()
