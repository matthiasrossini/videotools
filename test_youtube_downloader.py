
from utils.youtube_downloader import download_youtube_video, VideoDownloadError
import os

def test_download_and_trim():
    try:
        # Use a short YouTube video for testing
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        output_path = 'temp'
        start_time = 0
        end_time = 10

        trimmed_video = download_youtube_video(url, output_path, start_time, end_time)
        print(f"Trimmed video created: {trimmed_video}")
        print(f"File size: {os.path.getsize(trimmed_video)} bytes")
        
        return True
    except VideoDownloadError as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_download_and_trim()
    print(f"Test {'passed' if success else 'failed'}")
