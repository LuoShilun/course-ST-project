param(
  [string]$Version = "v1.11.3"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = Join-Path $ScriptDir "bin"
$MediaMtxExe = Join-Path $BinDir "mediamtx.exe"
$ConfigPath = Join-Path $ScriptDir "mediamtx.yml"
$MinZipSize = 1MB

function Download-File {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$OutputPath
  )

  try {
    Invoke-WebRequest -Uri $Url -OutFile $OutputPath
    return
  } catch {
    Write-Warning "Invoke-WebRequest failed, trying BITS transfer..."
  }

  Start-BitsTransfer -Source $Url -Destination $OutputPath
}

if (-not (Test-Path $ConfigPath)) {
  throw "Config not found: $ConfigPath"
}

if (-not (Test-Path $MediaMtxExe)) {
  New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

  $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
  $zipName = "mediamtx_${Version}_windows_${arch}.zip"
  $downloadUrl = "https://github.com/bluenviron/mediamtx/releases/download/$Version/$zipName"
  $zipPath = Join-Path $BinDir $zipName

  if (Test-Path $zipPath) {
    $existing = Get-Item $zipPath
    if ($existing.Length -lt $MinZipSize) {
      Remove-Item $zipPath -Force
    }
  }

  if (-not (Test-Path $zipPath)) {
    Write-Host "Downloading MediaMTX from: $downloadUrl"
    Download-File -Url $downloadUrl -OutputPath $zipPath
  }

  $zipInfo = Get-Item $zipPath
  if ($zipInfo.Length -lt $MinZipSize) {
    throw "Downloaded zip seems incomplete: $zipPath ($($zipInfo.Length) bytes)"
  }

  Write-Host "Extracting to: $BinDir"
  Expand-Archive -Path $zipPath -DestinationPath $BinDir -Force
}

if (-not (Test-Path $MediaMtxExe)) {
  throw "mediamtx.exe not found after extraction: $MediaMtxExe"
}

Write-Host "Starting MediaMTX..."
Start-Process -FilePath $MediaMtxExe -ArgumentList "$ConfigPath" -WorkingDirectory $BinDir
Write-Host "MediaMTX started."
Write-Host "RTSP: rtsp://localhost:8554"
Write-Host "API : http://localhost:9997/v3/paths/list"
