import os
import subprocess
import cv2
from scenedetect import detect, ContentDetector, split_video_ffmpeg

def process_video(video_path, start_time=None, end_time=None):
    # Detect scenes
    scene_list = detect(video_path, ContentDetector())
    
    # Get the directory and filename
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]
    
    # Split video into clips
    split_video_ffmpeg(video_path, scene_list, output_file_template=f"{directory}/{filename}_scene_$SCENE_NUMBER.mp4")
    
    # Get the list of generated clip paths
    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]
    
    # Extract frames from each clip
    all_frames = []
    for clip_path in clip_paths:
        frames = extract_frames(clip_path, start_time, end_time)
        all_frames.extend(frames)
    
    return clip_paths, all_frames

def extract_frames(video_path, start_time=None, end_time=None, frames_per_second=1):
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = fps // frames_per_second
    
    frame_count = 0
    extracted_count = 0
    
    # Create a directory for frames
    frames_dir = os.path.splitext(video_path)[0] + "_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_count / fps
        
        if (start_time is None or timestamp >= start_time) and (end_time is None or timestamp <= end_time):
            if frame_count % frame_interval == 0:
                frame_path = os.path.join(frames_dir, f"frame_{extracted_count:04d}.jpg")
                cv2.imwrite(frame_path, frame)
                frames.append({
                    'path': frame_path,
                    'timestamp': round(timestamp, 2),  # Round to 2 decimal places
                    'clip': os.path.basename(video_path)
                })
                extracted_count += 1
        elif end_time is not None and timestamp > end_time:
            break
        
        frame_count += 1
    
    cap.release()
    return frames
