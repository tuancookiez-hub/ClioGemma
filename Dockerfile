FROM python:3.11-slim

ARG CLIO_API_KEY
ARG CLIO_BASE_URL=https://api.novita.ai/openai
ARG CLIO_MODEL=google/gemma-3-27b-it
ARG SWIFTCLIP_FRAME_STRATEGY=anchors
ARG SWIFTCLIP_FRAME_COUNT=5

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CLIO_API_KEY=${CLIO_API_KEY} \
    CLIO_BASE_URL=${CLIO_BASE_URL} \
    CLIO_MODEL=${CLIO_MODEL} \
    CLIO_ENFORCE_NOVITA=1 \
    CLIO_FAST_MODE=1 \
    CLIO_PIPELINE=fast \
    CLIO_REQUEST_TIMEOUT=25 \
    SWIFTCLIP_FRAME_STRATEGY=${SWIFTCLIP_FRAME_STRATEGY} \
    SWIFTCLIP_FRAME_COUNT=${SWIFTCLIP_FRAME_COUNT} \
    SWIFTCLIP_FRAME_WIDTH=896 \
    SWIFTCLIP_PARALLEL=3 \
    SWIFTCLIP_CLIP_TIMEOUT=125

RUN apt-get update -y \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /input /output

CMD ["python", "-m", "app.visual", "/input/tasks.json", "/output/results.json"]
