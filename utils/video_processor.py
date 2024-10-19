import os
import cv2
import numpy as np
import yt_dlp
from scenedetect import detect, ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import base64
import logging
import re
import tempfile

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure OpenAI API key is loaded
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is missing.")

# Initialize OpenAI client with the API key
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Download video from YouTube
def download_youtube_video(url, output_dir):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return os.path.join(output_dir, f"{info['title']}.mp4")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Extract frames from a video
def extract_frames(video_path, num_frames=5, interval=None):
    logger.info(f"Extracting frames from video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if interval is None:
        interval = total_frames // num_frames
    else:
        num_frames = min(num_frames, total_frames // interval)

    for i in range(num_frames):
        frame_position = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            frames.append(buffer.tobytes())
        else:
            logger.warning(f"Failed to read frame {i} from video")

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from video")
    return frames

# Split video into scenes and process frames
def process_video(video_path, frames_per_clip=10):
    logger.info(f"Processing video: {video_path}")
    try:
        scene_list = detect(video_path, ContentDetector())
    except Exception as e:
        logger.error(f"Error detecting scenes: {e}")
        return [], []

    if len(scene_list) <= 1:
        logger.info("Only one scene detected, processing entire video.")
        scene_list = [(0, None)]

    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]
    output_file_template = os.path.join(directory, f"{filename}_scene_$SCENE_NUMBER.mp4")

    try:
        split_video_ffmpeg(video_path, scene_list, output_file_template=output_file_template)
    except Exception as e:
        logger.error(f"Error splitting video: {e}")
        return [], []

    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]

    if not clip_paths:
        clip_paths = [video_path]

    all_frames = []
    for clip_path in clip_paths:
        frames = extract_frames(clip_path, frames_per_clip)
        all_frames.extend(frames)

    return clip_paths, all_frames

# Create a combined image from frames
def create_combined_image(frames):
    decoded_frames = [cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR) for frame in frames]
    heights = [frame.shape[0] for frame in decoded_frames]
    max_height = max(heights)
    total_width = sum(frame.shape[1] for frame in decoded_frames)

    combined_image = np.zeros((max_height, total_width, 3), dtype=np.uint8)
    current_x = 0
    for frame in decoded_frames:
        h, w = frame.shape[:2]
        combined_image[0:h, current_x:current_x + w] = frame
        current_x += w

    return cv2.imencode('.jpg', combined_image)[1].tobytes()

# Generate transcript using YouTubeTranscriptApi
def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return None

# Summarize video content using OpenAI
def generate_summary(combined_image, transcript):
    if combined_image is None:
        return transcript

    encoded_image = base64.b64encode(combined_image).decode('utf-8')
    prompt = f"""Based on the following image of video frames and transcript, provide a concise summary:
Transcript: {transcript}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return f"Error generating summary: {e}"

# Example usage
if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=QC8iQqtG0hg"
    output_dir = "downloads"

    os.makedirs(output_dir, exist_ok=True)
    video_path = download_youtube_video(youtube_url, output_dir)

    if video_path:
        clip_paths, all_frames = process_video(video_path)
        combined_image = create_combined_image(all_frames)

        transcript = get_youtube_transcript(YouTube(youtube_url).video_id)
        summary = generate_summary(combined_image, transcript)
        print(f"Summary: {summary}")
    else:
        logger.error("Video download failed.")
