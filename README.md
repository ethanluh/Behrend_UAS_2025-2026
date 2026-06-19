# Behrend UAS 2025-2026

Computer-vision & ML pipeline for autonomous drone navigation. The system detects
mission objects (**mannequins** and **tents**) from a drone-mounted camera and
turns those detections into flight guidance, with a low-latency C++ inference path
for onboard deployment.

```
                      TRAINING (offline, workstation/GPU)
  Blender synthetic ─▶ augment ─▶ split ─▶ train (YOLOv8) ─▶ best.pt ─▶ export ONNX
   render scripts                                                          │
                                                                          ▼
                      DEPLOYMENT (onboard, Jetson + Pixhawk)
   camera ─▶ detector ─▶ decision ─▶ control            embedded/ (C++ ONNX)
   (cv2)     (YOLOv8)    (pure math   (MAVSDK/PX4)        low-latency inference
                         + SafetyGate)
```

## Modules

| Path | What it does |
|------|--------------|
| [`ObjectDetection/`](ObjectDetection/) | Synthetic-data generation (Blender), augmentation, dataset split, YOLOv8 training, evaluation, inference, and ONNX export. Full walkthrough in [`ObjectDetection-Guide.md`](ObjectDetection/ObjectDetection-Guide.md). |
| [`integration/`](integration/) | Real-time **perception → decision → control** node tying the detector to the Pixhawk over MAVLink. Observe-only by default; motion is opt-in and safety-gated. |
| [`embedded/`](embedded/) | C++17 low-latency YOLOv8 inference (ONNX Runtime, with an OpenCV-DNN fallback) for flight hardware. |
| [`tests/`](tests/) | Dependency-light pytest suite for the pure math/logic (bbox conversion, label parsing, dataset split, decision + safety logic). |
| [`testing/`](testing/) | Hardware bring-up scripts (Jetson camera, Pixhawk MAVLink telemetry/servo). |
| [`px4_control/`](px4_control/) | PX4 utilities (e.g. reboot over MAVSDK). |

## End-to-end workflow

1. **Generate data** — render synthetic images in Blender
   (`ObjectDetection/blender/scripts/render_*.py`); optionally diversify with
   `augment_dataset.py`.
2. **Prepare** — `split_dataset.py` (train/val/test) and `verify_labels.py`
   (sanity-check boxes).
3. **Train** — `train.py` (YOLOv8); evaluate with `evaluate.py`, try it with
   `infer.py`.
4. **Deploy (Python)** — run `integration/perception_control_node.py` on the
   Jetson with the trained `best.pt`.
5. **Deploy (C++)** — `export_onnx.py` → build `embedded/` → run `yolo_infer`
   for low-latency onboard inference.

See each module's README for exact commands.

## Quickstart

```bash
# Run the test suite (no GPU/torch/hardware needed)
pip install -r requirements-dev.txt
pytest -q

# Train (CPU by default; pass --device 0 for GPU)
pip install -r ObjectDetection/requirements.txt
python ObjectDetection/train.py

# Perception → control, observe-only (safe):
pip install -r integration/requirements.txt
python integration/perception_control_node.py --weights best.pt --source 0

# C++ geometry tests
cmake -S embedded -B embedded/build && cmake --build embedded/build --target geometry_tests
ctest --test-dir embedded/build
```

## Simulation

Validate the control law before flying — see [`docs/SIMULATION.md`](docs/SIMULATION.md):
a pure in-repo closed-loop validator (`integration/sim_run.py`, runs in CI) and a
PX4 SITL path for the real flight stack.

## Safety

The integration node **never arms the vehicle** and defaults to *observe-only*:
it computes and logs a corrective command without moving the drone. Motion
requires the explicit `--enable-control` flag **and** passing the `SafetyGate`
(armed + control enabled + a fresh detection). Always bench-test with props off.

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push/PR:
byte-compiles all Python, runs the pytest suite, and builds + runs the C++
geometry tests — all on a clean runner with no GPU, Blender, or hardware.
