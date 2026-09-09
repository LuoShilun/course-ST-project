param(
  [Parameter(Mandatory = $true)][string]$VideoPath,
  [string]$StreamName = "cam01",
  [string]$Server = "rtsp://localhost:8554/live",
  [switch]$CopyMode
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "resolve_ffmpeg.ps1")

if (-not (Test-Path $VideoPath)) {
  throw "Video file not found: $VideoPath"
}

$target = "$Server/$StreamName"
Write-Host "Pushing to: $target"
$ffmpegExe = Resolve-FfmpegExe

if ($CopyMode) {
  & $ffmpegExe -re -stream_loop -1 -i "$VideoPath" -c copy -f rtsp "$target"
} else {
  # Default to low-latency H264 with frequent keyframes for stable downstream CV decoding.
  & $ffmpegExe -re -stream_loop -1 -i "$VideoPath" -c:v libx264 -preset veryfast -tune zerolatency -g 25 -keyint_min 25 -sc_threshold 0 -an -f rtsp "$target"
}
