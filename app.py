import streamlit as st
import yt_dlp
from pathlib import Path
import time

# ---------------- UI ----------------
st.set_page_config(page_title="YouTube Downloader", page_icon="📥")
st.title("📥 YouTube Video Downloader")
st.caption(
    "Select quality → download starts → save via browser (correct file guaranteed)"
)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

url = st.text_input("🎬 Enter YouTube URL")

progress_bar = st.progress(0)
status_text = st.empty()

# Allowed qualities
ALLOWED_HEIGHTS = [480, 720, 1080, 1440, 2160, 4320]

# -------- Session State --------
if "qualities" not in st.session_state:
    st.session_state.qualities = []
if "title" not in st.session_state:
    st.session_state.title = ""
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
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    qualities = sorted(
        {
            f["height"]
            for f in info["formats"]
            if f.get("vcodec") != "none"
            and f.get("height") in ALLOWED_HEIGHTS
        }
    )

    return qualities, info.get("title", "video")


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
        status_text.text("🔧 Finalizing video (FFmpeg CFR)...")


def start_download():
    if st.session_state.downloading:
        return

    st.session_state.downloading = True
    st.session_state.file_path = None

    progress_bar.progress(0)
    status_text.text("Starting download...")

    height = st.session_state.selected_quality
    timestamp = int(time.time())

    # ✅ Unique & controlled filename (CRITICAL FIX)
    output_file = DOWNLOAD_DIR / f"video_{height}p_{timestamp}.mp4"

    ydl_opts = {
        # best video at chosen height + best audio
        "format": f"bestvideo[height={height}]+bestaudio/best",
        "outtmpl": str(output_file),
        "merge_output_format": "mp4",
        # Force CFR & fix timestamps
        "postprocessor_args": {
            "ffmpeg": ["-movflags", "+faststart", "-vsync", "cfr"]
        },
        "progress_hooks": [progress_hook],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # ✅ EXACT file path saved (no guessing)
    st.session_state.file_path = output_file
    st.session_state.downloading = False


# ---------------- Main UI ----------------

if url:
    if "youtube.com" not in url and "youtu.be" not in url:
        st.error("❌ Invalid YouTube URL")
    else:
        if not st.session_state.qualities:
            with st.spinner("🔍 Fetching available qualities..."):
                q, t = fetch_qualities(url)
                st.session_state.qualities = q
                st.session_state.title = t

        if st.session_state.qualities:
            st.selectbox(
                "🎯 Select Quality (download starts automatically)",
                st.session_state.qualities,
                format_func=lambda x: f"{x}p",
                key="selected_quality",
                on_change=start_download,
            )
        else:
            st.warning("⚠️ None of the selected qualities are available for this video.")


# ---------------- Final Browser Download ----------------

if st.session_state.file_path:
    st.success("✅ Video ready to download")

    with open(st.session_state.file_path, "rb") as f:
        st.download_button(
            label="⬇️ Download Video",
            data=f,
            file_name=st.session_state.file_path.name,
            mime="video/mp4",
        )
