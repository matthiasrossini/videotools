import os
import logging
import json
import base64
import re
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from utils.video_processor import process_video, generate_summary, download_youtube_video, get_youtube_transcript, create_combined_image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    logger.info("Received request to /process endpoint")
    try:
        # Input validation
        youtube_url = request.form.get('youtube_url')
        video_file = request.files.get('video')
        transcript = request.form.get('transcript')
        frame_interval = request.form.get('frame_interval')

        # Validate frame interval
        if frame_interval:
            try:
                frame_interval = int(frame_interval)
                if frame_interval <= 0:
                    raise ValueError('Frame interval must be a positive integer')
            except ValueError:
                raise ValueError('Invalid frame interval')
        else:
            frame_interval = None

        # Handle YouTube URL or uploaded video
        if youtube_url:
            # Validate YouTube URL
            youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
            if not re.match(youtube_regex, youtube_url):
                raise ValueError('Invalid YouTube URL')
            logger.info(f"Processing YouTube URL: {youtube_url}")
            input_source = youtube_url
            use_youtube_transcript = True
            video_path = download_youtube_video(youtube_url, app.config['UPLOAD_FOLDER'])

        elif video_file:
            if not video_file.filename:
                raise ValueError('No video file selected')
            logger.info(f"Processing uploaded video: {video_file.filename}")
            filename = secure_filename(video_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(filepath)
            input_source = filepath
            use_youtube_transcript = False
            video_path = filepath
        else:
            raise ValueError('No YouTube URL or video file provided')

        if not video_path:
            return jsonify({'success': False, 'error': 'Failed to download video.'})

        # Process video once and generate frames
        clip_paths, all_frames = process_video(video_path, frame_interval=frame_interval)

        if not clip_paths:
            return jsonify({'success': False, 'error': 'No clips generated.'})

        if not all_frames:
            return jsonify({'success': False, 'error': 'No frames extracted.'})

        # Sort frames by timestamp
        all_frames.sort(key=lambda x: x['timestamp'])

        # Prepare clips and corresponding frames for the response
        clips_and_frames = []
        for clip_path, frame in zip(clip_paths, all_frames):
            clip_filename = os.path.basename(clip_path)
            clips_and_frames.append({
                'clip': clip_filename,
                'frame': os.path.basename(frame['path'])
            })

        # Prepare timeline frames
        timeline_frames = [
            {
                'path': os.path.basename(frame['path']),
                'timestamp': frame['timestamp'],
                'clip': frame['clip']  # Clip metadata is now available
            } for frame in all_frames
        ]

        # If using a YouTube URL, get the transcript
        if use_youtube_transcript:
            video_id = re.search(r"v=([^&]+)", youtube_url).group(1)
            video_transcript = get_youtube_transcript(video_id)
        else:
            video_transcript = None

        # Generate the combined image from all frames
        combined_image = create_combined_image([frame['data'] for frame in all_frames])

        # Generate summary
        summary_json = generate_summary(combined_image, video_transcript or transcript)

        summary_data = json.loads(summary_json)

        # Encode frames and combined image to base64
        encoded_frames = [base64.b64encode(frame['data']).decode('utf-8') for frame in all_frames]
        base64_combined_image = base64.b64encode(combined_image).decode('utf-8')

        return jsonify({
            'success': True,
            'clips_and_frames': clips_and_frames,
            'timeline_frames': timeline_frames,
            'frames': encoded_frames,
            'combined_image': base64_combined_image,
            'summary': summary_data['summary'],
            'key_points': summary_data['key_points'],
            'visual_description': summary_data['visual_description']
        })

    except ValueError as e:
        logger.error(f'Input validation error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Unexpected error in /process: {str(e)}', exc_info=True)
        error_message = "An unexpected error occurred while processing the video. Please try again later or with a different video."
        if "HTTP Error 400" in str(e):
            error_message = "Unable to access the YouTube video. It might be unavailable or restricted."
        return jsonify({'success': False, 'error': error_message}), 500

@app.route('/download/<filename>')
def download(filename):
    # Send the requested file to download
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/download_frame/<clip_name>/<frame_name>')
def download_frame(clip_name, frame_name):
    # Locate the frames directory associated with the clip
    frames_dir = os.path.splitext(os.path.join(app.config['UPLOAD_FOLDER'], clip_name))[0] + "_frames"
    return send_from_directory(frames_dir, frame_name, as_attachment=True)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    # Clean up the temp folder by removing all files and directories
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER'], topdown=False):
        for file in files:
            os.unlink(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
