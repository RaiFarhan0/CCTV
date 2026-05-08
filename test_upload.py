import requests
import cv2
import numpy as np

# Create a short dummy video
width, height = 640, 480
fps = 30
duration = 2 # seconds
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('dummy.mp4', fourcc, fps, (width, height))

# Simulate something moving to trigger tracker
for i in range(fps * duration):
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Draw a moving square simulating a person
    x = int(i * 10) % width
    y = int(i * 5) % height
    cv2.rectangle(frame, (x, y), (x+50, y+50), (255, 255, 255), -1)

    # Draw a person trespassing in top left
    if i < 30:
        cv2.rectangle(frame, (10, 10), (60, 60), (255, 255, 255), -1)

    out.write(frame)

out.release()

url = 'http://localhost:5000/upload'
files = {'video': open('dummy.mp4', 'rb')}
r = requests.post(url, files=files)
print(r.json())
