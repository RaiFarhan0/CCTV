import os
import threading
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import traceback

from video_processor import process_video
from alert_generator import get_all_alerts

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "processed")
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(os.getenv("ALERTS_FOLDER", "alerts"), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

processing_status = {"status": "Idle", "progress": 0, "filename": None}

def run_video_processing(filepath, filename):
    global processing_status
    processing_status = {"status": "Processing", "progress": 0, "filename": filename}
    print(f"Starting background processing for {filename}...")
    try:
        process_video(filepath, socketio)
        processing_status = {"status": "Complete", "progress": 100, "filename": filename}
        print(f"Finished processing {filename}.")
    except Exception as e:
        print(f"Error during video processing: {e}")
        traceback.print_exc()
        processing_status = {"status": "Error", "progress": 0, "filename": filename, "error": str(e)}
        socketio.emit('processing_error', {'error': str(e), 'filename': filename})

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video part in the request'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Start background processing thread
        thread = threading.Thread(target=run_video_processing, args=(filepath, filename))
        thread.daemon = True
        thread.start()

        return jsonify({'message': 'File uploaded successfully. Processing started.', 'filename': filename}), 200
    else:
        return jsonify({'error': 'Invalid file type. Allowed types: mp4, avi, mov'}), 400

@app.route('/alerts', methods=['GET'])
def get_alerts():
    try:
        alerts = get_all_alerts()
        return jsonify(alerts), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video/<filename>', methods=['GET'])
def get_video(filename):
    processed_filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if os.path.exists(processed_filepath):
        return send_file(os.path.abspath(processed_filepath), mimetype='video/mp4')
    return jsonify({'error': 'Video not found or still processing'}), 404

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(processing_status), 200

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
