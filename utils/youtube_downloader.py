import os
import yt_dlp
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoDownloadError(Exception):
    pass

def sanitize_filename(filename):
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    sanitized = sanitized.strip('_')
    return sanitized

def download_youtube_video(url, output_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # Use os.path.abspath to get the full path
        full_path = os.path.abspath(filename)
        logging.info(f"Downloaded video file: {full_path}")
        
        if not os.path.exists(full_path):
            raise VideoDownloadError(f"Video file not found at {full_path}")

        return full_path
    except Exception as e:
        raise VideoDownloadError(f"Error downloading video: {str(e)}")
