import os
import cv2
import yt_dlp
from scenedetect import detect, ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg

# Step 1: Download the video from YouTube
def download_youtube_video(url, output_dir):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return os.path.join(output_dir, f"{info['title']}.mp4")  # Return the path to the downloaded video
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# Step 2: Process the video, detect scenes, and split it into sub-scenes
def process_video(video_path):
    print(f"Processing video: {video_path}")

    # Detect scenes
    try:
        scene_list = detect(video_path, ContentDetector())
        print(f"Detected scenes: {scene_list}")
    except Exception as e:
        print(f"Error detecting scenes: {e}")
        return [], []

    # If no scenes are detected or only one scene exists, process the entire video as one clip
    if len(scene_list) <= 1:
        print("Only one scene detected or no scenes found, treating the entire video as one scene.")
        scene_list = [(0, None)]

    # Split the video into sub-scenes
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]
    output_file_template = os.path.join(directory, f"{filename}_scene_$SCENE_NUMBER.mp4")

    try:
        split_video_ffmpeg(video_path, scene_list, output_file_template=output_file_template)
        print(f"Video successfully split into scenes. Output template: {output_file_template}")
    except Exception as e:
        print(f"Error splitting video: {e}")
        return [], []

    # Collect the generated sub-scene clips
    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]

    if not clip_paths:
        print(f"No sub-scenes generated. Using original video: {video_path}")
        clip_paths = [video_path]  # Use the original video if no scenes were split

    # Proceed to frame extraction
    all_frames = []
    for clip_path in clip_paths:
        frames = extract_frames(clip_path)
        all_frames.extend(frames)

    return clip_paths, all_frames

# Step 3: Extract frames from each sub-scene
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

    # Create a directory for the frames
    frames_dir = os.path.splitext(video_path)[0] + "_frames"
    os.makedirs(frames_dir, exist_ok=True)

    for i in range(frames_per_clip):
        frame_position = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()

        if ret:
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
            cv2.imwrite(frame_path, frame)

            # Get the timestamp for the frame
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            frames.append({
                'path': frame_path,
                'timestamp': round(timestamp, 2),
                'clip': os.path.basename(video_path)
            })
        else:
            print(f"Error: Could not read frame at position {frame_position} for clip: {video_path}")

    cap.release()
    return frames

# Example usage:
def main():
    youtube_url = "https://www.youtube.com/watch?v=QC8iQqtG0hg"
    output_dir = "downloads"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Download the video
    video_path = download_youtube_video(youtube_url, output_dir)
    if video_path:
        # Process the video (split into scenes and extract frames)
        clip_paths, all_frames = process_video(video_path)

        # Debug output
        print(f"Clip paths: {clip_paths}")
        print(f"Extracted frames: {all_frames}")
    else:
        print("Failed to download or process the video.")

if __name__ == "__main__":
    main()
