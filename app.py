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

        # ... [previous code for processing video remains unchanged] ...

        combined_images = create_combined_images([frame['data'] for frame in all_frames])

        if not combined_images:
            logger.error("Failed to create combined images")
            return jsonify({'success': False, 'error': 'Failed to create combined images.'})

        try:
            summary, key_points, visual_description = generate_summary(combined_images[0], video_transcript or transcript)
        except ValueError as e:
            logger.error(f"Error generating summary: {e}")
            summary = "Unable to generate summary due to an error."
            key_points = []
            visual_description = "Visual description unavailable."

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
            'key_points': key_points,
            'visual_description': visual_description,
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

# ... [rest of the file remains unchanged] ...
