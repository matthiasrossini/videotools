import os
import yt_dlp

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
    
    if start_time is not None or end_time is not None:
        ydl_opts['download_ranges'] = download_range_func(start_time, end_time)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    
    return filename

def download_range_func(start_time, end_time):
    def get_ranges(info_dict):
        duration = info_dict.get('duration')
        if duration is None:
            return []
        
        start = start_time if start_time is not None else 0
        end = min(end_time, duration) if end_time is not None else duration
        
        if start >= end:
            return []
        
        return [(start, end)]
    
    return get_ranges
