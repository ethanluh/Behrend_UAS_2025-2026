import pytest

import od_lib


def test_flip_reflects_x_center_only():
    cx, cy, w, h = od_lib.flip_box_horizontal(0.25, 0.4, 0.1, 0.2)
    assert cx == pytest.approx(0.75)
    assert (cy, w, h) == pytest.approx((0.4, 0.1, 0.2))


def test_flip_is_its_own_inverse():
    box = (0.3, 0.6, 0.2, 0.15)
    once = od_lib.flip_box_horizontal(*box)
    twice = od_lib.flip_box_horizontal(*once)
    assert twice == pytest.approx(box)


def test_flip_centered_box_unchanged():
    assert od_lib.flip_box_horizontal(0.5, 0.5, 0.4, 0.4) == pytest.approx(
        (0.5, 0.5, 0.4, 0.4))


def test_clip_keeps_inbounds_box_unchanged():
    box = (0.5, 0.5, 0.2, 0.2)
    assert od_lib.clip_box(*box) == pytest.approx(box)


def test_clip_trims_overflowing_box():
    # box centered on the left edge, half hanging off-frame
    cx, cy, w, h = od_lib.clip_box(0.0, 0.5, 0.4, 0.2)
    assert cx == pytest.approx(0.1)   # clipped corners 0..0.2 -> center 0.1
    assert w == pytest.approx(0.2)
    assert cy == pytest.approx(0.5)
    assert h == pytest.approx(0.2)


def test_clip_fully_outside_yields_nonpositive_size():
    # box entirely past the right edge
    _, _, w, h = od_lib.clip_box(1.5, 0.5, 0.2, 0.2)
    assert w <= 0
