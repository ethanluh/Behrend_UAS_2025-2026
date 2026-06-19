import pytest

import decision
from decision import (ControlGains, SafetyGate, DecisionConfig, SearchState,
                      target_offset, bearing_deg, pixel_to_velocity_cmd, decide,
                      search_velocity_cmd, next_search_state)


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


def test_gate_allows_search_even_when_stale():
    # A stationary yaw scan needs no fresh detection, but still needs arm+enable.
    g = SafetyGate(max_stale_frames=3)
    assert g.should_command(armed=True, control_enabled=True,
                            frames_since_detection=99, action="search") is True
    assert g.should_command(armed=False, control_enabled=True,
                            frames_since_detection=0, action="search") is False
    assert g.should_command(armed=True, control_enabled=False,
                            frames_since_detection=0, action="search") is False


def test_gate_blocks_hold():
    g = SafetyGate()
    assert g.should_command(armed=True, control_enabled=True,
                            frames_since_detection=0, action="hold") is False


# ── decide() orchestration ─────────────────────────────────────────────────

def test_decide_search_when_no_target():
    cfg = DecisionConfig(target_class=0)
    d = decide([], (640, 640), cfg)
    assert d.action == "search"
    # Search drives a yaw-only scan: no translation, nonzero yaw.
    vx, vy, yaw = d.velocity_cmd
    assert (vx, vy) == (0.0, 0.0)
    assert yaw != 0.0


def test_search_scans_toward_last_seen_side():
    cfg = DecisionConfig(target_class=0)
    right = decide([], (640, 640), cfg, SearchState(1, last_bearing_sign=+1.0))
    left = decide([], (640, 640), cfg, SearchState(1, last_bearing_sign=-1.0))
    assert right.velocity_cmd[2] > 0      # scan right
    assert left.velocity_cmd[2] < 0       # scan left


def test_search_times_out_to_hold():
    cfg = DecisionConfig(target_class=0, max_search_frames=10)
    state = SearchState(frames_since_detection=11)
    d = decide([], (640, 640), cfg, state)
    assert d.action == "hold"
    assert d.velocity_cmd == (0.0, 0.0, 0.0)


def test_search_velocity_cmd_is_clamped_yaw_only():
    g = ControlGains(scan_yaw_rate=5.0, max_yaw_rate=0.8)
    vx, vy, yaw = search_velocity_cmd(+1, g)
    assert (vx, vy) == (0.0, 0.0)
    assert yaw == pytest.approx(0.8)      # clamped to max_yaw_rate
    assert search_velocity_cmd(-1, g)[2] == pytest.approx(-0.8)


def test_next_search_state_resets_on_track_and_counts_on_loss():
    from decision import Decision
    track = Decision(action="track", bearing_deg=-12.0)
    reset = next_search_state(SearchState(frames_since_detection=7), track)
    assert reset.frames_since_detection == 0
    assert reset.last_bearing_sign == -1.0   # last seen on the left
    lost = next_search_state(reset, Decision(action="search"))
    assert lost.frames_since_detection == 1
    assert lost.last_bearing_sign == -1.0    # remembers the side


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
