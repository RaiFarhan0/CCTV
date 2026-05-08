# SENTINEL AI — CCTV Anomaly Detection System

## Description
AI-powered security system that detects anomalies in CCTV footage.

## Features
* 5 anomaly types (Fighting, Loitering, Abandoned Object, Crowd Dispersal, Trespassing)
* Real-time alerts
* Dark dashboard
* Annotated video output

## Tech Stack
* Python
* Flask
* YOLOv8
* OpenCV
* Socket.IO
* Vanilla JS

## Installation and run instructions

### Backend setup
1. Create a virtual environment: `python3 -m venv venv`
2. Activate the virtual environment: `source venv/bin/activate`
3. Install dependencies: `pip install -r backend/requirements.txt`
4. Start the server: `cd backend && python app.py`

The backend will automatically start listening on port 5000 and the YOLOv8 model will auto-download on first use.

### Frontend setup
Since this is pure vanilla JS, you can serve the frontend directory using any static web server, or directly integrate it into the Flask app.
For example, using Python's built-in http server:
```
cd frontend
python -m http.server 8000
```
Then navigate to `http://localhost:8000` in your browser.

## Dataset link
UCSD Anomaly Detection Dataset: http://www.svcl.ucsd.edu/projects/anomaly/dataset.htm

## Future improvements
* multi-camera support
* zone drawing tool
* mobile app integration
