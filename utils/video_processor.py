import os
import cv2
from scenedetect import detect, ContentDetector, SceneManager, VideoManager

def process_video(video_path):
    # Create a VideoManager
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    # Detect scenes
    video_manager.start()
    scene_list = detect(video_manager, scene_manager)

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
        frames = extract_frames(clip_path)
        all_frames.extend(frames)

    return clip_paths, all_frames

def extract_frames(video_path):
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

    # Extract 10 evenly spaced frames
    frame_indices = [i * (total_frames // 10) for i in range(10)]

    for i, frame_index in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
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
            print(f"Error: Could not read frame {frame_index} from video file {video_path}")

    cap.release()
    return frames
