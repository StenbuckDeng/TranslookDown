#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TranslookDown V4 - Animal Island Theme (Standalone Edition)
A fully standalone video downloader with embedded browser and all dependencies.
Usage: python video_downloader.py
Package: pyinstaller --onefile --name TranslookDown video_downloader.py
"""

import os
import sys
import json
import uuid
import re
import time
import shutil
import threading
import subprocess
import tempfile
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

# ============================================================
# Bundled binaries - will be extracted at runtime
# ============================================================
_BUNDLE_DIR = None  # set in setup_environment()

def get_bundle_dir():
    """Get the directory where bundled binaries are extracted."""
    global _BUNDLE_DIR
    if _BUNDLE_DIR is not None:
        return _BUNDLE_DIR
    return _BUNDLE_DIR

def setup_environment():
    """Extract bundled binaries (yt-dlp, ffmpeg, ffprobe) to a temp directory."""
    global _BUNDLE_DIR

    # Create a persistent temp dir (not deleted on exit)
    base = tempfile.gettempdir()
    _BUNDLE_DIR = os.path.join(base, "video_downloader_tools")
    os.makedirs(_BUNDLE_DIR, exist_ok=True)

    # List of binaries to extract from the bundled data
    binaries = ["yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"]

    for binary_name in binaries:
        dest = os.path.join(_BUNDLE_DIR, binary_name)
        if not os.path.exists(dest):
            # Try to read from PyInstaller bundle
            src_path = None
            if getattr(sys, "frozen", False):
                # Running as PyInstaller bundle
                src_path = os.path.join(sys._MEIPASS, "bundle", binary_name)
            else:
                # Running as script
                src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bundle", binary_name)

            if os.path.exists(src_path):
                shutil.copy2(src_path, dest)
                print(f"  Extracted: {binary_name}")

    return _BUNDLE_DIR

# ============================================================
# Configuration (resolved after setup_environment)
# ============================================================
def get_app_dir():
    """Get the directory where the EXE/script lives."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_ytdlp_path():
    return os.path.join(get_bundle_dir(), "yt-dlp.exe")

def get_ffmpeg_path():
    return os.path.join(get_bundle_dir(), "ffmpeg.exe")

def get_download_dir():
    d = os.path.join(get_app_dir(), "downloads")
    os.makedirs(d, exist_ok=True)
    return d

HISTORY_FILE = "download_history.json"
MAX_HISTORY = 200
HOST = "127.0.0.1"
PORT = 5000

# ============================================================
# Global State
# ============================================================
active_downloads = {}  # task_id -> {proc, url, status, progress, ...}
downloads_lock = threading.Lock()
history_lock = threading.Lock()

app = Flask(__name__)
CORS(app)

# ============================================================
# History Helpers
# ============================================================

