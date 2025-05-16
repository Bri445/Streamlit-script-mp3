import streamlit as st
import yt_dlp
import tempfile
import os
import zipfile
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="🎧 YouTube MP3 Batch & Playlist Downloader", layout="centered", page_icon="🎧")

# --- CSS Styling (Dark Purple Modern theme) ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        background: linear-gradient(135deg, #2b1055, #7597de);
        color: #e0e0e0 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTextArea textarea {
        background-color: #3a2f60 !important;
        color: #f0f0f0 !important;
        border-radius: 12px !important;
        border: 1px solid #9277d4 !important;
        font-size: 16px !important;
        padding: 12px !important;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #845ec2 !important;
        color: white !important;
        border-radius: 14px !important;
        padding: 0.75em 1.5em !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #d39df3 !important;
        color: #21005d !important;
    }
    .glass-box {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1.5px solid rgba(255, 255, 255, 0.15);
        margin-top: 1rem;
    }
    .video-title {
        font-weight: 600;
        font-size: 15px;
        color: #f0e6ff;
        margin-bottom: 4px;
        overflow-wrap: break-word;
    }
    .status-text {
        font-size: 14px;
        color: #d7c7ff;
        margin-bottom: 6px;
    }
    .speed-text {
        font-size: 13px;
        color: #b1a0f7;
        margin-top: -6px;
        margin-bottom: 10px;
    }
    hr {
        border: 0;
        height: 1px;
        background: #5a4f94;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def convert_speed_to_mbps(speed_str):
    try:
        if "MiB/s" in speed_str:
            return float(speed_str.replace("MiB/s", "").strip()) * 8
        elif "KiB/s" in speed_str:
            return float(speed_str.replace("KiB/s", "").strip()) * 8 / 1024
        elif "B/s" in speed_str:
            return float(speed_str.replace("B/s", "").strip()) * 8 / (1024*1024)
    except:
        return 0.0
    return 0.0


def download_audio_to_temp(youtube_url, temp_dir, progress_placeholder, speed_placeholder, title_placeholder, retries=3):
    output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
    attempt = 0
    last_error = None

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0.0%').replace('%', '').strip()
            speed = d.get('_speed_str', '0.0MiB/s')
            speed_mbps = convert_speed_to_mbps(speed)
            downloaded_title = d.get('filename', '').split('/')[-1].replace('.webm', '').replace('.m4a', '')
            try:
                progress_placeholder.progress(min(float(percent)/100, 1.0))
                speed_placeholder.text(f"📶 Speed: {speed_mbps:.2f} Mbps")
                if downloaded_title:
                    title_placeholder.text(f"🎵 Downloading: {downloaded_title}")
            except:
                pass

    while attempt < retries:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                filename = ydl.prepare_filename(info_dict)
                mp3_file = os.path.splitext(filename)[0] + '.mp3'
                progress_placeholder.progress(1.0)
                speed_placeholder.text("✅ Done")
                return mp3_file
        except Exception as e:
            last_error = e
            attempt += 1
            time.sleep(1)
            speed_placeholder.text(f"⚠️ Retrying... ({attempt}/{retries})")
            progress_placeholder.progress(0)
            title_placeholder.text(f"")

    raise last_error


def get_playlist_videos(playlist_url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        # Some playlist URLs return single video info, handle gracefully
        if 'entries' in info:
            entries = info['entries']
            videos = [{'title': e['title'], 'url': f"https://www.youtube.com/watch?v={e['id']}"} for e in entries if e]
            playlist_title = info.get('title', 'Playlist')
            return playlist_title, videos
        else:
            # Not a playlist, single video
            return None, [{'title': info.get('title', 'Video'), 'url': playlist_url}]


# UI Components & Logic
st.markdown("<h1 style='text-align: center; margin-bottom: 0.3em;'>🎧 YouTube MP3 Batch & Playlist Downloader</h1>", unsafe_allow_html=True)

st.markdown("<div class='glass-box'>", unsafe_allow_html=True)

urls_text = st.text_area(
    "📥 Paste YouTube URLs or Playlist URL (one per line or single playlist URL):",
    placeholder="https://www.youtube.com/watch?v=abc123\nhttps://www.youtube.com/playlist?list=PLxyz456",
    height=200
)

max_workers = 3  # Parallel download threads limit

if st.button("🚀 Fetch & Prepare Download List"):

    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    if not urls:
        st.warning("⚠️ Please enter at least one valid YouTube or playlist URL.")
    else:
        video_list = []
        errors_fetch = []

        with st.spinner("⏳ Fetching playlist info..."):
            for url in urls:
                try:
                    playlist_title, videos = get_playlist_videos(url)
                    if playlist_title:
                        st.markdown(f"### 📁 Playlist: {playlist_title} ({len(videos)} videos)")
                    else:
                        st.markdown(f"### 🎬 Single Video URL")

                    for vid in videos:
                        video_list.append(vid)
                except Exception as e:
                    errors_fetch.append(f"Failed to fetch videos from: {url} ({str(e)})")

        if errors_fetch:
            st.error("⚠️ Some URLs failed to fetch:")
            for err in errors_fetch:
                st.write(err)

        if video_list:
            st.markdown("---")
            st.markdown(f"#### 🎯 Ready to download {len(video_list)} videos. Click below to start batch download:")
            download_trigger = st.button("🚀 Download All as ZIP")

            if download_trigger:

                with tempfile.TemporaryDirectory() as temp_dir:
                    mp3_files = []
                    errors_download = []
                    lock = threading.Lock()

                    status_container = st.container()
                    progress_placeholders = []
                    speed_placeholders = []
                    title_placeholders = []

                    # Prepare placeholders for each video status
                    for vid in video_list:
                        with status_container:
                            st.markdown(f"<div class='video-title'>🎵 {vid['title']}</div>", unsafe_allow_html=True)
                            p = st.progress(0)
                            progress_placeholders.append(p)
                            speed_placeholders.append(st.empty())
                            title_placeholders.append(st.empty())

                    def worker(i, url):
                        try:
                            mp3_path = download_audio_to_temp(
                                url, temp_dir,
                                progress_placeholders[i], speed_placeholders[i], title_placeholders[i]
                            )
                            with lock:
                                mp3_files.append(mp3_path)
                        except Exception as e:
                            with lock:
                                errors_download.append(f"❌ Failed: {video_list[i]['title']} - {str(e)}")

                    # Run parallel downloads
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = []
                        for i, vid in enumerate(video_list):
                            futures.append(executor.submit(worker, i, vid['url']))

                        # Wait for all to finish
                        for f in futures:
                            f.result()

                    if mp3_files:
                        zip_path = os.path.join(temp_dir, "YouTube_MP3s.zip")
                        with zipfile.ZipFile(zip_path, 'w') as zipf:
                            for mp3_file in mp3_files:
                                zipf.write(mp3_file, os.path.basename(mp3_file))

                        with open(zip_path, "rb") as f:
                            zip_data = f.read()

                        st.success(f"✅ Downloaded {len(mp3_files)} files successfully!")
                        st.download_button(
                            label="📦 Download All MP3s (ZIP)",
                            data=zip_data,
                            file_name="YouTube_MP3s.zip",
                            mime="application/zip"
                        )

                    if errors_download:
                        st.error("⚠️ Some downloads failed:")
                        for err in errors_download:
                            st.write(err)

st.markdown("</div>", unsafe_allow_html=True)
st.caption("Made with ❤️ using Streamlit & yt-dlp")
