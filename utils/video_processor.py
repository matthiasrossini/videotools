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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    logger.error("OpenAI API key is missing.")
    raise ValueError("OpenAI API key is required to run this script.")

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY

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
            frame_data = buffer.tobytes()
            logger.debug(f"Frame {i} data type: {type(frame_data)}")
            
            # Generate the frame filename
            frame_filename = f"frame_{i}.jpg"
            
            frames.append({
                'data': frame_data,
                'timestamp': cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                'path': frame_filename,
                'clip': os.path.basename(video_path)
            })
            
            # Debug logging for frame path
            logger.debug(f"Frame {i} filename: {frame_filename}")
        else:
            logger.warning(f"Failed to read frame {i} from video")

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from video")
    return frames

def process_video(video_path, frames_per_clip=5, frame_interval=None):
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
        
        # Save frames for each clip
        clip_name = os.path.splitext(os.path.basename(clip_path))[0]
        frames_dir = os.path.join(directory, f"{clip_name}_frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        for i, frame in enumerate(frames):
            frame_path = os.path.join(frames_dir, frame['path'])
            with open(frame_path, "wb") as f:
                f.write(frame['data'])
            logger.debug(f"Saved frame to: {frame_path}")

    if all_frames:
        logger.info(f"Sorting {len(all_frames)} frames by timestamp")
        all_frames.sort(key=lambda x: x['timestamp'])

    return clip_paths, all_frames

def create_combined_images(frames, max_width=65500, max_height=65500, frames_per_image=1):
    combined_images = []

    for i in range(0, len(frames), frames_per_image):
        chunk = frames[i:i + frames_per_image]

        logger.debug(f"Processing chunk {i // frames_per_image + 1}")
        for j, frame in enumerate(chunk):
            logger.debug(f"Frame {j} in chunk {i // frames_per_image + 1} data type: {type(frame['data'])}")
            if not isinstance(frame['data'], bytes):
                logger.error(f"Frame {j} in chunk {i // frames_per_image + 1} is not bytes: {type(frame['data'])}")

        decoded_frames = [
            cv2.imdecode(np.frombuffer(frame['data'], np.uint8), cv2.IMREAD_COLOR)
            for frame in chunk if isinstance(frame['data'], bytes)
        ]

        if not decoded_frames:
            logger.error(f"No valid frames in chunk {i // frames_per_image + 1}")
            continue

        total_width = sum(frame.shape[1] for frame in decoded_frames)
        max_frame_height = max(frame.shape[0] for frame in decoded_frames)

        if total_width > max_width or max_frame_height > max_height:
            scale_factor = min(max_width / total_width, max_height / max_frame_height)
            decoded_frames = [
                cv2.resize(frame, (int(frame.shape[1] * scale_factor), int(frame.shape[0] * scale_factor)))
                for frame in decoded_frames
            ]

        heights = [frame.shape[0] for frame in decoded_frames]
        combined_height = max(heights)
        total_width = sum(frame.shape[1] for frame in decoded_frames)

        combined_image = np.zeros((combined_height, total_width, 3), dtype=np.uint8)
        current_x = 0
        for frame in decoded_frames:
            h, w = frame.shape[:2]
            combined_image[0:h, current_x:current_x + w] = frame
            current_x += w

        combined_images.append(cv2.imencode('.jpg', combined_image)[1].tobytes())

    return combined_images

def describe_frames(frames):
    descriptions = []
    for frame in frames:
        descriptions.append(f"Description of frame captured at {frame['timestamp']} seconds.")
    return descriptions

def get_youtube_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Error fetching YouTube transcript: {e}")
        return None

def generate_summary(combined_image, transcript):
    logger.info('Generating summary using OpenAI API with gpt-4-vision-preview model')

    encoded_image = base64.b64encode(combined_image).decode('utf-8')
    
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4-vision-preview',
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': f'Analyze this image and provide a concise summary of the video content. Here\'s the transcript for additional context: {transcript}'},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{encoded_image}'}}
                    ]
                }
            ],
            max_tokens=500
        )
        summary = response.choices[0].message['content'].strip()
        return summary
    except Exception as e:
        logger.error(f'Error generating summary: {e}')
        return f'Error generating summary: {e}'

if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=QC8iQqtG0hg"
    output_dir = "downloads"

    os.makedirs(output_dir, exist_ok=True)
    video_path = download_youtube_video(youtube_url, output_dir)

    if video_path:
        clip_paths, all_frames = process_video(video_path)
        combined_images = create_combined_images(all_frames)

        video_id_match = re.search(r"v=([^&]+)", youtube_url)
        if video_id_match:
            transcript = get_youtube_transcript(video_id_match.group(1))
            for combined_image in combined_images:
                summary = generate_summary(combined_image, transcript)
                print(f"Summary: {summary}")
        else:
            logger.error("Could not extract video ID from URL")
    else:
        logger.error("Video download failed.")