"""Perception -> decision -> control node.

Ties the YOLO detector (perception) to the decision logic and the Pixhawk
controller. By default it runs in OBSERVE mode: it detects the target, computes
the bearing/offset, and logs a corrective command WITHOUT moving the vehicle.

Motion is opt-in with ``--enable-control`` and is additionally gated by
``SafetyGate`` (vehicle armed + control enabled + a fresh detection). The
operator must arm the vehicle manually before any command is sent.

Examples:
    # Observe only (safe default) — prints bearing, sends nothing:
    python perception_control_node.py --weights best.pt --source 0

    # Closed-loop tracking (operator arms manually first):
    python perception_control_node.py --weights best.pt --source 0 \
        --mavlink serial:///dev/ttyACM0:57600 --enable-control
"""

import argparse
import asyncio
import json
import time

from decision import (DecisionConfig, ControlGains, SafetyGate, SearchState,
                      decide, next_search_state, select_target,
                      CLASS_NAMES_DEFAULT)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", required=True)
    p.add_argument("--source", default="0", help="camera index or video file path")
    p.add_argument("--mavlink", default="serial:///dev/ttyACM0:57600")
    p.add_argument("--target-class", default="mannequin",
                   choices=CLASS_NAMES_DEFAULT)
    p.add_argument("--hfov", type=float, default=60.0)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--enable-control", action="store_true",
                   help="allow sending velocity commands (default: observe only)")
    p.add_argument("--max-speed", type=float, default=1.0)
    p.add_argument("--max-stale-frames", type=int, default=5)
    p.add_argument("--show", action="store_true",
                   help="display an annotated preview window")
    p.add_argument("--record", default=None,
                   help="write an annotated video to this path (e.g. flight.mp4)")
    p.add_argument("--log-file", default=None,
                   help="append per-frame decision/telemetry records as JSONL")
    return p.parse_args()


async def run(args, *, source=None, detector=None, controller=None):
    """Run the perception->decision->control loop.

    ``source``/``detector``/``controller`` can be injected (e.g. by tests with
    stubs); when left ``None`` the real cv2/ultralytics/MAVSDK-backed objects
    are constructed from ``args``. Heavy imports stay inside this function.
    """
    target_class = CLASS_NAMES_DEFAULT.index(args.target_class)
    config = DecisionConfig(
        target_class=target_class,
        hfov_deg=args.hfov,
        gains=ControlGains(max_speed=args.max_speed),
    )
    gate = SafetyGate(max_stale_frames=args.max_stale_frames)

    if detector is None:
        from detector import Detector
        detector = Detector(args.weights, conf=args.conf)
    if source is None:
        from camera import FrameSource
        source = FrameSource(args.source)

    if args.enable_control and controller is None:
        from control import Controller
        controller = Controller(args.mavlink)
        await controller.connect()
        if not await controller.read_armed_once():
            print("WARNING: vehicle not armed — commands will stay gated off. "
                  "Arm manually to enable tracking.")
        controller.start_armed_watch()
        await controller.start_offboard()

    log_fh = open(args.log_file, "a") if args.log_file else None
    writer = None  # created lazily once we know the frame size
    search_state = SearchState()
    try:
        while True:
            frame = source.read()
            if frame is None:
                print("End of stream")
                break
            h, w = frame.shape[:2]

            detections = detector.detect(frame)
            decision = decide(detections, (w, h), config, search_state)

            armed = controller.armed if controller else False
            may_command = gate.should_command(
                armed, args.enable_control,
                search_state.frames_since_detection, decision.action)
            search_state = next_search_state(search_state, decision)

            _log(decision, may_command, armed)
            if log_fh:
                _log_jsonl(log_fh, decision, detections, may_command, armed)

            if controller:
                if may_command and decision.velocity_cmd:
                    await controller.send_velocity(*decision.velocity_cmd)
                else:
                    await controller.hold()

            if args.show or args.record:
                import cv2
                from visualize import draw_overlay
                target = select_target(detections, config.target_class)
                annotated = draw_overlay(frame, detections, decision, target)
                if args.record:
                    if writer is None:
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        writer = cv2.VideoWriter(args.record, fourcc, 20.0, (w, h))
                    writer.write(annotated)
                if args.show:
                    cv2.imshow("perception-control", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            # Stay cooperative even in observe-only mode (no awaits above).
            await asyncio.sleep(0)
    finally:
        source.release()
        if writer is not None:
            writer.release()
        if log_fh:
            log_fh.close()
        if args.show:
            import cv2
            cv2.destroyAllWindows()
        if controller:
            await controller.stop()


def _log(decision, may_command, armed):
    ts = time.strftime("%H:%M:%S")
    if decision.action == "track":
        dx, dy = decision.offset
        vx, vy, yaw = decision.velocity_cmd
        dist = f"{decision.distance_m:.1f}m" if decision.distance_m else "n/a"
        print(f"[{ts}] TRACK bearing={decision.bearing_deg:+.1f}deg "
              f"offset=({dx:+.2f},{dy:+.2f}) dist={dist} "
              f"cmd=(vx={vx:+.2f},yaw={yaw:+.2f}) "
              f"armed={armed} sent={may_command}")
    elif decision.action == "search" and decision.velocity_cmd:
        _, _, yaw = decision.velocity_cmd
        print(f"[{ts}] SEARCH scanning yaw={yaw:+.2f} sent={may_command}")
    else:
        print(f"[{ts}] {decision.action.upper()} ({decision.reason})")


def _log_jsonl(fh, decision, detections, may_command, armed):
    """Append one structured JSON record per frame for post-flight review."""
    record = {
        "ts": time.time(),
        "action": decision.action,
        "bearing_deg": decision.bearing_deg,
        "offset": decision.offset,
        "distance_m": decision.distance_m,
        "velocity_cmd": decision.velocity_cmd,
        "armed": armed,
        "command_sent": may_command,
        "num_detections": len(detections),
    }
    fh.write(json.dumps(record) + "\n")
    fh.flush()


def main():
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
