#!/bin/bash
set -e

echo "================================================"
echo "  TranslookDown — macOS 打包脚本"
echo "================================================"

# 检查必要工具
command -v python3 >/dev/null || { echo "❌ 请先安装 Python 3.11+"; exit 1; }
command -v brew >/dev/null || { echo "❌ 请先安装 Homebrew: https://brew.sh"; exit 1; }

echo ""
echo "► 步骤 1/5：安装 Python 依赖..."
pip3 install -r requirements.txt pyinstaller --quiet

echo "► 步骤 2/5：安装 yt-dlp 和 ffmpeg（通过 Homebrew）..."
brew install yt-dlp ffmpeg 2>/dev/null || brew upgrade yt-dlp ffmpeg 2>/dev/null || true

echo "► 步骤 3/5：复制二进制到 bundle/ 目录..."
mkdir -p bundle
cp "$(which yt-dlp)"  bundle/yt-dlp
cp "$(which ffmpeg)"  bundle/ffmpeg
cp "$(which ffprobe)" bundle/ffprobe
chmod +x bundle/yt-dlp bundle/ffmpeg bundle/ffprobe
echo "   yt-dlp:  $(bundle/yt-dlp --version 2>/dev/null || echo 'ok')"
echo "   ffmpeg:  $(bundle/ffmpeg -version 2>/dev/null | head -1 || echo 'ok')"

echo "► 步骤 4/5：PyInstaller 打包..."
pyinstaller \
  --name "TranslookDown" \
  --windowed \
  --onedir \
  --noconfirm \
  --add-data "config:config" \
  --add-data "license:license" \
  --add-binary "bundle/yt-dlp:bundle" \
  --add-binary "bundle/ffmpeg:bundle" \
  --add-binary "bundle/ffprobe:bundle" \
  --hidden-import "flask" \
  --hidden-import "flask_cors" \
  --hidden-import "webview" \
  --hidden-import "cryptography" \
  --hidden-import "PIL" \
  --hidden-import "qrcode" \
  src/video_downloader.py

echo "► 步骤 5/5：验证产物..."
if [ -d "dist/TranslookDown.app" ]; then
  echo ""
  echo "================================================"
  echo "  ✅ 打包成功！"
  echo "  📦 产物位置：dist/TranslookDown.app"
  echo "  📂 直接双击运行，或拖入 Applications 文件夹"
  echo "================================================"
  open dist/
else
  echo "❌ 打包失败，请检查上方错误信息"
  exit 1
fi
