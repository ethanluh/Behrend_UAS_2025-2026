import pytest

import decision
from decision import (ControlGains, SafetyGate, DecisionConfig,
                      target_offset, bearing_deg, pixel_to_velocity_cmd, decide)


# ── offset / bearing ───────────────────────────────────────────────────────

def test_offset_centered_is_zero():
    dx, dy = target_offset(320, 320, 640, 640)
    assert dx == pytest.approx(0.0)
    assert dy == pytest.approx(0.0)


def test_offset_signs():
    dx, dy = target_offset(640, 0, 640, 480)   # right edge, top edge
    assert dx == pytest.approx(1.0)
    assert dy == pytest.approx(-1.0)


def test_bearing_symmetry_and_zero():
    assert bearing_deg(0.0, 60.0) == pytest.approx(0.0)
    assert bearing_deg(1.0, 60.0) == pytest.approx(30.0)
    assert bearing_deg(-1.0, 60.0) == pytest.approx(-30.0)


# ── velocity command ───────────────────────────────────────────────────────

def test_deadzone_returns_zero():
    g = ControlGains(deadzone=0.1)
    vx, vy, yaw = pixel_to_velocity_cmd(0.05, 0.05, g)
    assert (vx, vy, yaw) == (0.0, 0.0, 0.0)


def test_command_sign():
    g = ControlGains(deadzone=0.01)
    _, _, yaw = pixel_to_velocity_cmd(0.5, 0.0, g)   # target to the right
    assert yaw > 0
    _, _, yaw = pixel_to_velocity_cmd(-0.5, 0.0, g)
    assert yaw < 0


def test_command_clamped():
    g = ControlGains(yaw=10.0, forward=10.0, deadzone=0.0,
                     max_speed=1.0, max_yaw_rate=0.8)
    vx, _, yaw = pixel_to_velocity_cmd(1.0, 1.0, g)
    assert vx == pytest.approx(1.0)
    assert yaw == pytest.approx(0.8)


# ── safety gate ────────────────────────────────────────────────────────────

def test_gate_blocks_when_control_disabled():
    g = SafetyGate(max_stale_frames=5)
    assert g.should_command(armed=True, control_enabled=False,
                            frames_since_detection=0) is False


def test_gate_blocks_when_not_armed():
    g = SafetyGate()
    assert g.should_command(armed=False, control_enabled=True,
                            frames_since_detection=0) is False


def test_gate_blocks_on_stale_detection():
    g = SafetyGate(max_stale_frames=3)
    assert g.should_command(armed=True, control_enabled=True,
                            frames_since_detection=10) is False


def test_gate_allows_when_all_conditions_met():
    g = SafetyGate(max_stale_frames=5)
    assert g.should_command(armed=True, control_enabled=True,
                            frames_since_detection=0) is True


# ── decide() orchestration ─────────────────────────────────────────────────

def test_decide_search_when_no_target():
    cfg = DecisionConfig(target_class=0)
    d = decide([], (640, 640), cfg)
    assert d.action == "search"
    assert d.velocity_cmd is None


def test_decide_tracks_target_class_only():
    cfg = DecisionConfig(target_class=0)
    # a tent (class 1) only -> no mannequin target -> search
    d = decide([(1, 0.9, 0, 0, 100, 100)], (640, 640), cfg)
    assert d.action == "search"


def test_decide_picks_highest_confidence():
    cfg = DecisionConfig(target_class=0)
    dets = [(0, 0.4, 0, 0, 50, 50), (0, 0.95, 300, 300, 340, 340)]
    d = decide(dets, (640, 640), cfg)
    assert d.action == "track"
    # the high-conf box is centered-ish -> small offset
    assert abs(d.offset[0]) < 0.1
    assert d.velocity_cmd is not None


def test_class_names_default_order():
    assert decision.CLASS_NAMES_DEFAULT == ["mannequin", "tent"]
