"""Split a flat YOLO dataset into train/val/test.

Images and labels start out under ``dataset/images/train`` and
``dataset/labels/train`` (where the render scripts write them). This script
moves a fraction of pairs into ``val`` and ``test`` subdirectories, leaving the
remainder in ``train``. See ObjectDetection-Guide.md Part 8.

The selection math lives in ``od_lib.plan_split`` (unit-tested for
no-leakage and determinism); this script only performs the file moves.

Examples:
    python split_dataset.py                 # default 80/10/10 split, seed 42
    python split_dataset.py --dry-run       # print the plan, move nothing
    python split_dataset.py --val-ratio 0.15 --test-ratio 0.15
"""

import argparse
import os
import shutil
from pathlib import Path

import od_lib


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset-root", type=Path, default=here / "dataset",
                   help="dataset root containing images/ and labels/ (default: ./dataset)")
    p.add_argument("--src-img", type=Path, default=None,
                   help="source image dir (default: <dataset-root>/images/train)")
    p.add_argument("--src-lbl", type=Path, default=None,
                   help="source label dir (default: <dataset-root>/labels/train)")
    p.add_argument("--val-ratio", type=float, default=0.10)
    p.add_argument("--test-ratio", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true",
                   help="print the planned split without moving any files")
    args = p.parse_args()
    if args.src_img is None:
        args.src_img = args.dataset_root / "images" / "train"
    if args.src_lbl is None:
        args.src_lbl = args.dataset_root / "labels" / "train"
    return args


def main():
    args = parse_args()

    if not args.src_img.is_dir():
        raise SystemExit(f"source image dir not found: {args.src_img}")

    all_imgs = sorted(f for f in os.listdir(args.src_img) if f.endswith(".png"))
    if not all_imgs:
        raise SystemExit(f"no .png images found in {args.src_img}")

    plan = od_lib.plan_split(all_imgs, args.val_ratio, args.test_ratio, args.seed)

    print(f"Train: {len(plan['train'])} | "
          f"Val: {len(plan['val'])} | Test: {len(plan['test'])}")

    if args.dry_run:
        print("[dry-run] no files moved")
        return

    # train files stay where they are; only val/test pairs move.
    for split in ("val", "test"):
        img_dst = args.dataset_root / "images" / split
        lbl_dst = args.dataset_root / "labels" / split
        img_dst.mkdir(parents=True, exist_ok=True)
        lbl_dst.mkdir(parents=True, exist_ok=True)
        for fname in plan[split]:
            shutil.move(str(args.src_img / fname), str(img_dst / fname))
            lbl = od_lib.label_path_for_image(fname, str(args.src_lbl))
            if os.path.exists(lbl):
                shutil.move(lbl, str(lbl_dst / os.path.basename(lbl)))


if __name__ == "__main__":
    main()
