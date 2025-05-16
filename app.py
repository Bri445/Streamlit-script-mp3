import streamlit as st
import yt_dlp
import tempfile
import os
import zipfile

st.set_page_config(page_title="🎧 YT MP3 Downloader", layout="centered")

# --- Custom Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        background: linear-gradient(135deg, #1c1c1c, #0f0f0f);
        color: #ffffff;
        font-family: 'Poppins', sans-serif;
    }
    .stTextArea textarea {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid #444 !important;
    }
    .stButton>button {
        background: linear-gradient(to right, #8e2de2, #4a00e0);
        color: white;
        border-radius: 8px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        border: none;
        transition: background 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background: linear-gradient(to right, #4a00e0, #8e2de2);
    }
    .stDownloadButton>button {
        background: linear-gradient(to right, #00b4db, #0083b0);
        color: white;
        border-radius: 8px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        border: none;
    }
    .glass-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 2rem;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

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

st.markdown("<h1 style='text-align: center;'>🎧 YouTube MP3 Batch Downloader</h1>", unsafe_allow_html=True)
st.markdown("<div class='glass-box'>", unsafe_allow_html=True)

urls_text = st.text_area(
    "📥 Paste YouTube URLs (1 per line)",
    placeholder="https://www.youtube.com/watch?v=abc123\nhttps://www.youtube.com/watch?v=xyz456",
    height=200
)

if st.button("🚀 Download All as ZIP"):
    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    if not urls:
        st.warning("⚠️ Please enter at least one valid YouTube URL.")
    else:
        with st.spinner("🛠️ Preparing to download..."):
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
                        speed_placeholder.text("✅ Done")
                    except Exception as e:
                        errors.append(f"❌ {url}: {str(e)}")

                if mp3_files:
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

                if errors:
                    st.error("⚠️ Some files failed:")
                    for err in errors:
                        st.write(err)

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Made with ❤️ using Streamlit & yt-dlp")
