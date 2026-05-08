import uuid
import json
import os
from datetime import datetime

ALERTS_FILE = os.path.join("alerts", "log.json")

def generate_alert(anomaly_type, confidence, frame_number, severity, thumbnail_base64, description, bbox=None):
    """
    Generate an alert object for an anomaly.

    Args:
        anomaly_type (str): Type of anomaly.
        confidence (float): Confidence score between 0 and 1.
        frame_number (int): Frame number of the video.
        severity (str): LOW, MEDIUM, HIGH, or CRITICAL.
        thumbnail_base64 (str): Base64 encoded frame image.
        description (str): Human-readable description.
        bbox (list): Bounding box coordinates [x1, y1, x2, y2].

    Returns:
        dict: The alert object.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")

    alert = {
        "id": str(uuid.uuid4()),
        "type": anomaly_type,
        "confidence": float(confidence),
        "timestamp": timestamp,
        "frame_number": int(frame_number),
        "severity": severity,
        "thumbnail": thumbnail_base64,
        "description": description,
        "bbox": [float(x) for x in bbox] if bbox else None
    }

    _save_alert(alert)
    return alert

def _save_alert(alert):
    """
    Save the alert to alerts/log.json.
    """
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)

    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "w") as f:
            json.dump([alert], f, indent=2)
    else:
        # Instead of fully reading/parsing, we can do a quick append for optimization
        # Since it's a JSON list, we read the file, strip the last ']', add our dict, and close it.
        try:
            with open(ALERTS_FILE, "r+") as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell() - 1
                while pos > 0:
                    f.seek(pos)
                    char = f.read(1)
                    if char == ']':
                        f.seek(pos)
                        f.truncate()
                        f.write(',\n  ')
                        json.dump(alert, f, indent=2)
                        # To fix indentation for the dump inside the array:
                        # (A simple dump is fine here, or format it manually)
                        f.write('\n]')
                        break
                    pos -= 1
        except Exception:
            # Fallback
            with open(ALERTS_FILE, "r") as f:
                try:
                    alerts = json.load(f)
                except json.JSONDecodeError:
                    alerts = []
            alerts.append(alert)
            with open(ALERTS_FILE, "w") as f:
                json.dump(alerts, f, indent=2)

def get_all_alerts():
    """
    Retrieve all alerts from alerts/log.json.
    """
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []
