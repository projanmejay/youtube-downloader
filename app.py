import streamlit as st
import yt_dlp
from pathlib import Path
import time
import os

# ---------------- CONFIG ----------------
# On Render, use a relative path. Ensure this file is in your GitHub repo
# or uploaded as a "Secret File" in Render.
COOKIES_PATH = "www.youtube.com_cookies.txt"

# Path to ffmpeg (installed via render-build.sh)
FFMPEG_LOCATION = "./ffmpeg"

ALLOWED_HEIGHTS = [480, 720, 1080, 1440, 2160, 4320]

# Use /tmp for temporary storage on cloud platforms
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ---------------- UI ----------------
st.set_page_config(page_title="YouTube Downloader", page_icon="📥")
st.title("📥 YouTube Video Downloader")
st.caption(
    "Select quality → download starts → save via browser"
)

url = st.text_input("🎬 Enter YouTube URL")

progress_bar = st.progress(0)
status_text = st.empty()

# ---------------- Session State ----------------
if "qualities" not in st.session_state:
    st.session_state.qualities = []
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "downloading" not in st.session_state:
    st.session_state.downloading = False
if "selected_quality" not in st.session_state:
    st.session_state.selected_quality = None

# ---------------- Functions ----------------

def fetch_qualities(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "cookies": COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        qualities = sorted(
            {
                f.get("height")
                for f in info.get("formats", [])
                if f.get("vcodec") != "none"
                and f.get("height") in ALLOWED_HEIGHTS
            }
        )
        return qualities
    except Exception as e:
        st.error(f"Error fetching info: {e}")
        return []


def progress_hook(d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 1)
        downloaded = d.get("downloaded_bytes", 0)

        percent = int(downloaded / total * 100)
        speed = d.get("speed", 0)
        eta = d.get("eta", 0)

        speed_mb = round(speed / (1024 * 1024), 2) if speed else 0

        progress_bar.progress(percent)
        status_text.text(
            f"⬇️ {percent}% | {speed_mb} MB/s | ETA: {eta}s"
        )

    elif d["status"] == "finished":
        status_text.text("🔧 Finalizing video (merging audio/video)...")


def start_download():
    if st.session_state.downloading:
        return

    st.session_state.downloading = True
    st.session_state.file_path = None

    progress_bar.progress(0)
    status_text.text("Starting download...")

    height = st.session_state.selected_quality
    timestamp = int(time.time())

    output_file = DOWNLOAD_DIR / f"video_{height}p_{timestamp}.mp4"

    ydl_opts = {
        "format": f"bestvideo[height={height}]+bestaudio/best",
        "outtmpl": str(output_file),
        "merge_output_format": "mp4",
        "cookies": COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
        "ffmpeg_location": FFMPEG_LOCATION,
        "progress_hooks": [progress_hook],
        "postprocessor_args": [
            "-movflags", "+faststart",
        ],
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        st.session_state.file_path = output_file
    except Exception as e:
        st.error(f"Download failed: {e}")
    finally:
        st.session_state.downloading = False


# ---------------- Main UI ----------------

if url:
    if "youtube.com" not in url and "youtu.be" not in url:
        st.error("❌ Invalid YouTube URL")
    else:
        # Clear qualities if URL changes
        if "last_url" not in st.session_state or st.session_state.last_url != url:
            st.session_state.qualities = []
            st.session_state.file_path = None
            st.session_state.last_url = url

        if not st.session_state.qualities:
            with st.spinner("🔍 Fetching available qualities..."):
                st.session_state.qualities = fetch_qualities(url)

        if st.session_state.qualities:
            st.selectbox(
                "🎯 Select Quality",
                st.session_state.qualities,
                format_func=lambda x: f"{x}p",
                key="selected_quality",
                on_change=start_download,
            )
        else:
            st.warning("⚠️ No supported qualities found.")


# ---------------- Download Button ----------------

if st.session_state.file_path and os.path.exists(st.session_state.file_path):
    st.success("✅ Video ready!")

    with open(st.session_state.file_path, "rb") as f:
        st.download_button(
            label="⬇️ Click here to Save to Device",
            data=f,
            file_name=st.session_state.file_path.name,
            mime="video/mp4",
        )
