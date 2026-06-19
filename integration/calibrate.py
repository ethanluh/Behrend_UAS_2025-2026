"""Camera focal-length / HFOV calibration helper.

Monocular distance estimates (decision.estimate_distance) need the camera's
focal length in pixels. Measure it once: place a known object of known real
height at a known distance, run the detector (or measure by hand), and feed the
object's pixel height in here.

Example:
    # A 1.7 m mannequin 3 m away spans 380 px in a 640-wide frame:
    python calibrate.py --bbox-px 380 --real-m 1.7 --distance-m 3 --frame-w 640
"""

import argparse

from decision import calibrate_focal, hfov_from_focal, estimate_distance


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bbox-px", type=float, required=True,
                   help="object's pixel height in the calibration image")
    p.add_argument("--real-m", type=float, required=True,
                   help="object's real height in meters")
    p.add_argument("--distance-m", type=float, required=True,
                   help="known distance to the object in meters")
    p.add_argument("--frame-w", type=int, default=640,
                   help="image width in pixels (to report implied HFOV)")
    return p.parse_args()


def main():
    args = parse_args()
    focal = calibrate_focal(args.bbox_px, args.real_m, args.distance_m)
    hfov = hfov_from_focal(args.frame_w, focal)
    print(f"focal_px = {focal:.1f}")
    print(f"implied HFOV = {hfov:.1f} deg (at frame width {args.frame_w})")
    # Sanity check: re-estimating the calibration distance should match.
    back = estimate_distance(args.bbox_px, args.real_m, focal)
    print(f"sanity: estimate_distance -> {back:.2f} m (expected {args.distance_m})")


if __name__ == "__main__":
    main()
