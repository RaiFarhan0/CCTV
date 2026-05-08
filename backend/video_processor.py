import cv2
import os
import base64
import numpy as np
from model_loader import load_model
from detector import AnomalyDetector
from alert_generator import generate_alert

def process_video(video_path, socketio=None):
    """
    Process video frame by frame, run YOLOv8 and AnomalyDetector, and save annotated video.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    model = load_model()
    if model is None:
        raise RuntimeError("Failed to load YOLOv8 model")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0:
        fps = 30 # fallback

    detector = AnomalyDetector(width, height)

    filename = os.path.basename(video_path)
    processed_path = os.path.join("processed", filename)
    os.makedirs("processed", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(processed_path, fourcc, fps, (width, height))

    frame_count = 0
    anomalies_detected = []

    colors = {
        "CRITICAL": (0, 0, 255), # Red
        "HIGH": (0, 165, 255), # Orange
        "MEDIUM": (0, 255, 255), # Yellow
        "LOW": (255, 0, 0) # Blue
    }

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        timestamp = frame_count / fps

        # Process every 3rd frame to speed up
        if frame_count % 3 == 0:
            # Run YOLOv8
            results = model(frame, verbose=False)

            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    detections.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "class": cls,
                        "conf": conf
                    })

            # Run Anomaly Detector
            frame_anomalies = detector.process_frame(detections, frame_count, timestamp)

            for anomaly in frame_anomalies:
                # Encode thumbnail
                _, buffer = cv2.imencode('.jpg', frame)
                thumbnail_base64 = base64.b64encode(buffer).decode('utf-8')

                alert = generate_alert(
                    anomaly_type=anomaly["type"],
                    confidence=anomaly["confidence"],
                    frame_number=frame_count,
                    severity=anomaly["severity"],
                    thumbnail_base64=thumbnail_base64,
                    description=anomaly["description"],
                    bbox=anomaly["bbox"]
                )
                anomalies_detected.append(alert)

                if socketio:
                    socketio.emit('alert_detected', alert)

            # Draw bounding boxes for anomalies
            for anomaly in frame_anomalies:
                severity = anomaly["severity"]
                color = colors.get(severity, (255, 255, 255))
                bbox = anomaly["bbox"]
                x1, y1, x2, y2 = map(int, bbox)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{anomaly['type']} ({anomaly['confidence']:.2f})"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Write frame to output video
        out.write(frame)

        # Progress update
        if frame_count % 30 == 0 and socketio:
            progress = int((frame_count / total_frames) * 100)
            socketio.emit('processing_progress', {'progress': progress, 'filename': filename})

    cap.release()
    if frame is not None:
        out.write(frame) # just in case
    out.release()

    if socketio:
        socketio.emit('processing_complete', {'filename': filename, 'total_alerts': len(anomalies_detected)})

    return anomalies_detected, processed_path
