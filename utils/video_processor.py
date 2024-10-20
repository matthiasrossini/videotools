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
from typing import List, Tuple, Optional

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    logger.error("OpenAI API key is missing.")
    raise ValueError("OpenAI API key is required to run this script.")

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

def download_youtube_video(url: str, output_dir: str) -> Optional[str]:
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info and 'title' in info:
                return os.path.join(output_dir, f"{info['title']}.mp4")
            else:
                logger.error("Failed to extract video information")
                return None
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

def extract_frames(video_path: str, num_frames: int = 5, interval: Optional[int] = None) -> List[dict]:
    logger.info(f"Extracting frames from video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if interval is None:
        interval = max(1, total_frames // num_frames)
    else:
        num_frames = min(num_frames, total_frames // interval)

    clip_name = os.path.basename(video_path)
    clip_base_name = os.path.splitext(clip_name)[0]
    frames_dir = os.path.join(os.path.dirname(video_path), f"{clip_base_name}_frames")
    os.makedirs(frames_dir, exist_ok=True)

    for i in range(num_frames):
        frame_position = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        if ret:
            frame_filename = f"frame_{i}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            
            _, buffer = cv2.imencode('.jpg', frame)
            frame_data = buffer.tobytes()
            
            frames.append({
                'data': frame_data,
                'timestamp': cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                'path': frame_filename,
                'clip': clip_name
            })
            
            logger.debug(f"Saved frame to: {frame_path}")
        else:
            logger.warning(f"Failed to read frame {i} from video")

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from video")
    return frames

def process_video(video_path: str, frames_per_clip: int = 5, frame_interval: Optional[int] = None) -> Tuple[List[str], List[dict]]:
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

def get_youtube_transcript(video_id: str) -> Optional[str]:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Error fetching YouTube transcript: {e}")
        return None

def generate_summary(image: np.ndarray, transcript: Optional[str] = None) -> Tuple[str, List[str], str]:
    try:
        _, buffer = cv2.imencode('.jpg', image)
        base64_image = base64.b64encode(buffer).decode('utf-8')

        messages = [
            {"role": "system", "content": "You are a helpful assistant that can analyze images and provide summaries."},
            {"role": "user", "content": "Please analyze this image and provide a summary, key points, and a visual description."}
        ]

        if transcript:
            messages.append({"role": "user", "content": f"Here's the transcript of the video: {transcript}"})

        messages.append(
            {"role": "user", "content": f"Image: data:image/jpeg;base64,{base64_image}\nWhat's in this image?"}
        )

        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=500,
        )

        summary = response.choices[0].message.content
        key_points = re.findall(r'\n\s*-\s*(.*)', summary)
        visual_description = re.search(r'Visual description:(.*?)(?=\n\n|$)', summary, re.DOTALL)
        visual_description = visual_description.group(1).strip() if visual_description else "No visual description available."

        return summary, key_points, visual_description

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return "Error generating summary", [], "Error generating visual description"

def create_combined_images(frames: List[bytes]) -> List[bytes]:
    try:
        num_frames = len(frames)
        rows = int(np.ceil(np.sqrt(num_frames)))
        cols = int(np.ceil(num_frames / rows))

        decoded_frames = [cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR) for frame in frames]
        frame_height, frame_width = decoded_frames[0].shape[:2]

        combined_image = np.zeros((frame_height * rows, frame_width * cols, 3), dtype=np.uint8)

        for idx, frame in enumerate(decoded_frames):
            row = idx // cols
            col = idx % cols
            combined_image[row*frame_height:(row+1)*frame_height, col*frame_width:(col+1)*frame_width] = frame

        _, buffer = cv2.imencode('.jpg', combined_image)
        return [buffer.tobytes()]

    except Exception as e:
        logger.error(f"Error creating combined images: {e}")
        return []
