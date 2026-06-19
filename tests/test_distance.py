import math

import pytest

import decision
from decision import (focal_px_from_hfov, estimate_distance, calibrate_focal,
                      hfov_from_focal, approach_velocity)


def test_focal_from_hfov_known():
    # 90 deg HFOV on a 640-wide frame: focal = 320 / tan(45) = 320.
    assert focal_px_from_hfov(640, 90.0) == pytest.approx(320.0)


def test_focal_hfov_roundtrip():
    f = focal_px_from_hfov(640, 60.0)
    assert hfov_from_focal(640, f) == pytest.approx(60.0)


def test_focal_rejects_bad_input():
    with pytest.raises(ValueError):
        focal_px_from_hfov(0, 60.0)
    with pytest.raises(ValueError):
        focal_px_from_hfov(640, 200.0)


def test_distance_inverse_with_pixel_height():
    focal = 500.0
    near = estimate_distance(bbox_px_height=400, real_height_m=2.0, focal_px=focal)
    far = estimate_distance(bbox_px_height=200, real_height_m=2.0, focal_px=focal)
    # Half the pixel height -> twice the distance.
    assert far == pytest.approx(2 * near)


def test_distance_degenerate_returns_none():
    assert estimate_distance(0, 1.7, 500) is None
    assert estimate_distance(-5, 1.7, 500) is None


def test_calibrate_focal_is_inverse_of_estimate():
    # An object spanning 380 px, 1.7 m tall, at 3 m.
    focal = calibrate_focal(380, 1.7, 3.0)
    assert estimate_distance(380, 1.7, focal) == pytest.approx(3.0)


def test_approach_velocity_sign_and_deadband():
    # Far from standoff -> move forward (+).
    assert approach_velocity(5.0, 2.0, gain=0.5, max_speed=2.0) > 0
    # Closer than standoff -> back off (-).
    assert approach_velocity(1.0, 2.0, gain=0.5, max_speed=2.0) < 0
    # Within deadband -> zero.
    assert approach_velocity(2.1, 2.0, gain=0.5, max_speed=2.0, deadband=0.3) == 0.0


def test_approach_velocity_clamped():
    v = approach_velocity(100.0, 2.0, gain=1.0, max_speed=1.5)
    assert v == pytest.approx(1.5)


def test_class_real_heights_present():
    assert decision.CLASS_REAL_HEIGHTS[0] > 0
    assert decision.CLASS_REAL_HEIGHTS[1] > 0
