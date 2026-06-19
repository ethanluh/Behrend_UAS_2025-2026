import bpy
import bpy_extras.object_utils
import mathutils
import random
import os
import math
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
# Paths default to this repo's layout (scripts -> blender -> ObjectDetection) and
# can be overridden with environment variables so the script runs on any machine:
#   OD_OUTPUT_IMAGES, OD_OUTPUT_LABELS, OD_HDRI_DIR, OD_NUM_RENDERS
PROJECT = Path(__file__).resolve().parents[2]   # .../ObjectDetection
OUTPUT_IMAGES = os.environ.get("OD_OUTPUT_IMAGES", str(PROJECT / "dataset/images/train") + "/")
OUTPUT_LABELS = os.environ.get("OD_OUTPUT_LABELS", str(PROJECT / "dataset/labels/train") + "/")
HDRI_DIR      = os.environ.get("OD_HDRI_DIR",      str(PROJECT / "blender/hdris") + "/")
NUM_RENDERS   = int(os.environ.get("OD_NUM_RENDERS", "1000"))
CLASS_ID      = 1           # 1 = tent
OBJECT_NAME   = "tent.001"      # exact name from outliner
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_IMAGES, exist_ok=True)
os.makedirs(OUTPUT_LABELS, exist_ok=True)

scene  = bpy.context.scene
camera = scene.camera
obj    = bpy.data.objects[OBJECT_NAME]
render = scene.render
res_x  = render.resolution_x
res_y  = render.resolution_y

hdri_files = [
    os.path.join(HDRI_DIR, f)
    for f in os.listdir(HDRI_DIR)
    if f.lower().endswith((".hdr", ".exr"))
]

def set_hdri(path):
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    env = nodes.new("ShaderNodeTexEnvironment")
    bg  = nodes.new("ShaderNodeBackground")
    out = nodes.new("ShaderNodeOutputWorld")
    env.image = bpy.data.images.load(path, check_existing=False)
    bg.inputs["Strength"].default_value = random.uniform(0.5, 2.0)
    links.new(env.outputs["Color"],     bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])

def get_2d_bbox(obj, camera, scene):
    corners_world = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    coords_2d = []
    for co in corners_world:
        ndc = bpy_extras.object_utils.world_to_camera_view(scene, camera, co)
        if ndc.z < 0:
            return None
        coords_2d.append((ndc.x * res_x, (1.0 - ndc.y) * res_y))
    xs, ys = zip(*coords_2d)
    return (max(0.0, min(xs)), max(0.0, min(ys)),
            min(float(res_x), max(xs)), min(float(res_y), max(ys)))

def to_yolo(x1, y1, x2, y2):
    return ((x1+x2)/2)/res_x, ((y1+y2)/2)/res_y, (x2-x1)/res_x, (y2-y1)/res_y

# ── Optional: composite over real backgrounds (sim-to-real) ────────────────────
# Default OFF — the working opaque-render path is untouched. When enabled, renders
# with a transparent film so the tent can be alpha-composited over random real
# photos (guide Part 12.1). Uses only Blender-bundled numpy. VERIFY IN BLENDER
# before a full run — this path is not exercised by CI.
import numpy as np

COMPOSITE_BACKGROUND = False
BACKGROUND_DIR = "/absolute/path/to/project/backgrounds/"

if COMPOSITE_BACKGROUND:
    scene.render.film_transparent = True
    _bg_files = [
        os.path.join(BACKGROUND_DIR, f)
        for f in os.listdir(BACKGROUND_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    assert _bg_files, f"No backgrounds found in {BACKGROUND_DIR}"


def composite_on_background(render_path):
    """Alpha-composite an RGBA render over a random real background (numpy)."""
    fg = bpy.data.images.load(render_path, check_existing=False)
    w, h = fg.size
    fg_px = np.array(fg.pixels[:]).reshape(h, w, 4)

    bg = bpy.data.images.load(random.choice(_bg_files), check_existing=False)
    bw, bh = bg.size
    bg_px = np.array(bg.pixels[:]).reshape(bh, bw, 4)
    ys = np.linspace(0, bh - 1, h).astype(int)
    xs = np.linspace(0, bw - 1, w).astype(int)
    bg_rs = bg_px[ys][:, xs]

    alpha = fg_px[:, :, 3:4]
    fg_px[:, :, :3] = alpha * fg_px[:, :, :3] + (1.0 - alpha) * bg_rs[:, :, :3]
    fg_px[:, :, 3] = 1.0
    fg.pixels = fg_px.reshape(-1)
    fg.filepath_raw = render_path
    fg.file_format = "PNG"
    fg.save()


for i in range(NUM_RENDERS):
    obj.location.x        = random.uniform(-1.5, 1.5)
    obj.location.y        = random.uniform(-1.5, 1.5)
    obj.location.z        = 0.0
    obj.rotation_euler[2] = random.uniform(0, 2 * math.pi)
    s = random.uniform(0.85, 1.15)
    obj.scale = (s, s, s)

    radius    = random.uniform(3.0, 8.0)
    azimuth   = random.uniform(0, 2 * math.pi)
    elevation = random.uniform(math.radians(10), math.radians(60))
    camera.location = (
        obj.location.x + radius * math.cos(azimuth) * math.cos(elevation),
        obj.location.y + radius * math.sin(azimuth) * math.cos(elevation),
        radius * math.sin(elevation),
    )
    direction = obj.location - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    set_hdri(random.choice(hdri_files))

    img_path = os.path.join(OUTPUT_IMAGES, f"tent_{i:05d}.png")
    scene.render.filepath = img_path
    bpy.ops.render.render(write_still=True)

    if COMPOSITE_BACKGROUND:
        composite_on_background(img_path)

    bbox = get_2d_bbox(obj, camera, scene)
    if bbox is None or (bbox[2]-bbox[0]) < 5 or (bbox[3]-bbox[1]) < 5:
        if os.path.exists(img_path):
            os.remove(img_path)
        continue

    cx, cy, w, h = to_yolo(*bbox)
    with open(os.path.join(OUTPUT_LABELS, f"tent_{i:05d}.txt"), "w") as f:
        f.write(f"{CLASS_ID} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    if i % 50 == 0:
        print(f"[{i}/{NUM_RENDERS}] OK — {img_path}")

print("Tent renders complete.")