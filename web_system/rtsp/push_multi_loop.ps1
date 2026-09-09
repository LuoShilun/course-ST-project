param(
  [Parameter(Mandatory = $true)][string]$Video1,
  [string]$Video2 = "",
  [string]$Server = "rtsp://localhost:8554/live",
  [switch]$CopyMode
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "resolve_ffmpeg.ps1")

if (-not (Test-Path $Video1)) {
  throw "Video file not found: $Video1"
}

$ffmpegExe = Resolve-FfmpegExe
if ($CopyMode) {
  Start-Process -FilePath $ffmpegExe -ArgumentList @("-re", "-stream_loop", "-1", "-i", "$Video1", "-c", "copy", "-f", "rtsp", "$Server/cam01") | Out-Null
} else {
  Start-Process -FilePath $ffmpegExe -ArgumentList @("-re", "-stream_loop", "-1", "-i", "$Video1", "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-g", "25", "-keyint_min", "25", "-sc_threshold", "0", "-an", "-f", "rtsp", "$Server/cam01") | Out-Null
}
Write-Host "Started stream: $Server/cam01"

if ($Video2 -and (Test-Path $Video2)) {
  if ($CopyMode) {
    Start-Process -FilePath $ffmpegExe -ArgumentList @("-re", "-stream_loop", "-1", "-i", "$Video2", "-c", "copy", "-f", "rtsp", "$Server/cam02") | Out-Null
  } else {
    Start-Process -FilePath $ffmpegExe -ArgumentList @("-re", "-stream_loop", "-1", "-i", "$Video2", "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-g", "25", "-keyint_min", "25", "-sc_threshold", "0", "-an", "-f", "rtsp", "$Server/cam02") | Out-Null
  }
  Write-Host "Started stream: $Server/cam02"
} elseif ($Video2) {
  Write-Warning "Video2 not found, skipped: $Video2"
}
