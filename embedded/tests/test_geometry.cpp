// Unit tests for geometry.hpp. No OpenCV / ONNX Runtime dependency, so this
// target always builds and runs in CI.
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

#include "geometry.hpp"

using namespace uas;

static bool close(float a, float b, float eps = 1e-4f) {
    return std::fabs(a - b) < eps;
}

static void test_xywh_roundtrip() {
    Box b = xywh_to_xyxy(50.0f, 60.0f, 20.0f, 40.0f);
    assert(close(b.x1, 40.0f) && close(b.y1, 40.0f));
    assert(close(b.x2, 60.0f) && close(b.y2, 80.0f));
    float cx, cy, w, h;
    xyxy_to_xywh(b, cx, cy, w, h);
    assert(close(cx, 50.0f) && close(cy, 60.0f));
    assert(close(w, 20.0f) && close(h, 40.0f));
}

static void test_letterbox_landscape() {
    // 1280x720 into 640x640: scale 0.5, no x-pad, vertical padding.
    Letterbox lb = compute_letterbox(1280, 720, 640, 640);
    assert(close(lb.scale, 0.5f));
    assert(close(lb.pad_x, 0.0f));
    assert(close(lb.pad_y, (640 - 360) / 2.0f));
    // A box in model space maps back to original pixels.
    Box model{lb.pad_x, lb.pad_y, lb.pad_x + 100, lb.pad_y + 100};
    Box orig = undo_letterbox(model, lb);
    assert(close(orig.x1, 0.0f) && close(orig.y1, 0.0f));
    assert(close(orig.x2, 200.0f) && close(orig.y2, 200.0f));
}

static void test_iou() {
    Box a{0, 0, 10, 10};
    Box b{0, 0, 10, 10};
    assert(close(iou(a, b), 1.0f));
    Box c{20, 20, 30, 30};
    assert(close(iou(a, c), 0.0f));
    Box d{5, 0, 15, 10};            // overlaps half of a
    assert(close(iou(a, d), 50.0f / 150.0f));
}

static void test_nms() {
    std::vector<Box> boxes = {
        {0, 0, 10, 10},   // highest score, kept
        {1, 1, 11, 11},   // big overlap -> suppressed
        {100, 100, 110, 110},  // disjoint -> kept
    };
    std::vector<float> scores = {0.9f, 0.8f, 0.7f};
    auto keep = nms(boxes, scores, 0.5f);
    assert(keep.size() == 2);
    assert(keep[0] == 0);
    assert(keep[1] == 2);
}

int main() {
    test_xywh_roundtrip();
    test_letterbox_landscape();
    test_iou();
    test_nms();
    std::printf("all geometry tests passed\n");
    return 0;
}