def get_history_path():
    """Get the path to the history JSON file, next to the EXE or script."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, HISTORY_FILE)


def load_history():
    path = get_history_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    path = get_history_path()
    # Keep only the last MAX_HISTORY records
    history = history[-MAX_HISTORY:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_history_record(record):
    with history_lock:
        history = load_history()
        history.append(record)
        save_history(history)


def delete_history_record(record_id):
    with history_lock:
        history = load_history()
        history = [h for h in history if h.get("id") != record_id]
        save_history(history)


def clear_history():
    with history_lock:
        save_history([])


# ============================================================
# Download Worker
# ============================================================

def parse_progress_line(line):
    """Parse yt-dlp progress line like:
    [download]  50.0% of ~ 100.00MiB at 1.00MiB/s ETA 00:50
    Returns dict with percent, total_size, speed, eta or None.
    """
    pattern = r"\[download\]\s+([\d.]+)%\s+of\s+~?\s*([\d.]+\w+)\s+at\s+([\d.]+\w+/s)\s+ETA\s+([\d:]+)"
    m = re.search(pattern, line)
    if m:
        return {
            "percent": float(m.group(1)),
            "total_size": m.group(2).strip(),
            "speed": m.group(3).strip(),
            "eta": m.group(4).strip(),
        }
    return None


def detect_filepath(line):
    """Detect the output filepath from yt-dlp output."""
    # "Merging formats into \"video.mp4\""
    m = re.search(r"Merging formats into\s+\"(.+?)\"", line)
    if m:
        return m.group(1)
    # "Destination: video.mp4"
    m = re.search(r"Destination:\s+(.+)", line)
    if m:
        return m.group(1).strip()
    # "has already been downloaded"
    m = re.search(r"has already been downloaded", line)
    if m:
        return "already_downloaded"
    return None


def download_worker(task_id, url, options=None):
    """Run yt-dlp in a subprocess and track progress."""
    if options is None:
        options = {}

    output_template = "%(title).80s [%(id)s].%(ext)s"
    cmd = [
        get_ytdlp_path(),
        "--newline",
        "--ffmpeg-location", get_bundle_dir(),
        "-o", os.path.join(get_download_dir(), output_template),
    ]

    # Apply format option
    fmt = options.get("format", "bestvideo+bestaudio/best")
    if fmt:
        cmd.extend(["-f", fmt])

    # Apply subtitle option
    if options.get("subtitle"):
        cmd.extend(["--write-subs", "--sub-langs", "en,zh-Hans,zh", "--embed-subs"])

    # Apply thumbnail option
    if options.get("thumbnail"):
        cmd.extend(["--write-thumbnail", "--embed-thumbnail"])

    # Apply metadata option
    if options.get("metadata"):
        cmd.extend(["--embed-metadata", "--embed-chapters"])

    cmd.append(url)

    filepath = None
    status = "downloading"
    progress_info = {"percent": 0, "total_size": "", "speed": "", "eta": ""}

    try:
        creation_flags = subprocess.CREATE_NO_WINDOW
    except AttributeError:
        creation_flags = 0

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )

    with downloads_lock:
        active_downloads[task_id]["proc"] = proc

    def decode_line(b: bytes) -> str:
        """Try UTF-8 first, fallback to GBK (Windows), then latin-1."""
        for enc in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return b.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return b.decode("utf-8", errors="replace")

    try:
        for raw_bytes in proc.stdout:
            line = decode_line(raw_bytes).strip()
            if not line:
                continue

            # Parse progress
            prog = parse_progress_line(line)
            if prog:
                progress_info = prog
                with downloads_lock:
                    active_downloads[task_id]["progress"] = prog
                    active_downloads[task_id]["status"] = "downloading"

            # Detect filepath
            fp = detect_filepath(line)
            if fp:
                filepath = fp

            # Check for errors
            if "ERROR:" in line.upper():
                status = "error"
                error_msg = line.split("ERROR:")[-1].strip()
                with downloads_lock:
                    active_downloads[task_id]["status"] = "error"
                    active_downloads[task_id]["error"] = error_msg

    except Exception as e:
        status = "error"
        with downloads_lock:
            active_downloads[task_id]["status"] = "error"
            active_downloads[task_id]["error"] = str(e)

    proc.wait()

    if status != "error":
        if proc.returncode == 0:
            status = "completed"
        else:
            status = "error"
            with downloads_lock:
                if "error" not in active_downloads.get(task_id, {}):
                    active_downloads[task_id]["error"] = f"Exit code: {proc.returncode}"

    # Resolve filepath if not yet detected
    if not filepath and status == "completed":
        filepath = "unknown"

    # Update final state
    with downloads_lock:
        if task_id in active_downloads:
            active_downloads[task_id]["status"] = status
            active_downloads[task_id]["filepath"] = filepath
            active_downloads[task_id]["finished_at"] = datetime.now().isoformat()

    # Add to history
    record = {
        "id": str(uuid.uuid4()),
        "url": url,
        "filepath": filepath or "",
        "status": status,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
    }
    add_history_record(record)

    # Remove from active after a delay
    time.sleep(5)
    with downloads_lock:
        active_downloads.pop(task_id, None)


# ============================================================
# API Routes
# ============================================================

@app.route("/")
def index():
    return HTML_PAGE


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Extract download options
    options = {
        "format": data.get("format", "bestvideo+bestaudio/best"),
        "subtitle": bool(data.get("subtitle", False)),
        "thumbnail": bool(data.get("thumbnail", False)),
        "metadata": bool(data.get("metadata", False)),
    }

    task_id = str(uuid.uuid4())[:8]
    with downloads_lock:
        active_downloads[task_id] = {
            "task_id": task_id,
            "url": url,
            "status": "starting",
            "progress": {"percent": 0, "total_size": "", "speed": "", "eta": ""},
            "filepath": None,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "proc": None,
        }

    t = threading.Thread(target=download_worker, args=(task_id, url, options), daemon=True)
    t.start()

    return jsonify({"task_id": task_id})


@app.route("/api/progress/<task_id>")
def api_progress(task_id):
    with downloads_lock:
        info = active_downloads.get(task_id)
    if not info:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({
        "task_id": info["task_id"],
        "url": info["url"],
        "status": info["status"],
        "progress": info["progress"],
        "filepath": info.get("filepath"),
        "error": info.get("error"),
    })


@app.route("/api/downloads")
def api_downloads():
    with downloads_lock:
        result = {}
        for tid, info in active_downloads.items():
            result[tid] = {
                "task_id": info["task_id"],
                "url": info["url"],
                "status": info["status"],
                "progress": info["progress"],
                "filepath": info.get("filepath"),
                "error": info.get("error"),
                "started_at": info.get("started_at"),
            }
    return jsonify(result)


@app.route("/api/history")
def api_history():
    history = load_history()
    # Return in reverse chronological order
    return jsonify(list(reversed(history)))


@app.route("/api/history/delete", methods=["POST"])
def api_history_delete():
    data = request.get_json(force=True)
    record_id = data.get("id", "")
    if not record_id:
        return jsonify({"error": "ID is required"}), 400
    delete_history_record(record_id)
    return jsonify({"ok": True})


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    clear_history()
    return jsonify({"ok": True})


@app.route("/api/open_file", methods=["POST"])
def api_open_file():
    data = request.get_json(force=True)
    filepath = data.get("filepath", "")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    os.startfile(filepath)
    return jsonify({"ok": True})


@app.route("/api/open_folder", methods=["POST"])
def api_open_folder():
    d = get_download_dir()
    os.startfile(d)
    return jsonify({"ok": True})


@app.route("/api/qr")
def api_qr():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return jsonify({"url": f"http://{ip}:{PORT}"})


# ============================================================
# Embedded HTML/CSS/JS Frontend (Animal Island Theme - V4)
# ============================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TranslookDown V4</title>
<style>
/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f7f3df;
  --bg-card: #fffcf0;
  --text: #725d42;
  --text-light: #a08b6e;
  --blue: #889df0;
  --blue-dark: #6a7fd4;
  --blue-light: #b3c2f7;
  --pink: #f8a6b2;
  --pink-dark: #e0889a;
  --purple: #b77dee;
  --purple-dark: #9a5fd4;
  --yellow: #f7cd67;
  --yellow-dark: #e0b44a;
  --teal: #82d5bb;
  --teal-dark: #5fb89a;
  --green: #8ac68a;
  --green-dark: #6aaa6a;
  --red: #fc736d;
  --red-dark: #e05550;
  --radius-card: 20px;
  --radius-btn: 12px;
  --radius-pill: 50px;
  --shadow-btn: 0 4px 0;
  --font: 'Nunito', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  line-height: 1.6;
  overflow: hidden;
}

/* ===== Decorative Background ===== */
body::before {
  content: '';
  position: fixed;
  top: -120px;
  right: -120px;
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(136,157,240,0.15) 0%, transparent 70%);
  border-radius: 50%;
  z-index: 0;
  pointer-events: none;
}
body::after {
  content: '';
  position: fixed;
  bottom: -80px;
  left: -80px;
  width: 280px;
  height: 280px;
  background: radial-gradient(circle, rgba(248,166,178,0.12) 0%, transparent 70%);
  border-radius: 50%;
  z-index: 0;
  pointer-events: none;
}

/* ===== Container ===== */
.container {
  max-width: 780px;
  margin: 0 auto;
  padding: 10px 14px 8px;
  position: relative;
  z-index: 1;
}

/* ===== Header Row ===== */
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0 6px;
  margin-bottom: 8px;
}
.logo-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo-wrap svg {
  width: 32px;
  height: 32px;
}
.logo-wrap h1 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
}
.version-badge {
  display: inline-block;
  background: var(--blue);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  vertical-align: middle;
  margin-left: 4px;
  box-shadow: 0 2px 0 var(--blue-dark);
}
.time-widget-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 2px solid #ede6d3;
  border-radius: 14px;
  padding: 6px 14px;
  box-shadow: 0 2px 8px rgba(114,93,66,0.08);
}
.time-widget-inline .time-day {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--green-dark);
  letter-spacing: 1px;
}
.time-widget-inline .time-clock {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: 1px;
}

/* ===== Input Card ===== */
.input-card {
  background: var(--blue);
  border-radius: var(--radius-card);
  padding: 14px 16px 12px;
  margin-bottom: 8px;
  box-shadow: var(--shadow-btn) var(--blue-dark);
  transition: transform 0.15s, box-shadow 0.15s;
}
.input-card:active {
  transform: translateY(2px);
  box-shadow: 0 2px 0 var(--blue-dark);
}
.input-card label {
  display: block;
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 8px;
}
.input-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.input-row input[type="text"] {
  flex: 1;
  padding: 10px 14px;
  border: 3px solid rgba(255,255,255,0.5);
  border-radius: var(--radius-btn);
  font-size: 0.9rem;
  font-family: var(--font);
  background: rgba(255,255,255,0.92);
  color: var(--text);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-row input[type="text"]:focus {
  border-color: #fff;
  box-shadow: 0 0 0 3px rgba(255,255,255,0.3);
}
.input-row input[type="text"]::placeholder {
  color: #b0a898;
}
.btn-paste {
  padding: 10px 12px;
  background: rgba(255,255,255,0.25);
  color: #fff;
  border: 3px solid rgba(255,255,255,0.4);
  border-radius: var(--radius-btn);
  font-size: 0.95rem;
  font-family: var(--font);
  cursor: pointer;
  transition: background 0.2s, transform 0.12s;
  white-space: nowrap;
  font-weight: 700;
}
.btn-paste:hover {
  background: rgba(255,255,255,0.4);
  transform: translateY(-1px);
}
.btn-paste:active {
  transform: translateY(1px);
}

.btn-row {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.btn-primary {
  flex: 1;
  min-width: 160px;
  padding: 10px 18px;
  background: var(--yellow);
  color: var(--text);
  border: none;
  border-radius: var(--radius-btn);
  font-size: 0.92rem;
  font-weight: 700;
  font-family: var(--font);
  cursor: pointer;
  box-shadow: var(--shadow-btn) var(--yellow-dark);
  transition: transform 0.12s, box-shadow 0.12s, opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 5px 0 var(--yellow-dark); }
.btn-primary:active { transform: translateY(2px); box-shadow: 0 2px 0 var(--yellow-dark); }
.btn-primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
  box-shadow: var(--shadow-btn) var(--yellow-dark);
}

.btn-text {
  background: none;
  border: none;
  color: rgba(255,255,255,0.85);
  font-size: 0.78rem;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  padding: 8px 4px;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 0.2s;
  white-space: nowrap;
}
.btn-text:hover { color: #fff; }

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 3px solid rgba(114,93,66,0.2);
  border-top-color: var(--text);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Options Panel ===== */
.options-panel {
  background: var(--bg-card);
  border: 2px solid #ede6d3;
  border-radius: var(--radius-card);
  margin-bottom: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(114,93,66,0.06);
}
.options-toggle {
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: none;
  font-size: 0.85rem;
  font-weight: 700;
  font-family: var(--font);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  transition: background 0.2s;
}
.options-toggle:hover { background: rgba(136,157,240,0.06); }
.options-toggle .arrow {
  font-size: 0.8rem;
  transition: transform 0.25s;
  flex-shrink: 0;
}
.options-panel.open .options-toggle .arrow { transform: rotate(180deg); }
.options-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease, padding 0.35s ease;
  padding: 0 20px;
}
.options-panel.open .options-body {
  max-height: 400px;
  padding: 0 20px 18px;
}

.option-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f0ebd8;
}
.option-row:last-child { border-bottom: none; }
.option-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text);
}
.option-label small {
  display: block;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-light);
  margin-top: 2px;
}

/* Quality dropdown */
.quality-select {
  padding: 6px 10px;
  border: 2px solid #ede6d3;
  border-radius: var(--radius-btn);
  font-size: 0.8rem;
  font-family: var(--font);
  font-weight: 600;
  color: var(--text);
  background: var(--bg);
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}
.quality-select:focus { border-color: var(--blue); }

/* Toggle switch */
.toggle-switch {
  position: relative;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #d4c9b0;
  border-radius: var(--radius-pill);
  transition: background 0.3s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle-switch input:checked + .toggle-slider {
  background: var(--green-dark);
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

/* ===== Tabs ===== */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.tab-btn {
  flex: 1;
  padding: 8px 12px;
  border: 3px solid transparent;
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: 700;
  font-family: var(--font);
  cursor: pointer;
  background: var(--bg-card);
  color: var(--text-light);
  transition: all 0.2s;
  text-align: center;
}
.tab-btn.active {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue-dark);
  box-shadow: var(--shadow-btn) var(--blue-dark);
}
.tab-btn:not(.active):hover {
  background: var(--blue-light);
  color: var(--text);
}

.tab-content { display: none; }
.tab-content.active { display: block; }

/* ===== Scrollable Content Area ===== */
.tab-content-area {
  height: calc(100vh - 310px);
  min-height: 180px;
  overflow-y: auto;
  overflow-x: hidden;
}
.tab-content-area::-webkit-scrollbar {
  width: 6px;
}
.tab-content-area::-webkit-scrollbar-track {
  background: transparent;
}
.tab-content-area::-webkit-scrollbar-thumb {
  background: #d4c9b0;
  border-radius: 3px;
}

/* ===== Download Items ===== */
.download-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.download-item {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(114,93,66,0.08);
  transition: transform 0.15s;
}
.download-item:hover { transform: translateY(-1px); }

.download-item .url {
  font-size: 0.78rem;
  color: var(--text-light);
  word-break: break-all;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.progress-bar-wrap {
  flex: 1;
  background: #ede6d3;
  border-radius: var(--radius-pill);
  height: 10px;
  overflow: hidden;
  position: relative;
}
.progress-bar-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, var(--teal), var(--green));
  transition: width 0.4s ease;
  min-width: 0;
}
.progress-bar-fill.error {
  background: linear-gradient(90deg, var(--pink), var(--red));
}

.download-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--text-light);
  flex-wrap: wrap;
  gap: 4px;
}
.download-meta .speed { font-weight: 700; color: var(--teal-dark); }

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-size: 0.7rem;
  font-weight: 700;
}
.status-badge.downloading { background: var(--blue-light); color: var(--blue-dark); }
.status-badge.completed { background: #d4edda; color: #2d7a3a; }
.status-badge.error { background: #fce4e4; color: var(--red-dark); }
.status-badge.starting { background: var(--yellow); color: #8a6d2b; }

.empty-state {
  text-align: center;
  padding: 16px 10px;
  color: var(--text-light);
  font-size: 0.85rem;
}
.empty-state .emoji { font-size: 1.6rem; margin-bottom: 8px; }

/* ===== Running Animal Animation ===== */
@keyframes animalRun {
  0% { transform: translateX(-10px); }
  50% { transform: translateX(10px); }
  100% { transform: translateX(-10px); }
}
@keyframes animalBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
.running-animal {
  display: inline-block;
  animation: animalRun 0.5s ease-in-out infinite;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.running-animal .body {
  display: inline-block;
  animation: animalBounce 0.25s ease-in-out infinite;
}

/* ===== History Items ===== */
.history-item {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 8px 14px;
  box-shadow: 0 2px 8px rgba(114,93,66,0.08);
  margin-bottom: 6px;
  transition: transform 0.15s;
}
.history-item:hover { transform: translateY(-1px); }

.history-item .top-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 6px;
}
.history-item .url {
  font-size: 0.78rem;
  color: var(--text-light);
  word-break: break-all;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.history-item .file-row {
  font-size: 0.75rem;
  color: var(--text-light);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-item .file-row span {
  cursor: pointer;
  color: var(--blue-dark);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.history-item .file-row span:hover { color: var(--purple-dark); }

.history-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-sm {
  padding: 4px 10px;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  font-weight: 700;
  font-family: var(--font);
  cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s;
}
.btn-sm:active { transform: translateY(1px); }
.btn-sm.open { background: var(--teal); color: #fff; box-shadow: 0 3px 0 var(--teal-dark); }
.btn-sm.copy { background: var(--purple); color: #fff; box-shadow: 0 3px 0 var(--purple-dark); }
.btn-sm.delete { background: var(--pink); color: #fff; box-shadow: 0 3px 0 var(--pink-dark); }

.btn-clear-all {
  display: block;
  margin: 8px auto 0;
  padding: 6px 16px;
  background: var(--red);
  color: #fff;
  border: none;
  border-radius: var(--radius-pill);
  font-size: 0.78rem;
  font-weight: 700;
  font-family: var(--font);
  cursor: pointer;
  box-shadow: 0 3px 0 var(--red-dark);
  transition: transform 0.12s, box-shadow 0.12s;
}
.btn-clear-all:hover { transform: translateY(-1px); box-shadow: 0 4px 0 var(--red-dark); }
.btn-clear-all:active { transform: translateY(1px); box-shadow: 0 2px 0 var(--red-dark); }

/* ===== Toast ===== */
.toast-container {
  position: fixed;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  pointer-events: none;
}
.toast {
  background: var(--text);
  color: #fff;
  padding: 8px 18px;
  border-radius: var(--radius-pill);
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  animation: toastIn 0.35s ease, toastOut 0.35s ease 2.5s forwards;
  pointer-events: auto;
  max-width: 90vw;
  text-align: center;
}
.toast.success { background: var(--green-dark); }
.toast.error { background: var(--red-dark); }

@keyframes toastIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes toastOut {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(20px); }
}
</style>
</head>
<body>

<div class="container">
  <!-- Header: logo + title + time widget in one row -->
  <div class="header-row">
    <div class="logo-wrap">
      <svg viewBox="0 0 60 60" width="32" height="32">
        <ellipse cx="30" cy="35" rx="22" ry="20" fill="#8B6F47"/>
        <ellipse cx="30" cy="32" rx="18" ry="16" fill="#A0845C"/>
        <circle cx="22" cy="28" r="3" fill="#333"/>
        <circle cx="38" cy="28" r="3" fill="#333"/>
        <circle cx="23" cy="27" r="1" fill="#fff"/>
        <circle cx="39" cy="27" r="1" fill="#fff"/>
        <ellipse cx="30" cy="34" rx="4" ry="3" fill="#E8967D"/>
        <path d="M18 42 L14 50 L20 46Z" fill="#fff" stroke="#ddd" stroke-width="0.5"/>
        <path d="M30 44 L30 52 L34 46Z" fill="#fff" stroke="#ddd" stroke-width="0.5"/>
        <path d="M42 42 L46 50 L40 46Z" fill="#fff" stroke="#ddd" stroke-width="0.5"/>
        <circle cx="12" cy="48" r="2" fill="#C4A265"/>
        <circle cx="48" cy="50" r="1.5" fill="#C4A265"/>
        <circle cx="30" cy="54" r="2.5" fill="#C4A265"/>
      </svg>
      <h1>TranslookDown <span class="version-badge">V4</span></h1>
    </div>
    <div class="time-widget-inline">
      <span id="timeDay" class="time-day">MON</span>
      <span id="timeClock" class="time-clock">00:00</span>
    </div>
  </div>

  <!-- Input Card -->
  <div class="input-card">
    <label>&#128279; 粘贴视频链接</label>
    <div class="input-row">
      <input type="text" id="urlInput" placeholder="https://..." autocomplete="off" spellcheck="false">
      <button class="btn-paste" id="pasteBtn" onclick="pasteAndDownload()" title="从剪贴板粘贴并下载">&#128203; 粘贴</button>
    </div>
    <div class="btn-row">
      <button class="btn-primary" id="downloadBtn" onclick="startDownload()">
        <span id="btnText">&#11015;&#65039; 开始下载</span>
      </button>
      <button class="btn-text" onclick="openFolder()">&#128193; 文件夹</button>
    </div>
  </div>

  <!-- Options (collapsed by default, compact) -->
  <div class="options-panel" id="optionsPanel">
    <button class="options-toggle" onclick="toggleOptions()">
      <span>&#9881; 选项</span>
      <span class="arrow">&#9660;</span>
    </button>
    <div class="options-body">
      <div class="option-row">
        <div class="option-label">
          画质选择
          <small>选择视频下载画质</small>
        </div>
        <select class="quality-select" id="optFormat">
          <option value="bestvideo+bestaudio/best">最佳画质</option>
          <option value="bestvideo[height<=1080]+bestaudio/best[height<=1080]">1080p</option>
          <option value="bestvideo[height<=720]+bestaudio/best[height<=720]">720p</option>
          <option value="bestaudio">仅音频</option>
        </select>
      </div>
      <div class="option-row">
        <div class="option-label">
          下载字幕
          <small>嵌入英文/中文字幕</small>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="optSubtitle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="option-row">
        <div class="option-label">
          下载缩略图
          <small>嵌入视频封面图</small>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="optThumbnail">
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="option-row">
        <div class="option-label">
          嵌入元数据
          <small>嵌入视频信息和章节</small>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="optMetadata">
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab-btn active" id="tabDownloads" onclick="switchTab('downloads')">&#11015;&#65039; 下载 (<span id="downloadCount">0</span>)</button>
    <button class="tab-btn" id="tabHistory" onclick="switchTab('history')">&#128203; 历史 (<span id="historyCount">0</span>)</button>
  </div>

  <!-- Scrollable content area -->
  <div class="tab-content-area">
    <div class="tab-content active" id="contentDownloads">
      <div class="download-list" id="downloadList">
        <div class="empty-state">
          <div class="emoji">&#127744;</div>
          <div>暂无下载任务，粘贴链接开始下载吧~</div>
        </div>
      </div>
    </div>
    <div class="tab-content" id="contentHistory">
      <div id="historyList">
        <div class="empty-state">
          <div class="emoji">&#128214;</div>
          <div>还没有下载记录哦~</div>
        </div>
      </div>
      <button class="btn-clear-all" id="clearAllBtn" style="display:none" onclick="clearHistory()">&#128465;&#65039; 清空</button>
    </div>
  </div>
</div>

<!-- Toast Container -->
<div class="toast-container" id="toastContainer"></div>

<script>
// ===== State =====
var activeDownloads = {};
var historyData = [];
var isDownloading = false;
var pollTimer = null;
var progressTimers = {};

// ===== Init =====
document.addEventListener('DOMContentLoaded', function() {
  loadHistory();
  startPolling();
  updateClock();
  setInterval(updateClock, 1000);
  // Enter key triggers download
  document.getElementById('urlInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') startDownload();
  });
});

// ===== Clock Widget =====
function updateClock() {
  var now = new Date();
  var days = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
  document.getElementById('timeDay').textContent = days[now.getDay()];
  var h = now.getHours().toString().padStart(2, '0');
  var m = now.getMinutes().toString().padStart(2, '0');
  document.getElementById('timeClock').textContent = h + ':' + m;
}

// ===== Paste & Download =====
async function pasteAndDownload() {
  try {
    var text = await navigator.clipboard.readText();
    if (text && text.trim().startsWith('http')) {
      document.getElementById('urlInput').value = text.trim();
      showToast('已粘贴并开始下载！', 'success');
      startDownload();
    } else {
      document.getElementById('urlInput').value = text;
      showToast('已粘贴，但内容不是有效链接', 'error');
    }
  } catch(e) {
    showToast('无法读取剪贴板，请手动粘贴', 'error');
  }
}

// ===== Options Panel =====
function toggleOptions() {
  document.getElementById('optionsPanel').classList.toggle('open');
}

// ===== Download =====
async function startDownload() {
  var input = document.getElementById('urlInput');
  var url = input.value.trim();
  if (!url) {
    showToast('请输入视频链接', 'error');
    input.focus();
    return;
  }
  if (isDownloading) return;

  var btn = document.getElementById('downloadBtn');
  var btnText = document.getElementById('btnText');
  btn.disabled = true;
  btnText.innerHTML = '<span class="spinner"></span> 请求中...';
  isDownloading = true;

  // Gather options
  var options = {
    format: document.getElementById('optFormat').value,
    subtitle: document.getElementById('optSubtitle').checked,
    thumbnail: document.getElementById('optThumbnail').checked,
    metadata: document.getElementById('optMetadata').checked
  };

  try {
    var resp = await fetch('/api/download', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url: url, format: options.format, subtitle: options.subtitle, thumbnail: options.thumbnail, metadata: options.metadata})
    });
    var data = await resp.json();
    if (data.error) {
      showToast(data.error, 'error');
      resetBtn();
      return;
    }
    showToast('下载已开始!', 'success');
    input.value = '';
    switchTab('downloads');
    startProgressPoll(data.task_id);
  } catch (e) {
    showToast('请求失败: ' + e.message, 'error');
  }
  resetBtn();
}

function resetBtn() {
  isDownloading = false;
  var btn = document.getElementById('downloadBtn');
  var btnText = document.getElementById('btnText');
  btn.disabled = false;
  btnText.innerHTML = '&#11015;&#65039; 开始下载';
}

// ===== Polling =====
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollDownloads, 2000);
}

async function pollDownloads() {
  try {
    var resp = await fetch('/api/downloads');
    var data = await resp.json();
    var prevCount = Object.keys(activeDownloads).length;
    activeDownloads = data;
    var newCount = Object.keys(activeDownloads).length;
    renderDownloads();
    document.getElementById('downloadCount').textContent = newCount;

    if (prevCount > 0 && newCount === 0) {
      loadHistory();
    }

    for (var tid in data) {
      if (!progressTimers[tid]) {
        startProgressPoll(tid);
      }
    }
  } catch (e) {
    // silent
  }
}

function startProgressPoll(taskId) {
  if (progressTimers[taskId]) return;
  progressTimers[taskId] = setInterval(async function() {
    try {
      var resp = await fetch('/api/progress/' + taskId);
      if (resp.status === 404) {
        clearInterval(progressTimers[taskId]);
        delete progressTimers[taskId];
        return;
      }
      var data = await resp.json();
      activeDownloads[taskId] = data;
      renderDownloads();

      if (data.status === 'completed' || data.status === 'error') {
        clearInterval(progressTimers[taskId]);
        delete progressTimers[taskId];
        if (data.status === 'completed') {
          showToast('下载完成!', 'success');
          loadHistory();
        } else {
          showToast('下载失败: ' + (data.error || '未知错误'), 'error');
        }
      }
    } catch (e) {
      // silent
    }
  }, 1500);
}

// ===== Render Downloads =====
function renderDownloads() {
  var list = document.getElementById('downloadList');
  var keys = Object.keys(activeDownloads);
  if (keys.length === 0) {
    list.innerHTML = '<div class="empty-state"><div class="emoji">&#127744;</div><div>暂无下载任务，粘贴链接开始下载吧~</div></div>';
    return;
  }
  var html = '';
  for (var i = 0; i < keys.length; i++) {
    var tid = keys[i];
    var d = activeDownloads[tid];
    var pct = d.progress ? d.progress.percent : 0;
    var speed = d.progress ? d.progress.speed : '';
    var eta = d.progress ? d.progress.eta : '';
    var totalSize = d.progress ? d.progress.total_size : '';
    var isError = d.status === 'error';
    var isDownloading2 = d.status === 'downloading';
    var statusLabel = d.status === 'starting' ? '准备中' : d.status === 'downloading' ? '下载中' : d.status === 'completed' ? '已完成' : '失败';
    var badgeClass = d.status;

    html += '<div class="download-item">';
    html += '<div class="url">' + escapeHtml(d.url) + '</div>';
    html += '<div class="progress-row">';
    html += '<span class="status-badge ' + badgeClass + '">' + statusLabel + '</span>';
    if (isDownloading2) {
      html += '<span class="running-animal"><span class="body">&#128560;</span></span>';
    }
    html += '<span style="font-size:0.85rem;font-weight:700;color:var(--text)">' + pct.toFixed(1) + '%</span>';
    html += '</div>';
    html += '<div class="progress-bar-wrap"><div class="progress-bar-fill' + (isError ? ' error' : '') + '" style="width:' + pct + '%"></div></div>';
    html += '<div class="download-meta">';
    html += '<span class="speed">' + (speed || '--') + '</span>';
    html += '<span>ETA ' + (eta || '--') + '</span>';
    html += '<span>' + (totalSize || '--') + '</span>';
    html += '</div>';
    if (isError && d.error) {
      html += '<div style="margin-top:6px;font-size:0.82rem;color:var(--red-dark)">' + escapeHtml(d.error) + '</div>';
    }
    html += '</div>';
  }
  list.innerHTML = html;
}

// ===== History =====
async function loadHistory() {
  try {
    var resp = await fetch('/api/history');
    historyData = await resp.json();
    document.getElementById('historyCount').textContent = historyData.length;
    renderHistory();
  } catch (e) {
    // silent
  }
}

function renderHistory() {
  var list = document.getElementById('historyList');
  var clearBtn = document.getElementById('clearAllBtn');
  if (historyData.length === 0) {
    list.innerHTML = '<div class="empty-state"><div class="emoji">&#128214;</div><div>还没有下载记录哦~</div></div>';
    clearBtn.style.display = 'none';
    return;
  }
  clearBtn.style.display = 'block';
  var html = '';
  for (var i = 0; i < historyData.length; i++) {
    var h = historyData[i];
    var statusLabel = h.status === 'completed' ? '已完成' : '失败';
    var badgeClass = h.status;
    var filename = h.filepath ? h.filepath.split(/[\/\\]/).pop() : '';
    var timeStr = h.finished_at ? formatTime(h.finished_at) : '';

    html += '<div class="history-item">';
    html += '<div class="top-row">';
    html += '<div class="url">' + escapeHtml(h.url) + '</div>';
    html += '<span class="status-badge ' + badgeClass + '">' + statusLabel + '</span>';
    html += '</div>';
    if (filename && filename !== 'unknown' && filename !== 'already_downloaded') {
      html += '<div class="file-row"><span onclick="openFile(\'' + escapeJs(h.filepath) + '\')" title="' + escapeHtml(h.filepath) + '">' + escapeHtml(filename) + '</span></div>';
    }
    html += '<div class="download-meta" style="margin-bottom:8px"><span>' + timeStr + '</span></div>';
    html += '<div class="history-actions">';
    if (h.filepath && h.filepath !== 'unknown' && h.filepath !== 'already_downloaded') {
      html += '<button class="btn-sm open" onclick="openFile(\'' + escapeJs(h.filepath) + '\')">&#128194; 打开</button>';
    }
    html += '<button class="btn-sm copy" onclick="copyUrl(\'' + escapeJs(h.url) + '\')">&#128203; 复制链接</button>';
    html += '<button class="btn-sm delete" onclick="deleteRecord(\'' + h.id + '\')">&#128465;&#65039; 删除</button>';
    html += '</div>';
    html += '</div>';
  }
  list.innerHTML = html;
}

async function deleteRecord(id) {
  try {
    await fetch('/api/history/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: id})
    });
    loadHistory();
    showToast('记录已删除', 'success');
  } catch (e) {
    showToast('删除失败', 'error');
  }
}

async function clearHistory() {
  if (!confirm('确定要清空全部历史记录吗？')) return;
  try {
    await fetch('/api/history/clear', {method: 'POST'});
    loadHistory();
    showToast('历史已清空', 'success');
  } catch (e) {
    showToast('清空失败', 'error');
  }
}

// ===== Actions =====
async function openFile(filepath) {
  try {
    await fetch('/api/open_file', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filepath: filepath})
    });
  } catch (e) {
    showToast('无法打开文件', 'error');
  }
}

async function openFolder() {
  try {
    await fetch('/api/open_folder', {method: 'POST'});
  } catch (e) {
    showToast('无法打开文件夹', 'error');
  }
}

function copyUrl(url) {
  navigator.clipboard.writeText(url).then(function() {
    showToast('链接已复制!', 'success');
  }).catch(function() {
    var ta = document.createElement('textarea');
    ta.value = url;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('链接已复制!', 'success');
  });
}

// ===== Tabs =====
function switchTab(tab) {
  document.getElementById('tabDownloads').classList.toggle('active', tab === 'downloads');
  document.getElementById('tabHistory').classList.toggle('active', tab === 'history');
  document.getElementById('contentDownloads').classList.toggle('active', tab === 'downloads');
  document.getElementById('contentHistory').classList.toggle('active', tab === 'history');
  if (tab === 'history') loadHistory();
}

// ===== Toast =====
function showToast(msg, type) {
  var container = document.getElementById('toastContainer');
  var toast = document.createElement('div');
  toast.className = 'toast' + (type ? ' ' + type : '');
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(function() {
    if (toast.parentElement) toast.remove();
  }, 3000);
}

// ===== Helpers =====
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function formatTime(isoStr) {
  try {
    var d = new Date(isoStr);
    var now = new Date();
    var diff = now - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff/60000) + ' 分钟前';
    if (diff < 86400000) return Math.floor(diff/3600000) + ' 小时前';
    var month = (d.getMonth()+1).toString().padStart(2,'0');
    var day = d.getDate().toString().padStart(2,'0');
    var hour = d.getHours().toString().padStart(2,'0');
    var min = d.getMinutes().toString().padStart(2,'0');
    return month + '-' + day + ' ' + hour + ':' + min;
  } catch(e) {
    return isoStr;
  }
}
</script>
</body>
</html>"""


