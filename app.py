import os
import logging
import json
import base64
import re
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from utils.video_processor import process_video, generate_summary, download_youtube_video, get_youtube_transcript, create_combined_images

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    logger.info("Received request to /process endpoint")
    try:
        youtube_url = request.form.get('youtube_url')
        video_file = request.files.get('video')
        transcript = request.form.get('transcript')
        frame_interval = request.form.get('frame_interval')

        if frame_interval:
            try:
                frame_interval = int(frame_interval)
                if frame_interval <= 0:
                    raise ValueError('Frame interval must be a positive integer')
            except ValueError:
                raise ValueError('Invalid frame interval')
        else:
            frame_interval = None

        if youtube_url:
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

        logger.info(f"Starting video processing with frame interval: {frame_interval}")
        clip_paths, all_frames = process_video(video_path, frame_interval=frame_interval)

        if not clip_paths:
            logger.error("No clips generated during video processing")
            return jsonify({'success': False, 'error': 'No clips generated.'})

        if not all_frames:
            logger.error("No frames extracted during video processing")
            return jsonify({'success': False, 'error': 'No frames extracted.'})

        logger.info(f"Successfully processed video. Generated {len(clip_paths)} clips and {len(all_frames)} frames.")

        all_frames.sort(key=lambda x: x['timestamp'])

        clips_and_frames = []
        for clip_path in clip_paths:
            clip_filename = os.path.basename(clip_path)
            clip_frames = [frame for frame in all_frames if frame['clip'] == clip_filename]
            clips_and_frames.append({
                'clip': clip_filename,
                'frames': [os.path.basename(frame['path']) for frame in clip_frames]
            })

        timeline_frames = [
            {
                'path': frame['path'],
                'timestamp': frame['timestamp'],
                'clip': frame['clip']
            } for frame in all_frames
        ]

        if use_youtube_transcript:
            video_id_match = re.search(r"v=([^&]+)", youtube_url)
            if video_id_match:
                video_transcript = get_youtube_transcript(video_id_match.group(1))
            else:
                video_transcript = None
        else:
            video_transcript = None

        frame_data_types = [type(frame['data']).__name__ for frame in all_frames]
        logger.debug(f"Frame data types before combining: {frame_data_types}")

        combined_images = create_combined_images([frame['data'] for frame in all_frames])

        if not combined_images:
            logger.error("Failed to create combined images")
            return jsonify({'success': False, 'error': 'Failed to create combined images.'})

        summary = generate_summary(combined_images[0], video_transcript or transcript)

        encoded_frames = [base64.b64encode(frame['data']).decode('utf-8') for frame in all_frames]
        base64_combined_image = base64.b64encode(combined_images[0]).decode('utf-8')

        logger.info("Successfully prepared response data")
        return jsonify({
            'success': True,
            'clips_and_frames': clips_and_frames,
            'timeline_frames': timeline_frames,
            'frames': encoded_frames,
            'combined_image': base64_combined_image,
            'summary': summary,
            'debug_info': {
                'frame_data_types': frame_data_types,
                'num_clips': len(clip_paths),
                'num_frames': len(all_frames)
            }
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
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/download_frame/<clip_name>/<frame_name>')
def download_frame(clip_name, frame_name):
    clip_base_name = os.path.splitext(clip_name)[0]
    frames_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{clip_base_name}_frames")
    frame_path = os.path.join(frames_dir, frame_name)
    logger.debug(f"Attempting to serve frame: {frame_name} from directory: {frames_dir}")
    logger.debug(f"Full frame path: {frame_path}")
    
    if os.path.exists(frame_path):
        logger.info(f"Serving frame: {frame_name} for clip: {clip_name}")
        return send_from_directory(frames_dir, frame_name)
    else:
        logger.error(f"Frame not found: {frame_name} in directory: {frames_dir}")
        placeholder_path = os.path.join(app.static_folder, 'images', 'placeholder.jpg')
        if os.path.exists(placeholder_path):
            logger.info(f"Serving placeholder image for frame: {frame_name}")
            return send_file(placeholder_path, mimetype='image/jpeg')
        else:
            logger.error("Placeholder image not found")
            return "Frame not found and placeholder image is missing", 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER'], topdown=False):
        for file in files:
            os.unlink(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
