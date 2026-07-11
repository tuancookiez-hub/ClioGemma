# Streamlit demo deployment

`streamlit_app.py` is the public human-facing demo. The AMD evaluator still
uses the Docker entrypoint (`python -m app.visual`) and its
`/input/tasks.json` → `/output/results.json` contract; Streamlit is not a
replacement for that container.

## Deploy on Streamlit Community Cloud

1. Push/merge this tree to the `main` branch of
   `https://github.com/tuancookiez-hub/ClioGemma`.
2. Open <https://share.streamlit.io>, choose **New app**, and select:
   - Repository: `tuancookiez-hub/ClioGemma`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: choose an available slug such as `cliogemma`
3. After the first deploy, open **Settings → Secrets** and add:

   ```toml
   CLIO_API_KEY = "<restricted Novita key>"
   CLIO_MODEL = "google/gemma-3-27b-it"
   CLIO_BASE_URL = "https://api.novita.ai/openai"
   ```

   Never commit these values. Rotate the key after the hackathon.
4. Upload a short MP4 and generate captions. The hosted demo is a lightweight
   presentation surface and may use the fast path; the scored Docker image uses
   the verified multi-stage path documented in the root README.

`packages.txt` installs FFmpeg on Streamlit Community Cloud. If the app shows
an FFmpeg error, open **Manage app → Reboot app** after the dependency install
has completed.

## Values for the lablab form

- **GitHub Repository:** `https://github.com/tuancookiez-hub/ClioGemma`
- **Demo Application Platform:** `Streamlit`
- **Demo Application URL:** the final `.streamlit.app` URL shown after deploy
- **Docker Image:** the public registry reference for the exact Track 2 image,
  for example `ghcr.io/tuancookiez-hub/cliogemma:release-1` once that tag has
  been pushed. Do not enter a local Docker tag or a web page URL.

Suggested additional information:

> ClioGemma is a Track 2 video-captioning container and Streamlit demo. The
> public demo uses Novita-hosted Gemma inference, chronological FFmpeg
> frames, grounded prompts, and four requested caption styles. The
> submitted Docker image reads `/input/tasks.json` and writes
> `/output/results.json` for `linux/amd64`. No API key is stored in GitHub;
> the demo key is supplied through Streamlit Secrets.
