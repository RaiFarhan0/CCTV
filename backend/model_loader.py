from ultralytics import YOLO

def load_model():
    """
    Loads the YOLOv8n model using ultralytics.
    Downloads the model automatically on first run.
    """
    print("Loading YOLOv8n model...")
    try:
        model = YOLO("yolov8n.pt")
        print("Model loaded successfully.")
        return model
    except Exception as e:
        print(f"Error loading YOLOv8n model: {e}")
        return None
