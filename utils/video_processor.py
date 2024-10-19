import os
import cv2
import numpy as np
import yt_dlp
from scenedetect import detect, ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from youtube_transcript_api import YouTubeTranscriptApi
import openai
import base64
import logging
import re
import tempfile

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    logger.error("OpenAI API key is missing.")
    raise ValueError("OpenAI API key is required to run this script.")

try:
    openai.api_key = OPENAI_API_KEY
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    raise

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
            frames.append({
                'data': buffer.tobytes(),
                'timestamp': cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                'path': f'frame_{i}.jpg',
                'clip': os.path.basename(video_path)
            })
        else:
            logger.warning(f"Failed to read frame {i} from video")

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from video")
    return frames

def process_video(video_path, frames_per_clip=10, frame_interval=None):
    logger.info(f"Processing video: {video_path}")
    if not os.path.exists(video_path):
        logger.error("Video file not found.")
        return [], []

    try:
        scene_list = detect(video_path, ContentDetector())
    except Exception as e:
        logger.error(f"Error detecting scenes: {e}")
        return [], []

    if len(scene_list) <= 1:
        logger.info("Only one scene detected, processing entire video.")
        scene_list = [(scene_list[0][0], None)]

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
        frames = extract_frames(clip_path, frames_per_clip, interval=frame_interval)
        all_frames.extend(frames)

    if all_frames:
        logger.info(f"Sorting {len(all_frames)} frames by timestamp")
        all_frames.sort(key=lambda x: x['timestamp'])

    return clip_paths, all_frames

def create_combined_image(frames, max_width=65500, max_height=65500):
    decoded_frames = [cv2.imdecode(np.frombuffer(frame['data'], np.uint8), cv2.IMREAD_COLOR) for frame in frames]

    heights = [frame.shape[0] for frame in decoded_frames]
    max_frame_height = max(heights)
    total_frame_width = sum(frame.shape[1] for frame in decoded_frames)

    scale_factor = min(max_width / total_frame_width, max_height / max_frame_height, 1.0)

    if scale_factor < 1.0:
        max_frame_height = int(max_frame_height * scale_factor)
        decoded_frames = [cv2.resize(frame, (int(frame.shape[1] * scale_factor), max_frame_height)) for frame in decoded_frames]
        total_frame_width = sum(frame.shape[1] for frame in decoded_frames)

    combined_image = np.zeros((max_frame_height, total_frame_width, 3), dtype=np.uint8)

    current_x = 0
    for frame in decoded_frames:
        h, w = frame.shape[:2]
        combined_image[0:h, current_x:current_x + w] = frame
        current_x += w

    return cv2.imencode('.jpg', combined_image)[1].tobytes()

def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Error fetching YouTube transcript: {e}")
        return None

def generate_summary(combined_image, transcript):
    logger.info("Generating summary using OpenAI API")

    if combined_image is None:
        return transcript

    encoded_image = base64.b64encode(combined_image).decode('utf-8')

    prompt = f"""Based on the following image of video frames and transcript, provide a concise summary of the video content:

Transcript: {transcript}

Please summarize the main points and key visuals from the video. The response should be in JSON format with the following structure:
{{
    "summary": "A concise summary of the video content",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "visual_description": "A brief description of the key visuals in the video"
}}
"""

    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            max_tokens=500
        )

        summary = response.choices[0].text.strip()

        logger.info("Summary generated successfully")
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return f"Error generating summary: {str(e)}"

if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=QC8iQqtG0hg"
    output_dir = "downloads"

    os.makedirs(output_dir, exist_ok=True)
    video_path = download_youtube_video(youtube_url, output_dir)

    if video_path:
        clip_paths, all_frames = process_video(video_path)
        combined_image = create_combined_image(all_frames)

        transcript = get_youtube_transcript(
            re.search(r"v=([^&]+)", youtube_url).group(1))
        summary = generate_summary(combined_image, transcript)
        print(f"Summary: {summary}")
    else:
        logger.error("Video download failed.")