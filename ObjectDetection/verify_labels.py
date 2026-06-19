"""Visually verify YOLO labels by drawing boxes on their images.

See ObjectDetection-Guide.md Part 7. A bbox-projection bug silently tanks mAP
and is invisible until you look, so run this before training.

By default it opens an interactive window (press any key to advance, ``q`` to
quit). On a headless machine pass ``--no-show`` to write annotated copies to an
output directory instead.

Examples:
    python verify_labels.py
    python verify_labels.py --no-show --out-dir /tmp/verify
"""

import argparse
import os
import random
from pathlib import Path

import cv2

import od_lib

COLORS = [(0, 255, 0), (0, 0, 255)]  # green = mannequin, blue = tent


def parse_args():
    here = Path(__file__).resolve().parent
    default_root = here / "dataset"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--img-dir", type=Path, default=default_root / "images" / "train")
    p.add_argument("--lbl-dir", type=Path, default=default_root / "labels" / "train")
    p.add_argument("--sample-size", type=int, default=30)
    p.add_argument("--no-show", action="store_true",
                   help="headless: write annotated images instead of opening a window")
    p.add_argument("--out-dir", type=Path, default=here / "verify_out",
                   help="output dir for --no-show mode")
    return p.parse_args()


def annotate(img, lbl_path):
    h, w = img.shape[:2]
    for cls_id, cx, cy, bw, bh in od_lib.parse_label_file(lbl_path):
        x1, y1, x2, y2 = od_lib.yolo_to_xyxy(cx, cy, bw, bh, w, h)
        color = COLORS[cls_id % len(COLORS)]
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, od_lib.CLASS_NAMES[cls_id], (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img


def main():
    args = parse_args()

    img_files = [f for f in os.listdir(args.img_dir) if f.endswith(".png")]
    if not img_files:
        raise SystemExit(f"no .png images found in {args.img_dir}")
    sample = random.sample(img_files, min(args.sample_size, len(img_files)))

    if args.no_show:
        args.out_dir.mkdir(parents=True, exist_ok=True)

    for fname in sample:
        img_path = os.path.join(args.img_dir, fname)
        lbl_path = od_lib.label_path_for_image(fname, str(args.lbl_dir))

        if not os.path.exists(lbl_path):
            print(f"Missing label: {fname}")
            continue
        img = cv2.imread(img_path)
        if img is None:
            print(f"Could not read: {img_path}")
            continue

        annotate(img, lbl_path)

        if args.no_show:
            cv2.imwrite(str(args.out_dir / fname), img)
        else:
            display = cv2.resize(img, (960, 960))
            cv2.imshow(f"Verify — {fname}", display)
            if cv2.waitKey(0) == ord("q"):
                break

    if args.no_show:
        print(f"Wrote {len(sample)} annotated images to {args.out_dir}")
    else:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
