"""Frame overlay helpers for the perception loop (cv2).

Draws all detections, highlights the selected target, and overlays the
decision summary (action / bearing / offset) so a runner or a recorded video is
readable during and after a flight. cv2 is imported lazily so importing this
module never requires OpenCV.
"""

from decision import CLASS_NAMES_DEFAULT

# BGR colors per class id (0 = mannequin green, 1 = tent blue).
CLASS_COLORS = [(0, 255, 0), (255, 128, 0)]
TARGET_COLOR = (0, 0, 255)   # red box for the selected target


def draw_overlay(frame, detections, decision, target=None):
    """Annotate ``frame`` in place and return it.

    ``detections`` is a list of (cls_id, conf, x1, y1, x2, y2); ``decision`` is
    a decision.Decision; ``target`` is the selected detection tuple or None.
    """
    import cv2

    for det in detections:
        cls_id, conf, x1, y1, x2, y2 = det
        is_target = target is not None and det == target
        color = TARGET_COLOR if is_target else CLASS_COLORS[cls_id % len(CLASS_COLORS)]
        thickness = 3 if is_target else 1
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(frame, p1, p2, color, thickness)
        name = CLASS_NAMES_DEFAULT[cls_id] if cls_id < len(CLASS_NAMES_DEFAULT) else str(cls_id)
        cv2.putText(frame, f"{name} {conf:.2f}", (p1[0], max(p1[1] - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    lines = [f"action: {decision.action}"]
    if decision.bearing_deg is not None:
        lines.append(f"bearing: {decision.bearing_deg:+.1f} deg")
    if decision.offset is not None:
        lines.append(f"offset: ({decision.offset[0]:+.2f}, {decision.offset[1]:+.2f})")
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 25 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame
