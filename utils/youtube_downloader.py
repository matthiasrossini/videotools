import os
import yt_dlp
import subprocess


def download_youtube_video(url, output_path, start_time=None, end_time=None):
    ydl_opts = {
        'format':
        'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl':
        os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format':
        'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # If start and end times are provided, trim the video
    if start_time is not None or end_time is not None:
        trimmed_filename = trim_video(filename, start_time, end_time)
        return trimmed_filename

    return filename


def trim_video(filename, start_time, end_time):
    # Build the ffmpeg command to trim the video
    output_file = f"trimmed_{filename}"
    start = f"-ss {start_time}" if start_time is not None else ""
    end = f"-to {end_time}" if end_time is not None else ""

    # ffmpeg command for trimming
    cmd = f"ffmpeg -i {filename} {start} {end} -c copy {output_file}"
    subprocess.run(cmd, shell=True)

    return output_file
