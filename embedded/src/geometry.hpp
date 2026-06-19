// Header-only geometry helpers for YOLO pre/post-processing.
//
// Deliberately free of OpenCV and ONNX Runtime so it can be unit-tested on any
// machine (see ../tests/test_geometry.cpp) and reused by the inference code.
#pragma once

#include <algorithm>
#include <cstddef>
#include <vector>

namespace uas {

struct Box {
    float x1, y1, x2, y2;
    float width()  const { return x2 - x1; }
    float height() const { return y2 - y1; }
    float area()   const { return std::max(0.0f, width()) * std::max(0.0f, height()); }
};

// Letterbox transform: how to resize a (srcW x srcH) image into a
// (dstW x dstH) square keeping aspect ratio, with symmetric padding.
struct Letterbox {
    float scale;  // multiply source coords by this to get padded-image coords
    float pad_x;  // pixels of padding added on the left
    float pad_y;  // pixels of padding added on the top
};

inline Letterbox compute_letterbox(int srcW, int srcH, int dstW, int dstH) {
    const float scale = std::min(static_cast<float>(dstW) / srcW,
                                 static_cast<float>(dstH) / srcH);
    const float new_w = srcW * scale;
    const float new_h = srcH * scale;
    return Letterbox{scale, (dstW - new_w) / 2.0f, (dstH - new_h) / 2.0f};
}

// Map a box from letterboxed/model space back to original-image pixels.
inline Box undo_letterbox(const Box& b, const Letterbox& lb) {
    return Box{(b.x1 - lb.pad_x) / lb.scale,
               (b.y1 - lb.pad_y) / lb.scale,
               (b.x2 - lb.pad_x) / lb.scale,
               (b.y2 - lb.pad_y) / lb.scale};
}

// YOLOv8 head emits center-x, center-y, width, height.
inline Box xywh_to_xyxy(float cx, float cy, float w, float h) {
    return Box{cx - w / 2.0f, cy - h / 2.0f, cx + w / 2.0f, cy + h / 2.0f};
}

inline void xyxy_to_xywh(const Box& b, float& cx, float& cy, float& w, float& h) {
    cx = (b.x1 + b.x2) / 2.0f;
    cy = (b.y1 + b.y2) / 2.0f;
    w = b.width();
    h = b.height();
}

inline float iou(const Box& a, const Box& b) {
    const float ix1 = std::max(a.x1, b.x1);
    const float iy1 = std::max(a.y1, b.y1);
    const float ix2 = std::min(a.x2, b.x2);
    const float iy2 = std::min(a.y2, b.y2);
    const float iw = std::max(0.0f, ix2 - ix1);
    const float ih = std::max(0.0f, iy2 - iy1);
    const float inter = iw * ih;
    const float uni = a.area() + b.area() - inter;
    return uni > 0.0f ? inter / uni : 0.0f;
}

// Greedy non-maximum suppression. Returns indices of kept boxes, highest score
// first. boxes and scores must be the same length.
inline std::vector<size_t> nms(const std::vector<Box>& boxes,
                               const std::vector<float>& scores,
                               float iou_thresh) {
    std::vector<size_t> order(boxes.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::sort(order.begin(), order.end(),
              [&](size_t a, size_t b) { return scores[a] > scores[b]; });

    std::vector<size_t> keep;
    std::vector<bool> removed(boxes.size(), false);
    for (size_t i = 0; i < order.size(); ++i) {
        const size_t idx = order[i];
        if (removed[idx]) continue;
        keep.push_back(idx);
        for (size_t j = i + 1; j < order.size(); ++j) {
            const size_t other = order[j];
            if (!removed[other] && iou(boxes[idx], boxes[other]) > iou_thresh)
                removed[other] = true;
        }
    }
    return keep;
}

}  // namespace uas
