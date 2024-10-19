import os
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from utils.youtube_downloader import download_youtube_video
from utils.video_processor import process_video

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
    
    try:
        # Download YouTube video
        video_path = download_youtube_video(youtube_url, app.config['UPLOAD_FOLDER'])
        
        # Process video and get clip paths and all frames
        clip_paths, all_frames = process_video(video_path)
        
        # Sort all frames by timestamp
        all_frames.sort(key=lambda x: x['timestamp'])
        
        # Create a list of clip filenames and their corresponding frame directories
        clips_and_frames = []
        for clip_path in clip_paths:
            clip_filename = os.path.basename(clip_path)
            frames_dir = os.path.splitext(clip_path)[0] + "_frames"
            frame_filenames = [f for f in os.listdir(frames_dir) if f.endswith('.jpg')]
            clips_and_frames.append({
                'clip': clip_filename,
                'frames': frame_filenames
            })
        
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

@app.route('/download_frame/<clip_name>/<frame_name>')
def download_frame(clip_name, frame_name):
    frames_dir = os.path.splitext(os.path.join(app.config['UPLOAD_FOLDER'], clip_name))[0] + "_frames"
    return send_from_directory(frames_dir, frame_name, as_attachment=True)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER'], topdown=False):
        for file in files:
            os.unlink(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
