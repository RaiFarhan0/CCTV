import math
from collections import OrderedDict
import numpy as np

class CentroidTracker:
    def __init__(self, max_disappeared=50, max_distance=50):
        self.next_object_id = 0
        self.objects = OrderedDict() # id -> centroid (x, y)
        self.disappeared = OrderedDict() # id -> count
        self.object_history = OrderedDict() # id -> list of dicts with frame data
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid, bbox, class_id, frame_number, timestamp):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.object_history[self.next_object_id] = [{
            "centroid": centroid,
            "bbox": bbox,
            "class_id": class_id,
            "frame_number": frame_number,
            "timestamp": timestamp
        }]
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
        # We can keep object_history for some time or delete it to save memory
        if object_id in self.object_history:
            del self.object_history[object_id]

    def update(self, rects, class_ids, frame_number, timestamp):
        # rects: list of (x1, y1, x2, y2)
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            input_centroids[i] = (cX, cY)

        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(input_centroids[i], rects[i], class_ids[i], frame_number, timestamp)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue

                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0

                self.object_history[object_id].append({
                    "centroid": input_centroids[col],
                    "bbox": rects[col],
                    "class_id": class_ids[col],
                    "frame_number": frame_number,
                    "timestamp": timestamp
                })
                # Keep history size manageable
                if len(self.object_history[object_id]) > 300:
                    self.object_history[object_id] = self.object_history[object_id][-300:]

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            if D.shape[0] >= D.shape[1]:
                for row in unused_rows:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            else:
                for col in unused_cols:
                    self.register(input_centroids[col], rects[col], class_ids[col], frame_number, timestamp)

        return self.objects

