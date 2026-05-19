# Object Detection with Synthetic Blender Data: Complete Guide

YOLOv8 object detector for mannequins and tents using synthetically rendered Blender data. The mannequin uses a rigged model with per-render pose randomization.

---

## Part 1: Environment Setup

### 1.1 Create and Activate a Virtual Environment

From inside your `project/` directory:

```bash
python -m venv venv
```

Activate it:

```bash
# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

Your terminal prompt should now be prefixed with `(venv)`. Every subsequent Python/pip command in this guide assumes the venv is active. Re-run the activate command any time you open a new terminal.

### 1.2 Install Dependencies from requirements.txt

With the venv active:

```bash
pip install -r requirements.txt
```

### 1.3 Install Blender

Download Blender from [blender.org](https://blender.org) (3.6 LTS recommended for stability). Install normally. Verify you can open it and navigate to the **Scripting** workspace tab.

> **Note:** Blender ships its own embedded Python interpreter. The render scripts run inside Blender's Python, not your venv. Your venv is only for training, evaluation, and the dataset utility scripts.

### 1.4 Create Your Project Directory Structure

```
project/
├── venv/
├── requirements.txt
├── blender/
│   ├── scenes/
│   │   ├── mannequin.blend
│   │   └── tent.blend
│   ├── scripts/
│   │   ├── render_mannequin.py
│   │   └── render_tent.py
│   └── hdris/
├── backgrounds/          ← real photos for compositing (Part 12)
├── dataset/
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
├── training/
│   └── dataset.yaml
├── verify_labels.py
├── split_dataset.py
├── train.py
└── runs/                 ← YOLO writes outputs here automatically
```

Create all directories now:

```bash
mkdir -p project/{blender/{scenes,scripts,hdris},backgrounds,dataset/{images,labels}/{train,val,test},training,runs}
```

---

## Part 2: Acquiring 3D Models

### 2.1 Find a Rigged Mannequin Model

Go to [Sketchfab.com](https://sketchfab.com). Search "mannequin rigged". Filter by **Free** and **Downloadable**. A rigged model has a skeleton/armature — look for the word "rigged" in the model description, or a skeleton icon in the model viewer.

When downloading, choose `.fbx` format. FBX preserves the armature, bone hierarchy, and any existing pose data better than OBJ (which has no rig support at all).

Alternative search terms: "rigged human figure", "rigged character base mesh", "mannequin armature".

If nothing free and rigged shows up on Sketchfab, try [Mixamo](https://mixamo.com) — Adobe's free service that provides rigged human base meshes. Sign in with a free Adobe account, go to **Characters**, pick a neutral base mesh, click **Download**, choose **FBX for Unity** format (works fine in Blender).

### 2.2 Verify the Model is Actually Rigged Before Downloading

In the Sketchfab 3D viewer, look for an animation tab or skeleton overlay. If the model page lists no animations and the description doesn't mention rigging, it is likely a static mesh — skip it.

### 2.3 Find a Tent Model

Go to [Sketchfab.com](https://sketchfab.com). Search "camping tent". Filter Free + Downloadable. The tent does not need to be rigged — it is a static object. Download as `.fbx` or `.obj`.

Alternatives if Sketchfab has nothing suitable:
- [BlendSwap](https://blendswap.com) — search `.blend` files directly
- [Poly Haven](https://polyhaven.com/models) — some outdoor/furniture models

### 2.4 Download HDRI Lighting Files

Go to [Poly Haven](https://polyhaven.com/hdris). Download 10–15 varied HDRIs (indoor, outdoor, studio, overcast, sunny, night). Use **1K or 2K** resolution — 4K is unnecessary for training data and significantly slows renders. Download as `.hdr` or `.exr`. Save everything to `project/blender/hdris/`.

Aim for variety: one studio neutral, one overcast outdoor, one sunset, one interior room, one cloudy sky, one night/artificial light.

---

## Part 3: Setting Up the Mannequin Scene in Blender

### 3.1 Open Blender and Clear the Default Scene

Open Blender. Click the default cube to select it, press `X`, then click **Delete**. Do the same for the default light. Leave the camera.

### 3.2 Import the Rigged Mannequin FBX

Go to **File → Import → FBX**. Navigate to your downloaded mannequin `.fbx` file and click **Import FBX**.

After import, you should see two objects in the outliner (top-right panel): the mesh object (e.g. "Mannequin" or "Body") and an armature object (e.g. "Armature" or "Mannequin_Rig"). If you see only one object, the rig may not have imported correctly — verify you downloaded the rigged version.

### 3.3 Identify and Rename the Armature and Mesh

In the outliner, note the exact names of both objects. Names are case-sensitive and must match what you put in the render script. Rename them now for clarity: double-click a name in the outliner to rename it. Use `Mannequin_Mesh` for the mesh and `Mannequin_Rig` for the armature.

### 3.4 Fix Scale and Position

Select the armature object. Check dimensions in the `N` panel (press `N`) → **Item** tab. A human-scale mannequin should be roughly 1.7–1.8m tall. If it is wildly off:

1. Press `S`, type a scale factor, press `Enter`.
2. Press `G` → `Z` to adjust height so the base is at Z=0.
3. **Apply all transforms**: press `Ctrl+A` → Apply → **All Transforms**. Unapplied transforms cause the bounding box projection code to give incorrect results.

### 3.5 Verify the Rig Works

Select the armature. Press `Ctrl+Tab` to enter **Pose Mode**. Click an upper arm bone and press `R`, then drag — the mesh should deform accordingly. If the mesh does not follow the bones, the model's skinning is broken; find a different model.

Press `Ctrl+Tab` to return to Object Mode. Press `Alt+R` with the armature selected to reset all bones to the rest pose.

### 3.6 Identify Bone Names for Pose Randomization

In Pose Mode, click each major bone. Its name appears in the `N` panel → **Item** tab. Write down the names for:

- Left and right upper arm (shoulder)
- Left and right forearm
- Left and right upper leg (thigh)
- Left and right lower leg
- Spine segments
- Head and neck

You will use these names in the `BONE_LIMITS` dict in the render script. Bone naming conventions vary: Mixamo uses `mixamorig:LeftArm`, others use `upper_arm.L`, `Arm_L`, etc.

### 3.7 Set Up the Camera

Press `Numpad 0` to enter camera view. Select the camera in the outliner. In the **Properties** panel → camera icon:
- Focal length: 35mm
- Leave clip start/end at defaults

### 3.8 Add a Ground Plane

Press `Shift+A` → Mesh → Plane. Press `S`, type `20`, press `Enter`. In **Properties** → **Material** tab, click **New** and set Base Color to neutral gray (0.4, 0.4, 0.4).

### 3.9 Configure Render Settings

In **Properties** → **Render** tab:
- Render Engine: **EEVEE** (fast, good enough) or **Cycles** (more realistic)
- Resolution X: `640`, Resolution Y: `640`
- For Cycles: Samples → `64`

In **Properties** → **Output** tab:
- File Format: **PNG**
- Color: **RGBA** (needed for background compositing later)

In **Render** tab → **Film** section:
- Check **Transparent** — makes the background transparent instead of black, giving a clean alpha channel

### 3.10 Save as a Blend File

**File → Save As** → `project/blender/scenes/mannequin.blend`

### 3.11 Set Up the Tent Scene

Open a new Blender file (**File → New → General**). Repeat steps 3.1–3.2 for the tent model (no rig needed). Apply transforms (3.4). Set up camera (3.7), ground plane (3.8), and render settings (3.9). Save as `project/blender/scenes/tent.blend`.

---

## Part 4: Writing the Mannequin Render Script

### 4.1 What the Script Does Per Render

1. Reset all bones to rest pose
2. Randomly rotate each bone within anatomically plausible limits
3. Randomize the object's position, yaw, and scale
4. Position the camera on a random point on a hemisphere around the object
5. Set a random HDRI for lighting
6. Render to PNG (RGBA)
7. Project the deformed mesh's 3D bounding box into 2D screen space
8. Write a YOLO-format `.txt` label
9. Discard the render if the object is off-screen or behind the camera

### 4.2 Bounding Box Projection

`obj.bound_box` returns 8 corners of the object's local-space AABB. After posing, the mesh deforms and `bound_box` updates to enclose the current geometry. We transform each corner by `matrix_world` to get world-space coordinates, then project with `world_to_camera_view` into NDC (normalized device coordinates, [0,1] range). Negative NDC z means behind the camera. We flip Y because Blender's origin is bottom-left but image convention is top-left.

### 4.3 Create `render_mannequin.py`

Create `project/blender/scripts/render_mannequin.py`:

```python
import bpy
import bpy_extras.object_utils
import mathutils
import random
import os
import math

