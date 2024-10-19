import os
import cv2
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def process_video(video_path, number_of_clips=None):
    logging.info(f"Starting video processing for: {video_path}")
    # Detect scenes
    logging.debug("Detecting scenes...")
    scene_list = detect(video_path, ContentDetector())
    logging.info(f"Detected {len(scene_list)} scenes")
    
    # Get the directory and filename
    directory = os.path.dirname(video_path)
    filename = os.path.splitext(os.path.basename(video_path))[0]
    
    # Split video into clips
    logging.debug("Splitting video into clips...")
    output_file_template = os.path.join(directory, f"{filename}_scene_$SCENE_NUMBER.mp4")
    split_video_ffmpeg(video_path, scene_list, output_file_template=output_file_template)
    
    # Get all clip paths
    clip_paths = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith(f"{filename}_scene_") and f.endswith(".mp4")
    ]
    logging.info(f"Generated {len(clip_paths)} clip(s)")
    
    # If number_of_clips is not specified, use all clips
    if number_of_clips is None:
        number_of_clips = len(clip_paths)
    
    # Use only the specified number of clips
    clip_paths = clip_paths[:number_of_clips]
    
    # Process each clip
    all_frames = []
    clips_and_frames = []
    for clip_path in clip_paths:
        try:
            logging.debug(f"Extracting frames from clip: {clip_path}")
            frames = extract_frames(clip_path)
            all_frames.extend(frames)
            
            clip_filename = os.path.basename(clip_path)
            frame_filenames = [os.path.basename(frame['path']) for frame in frames]
            clips_and_frames.append({
                'clip': clip_filename,
                'frames': frame_filenames
            })
            logging.info(f"Extracted {len(frames)} frame(s) from {clip_filename}")
        except Exception as e:
            logging.error(f"Error processing clip {clip_path}: {str(e)}")
    
    logging.info(f"Video processing completed. Total frames extracted: {len(all_frames)}")
    return clip_paths, all_frames, clips_and_frames

def extract_frames(video_path, num_frames=10):
    logging.debug(f"Extracting frames from: {video_path}")
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # Calculate frame positions to extract
    frame_positions = [int(i * total_frames / num_frames) for i in range(num_frames)]
    
    # Create a directory for frames specific to this clip
    clip_name = os.path.splitext(os.path.basename(video_path))[0]
    frames_dir = os.path.join(os.path.dirname(video_path), f"{clip_name}_frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    logging.info(f"Extracting {num_frames} frames for clip: {video_path}")
    logging.info(f"Frames directory: {frames_dir}")
    
    frames = []
    for i, frame_position in enumerate(frame_positions):
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
    logging.debug(f"Extracted {len(frames)} frame(s) from {video_path}")
    return frames
