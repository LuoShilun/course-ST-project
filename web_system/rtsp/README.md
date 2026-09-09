# RTSP 本地部署与推流

本目录用于快速完成 MediaMTX 本地部署、视频循环推流和流可用性验证。

## 1) 启动 RTSP 服务器 (MediaMTX)

在 PowerShell 中执行:

```powershell
cd web_system/rtsp
./start_mediamtx.ps1
```

如果 GitHub 直连较慢，可使用 winget 安装:

```powershell
winget install --id bluenviron.mediamtx --exact --accept-package-agreements --accept-source-agreements
```

默认地址:
- RTSP: `rtsp://localhost:8554`
- API: `http://localhost:9997/v3/paths/list`

验证服务:

```powershell
./list_paths.ps1
```

## 2) 视频循环推流

### 单路推流

```powershell
./push_single_loop.ps1 -VideoPath "E:/videos/video1.mp4" -StreamName cam01
```

可选参数:
- `-Server` 默认 `rtsp://localhost:8554/live`
- 默认即为低时延转码推流（推荐用于实时检测）
- `-CopyMode` 使用原始码流直推（可能导致关键帧等待时间较长）

### 多路推流

```powershell
./push_multi_loop.ps1 -Video1 "E:/videos/video1.mp4" -Video2 "E:/videos/video2.mp4"
```

可选参数:
- `-CopyMode` 使用原始码流直推（不推荐用于实时检测）

会分别启动:
- `rtsp://localhost:8554/live/cam01`
- `rtsp://localhost:8554/live/cam02`

## 3) 播放测试

```powershell
./test_play.ps1 -StreamUrl "rtsp://localhost:8554/live/cam01"
```

或直接:

```powershell
ffplay rtsp://localhost:8554/live/cam01
```

## 4) 输出信息模板

部署完成后，你可在任务记录中填写:
- RTSP服务器地址: `rtsp://localhost:8554`
- 视频流地址:
  - `rtsp://localhost:8554/live/cam01`
  - `rtsp://localhost:8554/live/cam02`
- 视频源文件路径:
  - `E:/videos/video1.mp4`
  - `E:/videos/video2.mp4`

本项目可直接使用的示例视频:
- `E:/MyProjectWorkSpace/underwater_project/web_system/backend/uploads/videos/1775979282719_manythings.mp4`
- `E:/MyProjectWorkSpace/underwater_project/web_system/backend/uploads/videos/1775977782233_several.mp4`

## 注意事项

- 支持 MP4/AVI/MKV
- 若端口冲突，编辑 `mediamtx.yml` 中 `rtspAddress`
- 推流终端关闭即停止推流
- 若 `ffmpeg` / `ffplay` 不在 PATH，请先安装并加入环境变量
- 若实时检测端长时间提示“等待关键帧”，请改用默认转码推流（不要启用 `-CopyMode`）
