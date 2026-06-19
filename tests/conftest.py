"""Make the pure modules importable without installing the project.

Adds ObjectDetection/ and integration/ to sys.path so tests can
`import od_lib` and `import decision` directly. These modules have no heavy
dependencies (no torch/cv2/mavsdk), so the suite runs on a clean machine.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("ObjectDetection", "integration"):
    sys.path.insert(0, str(ROOT / sub))
