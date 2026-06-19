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


def _args(log_file):
    return argparse.Namespace(
        weights="unused", source="unused", mavlink="unused",
        target_class="mannequin", hfov=60.0, conf=0.25,
        enable_control=False, max_speed=1.0, max_stale_frames=5,
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


def test_loop_handles_empty_stream(tmp_path):
    log_file = tmp_path / "empty.jsonl"
    asyncio.run(node.run(_args(str(log_file)),
                         source=FakeSource(n=0), detector=FakeDetector([])))
    assert log_file.read_text() == ""
