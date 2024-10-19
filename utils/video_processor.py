import os
import cv2
from scenedetect import SceneManager, ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg

def process_video(video_path):
    # Create a SceneManager
    scene_manager = SceneManager()
    
    # Add ContentDetector
    scene_manager.add_detector(ContentDetector())

    # Detect scenes
    video = cv2.VideoCapture(video_path)
    scene_manager.detect_scenes(video)
    
    # Get the list of scenes
    scene_list = scene_manager.get_scene_list()

    # Get the directory and filename
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]

    # Split video into clips based on scenes
    output_file_template = os.path.join(directory, f"{filename}_scene_$SCENE_NUMBER.mp4")
    
    # Process and split video based on scene list
    split_video_ffmpeg(video_path, scene_list, output_file_template=output_file_template)

    # Get the list of generated clip paths
    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]

    # Extract frames from each clip
    all_frames = []
    for clip_path in clip_paths:
        frames = extract_frames(clip_path)
        all_frames.extend(frames)

    return clip_paths, all_frames

def extract_frames(video_path, frames_per_clip=10):
    cap = cv2.VideoCapture(video_path)
    frames = []

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return frames

    # Get the total number of frames
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        print(f"Error: Video file {video_path} has no frames")
        cap.release()
        return frames

    # Calculate the interval between frames
    interval = max(1, total_frames // frames_per_clip)

    for i in range(frames_per_clip):
        frame_position = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()

        if ret:
            # Create a directory for frames
            frames_dir = os.path.splitext(video_path)[0] + "_frames"
            os.makedirs(frames_dir, exist_ok=True)

            # Save the frame
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
            cv2.imwrite(frame_path, frame)

            # Get the timestamp
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

            frame_info = {
                'path': frame_path,
                'timestamp': round(timestamp, 2),
                'clip': os.path.basename(video_path)
            }
            frames.append(frame_info)
        else:
            print(f"Error: Could not read frame at position {frame_position} for clip: {video_path}")

    cap.release()
    return frames
