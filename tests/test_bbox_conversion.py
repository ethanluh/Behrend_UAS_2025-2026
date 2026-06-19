import pytest

import od_lib


def test_centered_box():
    # A 100x100 box centered in a 640x640 image.
    cx, cy, w, h = od_lib.xyxy_to_yolo(270, 270, 370, 370, 640, 640)
    assert cx == pytest.approx(0.5)
    assert cy == pytest.approx(0.5)
    assert w == pytest.approx(100 / 640)
    assert h == pytest.approx(100 / 640)


def test_full_frame_box():
    cx, cy, w, h = od_lib.xyxy_to_yolo(0, 0, 640, 480, 640, 480)
    assert (cx, cy, w, h) == pytest.approx((0.5, 0.5, 1.0, 1.0))


def test_roundtrip():
    img_w, img_h = 640, 640
    for box in [(10, 20, 110, 220), (300, 300, 500, 600), (0, 0, 640, 640)]:
        cx, cy, w, h = od_lib.xyxy_to_yolo(*box, img_w, img_h)
        x1, y1, x2, y2 = od_lib.yolo_to_xyxy(cx, cy, w, h, img_w, img_h)
        assert x1 == pytest.approx(box[0], abs=1)
        assert y1 == pytest.approx(box[1], abs=1)
        assert x2 == pytest.approx(box[2], abs=1)
        assert y2 == pytest.approx(box[3], abs=1)


def test_degenerate_box_rejected():
    with pytest.raises(ValueError):
        od_lib.xyxy_to_yolo(100, 100, 100, 200, 640, 640)  # zero width
    with pytest.raises(ValueError):
        od_lib.xyxy_to_yolo(100, 100, 200, 50, 640, 640)   # y2 < y1


def test_bad_image_dims_rejected():
    with pytest.raises(ValueError):
        od_lib.xyxy_to_yolo(0, 0, 10, 10, 0, 640)
    with pytest.raises(ValueError):
        od_lib.yolo_to_xyxy(0.5, 0.5, 0.1, 0.1, -1, 640)
