# Hardware Bring-Up Runbook

End-to-end checklist to take the project from synthetic data to a flight test.
Steps 1–7 run on a workstation; 8–11 run on the drone (Jetson + Pixhawk/PX4).
Anything marked **(hardware)** cannot be validated in CI — verify it here.

> **Safety:** the integration node never arms the vehicle and defaults to
> observe-only. Do every first run with **props removed**. Only enable motion
> (`--enable-control`) after the observe-only bench test looks correct.

## 1. Render the synthetic dataset (hardware: needs Blender + GPU)

Paths default to the repo layout; override with env vars if needed
(`OD_OUTPUT_IMAGES`, `OD_OUTPUT_LABELS`, `OD_HDRI_DIR`, `OD_NUM_RENDERS`).

```bash
blender --background ObjectDetection/blender/scenes/mannequin.blend \
        --python ObjectDetection/blender/scripts/render_mannequin.py
blender --background ObjectDetection/blender/scenes/tent.blend \
        --python ObjectDetection/blender/scripts/render_tent.py
```

Do a 5-render smoke test first: `OD_NUM_RENDERS=5 blender --background ...`.

## 2. (Optional) Augment for sim-to-real

```bash
pip install -r ObjectDetection/requirements.txt
python ObjectDetection/augment_dataset.py --per-image 2
```

## 3. Split into train/val/test

```bash
python ObjectDetection/split_dataset.py            # 80/10/10, seed 42
python ObjectDetection/split_dataset.py --dry-run  # preview without moving
```

## 4. Verify labels (catch projection bugs before training)

```bash
python ObjectDetection/verify_labels.py --no-show --out-dir /tmp/verify
```

## 5. Train (hardware: GPU strongly recommended)

```bash
python ObjectDetection/train.py --device 0          # CPU is the default
```

Best weights land in `ObjectDetection/runs/v1/weights/best.pt`.

## 6. Evaluate

```bash
python ObjectDetection/evaluate.py --weights runs/v1/weights/best.pt --split test
```

Targets: mAP@0.5 > 0.7, mAP@0.5:0.95 > 0.4 on synthetic-only. If low, see
`ObjectDetection-Guide.md` Part 12 (more data, compositing, fine-tune on real).

## 7. Export ONNX (for the C++ runtime)

```bash
python ObjectDetection/export_onnx.py --weights runs/v1/weights/best.pt
```

## 8. Build the C++ inference binary (hardware: on the Jetson)

```bash
cmake -S embedded -B embedded/build -DONNXRUNTIME_ROOT=/path/to/onnxruntime
cmake --build embedded/build
./embedded/build/yolo_infer --model best.onnx --image frame.jpg
```

No ONNX Runtime? Use the OpenCV-DNN fallback: `-DUSE_OPENCV_DNN=ON`.

## 9. Calibrate the camera (for distance estimation)

Measure a known object of known size at a known distance, then:

```bash
python integration/calibrate.py --bbox-px 380 --real-m 1.7 --distance-m 3 --frame-w 640
```

Pass the reported HFOV to the node via `--hfov`.

## 10. Bench-test the node — observe only (hardware, PROPS OFF)

```bash
pip install -r integration/requirements.txt
python integration/perception_control_node.py --weights best.pt --source 0 \
    --hfov <calibrated> --log-file bench.jsonl
```

Confirm: detections track the target, bearing sign is correct (target right →
positive), distance estimate is sane. Nothing should be sent to the vehicle.

## 11. Closed-loop test (hardware, PROPS OFF first, then flight)

1. Connect the Pixhawk; confirm telemetry with `testing/PIXHAWK/` scripts.
2. **Arm manually.** The node never arms for you.
3. Run with control enabled — still gated by `SafetyGate` (armed + fresh
   detection):

```bash
python integration/perception_control_node.py --weights best.pt --source 0 \
    --mavlink serial:///dev/ttyACM0:57600 --enable-control \
    --hfov <calibrated> --max-speed 0.5 --record flight.mp4 --log-file flight.jsonl
```

Start with a low `--max-speed`. Review `flight.jsonl` / `flight.mp4` afterward.
Keep a kill switch ready and only fly once bench behavior is correct.
