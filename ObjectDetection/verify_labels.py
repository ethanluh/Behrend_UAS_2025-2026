import cv2
import os
import random

IMG_DIR     = "/home/ethluh/Repositories/Behrend_UAS_2025-2026/ObjectDetection/dataset/images/train"
LBL_DIR     = "/home/ethluh/Repositories/Behrend_UAS_2025-2026/ObjectDetection/dataset/labels/train"
CLASS_NAMES = ["mannequin", "tent"]
COLORS      = [(0, 255, 0), (0, 0, 255)]
SAMPLE_SIZE = 30

img_files = [f for f in os.listdir(IMG_DIR) if f.endswith(".png")]
sample = random.sample(img_files, min(SAMPLE_SIZE, len(img_files)))

for fname in sample:
    img_path = os.path.join(IMG_DIR, fname)
    lbl_path = os.path.join(LBL_DIR, fname.replace(".png", ".txt"))

    if not os.path.exists(lbl_path):
        print(f"Missing label: {fname}")
        continue

    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not read: {img_path}")
        continue

    h, w = img.shape[:2]
    with open(lbl_path) as f:
        for line in f:
            parts  = line.strip().split()
            cls_id = int(parts[0])
            cx, cy, bw, bh = map(float, parts[1:])
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)
            color = COLORS[cls_id % len(COLORS)]
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, CLASS_NAMES[cls_id], (x1, max(y1 - 5, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    display = cv2.resize(img, (960, 960))
    cv2.imshow(f"Verify — {fname}", display)
    key = cv2.waitKey(0)
    if key == ord("q"):
        break

cv2.destroyAllWindows()