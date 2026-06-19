# Embedded: low-latency C++ inference

Runs the YOLOv8 detector on flight hardware (e.g. Jetson) without the Python
runtime, for low-latency onboard inference. Consumes the ONNX model exported
from the training pipeline.

## Layout

| File | Purpose |
|------|---------|
| `src/geometry.hpp` | Header-only letterbox / xywh↔xyxy / IoU / NMS. No deps → unit-tested. |
| `src/yolo_infer.{hpp,cpp}` | `YoloInfer` class: preprocess → run model → NMS → detections. |
| `src/main.cpp` | CLI: run on an image or camera frame, print detections. |
| `tests/test_geometry.cpp` | Assert-based tests for `geometry.hpp`. |
| `CMakeLists.txt` | Builds `geometry_tests` (always) and `yolo_infer` (needs OpenCV/ORT). |

## 1. Export the model

```bash
cd ../ObjectDetection
python export_onnx.py --weights runs/v1/weights/best.pt   # -> best.onnx
```

The YOLOv8 head outputs `[1, 4 + nc, 8400] = [1, 6, 8400]` for our two classes
(`mannequin`, `tent`); the postprocessor in `yolo_infer.cpp` matches this.

## 2. Build

Default backend is **ONNX Runtime** (best performance, optional CUDA/TensorRT
on Jetson). Point CMake at your ORT install:

```bash
cmake -S . -B build -DONNXRUNTIME_ROOT=/path/to/onnxruntime
cmake --build build
```

**OpenCV-DNN fallback** (no ONNX Runtime needed, just OpenCV):

```bash
cmake -S . -B build -DUSE_OPENCV_DNN=ON
cmake --build build
```

**Just the geometry tests** (no OpenCV/ORT required — what CI runs):

```bash
cmake -S . -B build
cmake --build build --target geometry_tests
ctest --test-dir build
```

## 3. Run

```bash
./build/yolo_infer --model best.onnx --image frame.jpg
./build/yolo_infer --model best.onnx --camera 0
```

Output, one detection per line: `<class> <conf> <x1> <y1> <x2> <y2>`.

## Why C++ (not pure C)?

ONNX Runtime ships a first-class C++ API (`Ort::Session`, RAII) that is far less
error-prone than the verbose C tensor API, and OpenCV — already on the Jetson —
is C++-first for image I/O and NMS. The interface is narrow enough to wrap in
`extern "C"` later if a pure-C flight stack needs it.
