import os
import cv2
import logging
from scenedetect import detect, ContentDetector, split_video_ffmpeg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_video(video_path, number_of_clips=None, frames_per_clip=None):
    # Detect scenes
    scene_list = detect(video_path, ContentDetector())
    
    # Get the directory and filename
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]
    
    # Split video into clips
    output_file_template = os.path.join(directory, f"{filename}_scene_$SCENE_NUMBER.mp4")
    split_video_ffmpeg(video_path, scene_list, output_file_template=output_file_template)
    
    # Get the list of generated clip paths
    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]
    
    # If number_of_clips is not specified, use all clips
    if number_of_clips is None:
        number_of_clips = len(clip_paths)
    else:
        number_of_clips = min(number_of_clips, len(clip_paths))
    
    # Limit the number of clips
    clip_paths = clip_paths[:number_of_clips]
    
    # Extract frames from each clip
    all_frames = []
    clips_and_frames = []
    for clip_path in clip_paths:
        try:
            frames = extract_frames(clip_path, frames_per_clip)
            all_frames.extend(frames)
            
            clip_filename = os.path.basename(clip_path)
            frame_filenames = [os.path.basename(frame['path']) for frame in frames]
            clips_and_frames.append({
                'clip': clip_filename,
                'frames': frame_filenames
            })
        except Exception as e:
            logging.error(f"Error processing clip {clip_path}: {str(e)}")
    
    return clip_paths, all_frames, clips_and_frames

def extract_frames(video_path, frames_per_clip=None):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    if frames_per_clip is None:
        frames_per_clip = min(total_frames, 10)  # Default to 10 frames or total frames if less
    
    frame_interval = max(1, total_frames // frames_per_clip)
    
    # Create a directory for frames specific to this clip
    clip_name = os.path.splitext(os.path.basename(video_path))[0]
    frames_dir = os.path.join(os.path.dirname(video_path), f"{clip_name}_frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    logging.info(f"Extracting frames for clip: {video_path}")
    logging.info(f"Frames directory: {frames_dir}")
    
    frames = []
    for i in range(frames_per_clip):
        frame_position = i * frame_interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            timestamp = frame_position / fps
            frame_info = {
                'path': frame_path,
                'timestamp': round(timestamp, 2),
                'clip': os.path.basename(video_path)
            }
            frames.append(frame_info)
            logging.info(f"Saved frame: {frame_path}")
        else:
            logging.warning(f"Failed to read frame at position {frame_position} for clip: {video_path}")
    
    cap.release()
    return frames
