import os
import yt_dlp
import logging
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoDownloadError(Exception):
    pass

def sanitize_filename(filename):
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    sanitized = sanitized.strip('_')
    return sanitized

def download_youtube_video(url, output_path):
    logging.info(f"Starting download for URL: {url}")
    logging.info(f"Output path: {output_path}")

    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)
    logging.info(f"Output directory created/confirmed: {output_path}")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'verbose': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info("Extracting video info...")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            logging.info(f"Prepared filename: {filename}")
        
        # Sanitize the filename
        sanitized_filename = sanitize_filename(os.path.basename(filename))
        full_path = os.path.join(output_path, sanitized_filename)
        logging.info(f"Sanitized full path of downloaded video: {full_path}")
        
        if not os.path.exists(full_path):
            # Check if the file exists with the original filename
            if os.path.exists(filename):
                # Rename the file to the sanitized version
                os.rename(filename, full_path)
                logging.info(f"Renamed file from {filename} to {full_path}")
            else:
                logging.error(f"Video file not found at {full_path} or {filename}")
                # List contents of the output directory
                logging.debug(f"Contents of {output_path}:")
                for item in os.listdir(output_path):
                    logging.debug(f"- {item}")
                raise VideoDownloadError(f"Video file not found after download. Please check the YouTube URL and try again.")

        return full_path
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"YouTube download error: {str(e)}")
        raise VideoDownloadError(f"Failed to download video: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error during video download: {str(e)}")
        # List contents of the output directory
        logging.debug(f"Contents of {output_path}:")
        for item in os.listdir(output_path):
            logging.debug(f"- {item}")
        raise VideoDownloadError(f"Unexpected error during video download: {str(e)}")
