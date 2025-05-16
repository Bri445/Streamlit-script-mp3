import streamlit as st
import yt_dlp
import tempfile
import os
import zipfile
import time

st.set_page_config(page_title="🎧 YT MP3 Downloader with Playlist Support", layout="centered")

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

def download_audio_to_temp(youtube_url, temp_dir, progress_placeholder, speed_placeholder, title_placeholder):
    output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0.0%').replace('%', '').strip()
            speed = d.get('_speed_str', '0.0MiB/s')
            speed_mbps = convert_speed_to_mbps(speed)
            downloaded_title = d.get('filename', '').split('/')[-1].replace('.webm', '').replace('.m4a', '')
            try:
                progress_placeholder.progress(float(percent)/100)
                speed_placeholder.text(f"📶 Speed: {speed_mbps:.2f} Mbps")
                if downloaded_title:
                    title_placeholder.text(f"🎵 Downloading: {downloaded_title}")
            except:
                pass

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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        filename = ydl.prepare_filename(info_dict)
        mp3_file = os.path.splitext(filename)[0] + '.mp3'
    return mp3_file

def extract_playlist_info(playlist_url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        videos = []
        if 'entries' in info:
            for entry in info['entries']:
                title = entry.get('title', 'Unknown Title')
                url = entry.get('url') or entry.get('id')
                videos.append({'title': title, 'url': url})
        else:
            videos.append({'title': info.get('title', 'Unknown Title'), 'url': playlist_url})
        return videos

# --- Custom Styling ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        background-color: #0f0f0f !important;
        color: #f0f0f0 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTextArea textarea {
        background-color: #1f1f1f !important;
        color: #f0f0f0 !important;
        border-radius: 12px !important;
        border: 1px solid #444 !important;
    }
    .stButton>button {
        background-color: #6a0dad;
        color: white;
        border-radius: 12px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #a64ca6;
    }
    .stDownloadButton>button {
        background-color: #9c27b0;
        color: white;
        border-radius: 12px;
        padding: 0.6em 1.2em;
        font-weight: bold;
    }
    .glass-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 2rem;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>🎧 YouTube MP3 Downloader (Playlist & Retry Support)</h1>", unsafe_allow_html=True)
st.markdown("<div class='glass-box'>", unsafe_allow_html=True)

playlist_url = st.text_area(
    "📥 Paste a YouTube video or playlist URL",
    placeholder="https://www.youtube.com/watch?v=abc123\nor\nhttps://www.youtube.com/playlist?list=PLxyz",
    height=150
)

if playlist_url.strip():
    with st.spinner("🛠️ Extracting video titles..."):
        try:
            videos = extract_playlist_info(playlist_url.strip())
        except Exception as e:
            st.error(f"Failed to extract videos: {str(e)}")
            videos = []
else:
    videos = []

if videos:
    st.markdown(f"### 🎬 {len(videos)} videos found:")
    for idx, video in enumerate(videos, 1):
        st.markdown(f"{idx}. {video['title']}")

if st.button("🚀 Download All as ZIP") and videos:
    with st.spinner("🛠️ Downloading videos..."):
        with tempfile.TemporaryDirectory() as temp_dir:
            mp3_files = []
            errors = []

            for idx, video in enumerate(videos, 1):
                st.markdown(f"<hr><b>🔗 Processing ({idx}/{len(videos)}):</b> {video['title']}", unsafe_allow_html=True)
                title_placeholder = st.empty()
                speed_placeholder = st.empty()
                progress_placeholder = st.progress(0)

                retries = 0
                success = False
                while retries < 3 and not success:
                    try:
                        mp3_path = download_audio_to_temp(video['url'], temp_dir, progress_placeholder, speed_placeholder, title_placeholder)
                        mp3_files.append(mp3_path)
                        progress_placeholder.progress(100)
                        speed_placeholder.text("✅ Done")
                        success = True
                    except Exception as e:
                        retries += 1
                        if retries == 3:
                            errors.append(f"❌ {video['title']}: {str(e)}")
                        else:
                            speed_placeholder.text(f"⚠️ Retry {retries}...")

if 'mp3_files' in locals() and mp3_files:
    zip_path = os.path.join(temp_dir, "downloads.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for mp3_file in mp3_files:
            zipf.write(mp3_file, os.path.basename(mp3_file))

    with open(zip_path, "rb") as f:
        zip_data = f.read()

    st.success(f"✅ Downloaded {len(mp3_files)} files successfully!")
    st.download_button(
        label="📦 Download All (ZIP)",
        data=zip_data,
        file_name="YouTube_MP3s.zip",
        mime="application/zip"
    )

if 'errors' in locals() and errors:
    st.error("⚠️ Some files failed after retries:")
    for err in errors:
        st.write(err)

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Made with ❤️ using Streamlit & yt-dlp")
