"""Run YOLOv8 inference on an image, directory, or camera index.

See ObjectDetection-Guide.md Part 11.3.

Examples:
    python infer.py --weights runs/v1/weights/best.pt --source photo.jpg --save
    python infer.py --source 0           # live camera
"""

import argparse
from pathlib import Path

import od_lib


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", default=str(here / "runs" / "v1" / "weights" / "best.pt"))
    p.add_argument("--source", required=True,
                   help="image path, directory, or camera index (e.g. 0)")
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--save", action="store_true", help="write annotated output image(s)")
    return p.parse_args()


def main():
    args = parse_args()
    from ultralytics import YOLO

    model = YOLO(args.weights)
    results = model(args.source, conf=args.conf)

    for r in results:
        for box in r.boxes:
            xyxy = box.xyxy[0].tolist()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            name = od_lib.CLASS_NAMES[cls] if cls < len(od_lib.CLASS_NAMES) else str(cls)
            print(f"Class: {name}, Conf: {conf:.2f}, Box: {xyxy}")
        if args.save:
            out = r.save()
            print(f"Saved: {out}")


if __name__ == "__main__":
    main()
