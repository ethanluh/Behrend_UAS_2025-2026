"""Evaluate trained YOLOv8 weights on a dataset split.

See ObjectDetection-Guide.md Part 11.2.

Example:
    python evaluate.py --weights runs/v1/weights/best.pt --split test
"""

import argparse
from pathlib import Path


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", default=str(here / "runs" / "v1" / "weights" / "best.pt"))
    p.add_argument("--data", default=str(here / "training" / "dataset.yaml"))
    p.add_argument("--split", default="test", choices=["train", "val", "test"])
    return p.parse_args()


def main():
    args = parse_args()
    from ultralytics import YOLO

    model = YOLO(args.weights)
    metrics = model.val(data=args.data, split=args.split)
    print(f"mAP@0.5      : {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95 : {metrics.box.map:.4f}")


if __name__ == "__main__":
    main()