# ── Configuration ─────────────────────────────────────────────────────────────
OUTPUT_IMAGES  = "/absolute/path/to/project/dataset/images/train/"
OUTPUT_LABELS  = "/absolute/path/to/project/dataset/labels/train/"
HDRI_DIR       = "/absolute/path/to/project/blender/hdris/"
NUM_RENDERS    = 1000
CLASS_ID       = 0               # 0 = mannequin
MESH_NAME      = "Mannequin_Mesh"   # exact name from outliner
ARMATURE_NAME  = "Mannequin_Rig"    # exact name from outliner

# Bone name fragment → (x_range, y_range, z_range) in radians.
# Matching is case-insensitive; strips "mixamorig:", underscores, and dots.
# Adjust keys and ranges to match YOUR model's skeleton.
BONE_LIMITS = {
    # Spine: subtle lean/twist only
    "spine":        ((-0.15, 0.15), (-0.10, 0.10), (-0.15, 0.15)),
    "spine1":       ((-0.15, 0.15), (-0.10, 0.10), (-0.15, 0.15)),
    "spine2":       ((-0.10, 0.10), (-0.05, 0.05), (-0.10, 0.10)),

    # Head and neck
    "head":         ((-0.30, 0.30), (-0.10, 0.10), (-0.50, 0.50)),
    "neck":         ((-0.20, 0.20), (-0.05, 0.05), (-0.30, 0.30)),

    # Arms: wide range to cover raised/lowered/crossed poses
    "leftarm":      ((-0.50, 1.80), (-0.30, 0.30), (-1.50, 0.30)),
    "leftforearm":  (( 0.00, 2.00), ( 0.00, 0.00), ( 0.00, 0.00)),  # elbow flexion only
    "lefthand":     ((-0.30, 0.30), (-0.30, 0.30), (-0.50, 0.50)),
    "rightarm":     ((-0.50, 1.80), (-0.30, 0.30), (-0.30, 1.50)),
    "rightforearm": (( 0.00, 2.00), ( 0.00, 0.00), ( 0.00, 0.00)),
    "righthand":    ((-0.30, 0.30), (-0.30, 0.30), (-0.50, 0.50)),

    # Legs: standing poses only
    "leftupleg":    ((-0.30, 0.30), (-0.20, 0.20), (-0.30, 0.30)),
    "leftleg":      (( 0.00, 0.50), ( 0.00, 0.00), ( 0.00, 0.00)),  # knee flexion only
    "rightupleg":   ((-0.30, 0.30), (-0.20, 0.20), (-0.30, 0.30)),
    "rightleg":     (( 0.00, 0.50), ( 0.00, 0.00), ( 0.00, 0.00)),
}
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_IMAGES, exist_ok=True)
os.makedirs(OUTPUT_LABELS, exist_ok=True)

