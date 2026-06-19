"""Pure perception->decision logic for the autonomous navigation loop.

No cv2 / mavsdk / ultralytics imports — everything here is plain math and a
small state machine, so it is fully unit-testable. The node
(``perception_control_node.py``) feeds detections in and turns the returned
``Decision`` into MAVLink commands.

Convention: a detection is ``(cls_id, conf, x1, y1, x2, y2)`` in pixels.
Normalized offsets are in [-1, 1]: 0 = centered, +x = target is to the right,
+y = target is below center.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Detection = Tuple[int, float, float, float, float, float]

# Class id -> name, matching ObjectDetection (0 = mannequin, 1 = tent).
CLASS_NAMES_DEFAULT = ["mannequin", "tent"]

# Approximate real-world heights (meters) used for monocular range estimation.
CLASS_REAL_HEIGHTS = {0: 1.7, 1: 1.5}


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


# ── Monocular distance estimation ──────────────────────────────────────────

def focal_px_from_hfov(frame_w, hfov_deg):
    """Pinhole focal length in pixels from image width and horizontal FOV."""
    if frame_w <= 0 or not 0 < hfov_deg < 180:
        raise ValueError("frame_w must be > 0 and hfov in (0, 180)")
    return (frame_w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)


def estimate_distance(bbox_px_height, real_height_m, focal_px):
    """Distance (m) to an object of known real height from its pixel height.

    Pinhole model: distance = real_height * focal / pixel_height. Returns None
    for a non-positive pixel height (degenerate / off-screen box).
    """
    if bbox_px_height <= 0:
        return None
    return (real_height_m * focal_px) / bbox_px_height


def calibrate_focal(bbox_px_height, real_height_m, known_distance_m):
    """Solve for focal length (px) from an object of known size at a known
    distance — the inverse of ``estimate_distance``, for HFOV calibration."""
    if known_distance_m <= 0 or real_height_m <= 0:
        raise ValueError("distances and sizes must be positive")
    return bbox_px_height * known_distance_m / real_height_m


def hfov_from_focal(frame_w, focal_px):
    """Recover horizontal FOV (deg) from a calibrated focal length."""
    return math.degrees(2.0 * math.atan((frame_w / 2.0) / focal_px))


def approach_velocity(distance_m, standoff_m, gain, max_speed, deadband=0.3):
    """Signed forward speed (m/s) to drive toward a target standoff distance.

    Positive = move forward (target farther than standoff), negative = back off.
    Zero within ``deadband`` meters of the standoff. Clamped to ``max_speed``.
    """
    error = distance_m - standoff_m
    if abs(error) < deadband:
        return 0.0
    return _clamp(error * gain, -max_speed, max_speed)


# ── Proportional control ───────────────────────────────────────────────────

@dataclass
class ControlGains:
    yaw: float = 1.0      # rad/s per unit normalized x-offset
    forward: float = 0.5  # m/s per unit normalized y-offset (fallback term)
    approach: float = 0.5  # m/s per meter of standoff error
    deadzone: float = 0.05
    max_speed: float = 1.0      # m/s clamp on forward velocity
    max_yaw_rate: float = 0.8   # rad/s clamp on yaw rate
    scan_yaw_rate: float = 0.4  # rad/s in-place yaw sweep while searching


def pixel_to_velocity_cmd(dx_norm, dy_norm, gains: ControlGains, distance_m=None,
                          standoff_m=2.0):
    """Map a normalized offset to a clamped (vx, vy, yaw_rate) body command.

    Yaw turns the vehicle to face the target (driven by x-offset). Forward speed
    (vx) drives toward ``standoff_m`` when a range estimate is available
    (``distance_m``); otherwise it falls back to the y-offset term. vy is left at
    0 — yaw + forward is enough to center and approach a target predictably.
    """
    yaw_rate = 0.0 if abs(dx_norm) < gains.deadzone else dx_norm * gains.yaw
    if distance_m is not None:
        vx = approach_velocity(distance_m, standoff_m, gains.approach, gains.max_speed)
    else:
        vx = 0.0 if abs(dy_norm) < gains.deadzone else dy_norm * gains.forward
    yaw_rate = _clamp(yaw_rate, -gains.max_yaw_rate, gains.max_yaw_rate)
    vx = _clamp(vx, -gains.max_speed, gains.max_speed)
    return vx, 0.0, yaw_rate


def search_velocity_cmd(direction, gains: ControlGains):
    """Body command for an in-place yaw scan while no target is visible.

    Yaw-only (no translation), so an unlocalized search can never drive the
    vehicle into anything. ``direction`` is the sign to scan toward (+1 = right,
    matching ``bearing_deg``); the rate is clamped by ``max_yaw_rate``.
    """
    sign = 1.0 if direction >= 0 else -1.0
    yaw_rate = _clamp(sign * gains.scan_yaw_rate,
                      -gains.max_yaw_rate, gains.max_yaw_rate)
    return 0.0, 0.0, yaw_rate


# ── Safety gate ────────────────────────────────────────────────────────────

@dataclass
class SafetyGate:
    """Decides whether a motion command may be sent to the vehicle.

    The vehicle must always be armed and the operator must have explicitly
    enabled control. Beyond that, the gate depends on ``action``:

    - ``"track"`` additionally requires a fresh detection (not stale) — a
      command driving *toward* a target must be based on a recent sighting.
    - ``"search"`` is allowed without a fresh detection: it is a stationary
      yaw scan, safe to run while looking for a lost target.
    - ``"hold"`` (and anything else) is never sent.
    """
    max_stale_frames: int = 5

    def should_command(self, armed, control_enabled, frames_since_detection,
                       action="track"):
        if not control_enabled:
            return False
        if not armed:
            return False
        if action == "search":
            return True
        if action != "track":
            return False
        if frames_since_detection > self.max_stale_frames:
            return False
        return True


# ── Top-level decision ─────────────────────────────────────────────────────

@dataclass
class DecisionConfig:
    target_class: int = 0           # 0 = mannequin
    hfov_deg: float = 60.0
    standoff_m: float = 2.0         # desired distance to hold from the target
    max_search_frames: int = 80     # frames to scan before giving up (~8s @ 10Hz)
    gains: ControlGains = field(default_factory=ControlGains)


@dataclass
class SearchState:
    """Caller-held state that drives the search scan, kept out of ``decide`` so
    that ``decide`` stays a pure function of its inputs.

    ``frames_since_detection`` counts frames since the target was last tracked;
    ``last_bearing_sign`` is the side it was last seen on (+1 right, -1 left), so
    the scan sweeps back toward it. Defaults: never seen, scan right.
    """
    frames_since_detection: int = 0
    last_bearing_sign: float = 1.0


def next_search_state(state: SearchState, decision: "Decision") -> SearchState:
    """Advance the search state from the latest decision (shared by node + sim)."""
    if decision.action == "track":
        sign = 1.0 if (decision.bearing_deg or 0.0) >= 0 else -1.0
        return SearchState(frames_since_detection=0, last_bearing_sign=sign)
    return SearchState(frames_since_detection=state.frames_since_detection + 1,
                       last_bearing_sign=state.last_bearing_sign)


@dataclass
class Decision:
    action: str                                  # "search" | "track" | "hold"
    bearing_deg: Optional[float] = None
    offset: Optional[Tuple[float, float]] = None
    distance_m: Optional[float] = None
    velocity_cmd: Optional[Tuple[float, float, float]] = None
    reason: str = ""


def select_target(detections: List[Detection], target_class: int) -> Optional[Detection]:
    """Highest-confidence detection of the target class, or None."""
    candidates = [d for d in detections if d[0] == target_class]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d[1])


def decide(detections, frame_size, config: DecisionConfig,
           search_state: Optional[SearchState] = None) -> Decision:
    """Turn a frame's detections into a Decision (offset/bearing/velocity).

    With a target visible, returns a ``track`` decision. With none visible it
    returns a ``search`` decision carrying an in-place yaw-scan command (toward
    the side the target was last seen, via ``search_state``) until
    ``max_search_frames`` frames have elapsed, after which it gives up and
    returns ``hold`` (zero command) so the vehicle never spins forever.

    Whether a command is actually *sent* remains the caller's responsibility via
    ``SafetyGate``.
    """
    frame_w, frame_h = frame_size
    target = select_target(detections, config.target_class)
    if target is None:
        state = search_state if search_state is not None else SearchState()
        if state.frames_since_detection > config.max_search_frames:
            return Decision(action="hold", velocity_cmd=(0.0, 0.0, 0.0),
                            reason="search timeout")
        scan = search_velocity_cmd(state.last_bearing_sign, config.gains)
        return Decision(action="search", velocity_cmd=scan,
                        reason="scanning for target")

    cls_id, conf, x1, y1, x2, y2 = target
    cx, cy = box_center(x1, y1, x2, y2)
    dx, dy = target_offset(cx, cy, frame_w, frame_h)
    bearing = bearing_deg(dx, config.hfov_deg)

    # Monocular range estimate from the box height and the class's real height.
    focal = focal_px_from_hfov(frame_w, config.hfov_deg)
    real_h = CLASS_REAL_HEIGHTS.get(cls_id)
    distance = (estimate_distance(y2 - y1, real_h, focal)
                if real_h is not None else None)

    vel = pixel_to_velocity_cmd(dx, dy, config.gains, distance, config.standoff_m)

    return Decision(
        action="track",
        bearing_deg=bearing,
        offset=(dx, dy),
        distance_m=distance,
        velocity_cmd=vel,
        reason=f"tracking target conf={conf:.2f}",
    )
