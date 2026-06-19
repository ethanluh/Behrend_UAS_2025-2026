#include "yolo_infer.hpp"

#include <opencv2/imgproc.hpp>

#include "geometry.hpp"

#ifdef USE_OPENCV_DNN
#include <opencv2/dnn.hpp>
#else
#include <onnxruntime_cxx_api.h>
#endif

namespace uas {

// ── Backend-specific state ─────────────────────────────────────────────────
#ifdef USE_OPENCV_DNN

struct YoloInfer::Impl {
    cv::dnn::Net net;
    explicit Impl(const std::string& model_path) {
        net = cv::dnn::readNetFromONNX(model_path);
    }
};

#else  // ONNX Runtime backend

struct YoloInfer::Impl {
    Ort::Env env;
    Ort::Session session;
    Ort::AllocatorWithDefaultOptions alloc;
    std::string input_name;
    std::string output_name;

    explicit Impl(const std::string& model_path)
        : env(ORT_LOGGING_LEVEL_WARNING, "yolo"),
          session(env, model_path.c_str(), Ort::SessionOptions{}) {
        input_name  = session.GetInputNameAllocated(0, alloc).get();
        output_name = session.GetOutputNameAllocated(0, alloc).get();
    }
};

#endif

// ── Shared pre/post-processing ─────────────────────────────────────────────

// Letterbox a BGR frame into an imgsz x imgsz square and return the transform.
static cv::Mat letterbox_frame(const cv::Mat& frame, int imgsz, Letterbox& lb) {
    lb = compute_letterbox(frame.cols, frame.rows, imgsz, imgsz);
    cv::Mat resized;
    cv::resize(frame, resized,
               cv::Size(static_cast<int>(frame.cols * lb.scale),
                        static_cast<int>(frame.rows * lb.scale)));
    cv::Mat out(imgsz, imgsz, frame.type(), cv::Scalar(114, 114, 114));
    resized.copyTo(out(cv::Rect(static_cast<int>(lb.pad_x),
                                static_cast<int>(lb.pad_y),
                                resized.cols, resized.rows)));
    return out;
}

// Decode the YOLOv8 output buffer (layout [4 + nc, num_anchors], row-major
// after transpose) into thresholded, NMS-filtered detections in image pixels.
static std::vector<Detection> decode(const float* data, int num_classes,
                                     int num_anchors, const Letterbox& lb,
                                     float conf_thresh, float iou_thresh) {
    std::vector<Box> boxes;
    std::vector<float> scores;
    std::vector<int> class_ids;

    const int stride = 4 + num_classes;  // per-anchor record length
    for (int a = 0; a < num_anchors; ++a) {
        const float* rec = data + a * stride;
        int best = 0;
        float best_score = rec[4];
        for (int c = 1; c < num_classes; ++c) {
            if (rec[4 + c] > best_score) { best_score = rec[4 + c]; best = c; }
        }
        if (best_score < conf_thresh) continue;
        Box b = xywh_to_xyxy(rec[0], rec[1], rec[2], rec[3]);
        boxes.push_back(undo_letterbox(b, lb));
        scores.push_back(best_score);
        class_ids.push_back(best);
    }

    std::vector<Detection> dets;
    for (size_t k : nms(boxes, scores, iou_thresh))
        dets.push_back(Detection{class_ids[k], scores[k], boxes[k]});
    return dets;
}

// ── Public API ─────────────────────────────────────────────────────────────

YoloInfer::YoloInfer(const std::string& model_path, float conf_thresh,
                     float iou_thresh, int imgsz)
    : conf_thresh_(conf_thresh), iou_thresh_(iou_thresh), imgsz_(imgsz),
      impl_(new Impl(model_path)) {}

YoloInfer::~YoloInfer() { delete impl_; }

std::vector<Detection> YoloInfer::infer(const cv::Mat& frame) {
    Letterbox lb;
    cv::Mat input = letterbox_frame(frame, imgsz_, lb);

    const int num_classes = static_cast<int>(CLASS_NAMES.size());

#ifdef USE_OPENCV_DNN
    cv::Mat blob = cv::dnn::blobFromImage(
        input, 1.0 / 255.0, cv::Size(imgsz_, imgsz_),
        cv::Scalar(), /*swapRB=*/true, /*crop=*/false);
    impl_->net.setInput(blob);
    cv::Mat out = impl_->net.forward();  // [1, 4+nc, num_anchors]
    const int num_anchors = out.size[2];
    // Transpose to [num_anchors, 4+nc] so each anchor's fields are contiguous.
    cv::Mat out2d(out.size[1], num_anchors, CV_32F, out.ptr<float>());
    cv::Mat t;
    cv::transpose(out2d, t);
    return decode(reinterpret_cast<const float*>(t.data), num_classes,
                  num_anchors, lb, conf_thresh_, iou_thresh_);
#else
    // BGR->RGB, /255, HWC->CHW float blob.
    cv::Mat rgb;
    cv::cvtColor(input, rgb, cv::COLOR_BGR2RGB);
    rgb.convertTo(rgb, CV_32F, 1.0 / 255.0);
    std::vector<cv::Mat> chw(3);
    cv::split(rgb, chw);
    std::vector<float> tensor;
    tensor.reserve(3 * imgsz_ * imgsz_);
    for (int c = 0; c < 3; ++c)
        tensor.insert(tensor.end(), (float*)chw[c].datastart, (float*)chw[c].dataend);

    std::array<int64_t, 4> shape{1, 3, imgsz_, imgsz_};
    Ort::MemoryInfo mem = Ort::MemoryInfo::CreateCpu(
        OrtArenaAllocator, OrtMemTypeDefault);
    Ort::Value in = Ort::Value::CreateTensor<float>(
        mem, tensor.data(), tensor.size(), shape.data(), shape.size());

    const char* in_names[]  = {impl_->input_name.c_str()};
    const char* out_names[] = {impl_->output_name.c_str()};
    auto outs = impl_->session.Run(Ort::RunOptions{nullptr}, in_names, &in, 1,
                                   out_names, 1);

    // Output shape [1, 4+nc, num_anchors]; transpose to [num_anchors, 4+nc].
    auto info = outs[0].GetTensorTypeAndShapeInfo();
    auto dims = info.GetShape();  // {1, 4+nc, num_anchors}
    const int num_anchors = static_cast<int>(dims[2]);
    const float* raw = outs[0].GetTensorData<float>();
    std::vector<float> t(static_cast<size_t>(num_anchors) * (4 + num_classes));
    for (int f = 0; f < 4 + num_classes; ++f)
        for (int a = 0; a < num_anchors; ++a)
            t[a * (4 + num_classes) + f] = raw[f * num_anchors + a];
    return decode(t.data(), num_classes, num_anchors, lb,
                  conf_thresh_, iou_thresh_);
#endif
}

}  // namespace uas
