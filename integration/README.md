# Integration: Perception → Decision → Control

Real-time node that connects the YOLOv8 detector to the Pixhawk/PX4 flight
controller, closing the loop from camera frames to vehicle commands.

```
camera.py  ──frames──▶  detector.py  ──detections──▶  decision.py  ──cmd──▶  control.py
 (cv2)                   (ultralytics)                 (pure math)            (MAVSDK)
```

## Files

| File | Layer | Notes |
|------|-------|-------|
| `camera.py` | perception | `cv2.VideoCapture` frame source (camera index or video file) |
| `detector.py` | perception | YOLOv8 wrapper → `(cls_id, conf, x1, y1, x2, y2)` tuples |
| `decision.py` | decision | **Pure** math + `SafetyGate`; offset, bearing, velocity command |
| `control.py` | control | MAVSDK wrapper; OFFBOARD body-velocity setpoints |
| `perception_control_node.py` | orchestration | async main loop tying it together |

`decision.py` has no heavy dependencies and is unit-tested in `../tests/`.

## Safety model

- **Default = observe only.** The node detects the target, computes its bearing
  and a corrective velocity command, and *logs* it — it sends nothing to the
  vehicle.
- Motion requires `--enable-control` **and** passing the `SafetyGate`:
  vehicle armed + control enabled + a fresh detection (within
  `--max-stale-frames`). A lost target → `hold()` (zero velocity).
- The node **never arms** the vehicle. Arm manually before tracking.

## Usage

```bash
pip install -r requirements.txt

# Observe only (safe) — prints bearing/offset, sends nothing:
python perception_control_node.py --weights /path/to/best.pt --source 0

# Closed-loop tracking (operator arms the vehicle manually first):
python perception_control_node.py --weights /path/to/best.pt --source 0 \
    --mavlink serial:///dev/ttyACM0:57600 --enable-control --target-class mannequin
```

The `best.pt` weights come from `../ObjectDetection/train.py`.
