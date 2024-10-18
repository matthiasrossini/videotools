import os
import subprocess
from scenedetect import detect, ContentDetector, split_video_ffmpeg

def process_video(video_path):
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
    
    return clip_paths