scene    = bpy.context.scene
camera   = scene.camera
mesh_obj = bpy.data.objects[MESH_NAME]
armature = bpy.data.objects[ARMATURE_NAME]
render   = scene.render
res_x    = render.resolution_x   # 640
res_y    = render.resolution_y   # 640

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
        key = (bone.name.lower()
               .replace("mixamorig:", "")
               .replace("_", "")
               .replace(".", ""))

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
    """Replace the world shader with an HDRI environment texture."""
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
    """
    Project obj's world-space bounding box into screen space.
    Returns (x1, y1, x2, y2) in pixels clamped to image bounds,
    or None if any corner is behind the camera.
    """
    corners_world = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    coords_2d = []
    for co in corners_world:
        ndc = bpy_extras.object_utils.world_to_camera_view(scene, camera, co)
        if ndc.z < 0:
            return None   # behind camera
        px = ndc.x * res_x
        py = (1.0 - ndc.y) * res_y   # flip Y: Blender origin is bottom-left
        coords_2d.append((px, py))

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


# ── Render Loop ───────────────────────────────────────────────────────────────

for i in range(NUM_RENDERS):

    # 1. Reset to rest pose, then randomize
    reset_pose(armature)
    randomize_pose(armature)

    # 2. Randomize object-level transform
    armature.location.x        = random.uniform(-1.5, 1.5)
    armature.location.y        = random.uniform(-1.5, 1.5)
    armature.location.z        = 0.0
    armature.rotation_euler[2] = random.uniform(0, 2 * math.pi)  # yaw only
    s = random.uniform(0.85, 1.15)
    armature.scale = (s, s, s)

    # 3. Randomize camera on a hemisphere around the object
    radius    = random.uniform(2.5, 6.0)
    azimuth   = random.uniform(0, 2 * math.pi)
    elevation = random.uniform(math.radians(10), math.radians(70))
    camera.location = (
        armature.location.x + radius * math.cos(azimuth) * math.cos(elevation),
        armature.location.y + radius * math.sin(azimuth) * math.cos(elevation),
        radius * math.sin(elevation),
    )
    direction = armature.location - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    # 4. Randomize HDRI
    set_hdri(random.choice(hdri_files))

    # 5. Render
    img_path = os.path.join(OUTPUT_IMAGES, f"mannequin_{i:05d}.png")
    scene.render.filepath = img_path
    bpy.ops.render.render(write_still=True)

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
```

### 4.4 Customize BONE_LIMITS for Your Model

The `BONE_LIMITS` dict uses normalized name fragments for matching. Before running the full render job, verify your bone names:

1. Open `mannequin.blend` in Blender GUI.
2. Select the armature, enter Pose Mode (`Ctrl+Tab`).
3. Click each major bone and check its name in the `N` panel.
4. Update the keys in `BONE_LIMITS` to match your model.

For Mixamo models the prefix is `mixamorig:` — the script already strips this, so the key `"leftarm"` matches `"mixamorig:LeftArm"`. For other models with names like `upper_arm.L`, the stripped/lowercased form would be `"uppararml"` — adjust accordingly.

To debug matching, temporarily add `print(key)` inside the bone loop and run a 1-render test.

### 4.5 Create `render_tent.py`

Create `project/blender/scripts/render_tent.py`. Same structure as the mannequin script, but no pose randomization:

```python
import bpy
import bpy_extras.object_utils
import mathutils
import random
import os
import math

