# Guidance for Claude (and contributors)

Orientation for working in this repo. See `README.md` for the project overview
and each module's README for exact commands.

## What this is

A computer-vision + ML pipeline for autonomous drone navigation: detect mission
objects (**mannequins**, **tents**) from a drone camera and turn detections into
flight guidance. Two deployment paths share the same geometry — a Python
perception→control node and a low-latency C++ ONNX runtime.

```
TRAINING (offline / GPU):  Blender render → augment → split → train (YOLOv8) → best.pt → export ONNX
DEPLOYMENT (onboard):      camera → detector → decision (pure math + SafetyGate) → control (MAVSDK/PX4)
                           embedded/  → C++ ONNX low-latency inference path
```

## Repository map

- `ObjectDetection/` — data → train → deploy ML pipeline. Pure helpers in
  `od_lib.py` (bbox conversion, label parsing, dataset split); CLI scripts
  `train.py`, `split_dataset.py`, `evaluate.py`, `infer.py`, `export_onnx.py`,
  `augment_dataset.py`, `verify_labels.py`. Blender render scripts under
  `blender/scripts/`. Full guide: `ObjectDetection-Guide.md`.
- `integration/` — real-time perception→decision→control node. `decision.py`
  is pure (geometry, control law, `SafetyGate`, search state machine);
  `camera.py` / `detector.py` / `control.py` are thin I/O wrappers;
  `perception_control_node.py` is the async entry point; `visualize.py` draws
  overlays; `calibrate.py` recovers focal length; `sim.py` / `sim_run.py` are
  the in-repo closed-loop validator (runs in CI).
- `embedded/` — C++17 ONNX inference. `src/geometry.hpp` is header-only and
  unit-tested; `yolo_infer.{hpp,cpp}` + `main.cpp` are the runtime (ONNX
  Runtime, OpenCV-DNN fallback).
- `tests/` — pytest for the pure Python logic. `embedded/tests/` for the C++.
- `testing/` — hardware bring-up scripts (`Jetson Nano/` camera, `PIXHAWK/`
  MAVLink telemetry + servo). `px4_control/` — PX4 utilities (e.g. reboot).
- `docs/` — `SIMULATION.md`, `HARDWARE_RUNBOOK.md`, `HARDWARE_TODO.md`.

## Core conventions

1. **Pure logic in dependency-free modules.** Math and decision logic live in
   `od_lib.py`, `integration/decision.py`, and `embedded/src/geometry.hpp` — no
   torch / cv2 / mavsdk / ONNX Runtime imports. These are what the tests target.
2. **Heavy imports are lazy.** `import ultralytics` / `cv2` / `mavsdk` happen
   *inside* functions/methods, never at module top, so every file byte-compiles
   and imports on a clean runner. Keep it that way when adding code.
3. **Two object classes, fixed order:** `0 = mannequin`, `1 = tent`
   (`od_lib.CLASS_NAMES`, `decision.CLASS_NAMES_DEFAULT`). Keep these in sync.
4. **Safety first in control code.** Never auto-arm. Keep `--enable-control`
   opt-in and gated by `SafetyGate.should_command` (armed + control enabled +
   a fresh detection). Default is observe-only: compute and log, don't move.
5. **CPU-safe defaults** for training/inference CLIs (`--device cpu`).

## Running tests

```bash
pip install -r requirements-dev.txt        # pytest + PyYAML only
pytest -q                                   # pure-logic suite (testpaths=tests)

cmake -S embedded -B embedded/build         # geometry_tests needs no OpenCV/ORT
cmake --build embedded/build --target geometry_tests
ctest --test-dir embedded/build --output-on-failure
```

What can't run in CI / sandboxes (verify on real hardware): Blender renders,
GPU training, ONNX export, live camera, live MAVLink flight.

## Conventions for changes

- Add a unit test for any new pure helper.
- Match the surrounding style; keep comments at the existing density.
- Development happens on feature branches with PRs; CI must stay green
  (`.github/workflows/ci.yml` byte-compiles all Python, runs pytest, and
  builds + runs the C++ geometry tests on a clean runner).
