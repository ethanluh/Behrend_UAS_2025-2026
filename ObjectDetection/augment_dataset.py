"""Offline domain-randomization augmentation for the synthetic dataset.

Diversifies rendered RGB images to narrow the sim-to-real gap, producing extra
image+label pairs alongside the originals. Uses albumentations (already in
requirements.txt) with YOLO-format bbox params so boxes track the transforms.

Augmentations: photometric (brightness/contrast, hue/saturation, gaussian
noise, blur) plus an optional horizontal flip — chosen to stay label-safe (no
rotations/crops that would distort the single-object boxes).

Example:
    python augment_dataset.py --per-image 2          # 2 augmented copies each
    python augment_dataset.py --img-dir dataset/images/train \
        --lbl-dir dataset/labels/train --per-image 3 --seed 0
"""

import argparse
import os
import random
from pathlib import Path

import od_lib


def parse_args():
    here = Path(__file__).resolve().parent
    root = here / "dataset"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--img-dir", type=Path, default=root / "images" / "train")
    p.add_argument("--lbl-dir", type=Path, default=root / "labels" / "train")
    p.add_argument("--per-image", type=int, default=2,
                   help="number of augmented copies to make per source image")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--prefix", default="aug",
                   help="filename prefix for generated pairs")
    return p.parse_args()


def build_pipeline():
    """Construct the albumentations pipeline (imported lazily)."""
    import albumentations as A
    return A.Compose(
        [
            A.RandomBrightnessContrast(p=0.7),
            A.HueSaturationValue(p=0.5),
            A.GaussNoise(p=0.3),
            A.Blur(blur_limit=3, p=0.2),
            A.HorizontalFlip(p=0.5),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_ids"],
                                 min_visibility=0.3),
    )


def main():
    args = parse_args()
    import cv2

    random.seed(args.seed)
    pipeline = build_pipeline()

    img_files = sorted(f for f in os.listdir(args.img_dir) if f.endswith(".png"))
    if not img_files:
        raise SystemExit(f"no .png images found in {args.img_dir}")

    made = 0
    for fname in img_files:
        img = cv2.imread(str(args.img_dir / fname))
        if img is None:
            print(f"Could not read: {fname}")
            continue
        lbl_path = od_lib.label_path_for_image(fname, str(args.lbl_dir))
        if not os.path.exists(lbl_path):
            print(f"Skipping (no label): {fname}")
            continue

        boxes = od_lib.parse_label_file(lbl_path)
        class_ids = [b[0] for b in boxes]
        bboxes = [b[1:] for b in boxes]   # (cx, cy, w, h)

        stem = Path(fname).stem
        for k in range(args.per_image):
            out = pipeline(image=img, bboxes=bboxes, class_ids=class_ids)
            out_name = f"{args.prefix}_{stem}_{k}.png"
            cv2.imwrite(str(args.img_dir / out_name), out["image"])
            out_lbl = od_lib.label_path_for_image(out_name, str(args.lbl_dir))
            with open(out_lbl, "w") as f:
                for cls, (cx, cy, w, h) in zip(out["class_ids"], out["bboxes"]):
                    f.write(f"{int(cls)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
            made += 1

    print(f"Wrote {made} augmented image+label pairs to {args.img_dir}")


if __name__ == "__main__":
    main()
