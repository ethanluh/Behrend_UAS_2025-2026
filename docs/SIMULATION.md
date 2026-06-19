# Simulation

Two ways to validate the perception→control law before risking a vehicle.

## A. Pure control-law validator (no install, runs in CI)

`integration/sim.py` closes the loop *without* a camera, MAVLink, or PX4. It
places a target in the world, projects it into a synthetic bounding box (a
forward pinhole-camera model — the inverse of `decision.estimate_distance`),
feeds that through the **real** `decision.decide()`, and integrates the returned
body-velocity command to advance the vehicle. This proves the controller centers
the target and converges to the standoff distance.

```bash
python integration/sim_run.py --start-x -8 --start-y 0 --start-yaw 15 --standoff 2
```

Sample output converges from ~15° bearing / 8 m to ~0° / standoff and holds:

```
   t       x       y     yaw  action  bearing   range     vx yaw_rate
   0.0   -8.00    0.00    15.0   track     15.0    8.00   1.00     0.50
   3.0   -5.01    0.11     0.3   track      1.5    5.01   1.00     0.05
   9.0   -2.28    0.09    -0.9   track      1.4    2.29   0.00     0.00
── convergence ──
final bearing : +1.4 deg (target: ~0)
final range   : 2.29 m (standoff: 2.0)
```

Residual bearing/range offsets are the controller's deadbands working as
intended. The convergence and stability properties are asserted in
`tests/test_sim.py` (pure, runs under `pytest -q`).

> Convention note: `decision`/PX4 use NED yaw (positive = clockwise / turn toward
> a target on the image's right). The simulator's world yaw is CCW-from-+x, so
> `sim.step()` negates the commanded yaw rate to bridge the two.

## B. PX4 SITL (software-in-the-loop)

Run the actual node against the PX4 flight stack in simulation — no real
vehicle, but the genuine autopilot, MAVLink, and OFFBOARD path.

### 1. Launch PX4 SITL

```bash
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
make px4_sitl jmavsim          # or: make px4_sitl gz_x500
```

SITL exposes MAVSDK on `udpin://0.0.0.0:14540`.

### 2. Run the node against it

SITL has no camera, so feed a recorded clip as the source:

```bash
pip install -r integration/requirements.txt

# Observe-only first (safe): prints bearing/range, sends nothing
python integration/perception_control_node.py \
    --weights best.pt --source clip.mp4 \
    --mavlink udpin://0.0.0.0:14540 --hfov <calibrated>

# Closed-loop: arm in QGroundControl (or `commander arm` in the SITL shell) first
python integration/perception_control_node.py \
    --weights best.pt --source clip.mp4 \
    --mavlink udpin://0.0.0.0:14540 --enable-control --hfov <calibrated> \
    --max-speed 0.5 --log-file sitl.jsonl --record sitl.mp4
```

The `SafetyGate` applies exactly as on hardware: nothing is commanded unless the
vehicle is armed, `--enable-control` is set, and a fresh detection exists. Watch
the vehicle yaw/approach toward the detected target in jMAVSim/Gazebo, then
review `sitl.jsonl` / `sitl.mp4`.

### 3. Then move to hardware

Once SITL behavior looks correct, follow `docs/HARDWARE_RUNBOOK.md` — bench
observe-only (props off) → armed closed-loop → flight.
