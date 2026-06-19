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
OUTPUT_IMAGES  = os.environ.get("OD_OUTPUT_IMAGES", str(PROJECT / "dataset/images/train") + "/")
OUTPUT_LABELS  = os.environ.get("OD_OUTPUT_LABELS", str(PROJECT / "dataset/labels/train") + "/")
HDRI_DIR       = os.environ.get("OD_HDRI_DIR",      str(PROJECT / "blender/hdris") + "/")
NUM_RENDERS    = int(os.environ.get("OD_NUM_RENDERS", "1000"))
CLASS_ID       = 0               # 0 = mannequin
MESH_NAME     = "Ch36"
ARMATURE_NAME = "Armature"


BASE_LOCATION = mathutils.Vector((0.0, 0.0, 0.0))
BASE_ROTATION = mathutils.Euler((1.5708, 0.0, 0.0), 'XYZ')  # whatever the file has
BASE_SCALE    = mathutils.Vector((0.01, 0.01, 0.01))   

# Only drive primary deformation bones. The DHIbody rig has hundreds of
# corrective/twist/bulge secondaries — rotating those directly breaks the mesh.
# The matching logic strips "DHIbody:", underscores, and dots before comparing.
BONE_LIMITS = {
    # Spine: subtle lean and twist
    "spine01":      ((-0.15, 0.20), (-0.08, 0.08), (-0.12, 0.12)),
    "spine02":      ((-0.12, 0.18), (-0.06, 0.06), (-0.10, 0.10)),
    "spine03":      ((-0.10, 0.15), (-0.05, 0.05), (-0.08, 0.08)),
    "spine04":      ((-0.08, 0.12), (-0.04, 0.04), (-0.06, 0.06)),
    "spine05":      ((-0.06, 0.10), (-0.03, 0.03), (-0.05, 0.05)),

    # Neck and head
    "neck01":       ((-0.20, 0.25), (-0.05, 0.05), (-0.25, 0.25)),
    "neck02":       ((-0.15, 0.20), (-0.04, 0.04), (-0.20, 0.20)),
    "head":         ((-0.30, 0.30), (-0.08, 0.08), (-0.45, 0.45)),

    # Clavicles: shrug range
    "clavicle_l":   ((-0.15, 0.25), (-0.10, 0.10), (-0.10, 0.20)),
    "clavicle_r":   ((-0.15, 0.25), (-0.10, 0.10), (-0.20, 0.10)),

    # Upper arms: wide range for raised/lowered/crossed poses
    "upperarm_l":   ((-0.40, 1.80), (-0.30, 0.30), (-1.40, 0.30)),
    "upperarm_r":   ((-0.40, 1.80), (-0.30, 0.30), (-0.30, 1.40)),

    # Forearms: elbow flexion only (no supination — that tears the mesh)
    "lowerarm_l":   (( 0.00, 2.00), ( 0.00, 0.00), ( 0.00, 0.00)),
    "lowerarm_r":   (( 0.00, 2.00), ( 0.00, 0.00), ( 0.00, 0.00)),

    # Hands: wrist flex/ulnar deviation
    "hand_l":       ((-0.40, 0.40), (-0.20, 0.20), (-0.40, 0.40)),
    "hand_r":       ((-0.40, 0.40), (-0.20, 0.20), (-0.40, 0.40)),

    # Thighs: standing pose range only
    "thigh_l":      ((-0.35, 0.50), (-0.20, 0.20), (-0.20, 0.35)),
    "thigh_r":      ((-0.35, 0.50), (-0.20, 0.20), (-0.35, 0.20)),

    # Calves: knee flexion only
    "calf_l":       (( 0.00, 0.60), ( 0.00, 0.00), ( 0.00, 0.00)),
    "calf_r":       (( 0.00, 0.60), ( 0.00, 0.00), ( 0.00, 0.00)),

    # Feet: ankle flex/extension
    "foot_l":       ((-0.30, 0.40), (-0.10, 0.10), (-0.15, 0.15)),
    "foot_r":       ((-0.30, 0.40), (-0.10, 0.10), (-0.15, 0.15)),
}
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_IMAGES, exist_ok=True)
os.makedirs(OUTPUT_LABELS, exist_ok=True)

