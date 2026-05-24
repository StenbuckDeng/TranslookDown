# Bundle 目录

此目录需要放置以下文件才能运行程序：

## 所需文件

| 文件 | 说明 | 下载地址 |
|------|------|----------|
| `yt-dlp.exe` | 视频下载核心 | https://github.com/yt-dlp/yt-dlp/releases |
| `ffmpeg.exe` | 音视频合并/转码 | https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip |
| `ffprobe.exe` | 媒体信息探测 | 同 ffmpeg（在同一压缩包内） |

## 快速下载（Windows PowerShell）

```powershell
# 下载 yt-dlp
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile "bundle/yt-dlp.exe"

# 下载 ffmpeg (需要手动解压并复制 ffmpeg.exe 和 ffprobe.exe)
# 从 https://www.gyan.dev/ffmpeg/builds/ 下载 ffmpeg-release-essentials.zip
# 解压后将 bin/ffmpeg.exe 和 bin/ffprobe.exe 复制到此目录
```
