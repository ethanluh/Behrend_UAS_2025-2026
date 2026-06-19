# Guidance for Claude (and contributors)

Orientation for working in this repo. See `README.md` for the project overview.

## Repository map

- `ObjectDetection/` — data → train → deploy ML pipeline. Pure helpers in
  `od_lib.py`; CLI scripts (`train.py`, `split_dataset.py`, `evaluate.py`,
  `infer.py`, `export_onnx.py`, `augment_dataset.py`, `verify_labels.py`).
  Blender render scripts under `blender/scripts/`. Full guide:
  `ObjectDetection-Guide.md`.
- `integration/` — perception→decision→control node. `decision.py` is pure;
  `camera.py`/`detector.py`/`control.py` are thin I/O wrappers;
  `perception_control_node.py` is the async entry point; `visualize.py` draws
  overlays.
- `embedded/` — C++17 ONNX inference. `src/geometry.hpp` is header-only and
  unit-tested; `yolo_infer.{hpp,cpp}` + `main.cpp` are the runtime.
- `tests/` — pytest for the pure Python logic. `embedded/tests/` for the C++.

## Core conventions

1. **Pure logic in dependency-free modules.** Math and decision logic live in
   `od_lib.py`, `integration/decision.py`, and `embedded/src/geometry.hpp` — no
   torch / cv2 / mavsdk / ONNX Runtime. These are what the tests target.
2. **Heavy imports are lazy.** `import ultralytics` / `cv2` / `mavsdk` happen
   *inside* functions/methods, never at module top, so every file byte-compiles
   and imports on a clean runner. Keep it that way when adding code.
3. **Two object classes, fixed order:** `0 = mannequin`, `1 = tent`
   (`od_lib.CLASS_NAMES`, `decision.CLASS_NAMES_DEFAULT`).
4. **Safety first in control code.** Never auto-arm; keep `--enable-control`
   opt-in and gated by `SafetyGate`.
5. **CPU-safe defaults** for training/inference CLIs (`--device cpu`).

## Running tests

```bash
pip install -r requirements-dev.txt        # pytest + pyyaml only
pytest -q                                   # pure-logic suite

cmake -S embedded -B embedded/build         # geometry_tests needs no OpenCV/ORT
cmake --build embedded/build --target geometry_tests
ctest --test-dir embedded/build
```

What can't run in CI / sandboxes (verify on real hardware): Blender renders,
GPU training, ONNX export, live camera, live MAVLink flight.

## Conventions for changes

- Add a unit test for any new pure helper.
- Match the surrounding style; keep comments at the existing density.
- Development happens on feature branches with PRs; CI must stay green
  (`.github/workflows/ci.yml`).
