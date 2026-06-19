// Low-latency YOLOv8 inference entry point for flight hardware.
//
// Runs the ONNX model on a single image or a live camera frame and prints
// detections as: <class> <conf> <x1> <y1> <x2> <y2>
//
// Usage:
//   yolo_infer --model model.onnx --image frame.jpg [--conf 0.25] [--iou 0.45]
//   yolo_infer --model model.onnx --camera 0
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include "yolo_infer.hpp"

namespace {

const char* arg_value(int argc, char** argv, const char* flag) {
    for (int i = 1; i < argc - 1; ++i)
        if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
    return nullptr;
}

void print_detections(const std::vector<uas::Detection>& dets) {
    for (const auto& d : dets) {
        const std::string name = d.class_id < (int)uas::CLASS_NAMES.size()
                                     ? uas::CLASS_NAMES[d.class_id]
                                     : std::to_string(d.class_id);
        std::cout << name << " " << d.confidence << " " << d.box.x1 << " "
                  << d.box.y1 << " " << d.box.x2 << " " << d.box.y2 << "\n";
    }
}

}  // namespace

int main(int argc, char** argv) {
    const char* model  = arg_value(argc, argv, "--model");
    const char* image  = arg_value(argc, argv, "--image");
    const char* camera = arg_value(argc, argv, "--camera");
    const char* conf_s = arg_value(argc, argv, "--conf");
    const char* iou_s  = arg_value(argc, argv, "--iou");

    if (!model || (!image && !camera)) {
        std::cerr << "usage: yolo_infer --model M.onnx "
                     "(--image F.jpg | --camera 0) [--conf C] [--iou I]\n";
        return 1;
    }

    const float conf = conf_s ? std::atof(conf_s) : 0.25f;
    const float iou  = iou_s ? std::atof(iou_s) : 0.45f;

    uas::YoloInfer detector(model, conf, iou);

    cv::Mat frame;
    if (image) {
        frame = cv::imread(image);
        if (frame.empty()) {
            std::cerr << "cannot read image: " << image << "\n";
            return 1;
        }
    } else {
        cv::VideoCapture cap(std::atoi(camera));
        if (!cap.isOpened()) {
            std::cerr << "cannot open camera: " << camera << "\n";
            return 1;
        }
        cap >> frame;
        if (frame.empty()) {
            std::cerr << "failed to grab frame\n";
            return 1;
        }
    }

    print_detections(detector.infer(frame));
    return 0;
}
