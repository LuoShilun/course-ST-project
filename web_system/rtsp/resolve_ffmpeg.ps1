function Resolve-FfmpegExe {
  $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  $pythonCandidates = @()
  $pyCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pyCmd) {
    $pythonCandidates += $pyCmd.Source
  }
  if (Test-Path "D:\Anaconda\envs\dl\python.exe") {
    $pythonCandidates += "D:\Anaconda\envs\dl\python.exe"
  }

  foreach ($pyExe in $pythonCandidates) {
    try {
      $exe = & $pyExe -c "import imageio_ffmpeg,sys;sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())" 2>$null
      if ($exe) {
        return $exe
      }
    } catch {
      continue
    }
  }

  throw "ffmpeg not found in PATH, and no usable imageio-ffmpeg runtime was found"
}