# ── Configuration ─────────────────────────────────────────────────────────────
OUTPUT_IMAGES = "/absolute/path/to/project/dataset/images/train/"
OUTPUT_LABELS = "/absolute/path/to/project/dataset/labels/train/"
HDRI_DIR      = "/absolute/path/to/project/blender/hdris/"
NUM_RENDERS   = 1000
CLASS_ID      = 1           # 1 = tent
OBJECT_NAME   = "Tent"      # exact name from outliner
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
```

---

## Part 5: Test Run Before Full Render

### 5.1 Set NUM_RENDERS to 5

In `render_mannequin.py`, temporarily set `NUM_RENDERS = 5`.

### 5.2 Run Headlessly

```bash
# macOS / Linux
blender --background /path/to/project/blender/scenes/mannequin.blend \
        --python /path/to/project/blender/scripts/render_mannequin.py

# Windows
"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe" ^
    --background C:\path\to\mannequin.blend ^
    --python C:\path\to\render_mannequin.py

# macOS app bundle
/Applications/Blender.app/Contents/MacOS/Blender --background \
    /path/to/mannequin.blend --python /path/to/render_mannequin.py
```

### 5.3 Check the Output

Verify 5 images and 5 label files appear in the train directories. Open a few images and confirm:
- The mannequin is visible
- Each render shows a different pose (arms, legs, torso varied)
- The model is not in the exact same position every frame

If Blender errors out, the terminal prints a Python traceback pointing to the failing line.

### 5.4 Verify Labels on the Test Renders

Run the verify script (Part 7) on these 5 images before doing the full render. Fix any projection issues now.

---

## Part 6: Full Render Run

### 6.1 Set NUM_RENDERS Back to 1000

In both scripts, set `NUM_RENDERS = 1000`.

### 6.2 Run Both Scripts

```bash
blender --background /path/to/mannequin.blend --python /path/to/render_mannequin.py
blender --background /path/to/tent.blend      --python /path/to/render_tent.py
```

Run sequentially or in two terminals. EEVEE: ~1–2 hours per 1000 renders. Cycles: ~3–6 hours.

### 6.3 Verify Output Counts

```bash
ls project/dataset/images/train/ | wc -l
ls project/dataset/labels/train/ | wc -l
```

Both numbers must match. Skipped renders (off-screen) have their image deleted automatically, so some attrition is expected.

---

## Part 7: Verifying Labels

Do this before training. A bbox projection bug silently tanks mAP and is invisible until you look.

### 7.1 Create `verify_labels.py`

Create `project/verify_labels.py`:

```python
import cv2
import os
import random

IMG_DIR     = "project/dataset/images/train"
LBL_DIR     = "project/dataset/labels/train"
CLASS_NAMES = ["mannequin", "tent"]
COLORS      = [(0, 255, 0), (0, 0, 255)]  # green = mannequin, blue = tent
SAMPLE_SIZE = 30

