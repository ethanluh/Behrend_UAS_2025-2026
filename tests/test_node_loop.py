"""Headless integration test for the perception->decision->control loop.

Drives perception_control_node.run() with stub source/detector (no camera,
cv2, ultralytics, or MAVLink) and reads the JSONL log it writes. cv2 is never
imported because --show/--record are off, so this runs on a clean CI machine.
"""

import argparse
import asyncio
import json

import perception_control_node as node


class FakeFrame:
    """Stand-in for a cv2 frame — the loop only needs ``.shape``."""
    def __init__(self, h=480, w=640):
        self.shape = (h, w, 3)


class FakeSource:
    def __init__(self, n):
        self._remaining = n

    def read(self):
        if self._remaining <= 0:
            return None
        self._remaining -= 1
        return FakeFrame()

    def release(self):
        pass


class FakeDetector:
    """Returns a scripted list of detections per frame, in order."""
    def __init__(self, scripted):
        self._scripted = list(scripted)
        self._i = 0

    def detect(self, frame):
        dets = self._scripted[self._i] if self._i < len(self._scripted) else []
        self._i += 1
        return dets


class FakeController:
    """Records the commands the loop would send; always reports armed."""
    def __init__(self):
        self.armed = True
        self.sends = []
        self.holds = 0

    async def send_velocity(self, vx, vy, yaw):
        self.sends.append((vx, vy, yaw))

    async def hold(self):
        self.holds += 1

    async def stop(self):
        pass


def _args(log_file, enable_control=False, max_stale_frames=5):
    return argparse.Namespace(
        weights="unused", source="unused", mavlink="unused",
        target_class="mannequin", hfov=60.0, conf=0.25,
        enable_control=enable_control, max_speed=1.0,
        max_stale_frames=max_stale_frames,
        show=False, record=None, log_file=log_file,
    )


def test_loop_transitions_and_no_commands(tmp_path):
    log_file = tmp_path / "run.jsonl"
    # frame0: nothing -> search; frame1: centered mannequin -> track; frame2: nothing -> search
    centered_mannequin = (0, 0.9, 300, 200, 340, 280)
    detector = FakeDetector([[], [centered_mannequin], []])
    source = FakeSource(n=3)

    asyncio.run(node.run(_args(str(log_file)), source=source, detector=detector))

    records = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert [r["action"] for r in records] == ["search", "track", "search"]
    # Control disabled -> nothing is ever sent.
    assert all(r["command_sent"] is False for r in records)
    # The track frame carries a finite range estimate.
    track = records[1]
    assert track["distance_m"] is not None and track["distance_m"] > 0


def test_reacquired_track_after_long_search_is_commanded(tmp_path):
    # 7 empty frames (> max_stale_frames=5) build up a stale search count, then
    # a centered mannequin reacquires. The track frame must be commanded, not
    # gated off as stale — the search state is advanced before the gate check.
    log_file = tmp_path / "reacq.jsonl"
    centered_mannequin = (0, 0.9, 300, 200, 340, 280)
    detector = FakeDetector([[]] * 7 + [[centered_mannequin]])
    source = FakeSource(n=8)
    controller = FakeController()

    asyncio.run(node.run(_args(str(log_file), enable_control=True),
                         source=source, detector=detector, controller=controller))

    records = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert records[-1]["action"] == "track"
    assert records[-1]["command_sent"] is True      # reacquire not gated off
    # The track command (nonzero forward approach) was forwarded — search
    # commands are yaw-only with vx == 0, so this confirms it was the track one.
    assert controller.sends[-1][0] != 0.0


def test_loop_handles_empty_stream(tmp_path):
    log_file = tmp_path / "empty.jsonl"
    asyncio.run(node.run(_args(str(log_file)),
                         source=FakeSource(n=0), detector=FakeDetector([])))
    assert log_file.read_text() == ""
