param(
  [string]$StreamUrl = "rtsp://localhost:8554/live/cam01"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "resolve_ffmpeg.ps1")
Write-Host "Testing stream: $StreamUrl"
$ffmpegExe = Resolve-FfmpegExe
& $ffmpegExe -rtsp_transport tcp -i "$StreamUrl" -t 5 -f null -