# ============================================================
# Main Entry Point
# ============================================================

def main():
    # Step 1: Extract bundled binaries
    print("=" * 50)
    print("  TranslookDown V4 - Standalone Edition")
    print("=" * 50)
    print("  正在初始化工具...")
    bundle = setup_environment()

    ytdlp = get_ytdlp_path()
    ffmpeg = get_ffmpeg_path()
    download_dir = get_download_dir()

    print(f"  yt-dlp: {ytdlp}")
    print(f"  ffmpeg: {ffmpeg}")
    print(f"  下载目录: {download_dir}")
    print(f"  历史文件: {get_history_path()}")
    print("=" * 50)
    print("  正在启动...")

    # Verify yt-dlp exists
    if not os.path.exists(ytdlp):
        print(f"  ERROR: yt-dlp not found at {ytdlp}")
        input("Press Enter to exit...")
        return

    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)

    # Start Flask in background thread
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    flask_thread = threading.Thread(
        target=lambda: app.run(host=HOST, port=PORT, debug=False, threaded=True),
        daemon=True,
    )
    flask_thread.start()

    # Wait for Flask to be ready
    time.sleep(1)

    # Launch pywebview window (embedded browser, no external browser needed)
    import webview

    webview.create_window(
        title="TranslookDown V4",
        url=f"http://localhost:{PORT}",
        width=820,
        height=680,
        min_size=(820, 680),
        frameless=True,       # No window frame/border
        easy_drag=True,       # Allow dragging the window from any point
        text_select=True,
        shadow=True,          # Window shadow for 3D depth effect
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
