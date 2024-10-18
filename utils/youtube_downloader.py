import os
import subprocess
import yt_dlp
import shutil
import tempfile
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoDownloadError(Exception):
    pass

def sanitize_filename(filename):
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    sanitized = sanitized.strip('_')
    return sanitized

def download_youtube_video(url, output_path, start_time=None, end_time=None, precise_trim=False):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        logging.info(f"Downloaded video file: {os.path.abspath(filename)}")
        
        if not os.path.exists(filename):
            raise VideoDownloadError(f"Video file not found at {os.path.abspath(filename)}")

        # If start and end times are provided, trim the video
        if start_time is not None or end_time is not None:
            trimmed_filename = trim_video(filename, start_time, end_time, precise_trim)
            return trimmed_filename

        return filename
    except Exception as e:
        raise VideoDownloadError(f"Error downloading video: {str(e)}")

def trim_video(filename, start_time, end_time, precise_trim=False):
    if not os.path.exists(filename):
        raise VideoDownloadError(f"Input video file not found at {os.path.abspath(filename)}")

    sanitized_input = sanitize_filename(os.path.basename(filename))
    input_file = os.path.join(os.path.dirname(filename), sanitized_input)
    os.rename(filename, input_file)

    output_dir = os.path.join(os.path.dirname(input_file), "trimmed_temp")
    os.makedirs(output_dir, exist_ok=True)

    sanitized_output = f"trimmed_{sanitized_input}"
    output_file = os.path.abspath(os.path.join(output_dir, sanitized_output))

    cmd = ["ffmpeg", "-i", input_file]
    
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    
    if end_time is not None:
        if start_time is not None and end_time <= start_time:
            raise VideoDownloadError("End time must be greater than start time")
        cmd.extend(["-to", str(end_time)])
    
    if precise_trim:
        cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
    else:
        cmd.extend(["-c", "copy"])

    cmd.append(output_file)

    logging.info(f"Executing ffmpeg command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"ffmpeg command output: {result.stdout}")
        logging.info(f"ffmpeg command error output: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"ffmpeg command failed with error: {e.stderr}")
        raise VideoDownloadError(f"Error trimming video: {e.stderr}")

    if not os.path.exists(output_file):
        logging.error(f"Output file not found at expected location: {output_file}")
        raise VideoDownloadError(f"Trimmed video file not found at {output_file}")

    logging.info(f"Trimmed video file created: {output_file}")
    return output_file
