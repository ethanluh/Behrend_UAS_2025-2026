"""Export trained YOLOv8 weights to ONNX for the C++ embedded runtime.

The exported model feeds ``embedded/`` (ONNX Runtime / OpenCV-DNN). For two
classes the YOLOv8 detection head outputs a tensor of shape:

    [1, 4 + nc, 8400] = [1, 6, 8400]

i.e. 8400 anchor predictions, each [cx, cy, w, h, score_mannequin, score_tent]
in input-image (letterboxed 640x640) pixel coordinates. The C++ postprocessor
in embedded/src/yolo_infer.cpp must match this layout.

Example:
    python export_onnx.py --weights runs/v1/weights/best.pt
"""

import argparse
from pathlib import Path


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", default=str(here / "runs" / "v1" / "weights" / "best.pt"))
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--opset", type=int, default=12)
    p.add_argument("--no-simplify", action="store_true",
                   help="disable onnx-simplifier pass")
    return p.parse_args()


def main():
    args = parse_args()
    from ultralytics import YOLO

    model = YOLO(args.weights)
    out_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=not args.no_simplify,
    )
    print(f"Exported ONNX model: {out_path}")
    print("Use it with: ./yolo_infer --model <path> --image <frame.jpg>")


if __name__ == "__main__":
    main()
