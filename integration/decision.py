"""Pure perception->decision logic for the autonomous navigation loop.

No cv2 / mavsdk / ultralytics imports — everything here is plain math and a
small state machine, so it is fully unit-testable. The node
(``perception_control_node.py``) feeds detections in and turns the returned
``Decision`` into MAVLink commands.

Convention: a detection is ``(cls_id, conf, x1, y1, x2, y2)`` in pixels.
Normalized offsets are in [-1, 1]: 0 = centered, +x = target is to the right,
+y = target is below center.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Detection = Tuple[int, float, float, float, float, float]

# Class id -> name, matching ObjectDetection (0 = mannequin, 1 = tent).
CLASS_NAMES_DEFAULT = ["mannequin", "tent"]


# ── Geometry helpers ───────────────────────────────────────────────────────

def box_center(x1, y1, x2, y2):
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def target_offset(cx, cy, frame_w, frame_h):
    """Normalized offset of a pixel point from frame center, in [-1, 1]."""
    if frame_w <= 0 or frame_h <= 0:
        raise ValueError("frame dimensions must be positive")
    dx = (cx - frame_w / 2.0) / (frame_w / 2.0)
    dy = (cy - frame_h / 2.0) / (frame_h / 2.0)
    return _clamp(dx, -1.0, 1.0), _clamp(dy, -1.0, 1.0)


def bearing_deg(dx_norm, hfov_deg=60.0):
    """Signed horizontal bearing to the target from frame center.

    Negative = left, positive = right. Linear approximation across the FOV,
    which is plenty for centering a target.
    """
    return dx_norm * (hfov_deg / 2.0)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ── Proportional control ───────────────────────────────────────────────────

@dataclass
class ControlGains:
    yaw: float = 1.0      # rad/s per unit normalized x-offset
    forward: float = 0.5  # m/s per unit normalized y-offset
    deadzone: float = 0.05
    max_speed: float = 1.0      # m/s clamp on forward velocity
    max_yaw_rate: float = 0.8   # rad/s clamp on yaw rate


def pixel_to_velocity_cmd(dx_norm, dy_norm, gains: ControlGains):
    """Map a normalized offset to a clamped (vx, vy, yaw_rate) body command.

    Within the deadzone the corresponding axis returns 0. Yaw turns the vehicle
    to face the target (driven by x-offset); vx nudges forward when the target
    sits low/far in frame (driven by y-offset). vy is left at 0 — yaw+forward
    is enough to center and approach a target and keeps behavior predictable.
    """
    yaw_rate = 0.0 if abs(dx_norm) < gains.deadzone else dx_norm * gains.yaw
    vx = 0.0 if abs(dy_norm) < gains.deadzone else dy_norm * gains.forward
    yaw_rate = _clamp(yaw_rate, -gains.max_yaw_rate, gains.max_yaw_rate)
    vx = _clamp(vx, -gains.max_speed, gains.max_speed)
    return vx, 0.0, yaw_rate


# ── Safety gate ────────────────────────────────────────────────────────────

@dataclass
class SafetyGate:
    """Decides whether a motion command may be sent to the vehicle.

    All conditions must hold: the vehicle is armed, the operator has explicitly
    enabled control, and the most recent detection is fresh (not stale).
    """
    max_stale_frames: int = 5

    def should_command(self, armed, control_enabled, frames_since_detection):
        if not control_enabled:
            return False
        if not armed:
            return False
        if frames_since_detection > self.max_stale_frames:
            return False
        return True


# ── Top-level decision ─────────────────────────────────────────────────────

@dataclass
class DecisionConfig:
    target_class: int = 0           # 0 = mannequin
    hfov_deg: float = 60.0
    gains: ControlGains = field(default_factory=ControlGains)


@dataclass
class Decision:
    action: str                                  # "search" | "track" | "hold"
    bearing_deg: Optional[float] = None
    offset: Optional[Tuple[float, float]] = None
    velocity_cmd: Optional[Tuple[float, float, float]] = None
    reason: str = ""


def select_target(detections: List[Detection], target_class: int) -> Optional[Detection]:
    """Highest-confidence detection of the target class, or None."""
    candidates = [d for d in detections if d[0] == target_class]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d[1])


def decide(detections, frame_size, config: DecisionConfig) -> Decision:
    """Turn a frame's detections into a Decision (offset/bearing/velocity).

    Always computes the velocity command for the selected target; whether it is
    actually *sent* is the caller's responsibility via ``SafetyGate``.
    """
    frame_w, frame_h = frame_size
    target = select_target(detections, config.target_class)
    if target is None:
        return Decision(action="search", reason="no target detected")

    _, conf, x1, y1, x2, y2 = target
    cx, cy = box_center(x1, y1, x2, y2)
    dx, dy = target_offset(cx, cy, frame_w, frame_h)
    bearing = bearing_deg(dx, config.hfov_deg)
    vel = pixel_to_velocity_cmd(dx, dy, config.gains)

    return Decision(
        action="track",
        bearing_deg=bearing,
        offset=(dx, dy),
        velocity_cmd=vel,
        reason=f"tracking target conf={conf:.2f}",
    )
