# 🐹 TranslookDown

**[中文](#中文) | [English](#english)**

---

## 中文

> 一款基于 **yt-dlp** 的全功能本地视频下载器，采用动森（Animal Island）主题设计，内嵌浏览器引擎，双击即用。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-10%2F11-success.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Version](https://img.shields.io/badge/Version-V4-orange.svg)

### ✨ 功能特性

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
- 🌐 **中英双语** — 提供中文版和英文版

### 🚀 快速开始

**方式一：直接运行 EXE（推荐）**

1. 从 [Releases](../../releases) 下载：
   - 中文版：`TranslookDown_V4.exe`
   - English: `TranslookDown_V4_EN.exe`
2. 双击运行
3. 粘贴视频链接 → 点击下载

> **系统要求：** Windows 10/11（自带 Edge WebView2）

**方式二：从源码运行**

```bash
git clone https://github.com/StenbuckDeng/TranslookDown.git
cd TranslookDown
pip install flask flask-cors pywebview
# 将 yt-dlp.exe / ffmpeg.exe / ffprobe.exe 放入 bundle/ 目录
python src/video_downloader.py      # 中文版
python src/video_downloader_en.py   # English
```

### 📂 项目结构

```
TranslookDown/
├── src/
│   ├── video_downloader.py      # 中文版主程序
│   └── video_downloader_en.py   # English version
├── bundle/
│   ├── README.md                # 依赖获取说明
│   ├── yt-dlp.exe               # 视频下载核心（需自行下载）
│   ├── ffmpeg.exe               # 音视频处理（需自行下载）
│   └── ffprobe.exe              # 媒体探测（需自行下载）
├── README.md
├── LICENSE
└── .gitignore
```

### ⚙️ 下载选项

| 选项 | 说明 | yt-dlp 参数 |
|------|------|-------------|
| **画质选择** | 最佳画质 / 1080p / 720p / 仅音频 | `-f` |
| **下载字幕** | 嵌入英/中文字幕 | `--write-subs --sub-langs "en,zh-Hans,zh" --embed-subs` |
| **下载缩略图** | 嵌入视频封面 | `--write-thumbnail --embed-thumbnail` |
| **嵌入元数据** | 嵌入视频信息和章节 | `--embed-metadata --embed-chapters` |

### 📝 版本历史

| 版本 | 说明 |
|------|------|
| **V4** | 无边框窗口、三栏布局、中英双语、粘贴按钮、二维码、FAQ |
| **V3** | 选项面板、运行动画、鼹鼠 Logo |
| **V2** | 内嵌浏览器、打包 yt-dlp + ffmpeg |
| **V1** | 基础版本 |

### 📄 许可证

[MIT License](LICENSE)

---

## English

> A fully standalone local video downloader powered by **yt-dlp**, featuring an Animal Island themed UI with an embedded browser engine. Double-click to run.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-10%2F11-success.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Version](https://img.shields.io/badge/Version-V4-orange.svg)

### ✨ Features

- 🎬 **Multi-platform** — YouTube, X (Twitter), LinkedIn, Bilibili, Instagram, TikTok and thousands more
- 🖼️ **Embedded Browser** — Powered by Edge WebView2, no external browser needed
- 📦 **Fully Standalone** — Bundled yt-dlp + ffmpeg, zero dependencies
- 🎨 **Animal Island Theme** — Warm pastel cards, cute mole logo
- ⬇️ **Real-time Progress** — Progress bar, speed, ETA
- 🐹 **Running Animation** — Cute mole runs while downloading
- 📋 **One-click Paste** — Auto-read clipboard and start download
- ⚙️ **Download Options** — Quality, subtitles, thumbnail, metadata
- 📱 **Mobile Access** — QR code for LAN access
- 📜 **History** — Auto-saved download history with open/copy/delete
- 🖥️ **Frameless Window** — V4 borderless design with shadow
- 🌐 **Bilingual** — Chinese and English versions available

### 🚀 Quick Start

**Option 1: Run EXE (Recommended)**

1. Download from [Releases](../../releases):
   - Chinese: `TranslookDown_V4.exe`
   - English: `TranslookDown_V4_EN.exe`
2. Double-click to run
3. Paste a video link → Click download

> **Requirements:** Windows 10/11 (Edge WebView2 included)

**Option 2: Run from Source**

```bash
git clone https://github.com/StenbuckDeng/TranslookDown.git
cd TranslookDown
pip install flask flask-cors pywebview
# Place yt-dlp.exe / ffmpeg.exe / ffprobe.exe in bundle/ directory
python src/video_downloader.py      # Chinese version
python src/video_downloader_en.py   # English version
```

### 📂 Project Structure

```
TranslookDown/
├── src/
│   ├── video_downloader.py      # Chinese version
│   └── video_downloader_en.py   # English version
├── bundle/
│   ├── README.md                # Dependency download guide
│   ├── yt-dlp.exe               # Video downloader (download separately)
│   ├── ffmpeg.exe               # Audio/video processing (download separately)
│   └── ffprobe.exe              # Media probe (download separately)
├── README.md
├── LICENSE
└── .gitignore
```

### ⚙️ Download Options

| Option | Description | yt-dlp Flag |
|--------|-------------|-------------|
| **Quality** | Best / 1080p / 720p / Audio Only | `-f` |
| **Subtitles** | Embed English/Chinese subtitles | `--write-subs --sub-langs "en,zh-Hans,zh" --embed-subs` |
| **Thumbnail** | Embed video cover image | `--write-thumbnail --embed-thumbnail` |
| **Metadata** | Embed video info and chapters | `--embed-metadata --embed-chapters` |

### 🛠️ Tech Stack

| Component | Technology | Description |
|-----------|-----------|-------------|
| Backend | Python + Flask | API server + download management |
| Frontend | Inline HTML/CSS/JS | Animal Island themed UI |
| Browser | pywebview (Edge WebView2) | Frameless window |
| Downloader | yt-dlp | Supports thousands of sites |
| Media | ffmpeg | Merge, transcode, embed subtitles |
| Packaging | PyInstaller | Single-file EXE |

### 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/download` | POST | Start download `{"url": "...", "format": "...", ...}` |
| `/api/progress/<task_id>` | GET | Query download progress |
| `/api/downloads` | GET | Get all active downloads |
| `/api/history` | GET | Get download history |
| `/api/history/delete` | POST | Delete history record |
| `/api/history/clear` | POST | Clear all history |
| `/api/open_file` | POST | Open file |
| `/api/open_folder` | POST | Open download folder |
| `/api/qr` | GET | Get LAN QR code URL |
| `/api/quit` | POST | Shutdown application |

### 📝 Version History

| Version | Description |
|---------|-------------|
| **V4** | Frameless window, 3-column layout, bilingual, paste button, QR code, FAQ |
| **V3** | Options panel, running animation, mole logo |
| **V2** | Embedded browser, bundled yt-dlp + ffmpeg |
| **V1** | Basic version |

### 📄 License

[MIT License](LICENSE)

### 🙏 Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Powerful video downloader
- [ffmpeg](https://ffmpeg.org/) — Swiss army knife of audio/video
- [pywebview](https://github.com/r0x0r/pywebview) — Lightweight browser window for Python
- [Flask](https://flask.palletsprojects.com/) — Python web framework
- [animal-island-ui](https://github.com/guokaigdg/animal-island-ui) — UI design inspiration

---

<p align="center">
  Made with 🐹 by <a href="https://github.com/StenbuckDeng">StenbuckDeng</a>
</p>