scene    = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE"
scene.world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
scene.world.use_nodes = True

camera   = scene.camera
mesh_obj = bpy.data.objects[MESH_NAME]
armature = bpy.data.objects[ARMATURE_NAME]

render   = scene.render
res_x    = render.resolution_x   # 640
res_y    = render.resolution_y   # 640
# Add after scene/object setup at the top of the script
ground = bpy.data.objects["Plane"]

def randomize_ground(plane):
    mat = plane.data.materials[0] if plane.data.materials else None
    if mat is None:
        mat = bpy.data.materials.new("Ground")
        plane.data.materials.append(mat)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (
            random.uniform(0.05, 0.6),
            random.uniform(0.05, 0.6),
            random.uniform(0.05, 0.6),
            1.0,
        )
        bsdf.inputs["Roughness"].default_value = random.uniform(0.5, 1.0)

hdri_files = [
    os.path.join(HDRI_DIR, f)
    for f in os.listdir(HDRI_DIR)
    if f.lower().endswith((".hdr", ".exr"))
]
assert hdri_files, f"No HDRI files found in {HDRI_DIR}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def reset_pose(armature):
    """Reset all bones to rest pose."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    for bone in armature.pose.bones:
        bone.rotation_mode  = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location       = (0.0, 0.0, 0.0)
        bone.scale          = (1.0, 1.0, 1.0)
    bpy.ops.object.mode_set(mode="OBJECT")


def randomize_pose(armature):
    """
    Randomize bone rotations within limits defined in BONE_LIMITS.
    Matching strips 'mixamorig:' prefix, underscores, dots, and lowercases.
    """
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")

    for bone in armature.pose.bones:
        # Normalize name for dict lookup
        key = bone.name.lower().split(":")[-1].replace("_", "").replace(".", "")

        for limit_key, (rx, ry, rz) in BONE_LIMITS.items():
            if limit_key in key:
                bone.rotation_mode  = "XYZ"
                bone.rotation_euler = (
                    random.uniform(*rx),
                    random.uniform(*ry),
                    random.uniform(*rz),
                )
                break  # matched — move on to next bone

    bpy.ops.object.mode_set(mode="OBJECT")
    # Force mesh deformation update before reading bound_box
    bpy.context.view_layer.update()


def set_hdri(path):
    world = scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True  # still works in 5.1, just deprecated
    nt = world.node_tree
    nt.nodes.clear()

    coord  = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    env    = nt.nodes.new("ShaderNodeTexEnvironment")
    bg     = nt.nodes.new("ShaderNodeBackground")
    out    = nt.nodes.new("ShaderNodeOutputWorld")

    env.image = bpy.data.images.load(path, check_existing=False)
    bg.inputs["Strength"].default_value = random.uniform(0.8, 2.5)

    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"],  env.inputs["Vector"])
    nt.links.new(env.outputs["Color"],       bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"],   out.inputs["Surface"])


def get_2d_bbox(mesh_obj, camera, scene):
    """
    Project actual evaluated mesh vertices into screen space.
    More accurate than bound_box for deforming/skinned meshes, and avoids
    the issue of rig helper bones inflating the bounding box.
    """
    # Get the evaluated (post-modifier, post-armature) mesh
    depsgraph   = bpy.context.evaluated_depsgraph_get()
    eval_obj    = mesh_obj.evaluated_get(depsgraph)
    eval_mesh   = eval_obj.to_mesh()

    coords_2d = []
    for vert in eval_mesh.vertices:
        # Transform vertex to world space
        co_world = eval_obj.matrix_world @ vert.co
        ndc = bpy_extras.object_utils.world_to_camera_view(scene, camera, co_world)
        if ndc.z > 0:   # only include vertices in front of camera
            coords_2d.append((ndc.x * res_x, (1.0 - ndc.y) * res_y))

    # Free the temporary mesh
    eval_obj.to_mesh_clear()

    if not coords_2d:
        return None   # entire mesh behind camera

    xs, ys = zip(*coords_2d)
    x1 = max(0.0,          min(xs))
    y1 = max(0.0,          min(ys))
    x2 = min(float(res_x), max(xs))
    y2 = min(float(res_y), max(ys))
    return x1, y1, x2, y2


def to_yolo(x1, y1, x2, y2):
    """Convert pixel bbox to normalized YOLO (cx, cy, w, h)."""
    cx = ((x1 + x2) / 2.0) / res_x
    cy = ((y1 + y2) / 2.0) / res_y
    w  = (x2 - x1) / res_x
    h  = (y2 - y1) / res_y
    return cx, cy, w, h


# ── Optional: composite over real backgrounds (sim-to-real) ────────────────────
# Default OFF — the working opaque-render path above is untouched. When enabled,
# renders with a transparent film so the subject can be alpha-composited over
# random real photos (guide Part 12.1), narrowing the sim-to-real gap. Uses only
# Blender-bundled numpy (no OpenCV). VERIFY IN BLENDER before a full run — this
# path is not exercised by CI.
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
    # Nearest-neighbour resize of the background to the render size.
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


# ── Render Loop ───────────────────────────────────────────────────────────────

for i in range(NUM_RENDERS):

    # Reset armature to neutral transform before each render
    armature.location      = BASE_LOCATION.copy()
    armature.rotation_euler = BASE_ROTATION.copy()
    armature.scale         = BASE_SCALE.copy()
    bpy.context.view_layer.update()

    # 1. Reset to rest pose, then randomize
    reset_pose(armature)
    randomize_pose(armature)
    randomize_ground(ground)

    # 2. Randomize object-level transform
    armature.location.x        = random.uniform(-1.5, 1.5)
    armature.location.y        = random.uniform(-1.5, 1.5)
    armature.location.z        = 0.0
    armature.rotation_euler[2] = random.uniform(0, 2 * math.pi)  # yaw only
    s = random.uniform(0.0085, 0.0115)
    armature.scale = (s, s, s)

    # 3. Randomize camera on a hemisphere around the object
    radius    = random.uniform(4.0, 8.0)
    azimuth   = random.uniform(0, 2 * math.pi)
    elevation = random.uniform(math.radians(10), math.radians(70))
    camera.location = (
        armature.location.x + radius * math.cos(azimuth) * math.cos(elevation),
        armature.location.y + radius * math.sin(azimuth) * math.cos(elevation),
        radius * math.sin(elevation),
    )
    # Replace the camera aim line with this
    target = armature.location + mathutils.Vector((0, 0, 0.9))  # aim at ~hip height
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    # 4. Randomize HDRI
    set_hdri(random.choice(hdri_files))

    # 5. Render
    img_path = os.path.join(OUTPUT_IMAGES, f"mannequin_{i:05d}.png")
    scene.render.filepath = img_path
    bpy.ops.render.render(write_still=True)

    if COMPOSITE_BACKGROUND:
        composite_on_background(img_path)

    # 6. Compute bbox using the MESH object (not armature) — bound_box
    #    reflects deformed mesh geometry, not the skeleton.
    bbox = get_2d_bbox(mesh_obj, camera, scene)

    if bbox is None:
        print(f"[{i}] Skipped: object behind camera")
        if os.path.exists(img_path):
            os.remove(img_path)
        continue

    x1, y1, x2, y2 = bbox
    if (x2 - x1) < 5 or (y2 - y1) < 5:
        print(f"[{i}] Skipped: degenerate bbox (object mostly off-screen)")
        if os.path.exists(img_path):
            os.remove(img_path)
        continue

    cx, cy, w, h = to_yolo(x1, y1, x2, y2)
    lbl_path = os.path.join(OUTPUT_LABELS, f"mannequin_{i:05d}.txt")
    with open(lbl_path, "w") as f:
        f.write(f"{CLASS_ID} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    if i % 50 == 0:
        print(f"[{i}/{NUM_RENDERS}] OK — {img_path}")

print("Mannequin renders complete.")