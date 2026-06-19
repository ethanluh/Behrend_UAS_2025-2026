# Hardware To-Do Checklist

A trackable checklist for taking the project from synthetic data to a flight
test. The software is complete and CI-green; everything here is physical
bring-up that can't be validated in CI.

For the **exact commands** at each step, see
[`HARDWARE_RUNBOOK.md`](HARDWARE_RUNBOOK.md) — this file is the checklist, the
runbook is the reference. Each item lists the pass/fail gate to clear before
moving on.

> **Safety:** the integration node never arms the vehicle and defaults to
> observe-only. Do every first run with **props removed**, and only enable
> motion (`--enable-control`) after the observe-only bench test looks correct.

## 1. Workstation — dataset & model (needs Blender + GPU)

- [ ] **Render the dataset** — smoke-test with `OD_NUM_RENDERS=5` first, then a
      full render of both scenes. *Gate: images + YOLO `.txt` labels in `dataset/`.*
- [ ] **(Optional) Augment** for sim-to-real (`augment_dataset.py --per-image 2`).
- [ ] **Split** train/val/test (`split_dataset.py`); preview with `--dry-run` first.
- [ ] **Verify labels** headless (`verify_labels.py --no-show`) and eyeball a few.
      *Gate: boxes land on the objects — catch projection bugs before training.*
- [ ] **Train** on GPU (`train.py --device 0`). *Gate: `runs/v1/weights/best.pt`
      exists, loss converges.*
- [ ] **Evaluate** on the test split. *Gate: mAP@0.5 > 0.7 and mAP@0.5:0.95 > 0.4.
      If low → more data / compositing / real fine-tune (Guide Part 12).*
- [ ] **Export ONNX** (`export_onnx.py`). *Gate: output shape `[1, 6, 8400]`.*

## 2. Jetson — embedded inference

- [ ] **Install ONNX Runtime** (or plan the `-DUSE_OPENCV_DNN=ON` fallback).
- [ ] **Build** `embedded/` and run `yolo_infer` on a sample frame.
      *Gate: detections match Python `infer.py` on the same image.*
- [ ] **Benchmark latency / FPS** on the Jetson. *Gate: fast enough for the
      control loop — this is the reason the C++ path exists.*

## 3. Camera calibration

- [ ] **Measure** a known-size object at a known distance; run
      `integration/calibrate.py`.
- [ ] **Record the HFOV** — every node run passes it via `--hfov`.
      *Gate: `estimate_distance` is accurate at 2–3 known distances.*

## 4. Bench test — PROPS OFF

- [ ] **Observe-only run** of the node (`--hfov <cal> --log-file bench.jsonl`,
      no `--enable-control`). *Gate: bearing sign correct (target right →
      positive), distance sane, nothing sent to the vehicle.*
- [ ] **Verify the Pixhawk link** with `testing/PIXHAWK/` scripts (telemetry,
      armed state).
- [ ] **Tune gains against real data** — `ControlGains` (yaw, approach, deadzone)
      plus `scan_yaw_rate` / `max_search_frames` for the search sweep, using
      `bench.jsonl` to inspect the commands the controller *would* send.

## 5. Closed-loop — PROPS OFF, then flight

- [ ] **Manual arm + control enabled, props still off** (`--enable-control
      --max-speed 0.5 --record flight.mp4 --log-file flight.jsonl`). *Gate:
      yaw/forward commands move in the correct direction; `SafetyGate` blocks
      when disarmed or the detection is stale.*
- [ ] **Validate search/reacquire live** — walk the target out of frame; confirm
      the in-place yaw scan sweeps toward the last-seen side and reacquires, and
      that it gives up to a hold after the timeout (no endless spin).
- [ ] **First flight** — low `--max-speed`, kill switch ready, open area; review
      `flight.jsonl` / `flight.mp4` afterward.
- [ ] **Iterate** on gains / standoff from flight logs.
