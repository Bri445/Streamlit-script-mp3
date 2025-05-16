import streamlit as st
import yt_dlp
import tempfile
import os
import zipfile

st.set_page_config(page_title="🎧 YT MP3 Downloader", layout="centered")

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
                speed_placeholder.markdown(f"📶 <b>Speed:</b> {speed_mbps:.2f} Mbps", unsafe_allow_html=True)
                if downloaded_title:
                    title_placeholder.markdown(f"🎵 <b>Downloading:</b> {downloaded_title}", unsafe_allow_html=True)
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

# --- Custom Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        background: #0d0c1d;
        color: #f5f5f5;
        font-family: 'Outfit', sans-serif;
    }

    .stTextArea textarea {
        background-color: #1e1e2f;
        color: #fff;
        border: 1px solid #444;
        border-radius: 12px;
    }

    .stButton>button {
        background: linear-gradient(135deg, #6e34d2, #9b59b6);
        color: #fff;
        border: none;
        border-radius: 10px;
        padding: 0.7em 1.5em;
        font-weight: 600;
        font-size: 1rem;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #9b59b6, #be63f9);
        transition: 0.3s ease;
    }

    .stDownloadButton>button {
        background: linear-gradient(135deg, #00c6ff, #0072ff);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.7em 1.5em;
    }

    .glass-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 2rem;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: 1rem;
        box-shadow: 0 0 20px rgba(155, 89, 182, 0.2);
    }

    h1 {
        color: #e1bfff;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- UI Layout ---
st.markdown("<h1 style='text-align: center;'>🎶 YouTube MP3 Batch Downloader</h1>", unsafe_allow_html=True)
st.markdown("<div class='glass-box'>", unsafe_allow_html=True)

urls_text = st.text_area(
    "🎥 Enter YouTube video links (one per line):",
    placeholder="https://youtube.com/watch?v=video1\nhttps://youtube.com/watch?v=video2",
    height=200
)

if st.button("🚀 Start Batch Download"):
    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    if not urls:
        st.warning("⚠️ Please provide at least one YouTube link.")
    else:
        with st.spinner("🔄 Downloading & converting..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                mp3_files = []
                errors = []

                for url in urls:
                    st.markdown(f"<hr><b>🔗 Processing:</b> {url}", unsafe_allow_html=True)
                    title_placeholder = st.empty()
                    speed_placeholder = st.empty()
                    progress_placeholder = st.progress(0)

                    try:
                        mp3_path = download_audio_to_temp(url, temp_dir, progress_placeholder, speed_placeholder, title_placeholder)
                        mp3_files.append(mp3_path)
                        progress_placeholder.progress(100)
                        speed_placeholder.markdown("✅ <b>Completed</b>", unsafe_allow_html=True)
                    except Exception as e:
                        errors.append(f"❌ {url}: {str(e)}")

                if mp3_files:
                    zip_path = os.path.join(temp_dir, "YouTube_MP3s.zip")
                    with zipfile.ZipFile(zip_path, 'w') as zipf:
                        for mp3_file in mp3_files:
                            zipf.write(mp3_file, os.path.basename(mp3_file))

                    with open(zip_path, "rb") as f:
                        zip_data = f.read()

                    st.success(f"✅ {len(mp3_files)} songs downloaded successfully!")
                    st.download_button(
                        label="📦 Download All MP3s as ZIP",
                        data=zip_data,
                        file_name="YouTube_MP3s.zip",
                        mime="application/zip"
                    )

                if errors:
                    st.error("⚠️ Some downloads failed:")
                    for err in errors:
                        st.write(err)

st.markdown("</div>", unsafe_allow_html=True)
st.caption("🎧 Built with ❤️ using Streamlit + yt-dlp + FFmpeg")
