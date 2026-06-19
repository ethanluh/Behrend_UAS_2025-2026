"""Pure helper functions for the Object Detection pipeline.

This module intentionally has no heavy dependencies (no torch, cv2, or
ultralytics) so it can be imported and unit-tested anywhere. It holds the
bounding-box math, YOLO label parsing, and dataset-split planning that the
pipeline scripts (``split_dataset.py``, ``verify_labels.py``) and the test
suite both rely on.

Class id map (see ObjectDetection-Guide.md):
    0 = mannequin
    1 = tent
"""

import os
import random

CLASS_NAMES = ["mannequin", "tent"]


# ── Bounding-box conversion ────────────────────────────────────────────────

def xyxy_to_yolo(x1, y1, x2, y2, img_w, img_h):
    """Convert a pixel ``(x1, y1, x2, y2)`` box to normalized YOLO
    ``(cx, cy, w, h)``. Mirrors ``to_yolo`` in the render scripts.

    Raises ``ValueError`` for non-positive image dimensions or a degenerate
    box (x2 <= x1 or y2 <= y1).
    """
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"image dimensions must be positive, got {img_w}x{img_h}")
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"degenerate box: ({x1}, {y1}, {x2}, {y2})")
    cx = ((x1 + x2) / 2.0) / img_w
    cy = ((y1 + y2) / 2.0) / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return cx, cy, w, h


def yolo_to_xyxy(cx, cy, w, h, img_w, img_h):
    """Convert a normalized YOLO ``(cx, cy, w, h)`` box to integer pixel
    ``(x1, y1, x2, y2)``. Mirrors the inline math in ``verify_labels.py``.
    """
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"image dimensions must be positive, got {img_w}x{img_h}")
    x1 = int((cx - w / 2) * img_w)
    y1 = int((cy - h / 2) * img_h)
    x2 = int((cx + w / 2) * img_w)
    y2 = int((cy + h / 2) * img_h)
    return x1, y1, x2, y2


# ── YOLO label parsing ─────────────────────────────────────────────────────

def parse_label_line(line):
    """Parse a single YOLO label line into ``(cls_id, cx, cy, w, h)``.

    Expects exactly five whitespace-separated fields: an integer class id and
    four floats in ``[0, 1]``. Raises ``ValueError`` on any deviation so
    corrupt labels surface loudly instead of silently tanking training.
    """
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError(f"expected 5 fields, got {len(parts)}: {line!r}")
    try:
        cls_id = int(parts[0])
    except ValueError:
        raise ValueError(f"class id must be an integer: {parts[0]!r}")
    cx, cy, w, h = (float(p) for p in parts[1:])
    for name, val in (("cx", cx), ("cy", cy), ("w", w), ("h", h)):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} out of [0, 1] range: {val}")
    return cls_id, cx, cy, w, h


def parse_label_file(path):
    """Parse a YOLO ``.txt`` label file into a list of
    ``(cls_id, cx, cy, w, h)`` tuples. Blank lines are skipped.
    """
    boxes = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            boxes.append(parse_label_line(line))
    return boxes


def label_path_for_image(img_name, lbl_dir):
    """Map an image filename to its label path: ``foo.png`` -> ``<lbl_dir>/foo.txt``."""
    stem, _ = os.path.splitext(img_name)
    return os.path.join(lbl_dir, stem + ".txt")


# ── Dataset split planning ─────────────────────────────────────────────────

def plan_split(filenames, val_ratio=0.10, test_ratio=0.10, seed=42):
    """Plan a train/val/test split without touching the filesystem.

    Returns a dict ``{"train": [...], "val": [...], "test": [...]}``. The three
    lists are disjoint and their union equals ``filenames`` (no leakage, full
    coverage). Deterministic for a fixed ``seed``. Mirrors the index math in
    guide Part 8, but also returns the train remainder explicitly.
    """
    if val_ratio < 0 or test_ratio < 0:
        raise ValueError("ratios must be non-negative")
    if val_ratio + test_ratio > 1.0:
        raise ValueError("val_ratio + test_ratio must not exceed 1.0")

    shuffled = list(filenames)
    random.Random(seed).shuffle(shuffled)

    n = len(shuffled)
    n_val = int(n * val_ratio)
    n_test = int(n * test_ratio)

    return {
        "val": shuffled[:n_val],
        "test": shuffled[n_val:n_val + n_test],
        "train": shuffled[n_val + n_test:],
    }
