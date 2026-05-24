# 🐹 TranslookDown

> 一款基于 **yt-dlp** 的全功能本地视频下载器，采用动森（Animal Island）主题设计，内嵌浏览器引擎，双击即用。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-10%2F11-success.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Version](https://img.shields.io/badge/Version-V4-orange.svg)

---

## ✨ 功能特性

- 🎬 **多平台支持** — YouTube、X (Twitter)、LinkedIn、B站、Instagram、TikTok 等数千个网站
- 🖼️ **内嵌浏览器** — 基于 Edge WebView2，无需打开外部浏览器
- 📦 **完全独立** — 内置 yt-dlp + ffmpeg，无需安装任何依赖
- 🎨 **动森主题** — 暖色调圆角卡片 UI，可爱鼹鼠 Logo
- ⬇️ **实时进度** — 下载进度条、速度、ETA 实时显示
- 🐹 **运行动画** — 下载中显示奔跑的小鼹鼠
- 📋 **一键粘贴** — 自动读取剪贴板链接并开始下载
- ⚙️ **下载选项** — 画质选择、字幕、缩略图、元数据
- 📱 **手机访问** — 局域网二维码扫码访问
- 📜 **历史记录** — 自动保存下载历史，支持打开/复制/删除
- 🖥️ **无边框窗口** — V4 版本，无边框设计，带立体阴影

---

## 📸 截图预览

### V4 — 无边框紧凑版
```
┌─────────────────────────────────────────────┐
│  🐹 TranslookDown V4          MON  14:30    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ 🔗 粘贴视频链接                      │    │
│  │ [https://youtube.com/watch?v=...] 📋│    │
│  │ [⬇️ 开始下载]          [📂 文件夹]   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ⚙️ 选项 ▼                                  │
│  ┌─────────────────────────────────────┐    │
│  │ ⬇️ 下载中 (1)  │  📋 历史 (5)       │    │
│  ├─────────────────────────────────────┤    │
│  │ 🐹 奔跑中...  67.3%                  │    │
│  │ ████████████░░░░░░░░░░  1.2MiB/s    │    │
│  │ ETA 03:24     ~150MiB               │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式一：直接运行 EXE（推荐）

1. 从 [Releases](../../releases) 下载最新版 `TranslookDown_V4.exe`
2. 双击运行，自动弹出程序窗口
3. 粘贴视频链接 → 点击下载

> **系统要求：** Windows 10/11（自带 Edge WebView2）

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/StenbuckDeng/TranslookDown.git
cd TranslookDown

# 2. 安装 Python 依赖
pip install flask flask-cors pywebview

# 3. 将 yt-dlp.exe 和 ffmpeg 放入 bundle/ 目录
#    - yt-dlp.exe: https://github.com/yt-dlp/yt-dlp/releases
#    - ffmpeg:     https://www.gyan.dev/ffmpeg/builds/

# 4. 运行
python src/video_downloader.py
```

### 方式三：打包自己的 EXE

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包（bundle/ 目录需包含 yt-dlp.exe, ffmpeg.exe, ffprobe.exe）
pyinstaller --onefile --name "TranslookDown_V4" --noconsole ^
  --hidden-import=webview ^
  --hidden-import=webview.platforms.edgechromium ^
  --hidden-import=webview.platforms.win32 ^
  --hidden-import=clr_loader ^
  --hidden-import=pythonnet ^
  --collect-all webview ^
  --add-data "bundle;bundle" ^
  src/video_downloader.py
```

打包后的 EXE 在 `dist/TranslookDown_V4.exe`。

---

## 📂 项目结构

```
TranslookDown/
├── src/
│   └── video_downloader.py    # 主程序（Flask 后端 + 内嵌 HTML 前端）
├── bundle/
│   ├── yt-dlp.exe             # 视频下载核心
│   ├── ffmpeg.exe             # 音视频合并/转码
│   └── ffprobe.exe            # 媒体信息探测
├── README.md                  # 项目说明
├── LICENSE                    # MIT 许可证
└── .gitignore
```

---

## ⚙️ 下载选项

| 选项 | 说明 | yt-dlp 参数 |
|------|------|-------------|
| **画质选择** | 最佳画质 / 1080p / 720p / 仅音频 | `-f` |
| **下载字幕** | 嵌入英文/中文字幕 | `--write-subs --sub-langs "en,zh-Hans,zh" --embed-subs` |
| **下载缩略图** | 嵌入视频封面图 | `--write-thumbnail --embed-thumbnail` |
| **嵌入元数据** | 嵌入视频信息和章节 | `--embed-metadata --embed-chapters` |

---

## 🛠️ 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 后端 | Python + Flask | API 服务 + 下载管理 |
| 前端 | 内嵌 HTML/CSS/JS | 动森主题 UI |
| 浏览器引擎 | pywebview (Edge WebView2) | 无边框窗口 |
| 视频下载 | yt-dlp | 支持数千个网站 |
| 音视频处理 | ffmpeg | 合并、转码、嵌入字幕 |
| 打包 | PyInstaller | 单文件 EXE |

---

## 📡 API 接口

程序内置 Flask API 服务（端口 5000）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/download` | POST | 开始下载 `{"url": "...", "format": "...", ...}` |
| `/api/progress/<task_id>` | GET | 查询下载进度 |
| `/api/downloads` | GET | 获取所有活跃下载 |
| `/api/history` | GET | 获取下载历史 |
| `/api/history/delete` | POST | 删除历史记录 |
| `/api/history/clear` | POST | 清空历史 |
| `/api/open_file` | POST | 打开文件 |
| `/api/open_folder` | POST | 打开下载文件夹 |
| `/api/qr` | GET | 获取局域网二维码地址 |

---

## 📱 手机访问

1. 确保手机和电脑在同一局域网
2. 程序启动后，访问 `http://电脑IP:5000`
3. 或扫描界面上的二维码

---

## 📝 版本历史

| 版本 | 说明 |
|------|------|
| **V4** | 无边框窗口、紧凑单页布局、立体阴影 |
| **V3** | 新增选项面板、粘贴按钮、二维码、运行动画、鼹鼠 Logo |
| **V2** | 内嵌浏览器（pywebview）、打包 yt-dlp + ffmpeg |
| **V1** | 基础版本，外部浏览器 |

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 强大的视频下载工具
- [ffmpeg](https://ffmpeg.org/) — 音视频处理瑞士军刀
- [pywebview](https://github.com/r0x0r/pywebview) — Python 轻量级浏览器窗口
- [Flask](https://flask.palletsprojects.com/) — Python Web 框架
- [animal-island-ui](https://github.com/guokaigdg/animal-island-ui) — UI 设计灵感来源

---

<p align="center">
  Made with 🐹 by <a href="https://github.com/StenbuckDeng">StenbuckDeng</a>
</p>
