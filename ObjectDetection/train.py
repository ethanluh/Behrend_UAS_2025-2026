"""Train a YOLOv8 detector on the synthetic mannequin/tent dataset.

See ObjectDetection-Guide.md Part 10. Defaults to CPU so it never assumes a
GPU is present; pass ``--device 0`` (or another index) to train on GPU.

Examples:
    python train.py                         # yolov8n, 50 epochs, cpu
    python train.py --device 0 --batch 16   # GPU
    python train.py --model yolov8s.pt --epochs 100
"""

import argparse
from pathlib import Path


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(here / "training" / "dataset.yaml"),
                   help="path to dataset.yaml")
    p.add_argument("--model", default="yolov8n.pt",
                   help="base model / weights (downloads pretrained on first run)")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16,
                   help="reduce to 8 if you run out of VRAM")
    p.add_argument("--device", default="cpu",
                   help='GPU index (e.g. "0") or "cpu"')
    p.add_argument("--project", default=str(here / "runs"))
    p.add_argument("--name", default="v1")
    return p.parse_args()


def main():
    args = parse_args()
    # Imported here so the module compiles/imports without ultralytics installed.
    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        augment=True,   # mosaic, flips, color jitter, etc.
    )
    print(f"Training complete. Best weights: {args.project}/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
