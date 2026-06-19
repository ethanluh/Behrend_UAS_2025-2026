import math

import pytest

from decision import DecisionConfig, ControlGains, estimate_distance, CLASS_REAL_HEIGHTS
from sim import VehicleState, Target, project_target_to_bbox, step, simulate

FRAME_W, FRAME_H, HFOV = 640, 480, 60.0


def _bbox_center_x(bbox):
    return (bbox[2] + bbox[4]) / 2.0


# ── Forward camera model ───────────────────────────────────────────────────

def test_target_straight_ahead_is_centered():
    veh = VehicleState(x=0, y=0, yaw=0.0)        # facing +x
    tgt = Target(x=5, y=0)                        # directly ahead
    bbox = project_target_to_bbox(veh, tgt, FRAME_W, FRAME_H, HFOV)
    assert bbox is not None
    assert _bbox_center_x(bbox) == pytest.approx(FRAME_W / 2, abs=1.0)


def test_target_to_the_right_projects_right():
    veh = VehicleState(x=0, y=0, yaw=0.0)
    tgt = Target(x=5, y=-2)                        # to the vehicle's right (-y)
    bbox = project_target_to_bbox(veh, tgt, FRAME_W, FRAME_H, HFOV)
    assert bbox is not None
    assert _bbox_center_x(bbox) > FRAME_W / 2


def test_target_behind_returns_none():
    veh = VehicleState(x=0, y=0, yaw=0.0)
    tgt = Target(x=-5, y=0)                        # behind
    assert project_target_to_bbox(veh, tgt, FRAME_W, FRAME_H, HFOV) is None


def test_target_outside_fov_returns_none():
    veh = VehicleState(x=0, y=0, yaw=0.0)
    tgt = Target(x=1, y=-5)                        # ~79deg off axis, hfov/2=30
    assert project_target_to_bbox(veh, tgt, FRAME_W, FRAME_H, HFOV) is None


def test_projected_height_round_trips_to_range():
    veh = VehicleState(x=0, y=0, yaw=0.0)
    tgt = Target(x=6, y=0, class_id=0)
    bbox = project_target_to_bbox(veh, tgt, FRAME_W, FRAME_H, HFOV)
    px_h = bbox[5] - bbox[3]
    from decision import focal_px_from_hfov
    focal = focal_px_from_hfov(FRAME_W, HFOV)
    est = estimate_distance(px_h, CLASS_REAL_HEIGHTS[0], focal)
    assert est == pytest.approx(6.0, rel=1e-3)


# ── Integration ────────────────────────────────────────────────────────────

def test_step_moves_forward_along_heading():
    veh = VehicleState(x=0, y=0, yaw=0.0)
    moved = step(veh, (1.0, 0.0, 0.0), dt=1.0)    # 1 m/s forward, facing +x
    assert moved.x == pytest.approx(1.0)
    assert moved.y == pytest.approx(0.0)


# ── Closed-loop behavior ───────────────────────────────────────────────────

def _config(standoff=2.0):
    return DecisionConfig(target_class=0, hfov_deg=HFOV, standoff_m=standoff,
                          gains=ControlGains())


def test_converges_to_centered_standoff():
    # Target starts visible but off-center (~15deg right) and far (~8 m).
    veh = VehicleState(x=-8.0, y=0.0, yaw=math.radians(15))
    tgt = Target(x=0.0, y=0.0, class_id=0)
    traj = simulate(veh, tgt, _config(standoff=2.0), steps=400, dt=0.1)

    # Must actually have seen the target.
    assert any(r.action == "track" for r in traj)
    final = traj[-1]
    assert final.action == "track"
    # Centered and at standoff.
    assert abs(final.bearing_deg) < 3.0
    assert final.distance_m == pytest.approx(2.0, abs=0.5)


def test_bearing_magnitude_decreases_overall():
    veh = VehicleState(x=-8.0, y=0.0, yaw=math.radians(18))
    tgt = Target(x=0.0, y=0.0, class_id=0)
    traj = [r for r in simulate(veh, tgt, _config(), steps=400, dt=0.1)
            if r.action == "track"]
    assert len(traj) > 1
    assert abs(traj[-1].bearing_deg) < abs(traj[0].bearing_deg)


def test_stable_when_started_at_standoff_centered():
    # Place the vehicle 2 m from the target, already facing it.
    veh = VehicleState(x=-2.0, y=0.0, yaw=0.0)
    tgt = Target(x=0.0, y=0.0, class_id=0)
    traj = simulate(veh, tgt, _config(standoff=2.0), steps=50, dt=0.1)
    # Within deadbands -> essentially no commanded motion, range stays put.
    assert all(r.action == "track" for r in traj)
    assert traj[-1].distance_m == pytest.approx(2.0, abs=0.3)
    max_speed = max(abs(r.velocity_cmd[0]) for r in traj)
    assert max_speed < 0.1


def test_reacquires_target_out_of_fov():
    # Target starts ~45deg to the right (hfov/2 = 30deg) -> out of view. The
    # default scan sweeps right, should bring it into frame, then track it in.
    veh = VehicleState(x=0.0, y=0.0, yaw=0.0)
    tgt = Target(x=4.0, y=-4.0, class_id=0)
    traj = simulate(veh, tgt, _config(standoff=2.0), steps=600, dt=0.1)

    assert traj[0].action == "search"           # not visible at the start
    assert any(r.action == "search" for r in traj[:30])
    assert any(r.action == "track" for r in traj)   # reacquired
    final = traj[-1]
    assert final.action == "track"
    assert abs(final.bearing_deg) < 3.0
    assert final.distance_m == pytest.approx(2.0, abs=0.5)


def test_search_scans_in_place_then_holds():
    # Target directly behind and a short give-up bound -> never reacquired.
    veh = VehicleState(x=0.0, y=0.0, yaw=0.0)
    tgt = Target(x=-5.0, y=0.0, class_id=0)
    cfg = DecisionConfig(target_class=0, hfov_deg=HFOV, max_search_frames=10,
                         gains=ControlGains())
    traj = simulate(veh, tgt, cfg, steps=20, dt=0.1)

    # A scan is yaw-only: position never changes, but heading sweeps.
    assert all(r.x == 0.0 and r.y == 0.0 for r in traj)
    assert traj[-1].yaw != traj[0].yaw
    # First it searches, then gives up and holds (no infinite spin).
    assert traj[0].action == "search"
    assert traj[-1].action == "hold"
    assert traj[-1].velocity_cmd == (0.0, 0.0, 0.0)
