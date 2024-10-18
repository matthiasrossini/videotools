import os
import logging
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from utils.youtube_downloader import download_youtube_video, VideoDownloadError
from utils.video_processor import process_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    youtube_url = request.form['youtube_url']
    
    start_minutes = request.form.get('start_minutes', type=int)
    start_seconds = request.form.get('start_seconds', type=int)
    end_minutes = request.form.get('end_minutes', type=int)
    end_seconds = request.form.get('end_seconds', type=int)
    
    start_time = None
    end_time = None
    
    if start_minutes is not None or start_seconds is not None:
        start_time = (start_minutes or 0) * 60 + (start_seconds or 0)
    
    if end_minutes is not None or end_seconds is not None:
        end_time = (end_minutes or 0) * 60 + (end_seconds or 0)
    
    precise_trim = request.form.get('precise_trim') == 'true'
    
    try:
        video_path = download_youtube_video(youtube_url, app.config['UPLOAD_FOLDER'], start_time, end_time, precise_trim)
        clip_paths, all_frames, clips_and_frames = process_video(video_path, start_time, end_time)
        
        all_frames.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'success': True,
            'clips_and_frames': clips_and_frames,
            'timeline_frames': [
                {
                    'path': os.path.basename(frame['path']),
                    'timestamp': frame['timestamp'],
                    'clip': frame['clip']
                } for frame in all_frames
            ]
        })
    except VideoDownloadError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': f"An unexpected error occurred: {str(e)}"})

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/download_frame/<clip_name>/<frame_name>')
def download_frame(clip_name, frame_name):
    frames_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'trimmed_temp', f"trimmed_{clip_name}_frames")
    file_path = os.path.join(frames_dir, frame_name)
    logging.info(f"Attempting to serve frame: {file_path}")
    
    if os.path.exists(file_path):
        logging.info(f"Frame file found: {file_path}")
        return send_file(file_path, mimetype='image/jpeg')
    else:
        logging.error(f"Frame file not found: {file_path}")
        return jsonify({'error': 'Frame not found'}), 404

@app.route('/debug/list_files')
def list_files():
    files = []
    for root, dirs, filenames in os.walk(app.config['UPLOAD_FOLDER']):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    return jsonify({'files': files})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
