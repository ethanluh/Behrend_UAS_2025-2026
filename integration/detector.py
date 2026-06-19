"""YOLOv8 detector wrapper for the perception loop.

Returns detections as plain tuples ``(cls_id, conf, x1, y1, x2, y2)`` so the
downstream decision logic stays free of ultralytics types. ultralytics is
imported lazily so this module imports without torch installed.
"""

from decision import Detection  # noqa: F401  (re-export the tuple type)


class Detector:
    def __init__(self, weights, conf=0.25, imgsz=640):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.conf = conf
        self.imgsz = imgsz

    def detect(self, frame):
        """Run inference on a single BGR frame -> list of detection tuples."""
        results = self.model(frame, conf=self.conf, imgsz=self.imgsz, verbose=False)
        dets = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                dets.append((int(box.cls[0]), float(box.conf[0]), x1, y1, x2, y2))
        return dets
