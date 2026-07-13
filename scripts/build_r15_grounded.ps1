param(
    [string]$Tag = "ghcr.io/tuancookiez-hub/cliogemma:score-max-r15-grounded",
    [string]$Pipeline = "score-max-r15-grounded",
    [string]$VisionModel = "moonshotai/kimi-k2.6",
    [int]$ClipTimeout = 65,
    [int]$RequestTimeout = 20,
    [switch]$Push
)

$ErrorActionPreference = "Stop"
if (-not $env:NOVITA_API_KEY) {
    throw "NOVITA_API_KEY is not set in this PowerShell session. Set it without printing it, then rerun."
}

$buildArgs = @(
    "buildx", "build", "--platform", "linux/amd64",
    "--provenance=false", "--sbom=false",
    "--build-arg", "CLIO_API_KEY=$env:NOVITA_API_KEY",
    "--build-arg", "CLIO_MODEL=google/gemma-4-31b-it",
    "--build-arg", "CLIO_VERIFY_MODEL=google/gemma-4-31b-it",
    "--build-arg", "CLIO_CAPTION_MODEL=google/gemma-4-31b-it",
    "--build-arg", "CLIO_VISION_MODEL=$VisionModel",
    "--build-arg", "CLIO_PIPELINE=$Pipeline",
    "--build-arg", "SWIFTCLIP_FRAME_STRATEGY=anchors",
    "--build-arg", "SWIFTCLIP_FRAME_COUNT=4",
    "--build-arg", "SWIFTCLIP_FRAME_WIDTH=768",
    "--build-arg", "CLIO_GRID_INPUT=1",
    "--build-arg", "CLIO_STABILITY_MODE=1",
    "--build-arg", "SWIFTCLIP_PARALLEL=2",
    "--build-arg", "SWIFTCLIP_CLIP_TIMEOUT=$ClipTimeout",
    "--build-arg", "SWIFTCLIP_OCR=0",
    "--build-arg", "CLIO_REQUEST_TIMEOUT=$RequestTimeout",
    "--build-arg", "CLIO_RATE_LIMIT_RETRIES=0",
    "--tag", $Tag
)

if ($Push) {
    $buildArgs += "--push"
} else {
    $buildArgs += "--load"
}
$buildArgs += "."

Write-Host "Building $Tag (${Pipeline}: Kimi evidence + image-grounded Gemma batch writer)..."
& docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE"
}
Write-Host "Built $Tag"
