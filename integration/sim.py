"""Pure kinematic closed-loop simulator for the perception->control law.

Validates that ``decision.decide`` actually drives a vehicle to center a target
and hold a standoff distance — without any camera, MAVLink, or PX4. It is the
*inverse* of the perception step: it places a target in the world, projects it
into a synthetic bounding box (a forward pinhole camera model), feeds that
through the real ``decide()``, then integrates the returned body-velocity command
to advance the vehicle and repeats.

No cv2 / mavsdk / numpy — plain math and the pure ``decision`` module, so the
whole loop runs in CI. See ``sim_run.py`` for a CLI and ``tests/test_sim.py``.

Frames: world is right-handed with yaw measured from +x toward +y. The camera
looks along the vehicle's body +x (forward); body +y is left.
"""

import math
from dataclasses import dataclass

import decision
from decision import (DecisionConfig, SearchState, next_search_state,
                     focal_px_from_hfov, CLASS_REAL_HEIGHTS)


@dataclass
class VehicleState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0   # radians, 0 = facing +x


@dataclass
class Target:
    x: float
    y: float
    z: float = 0.0
    class_id: int = 0

    @property
    def real_height_m(self):
        return CLASS_REAL_HEIGHTS.get(self.class_id, 1.7)


def project_target_to_bbox(vehicle: VehicleState, target: Target,
                           frame_w, frame_h, hfov_deg):
    """Project a world target into a synthetic pixel bbox, or None if it is
    behind the camera or outside the horizontal field of view.

    Returns ``(cls_id, conf, x1, y1, x2, y2)`` — the same detection tuple the
    real detector emits — so it can be fed straight into ``decide``.
    """
    # Vector to target in world, rotated into the body frame by -yaw.
    dxw = target.x - vehicle.x
    dyw = target.y - vehicle.y
    dz = target.z - vehicle.z
    cos_y, sin_y = math.cos(vehicle.yaw), math.sin(vehicle.yaw)
    forward = dxw * cos_y + dyw * sin_y
    lateral = -dxw * sin_y + dyw * cos_y   # +left

    if forward <= 0:
        return None   # behind the camera

    theta = math.degrees(math.atan2(lateral, forward))   # +left, -right
    if abs(theta) > hfov_deg / 2.0:
        return None   # outside horizontal FOV

    # +theta is to the LEFT, but image x grows to the RIGHT -> negate.
    dx_norm = -theta / (hfov_deg / 2.0)
    cx = (dx_norm + 1.0) / 2.0 * frame_w

    rng = math.sqrt(forward * forward + lateral * lateral + dz * dz)
    focal = focal_px_from_hfov(frame_w, hfov_deg)
    px_h = target.real_height_m * focal / rng
    px_w = px_h * 0.45   # plausible aspect; only the height drives distance

    # Vertical placement from elevation angle (small for level flight).
    horiz = math.sqrt(forward * forward + lateral * lateral)
    phi = math.degrees(math.atan2(dz, horiz))
    vfov = hfov_deg * frame_h / frame_w
    cy = (1.0 - phi / (vfov / 2.0)) / 2.0 * frame_h

    x1 = cx - px_w / 2.0
    x2 = cx + px_w / 2.0
    y1 = cy - px_h / 2.0
    y2 = cy + px_h / 2.0
    return (target.class_id, 1.0, x1, y1, x2, y2)


def step(vehicle: VehicleState, velocity_cmd, dt) -> VehicleState:
    """Advance the vehicle one tick given a body-frame (vx, vy, yaw_rate).

    ``yaw_rate`` follows the controller/PX4 convention (positive = clockwise /
    turn toward a target on the image's right). World yaw here is measured
    counter-clockwise from +x, so a positive command *decreases* yaw.
    """
    vx, vy, yaw_rate = velocity_cmd
    new_yaw = vehicle.yaw - yaw_rate * dt
    cos_y, sin_y = math.cos(new_yaw), math.sin(new_yaw)
    # Rotate body velocity (forward, left) into the world frame.
    wvx = vx * cos_y - vy * sin_y
    wvy = vx * sin_y + vy * cos_y
    return VehicleState(
        x=vehicle.x + wvx * dt,
        y=vehicle.y + wvy * dt,
        z=vehicle.z,
        yaw=new_yaw,
    )


@dataclass
class SimRecord:
    t: float
    x: float
    y: float
    yaw: float
    action: str
    bearing_deg: float
    distance_m: float
    velocity_cmd: tuple


def simulate(vehicle: VehicleState, target: Target, config: DecisionConfig,
             steps=200, dt=0.1, frame_w=640, frame_h=480):
    """Run the closed loop and return a list of SimRecord.

    The velocity command is applied directly each tick — this exercises the
    control law itself; the SafetyGate is validated separately in
    test_decision_logic. With the target out of view the vehicle runs the same
    in-place yaw scan the node uses (via ``decide`` + ``SearchState``), so this
    loop models reacquire, not just hold.
    """
    trajectory = []
    search_state = SearchState()
    for i in range(steps):
        det = project_target_to_bbox(vehicle, target, frame_w, frame_h,
                                     config.hfov_deg)
        detections = [det] if det is not None else []
        d = decision.decide(detections, (frame_w, frame_h), config, search_state)
        cmd = d.velocity_cmd if d.velocity_cmd is not None else (0.0, 0.0, 0.0)
        search_state = next_search_state(search_state, d)

        trajectory.append(SimRecord(
            t=i * dt, x=vehicle.x, y=vehicle.y, yaw=vehicle.yaw,
            action=d.action,
            bearing_deg=d.bearing_deg if d.bearing_deg is not None else float("nan"),
            distance_m=d.distance_m if d.distance_m is not None else float("nan"),
            velocity_cmd=cmd,
        ))
        vehicle = step(vehicle, cmd, dt)
    return trajectory
