import streamlit as st
import yt_dlp
import tempfile
import os

def download_audio_to_temp(youtube_url, temp_dir):
    output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
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

st.title("Batch YouTube to MP3 Downloader")

urls_text = st.text_area("Enter multiple YouTube URLs (one per line):")

if st.button("Download All"):
    urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
    if not urls:
        st.warning("Please enter at least one valid YouTube URL.")
    else:
        with st.spinner("Downloading and converting all files..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                mp3_files = []
                errors = []
                for url in urls:
                    try:
                        mp3_path = download_audio_to_temp(url, temp_dir)
                        mp3_files.append(mp3_path)
                    except Exception as e:
                        errors.append(f"Failed to download {url}: {str(e)}")

                if mp3_files:
                    st.success(f"Downloaded {len(mp3_files)} files successfully. Download below:")
                    for mp3_file in mp3_files:
                        with open(mp3_file, "rb") as f:
                            mp3_bytes = f.read()
                        st.download_button(
                            label=os.path.basename(mp3_file),
                            data=mp3_bytes,
                            file_name=os.path.basename(mp3_file),
                            mime="audio/mpeg"
                        )

                if errors:
                    st.error("Some downloads failed:")
                    for err in errors:
                        st.write(err)
