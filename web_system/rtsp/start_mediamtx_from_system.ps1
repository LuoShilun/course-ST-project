$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "mediamtx.yml"

if (-not (Test-Path $ConfigPath)) {
  throw "Config not found: $ConfigPath"
}

$paths = @(
  "C:\Program Files\mediamtx\mediamtx.exe",
  "C:\Program Files (x86)\mediamtx\mediamtx.exe",
  "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\bluenviron.mediamtx_Microsoft.Winget.Source_8wekyb3d8bbwe\mediamtx.exe"
)

$exe = $null
foreach ($p in $paths) {
  if (Test-Path $p) {
    $exe = $p
    break
  }
}

if (-not $exe) {
  $cmd = Get-Command mediamtx -ErrorAction SilentlyContinue
  if ($cmd) {
    $exe = $cmd.Source
  }
}

if (-not $exe) {
  throw "mediamtx executable not found. Install first using: winget install --id bluenviron.mediamtx --exact"
}

Write-Host "Starting MediaMTX from: $exe"
Start-Process -FilePath $exe -ArgumentList "$ConfigPath" -WorkingDirectory (Split-Path $exe -Parent)
Write-Host "MediaMTX started."
Write-Host "RTSP: rtsp://localhost:8554"
Write-Host "API : http://localhost:9997/v3/paths/list"
