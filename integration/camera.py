"""Frame source for the perception loop.

Thin wrapper over cv2.VideoCapture, reusing the pattern from
``testing/Jetson Nano/camera_test.py``. The source may be a camera index
(int, e.g. 0) or a path to a video file for offline testing without hardware.
"""


class FrameSource:
    def __init__(self, source=0, width=None, height=None):
        # cv2 imported lazily so this module imports without OpenCV present.
        import cv2
        self._cv2 = cv2
        # Accept "0" / 0 as a camera index, otherwise treat as a file path.
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open video source: {source!r}")
        if width:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        """Return the next frame, or None if the stream ended / failed."""
        ret, frame = self.cap.read()
        return frame if ret else None

    @property
    def size(self):
        w = int(self.cap.get(self._cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(self._cv2.CAP_PROP_FRAME_HEIGHT))
        return w, h

    def release(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
