param(
    [string]$Tag = "ghcr.io/tuancookiez-hub/cliogemma:gemma4-champion-r1",
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
    "--build-arg", "CLIO_PIPELINE=verified5-champion",
    "--build-arg", "SWIFTCLIP_FRAME_COUNT=4",
    "--build-arg", "SWIFTCLIP_FRAME_WIDTH=768",
    "--build-arg", "SWIFTCLIP_PARALLEL=2",
    "--tag", $Tag
)

if ($Push) {
    $buildArgs += "--push"
} else {
    $buildArgs += "--load"
}
$buildArgs += "."

Write-Host "Building $Tag (Gemma 4 31B, four chronological frames, champion pipeline)..."
& docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE"
}
Write-Host "Built $Tag"