class AnomalyDetector:
    def __init__(self, frame_width, frame_height):
        self.tracker = CentroidTracker(max_disappeared=30, max_distance=100)
        self.frame_width = frame_width
        self.frame_height = frame_height
        # Cooldowns to avoid spamming alerts for the same anomaly
        self.cooldowns = {
            "Fighting": 0,
            "Loitering": {},
            "Abandoned Object": {},
            "Crowd Dispersal": 0,
            "Trespassing": {}
        }

    def process_frame(self, detections, frame_number, timestamp):
        """
        detections: list of dicts {"bbox": [x1, y1, x2, y2], "class": id, "conf": float}
        """
        rects = []
        class_ids = []
        confs = []

        for d in detections:
            rects.append(d["bbox"])
            class_ids.append(d["class"])
            confs.append(d["conf"])

        self.tracker.update(rects, class_ids, frame_number, timestamp)

        anomalies = []

        # Decrement global cooldowns
        for key in ["Fighting", "Crowd Dispersal"]:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= 1

        # 1. Trespassing
        # Zone: top-left 30% of width and height
        trespass_zone_x = self.frame_width * 0.3
        trespass_zone_y = self.frame_height * 0.3

        for obj_id, history in self.tracker.object_history.items():
            if not history: continue
            latest = history[-1]
            if latest["class_id"] == 0: # Person
                cx, cy = latest["centroid"]
                if cx < trespass_zone_x and cy < trespass_zone_y:
                    if self.cooldowns["Trespassing"].get(obj_id, 0) == 0:
                        anomalies.append({
                            "type": "Trespassing",
                            "confidence": 0.85,
                            "bbox": latest["bbox"],
                            "severity": "CRITICAL",
                            "description": "Person detected in restricted top-left zone."
                        })
                        self.cooldowns["Trespassing"][obj_id] = 50 # frames cooldown

        # Decrease obj-specific cooldowns
        for k in ["Trespassing", "Loitering", "Abandoned Object"]:
            for obj_id in list(self.cooldowns[k].keys()):
                if self.cooldowns[k][obj_id] > 0:
                    self.cooldowns[k][obj_id] -= 1
                else:
                    del self.cooldowns[k][obj_id]

        # 2. Loitering
        # Person in the same area for > 30 seconds
        for obj_id, history in self.tracker.object_history.items():
            if not history: continue
            latest = history[-1]
            if latest["class_id"] == 0:
                first = history[0]
                time_diff = latest["timestamp"] - first["timestamp"]
                if time_diff > 30.0:
                    # Check if they stayed in roughly the same area
                    dist = math.hypot(latest["centroid"][0] - first["centroid"][0], latest["centroid"][1] - first["centroid"][1])
                    if dist < 150: # max movement allowed to be considered loitering
                        if self.cooldowns["Loitering"].get(obj_id, 0) == 0:
                            anomalies.append({
                                "type": "Loitering",
                                "confidence": 0.75,
                                "bbox": latest["bbox"],
                                "severity": "MEDIUM",
                                "description": f"Person loitering in same zone for {int(time_diff)}s."
                            })
                            self.cooldowns["Loitering"][obj_id] = 100

        # 3. Abandoned Object
        # Object (bag, suitcase) static for 15+ seconds with no person nearby
        luggage_classes = [24, 26, 28] # backpack, handbag, suitcase
        for obj_id, history in self.tracker.object_history.items():
            if not history: continue
            latest = history[-1]
            if latest["class_id"] in luggage_classes:
                first = history[0]
                time_diff = latest["timestamp"] - first["timestamp"]
                if time_diff > 15.0:
                    dist = math.hypot(latest["centroid"][0] - first["centroid"][0], latest["centroid"][1] - first["centroid"][1])
                    if dist < 50: # static object
                        # Check for nearby persons
                        person_nearby = False
                        for p_id, p_history in self.tracker.object_history.items():
                            if not p_history: continue
                            p_latest = p_history[-1]
                            if p_latest["class_id"] == 0:
                                p_dist = math.hypot(latest["centroid"][0] - p_latest["centroid"][0], latest["centroid"][1] - p_latest["centroid"][1])
                                if p_dist < 150:
                                    person_nearby = True
                                    break
                        if not person_nearby:
                            if self.cooldowns["Abandoned Object"].get(obj_id, 0) == 0:
                                anomalies.append({
                                    "type": "Abandoned Object",
                                    "confidence": 0.80,
                                    "bbox": latest["bbox"],
                                    "severity": "HIGH",
                                    "description": f"Static object abandoned for {int(time_diff)}s."
                                })
                                self.cooldowns["Abandoned Object"][obj_id] = 100

        # 4. Fighting
        # Multiple persons with rapid overlapping bounding boxes
        persons = [(oid, h[-1]) for oid, h in self.tracker.object_history.items() if h and h[-1]["class_id"] == 0]
        if len(persons) >= 2 and self.cooldowns["Fighting"] == 0:
            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    id1, p1 = persons[i]
                    id2, p2 = persons[j]

                    # Check overlap
                    b1 = p1["bbox"]
                    b2 = p2["bbox"]
                    overlap = not (b1[2] < b2[0] or b1[0] > b2[2] or b1[3] < b2[1] or b1[1] > b2[3])

                    if overlap:
                        # Check rapid movement (velocity)
                        h1 = self.tracker.object_history[id1]
                        h2 = self.tracker.object_history[id2]
                        if len(h1) > 5 and len(h2) > 5:
                            v1 = math.hypot(h1[-1]["centroid"][0] - h1[-5]["centroid"][0], h1[-1]["centroid"][1] - h1[-5]["centroid"][1])
                            v2 = math.hypot(h2[-1]["centroid"][0] - h2[-5]["centroid"][0], h2[-1]["centroid"][1] - h2[-5]["centroid"][1])

                            # Normalize by time
                            dt1 = h1[-1]["timestamp"] - h1[-5]["timestamp"]
                            dt2 = h2[-1]["timestamp"] - h2[-5]["timestamp"]

                            if dt1 > 0 and dt2 > 0:
                                speed1 = v1 / dt1
                                speed2 = v2 / dt2

                                if speed1 > 100 and speed2 > 100: # threshold for rapid movement
                                    anomalies.append({
                                        "type": "Fighting",
                                        "confidence": 0.90,
                                        "bbox": [
                                            min(b1[0], b2[0]), min(b1[1], b2[1]),
                                            max(b1[2], b2[2]), max(b1[3], b2[3])
                                        ],
                                        "severity": "CRITICAL",
                                        "description": "Rapid overlapping movements detected between multiple persons."
                                    })
                                    self.cooldowns["Fighting"] = 50
                                    break
                if self.cooldowns["Fighting"] > 0:
                    break

        # 5. Crowd Dispersal
        # 3+ people moving rapidly outward from a center point
        if len(persons) >= 3 and self.cooldowns["Crowd Dispersal"] == 0:
            # Calculate center point of all persons
            cx = sum([p["centroid"][0] for id, p in persons]) / len(persons)
            cy = sum([p["centroid"][1] for id, p in persons]) / len(persons)

            dispersing_count = 0
            for oid, p in persons:
                h = self.tracker.object_history[oid]
                if len(h) > 5:
                    old_dist = math.hypot(h[-5]["centroid"][0] - cx, h[-5]["centroid"][1] - cy)
                    new_dist = math.hypot(p["centroid"][0] - cx, p["centroid"][1] - cy)

                    dt = p["timestamp"] - h[-5]["timestamp"]
                    if dt > 0 and (new_dist - old_dist) / dt > 50: # moving outward rapidly
                        dispersing_count += 1

            if dispersing_count >= 3:
                anomalies.append({
                    "type": "Crowd Dispersal",
                    "confidence": 0.85,
                    "bbox": [0, 0, self.frame_width, self.frame_height], # Full frame or bounding box encompassing them
                    "severity": "HIGH",
                    "description": "Multiple persons dispersing rapidly from a central area."
                })
                self.cooldowns["Crowd Dispersal"] = 100

        return anomalies
