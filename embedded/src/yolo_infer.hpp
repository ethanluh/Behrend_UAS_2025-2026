// YOLOv8 ONNX inference on the edge (Jetson) using ONNX Runtime + OpenCV.
//
// Build with -DUSE_OPENCV_DNN=ON to use OpenCV's DNN module instead of ONNX
// Runtime (no extra dependency beyond OpenCV). Either backend consumes the
// .onnx produced by ../../ObjectDetection/export_onnx.py.
#pragma once

#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "geometry.hpp"

namespace uas {

struct Detection {
    int   class_id;
    float confidence;
    Box   box;  // pixels in the original image
};

const std::vector<std::string> CLASS_NAMES = {"mannequin", "tent"};

class YoloInfer {
public:
    YoloInfer(const std::string& model_path,
              float conf_thresh = 0.25f,
              float iou_thresh  = 0.45f,
              int   imgsz       = 640);
    ~YoloInfer();

    // Run detection on a single BGR frame.
    std::vector<Detection> infer(const cv::Mat& frame);

private:
    float conf_thresh_;
    float iou_thresh_;
    int   imgsz_;

    // Pimpl: hides the ORT / OpenCV-DNN backend handles from this header so
    // callers don't need the backend's headers on their include path.
    struct Impl;
    Impl* impl_;
};

}  // namespace uas