img_files = [f for f in os.listdir(IMG_DIR) if f.endswith(".png")]
sample = random.sample(img_files, min(SAMPLE_SIZE, len(img_files)))

for fname in sample:
    img_path = os.path.join(IMG_DIR, fname)
    lbl_path = os.path.join(LBL_DIR, fname.replace(".png", ".txt"))

    if not os.path.exists(lbl_path):
        print(f"Missing label: {fname}")
        continue

    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not read: {img_path}")
        continue

    h, w = img.shape[:2]
    with open(lbl_path) as f:
        for line in f:
            parts  = line.strip().split()
            cls_id = int(parts[0])
            cx, cy, bw, bh = map(float, parts[1:])
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)
            color = COLORS[cls_id % len(COLORS)]
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, CLASS_NAMES[cls_id], (x1, max(y1 - 5, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow(f"Verify — {fname}", img)
    key = cv2.waitKey(0)
    if key == ord("q"):
        break

cv2.destroyAllWindows()
```

### 7.2 Run It

```bash
python project/verify_labels.py
```

Press any key to advance, `q` to quit. Boxes must tightly wrap the visible object. Common failure modes:

- **Boxes mirrored horizontally**: flip is wrong — change `(1.0 - ndc.y)` to `ndc.y` in `get_2d_bbox`
- **Boxes cover the whole image**: you are using the armature object instead of the mesh object for bbox — confirm `MESH_NAME` is correct
- **Boxes correct on some poses but wrong on others**: `bpy.context.view_layer.update()` call is missing after `mode_set` in `randomize_pose`

---

## Part 8: Splitting the Dataset

### 8.1 Create `split_dataset.py`

Create `project/split_dataset.py`:

```python
import os, shutil, random

SRC_IMG    = "project/dataset/images/train"
SRC_LBL    = "project/dataset/labels/train"
VAL_RATIO  = 0.10
TEST_RATIO = 0.10
SEED       = 42

random.seed(SEED)
all_imgs = [f for f in os.listdir(SRC_IMG) if f.endswith(".png")]
random.shuffle(all_imgs)

n      = len(all_imgs)
n_val  = int(n * VAL_RATIO)
n_test = int(n * TEST_RATIO)

splits = {
    "val":  all_imgs[:n_val],
    "test": all_imgs[n_val:n_val + n_test],
}

for split, files in splits.items():
    img_dst = f"project/dataset/images/{split}"
    lbl_dst = f"project/dataset/labels/{split}"
    os.makedirs(img_dst, exist_ok=True)
    os.makedirs(lbl_dst, exist_ok=True)
    for fname in files:
        shutil.move(os.path.join(SRC_IMG, fname), os.path.join(img_dst, fname))
        lbl = fname.replace(".png", ".txt")
        src_lbl = os.path.join(SRC_LBL, lbl)
        if os.path.exists(src_lbl):
            shutil.move(src_lbl, os.path.join(lbl_dst, lbl))

print(f"Train: {n - n_val - n_test} | Val: {n_val} | Test: {n_test}")
```

### 8.2 Run It

```bash
python project/split_dataset.py
```

---

## Part 9: Configuring YOLO

### 9.1 Create `dataset.yaml`

Create `project/training/dataset.yaml`:

```yaml
path: /absolute/path/to/project/dataset
train: images/train
val:   images/val
test:  images/test

nc: 2
names: ["mannequin", "tent"]
```

Use an absolute path for `path`. YOLO resolves image subdirectories relative to it.

---

## Part 10: Training

### 10.1 Create `train.py`

Create `project/train.py`:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # downloads pretrained weights on first run

model.train(
    data="project/training/dataset.yaml",
    epochs=50,
    imgsz=640,
    batch=16,       # reduce to 8 if you run out of VRAM
    device=0,       # GPU index; use "cpu" if no GPU
    project="project/runs",
    name="v1",
    augment=True,   # enables mosaic, flips, color jitter, etc.
)
```

### 10.2 Run Training

With venv active:

```bash
python project/train.py
```

Output goes to `project/runs/v1/`. Best weights saved automatically to `project/runs/v1/weights/best.pt`.

### 10.3 Monitor with TensorBoard (Optional)

```bash
tensorboard --logdir project/runs/v1
```

Open `http://localhost:6006`.

### 10.4 Backbone Selection

Start with `yolov8n`. If val mAP@0.5 plateaus below ~0.5, step up: `yolov8s` → `yolov8m`. Larger backbones need more data and VRAM.

---

## Part 11: Evaluating the Model

### 11.1 Metrics to Watch

YOLO prints these after each epoch:

- **mAP@0.5**: mean average precision at IoU ≥ 0.5. Aim for >0.7 on synthetic data.
- **mAP@0.5:0.95**: averaged across IoU thresholds 0.5–0.95. >0.4 is reasonable for synthetic-only.

### 11.2 Run on the Test Set

```python
from ultralytics import YOLO

model   = YOLO("project/runs/v1/weights/best.pt")
metrics = model.val(data="project/training/dataset.yaml", split="test")
print(metrics.box.map50)    # mAP@0.5
print(metrics.box.map)      # mAP@0.5:0.95
```

### 11.3 Inference on a New Image

```python
results = model("path/to/image.jpg")
for box in results[0].boxes:
    xyxy = box.xyxy[0].tolist()     # [x1, y1, x2, y2] pixels
    cls  = int(box.cls[0])
    conf = float(box.conf[0])
    print(f"Class: {['mannequin','tent'][cls]}, Conf: {conf:.2f}, Box: {xyxy}")

results[0].save("output.jpg")   # saves image with boxes drawn
```

---

## Part 12: Improving Performance

### 12.1 Background Compositing (Highest Impact)

The renders currently use HDRI backgrounds which look synthetic. Compositing the object over real photographs significantly closes the sim-to-real gap. This works because you rendered with Transparent film mode (Part 3.9), giving RGBA output.

Collect 200+ real background photos and save to `project/backgrounds/`. Add this to your render scripts and call `composite_on_background(img_path)` immediately after `bpy.ops.render.render(write_still=True)`:

```python
import cv2
import numpy as np

BACKGROUND_DIR = "/absolute/path/to/project/backgrounds/"

bg_files = [
    os.path.join(BACKGROUND_DIR, f)
    for f in os.listdir(BACKGROUND_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

def composite_on_background(render_path):
    """Alpha-composite RGBA render over a random real background. Overwrites render_path."""
    render = cv2.imread(render_path, cv2.IMREAD_UNCHANGED)
    if render is None or render.shape[2] < 4:
        return
    bg    = cv2.imread(random.choice(bg_files))
    bg    = cv2.resize(bg, (render.shape[1], render.shape[0]))
    alpha = render[:, :, 3:4].astype(float) / 255.0
    rgb   = render[:, :, :3].astype(float)
    comp  = (alpha * rgb + (1.0 - alpha) * bg.astype(float)).astype(np.uint8)
    cv2.imwrite(render_path, comp)
```

### 12.2 Fine-tune on a Small Real Dataset

Collect 50–100 real images, annotate them in [Label Studio](https://labelstud.io) or [Roboflow](https://roboflow.com) (draw boxes manually, export YOLO format), then fine-tune from your synthetic weights:

```python
model = YOLO("project/runs/v1/weights/best.pt")
model.train(
    data="project/training/real_finetune.yaml",
    epochs=20,
    imgsz=640,
    batch=8,
    lr0=1e-4,
)
```

### 12.3 If mAP is Still Low — Ranked Checklist

1. Widen `BONE_LIMITS` ranges or add more bones to increase pose diversity
2. Add background compositing (12.1) if not already done
3. Generate more data (2000–5000 renders per class)
4. Increase HDRI variety
5. Step up to `yolov8s` or `yolov8m` backbone
6. Train more epochs (100–150)
7. Collect more real fine-tuning images

---

## Quick Reference

### Class ID Map

| Class     | ID |
|-----------|----|
| mannequin | 0  |
| tent      | 1  |

### Key File Locations

| File                    | Path                                          |
|-------------------------|-----------------------------------------------|
| YOLO best weights       | `project/runs/v1/weights/best.pt`             |
| Training config         | `project/training/dataset.yaml`               |
| Mannequin render script | `project/blender/scripts/render_mannequin.py` |
| Tent render script      | `project/blender/scripts/render_tent.py`      |
| Mannequin images        | `project/dataset/images/train/mannequin_*.png`|
| Tent images             | `project/dataset/images/train/tent_*.png`     |
| Labels                  | Same structure under `labels/`, `.txt` ext    |

### Render Script Checklist (Before Each Full Job)

- [ ] All absolute paths updated in the script
- [ ] `MESH_NAME` and `ARMATURE_NAME` match outliner names exactly
- [ ] `BONE_LIMITS` keys verified against actual bone names in Pose Mode
- [ ] `NUM_RENDERS` set back to 1000 after test run
- [ ] 5-render test completed and labels visually verified
