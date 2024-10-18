import os
import subprocess
import yt_dlp

class VideoDownloadError(Exception):
    pass

def download_youtube_video(url, output_path, start_time=None, end_time=None):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        print(f"Downloaded video file: {filename}")
        
        if not os.path.exists(filename):
            raise VideoDownloadError(f"Video file not found at {filename}")

        # If start and end times are provided, trim the video
        if start_time is not None or end_time is not None:
            trimmed_filename = trim_video(filename, start_time, end_time)
            return trimmed_filename

        return filename
    except Exception as e:
        raise VideoDownloadError(f"Error downloading video: {str(e)}")

def trim_video(filename, start_time, end_time):
    # Check if input file exists
    if not os.path.exists(filename):
        raise VideoDownloadError(f"Input video file not found at {filename}")

    # Build the ffmpeg command to trim the video
    output_file = f"trimmed_{os.path.basename(filename)}"
    start = f"-ss {start_time}" if start_time is not None else ""
    end = f"-to {end_time}" if end_time is not None else ""

    # ffmpeg command for trimming
    cmd = f"ffmpeg -i {filename} {start} {end} -c copy {output_file}"
    
    print(f"Executing ffmpeg command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"ffmpeg command output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg command failed with error: {e.stderr}")
        raise VideoDownloadError(f"Error trimming video: {e.stderr}")

    if not os.path.exists(output_file):
        raise VideoDownloadError(f"Trimmed video file not found at {output_file}")

    print(f"Trimmed video file: {os.path.abspath(output_file)}")
    return output_file
