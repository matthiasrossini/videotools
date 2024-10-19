import os
import cv2
from scenedetect import detect, ContentDetector, SceneManager
from scenedetect.video_manager import VideoManager

def process_video(video_path):
    # Create a VideoManager and SceneManager
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    # Detect scenes
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()

    # Get the directory and filename
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]

    # Split video into clips
    clip_paths = []
    for i, scene in enumerate(scene_list):
        start_time, end_time = scene
        output_path = os.path.join(directory, f"{filename}_scene_{i+1:03d}.mp4")
        cmd = f"ffmpeg -i {video_path} -ss {start_time.get_seconds()} -to {end_time.get_seconds()} -c copy {output_path}"
        os.system(cmd)
        clip_paths.append(output_path)

    # Extract frames from each clip
    all_frames = []
    for clip_path in clip_paths:
        frame = extract_frame(clip_path)
        if frame:
            all_frames.append(frame)

    return clip_paths, all_frames

def extract_frame(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return None

    # Get the total number of frames
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames == 0:
        print(f"Error: Video file {video_path} has no frames")
        cap.release()
        return None

    # Calculate the middle frame
    middle_frame = total_frames // 2

    # Set the frame position to the middle frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)

    # Read the frame
    ret, frame = cap.read()

    if ret:
        # Create a directory for frames
        frames_dir = os.path.splitext(video_path)[0] + "_frames"
        os.makedirs(frames_dir, exist_ok=True)

        # Save the frame
        frame_path = os.path.join(frames_dir, f"frame_middle.jpg")
        cv2.imwrite(frame_path, frame)

        # Get the timestamp
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        frame_info = {
            'path': frame_path,
            'timestamp': round(timestamp, 2),
            'clip': os.path.basename(video_path)
        }
    else:
        print(f"Error: Could not read frame from video file {video_path}")
        frame_info = None

    cap.release()
    return frame_info
