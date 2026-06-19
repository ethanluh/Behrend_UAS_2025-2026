"""Run the kinematic closed-loop simulator and report convergence.

Validates the perception->control law (centering + approach-to-standoff) with no
camera, MAVLink, or PX4. Prints a trajectory table and a summary; optionally
writes CSV.

Example:
    python sim_run.py --start-x -8 --start-y 4 --start-yaw 40 --standoff 2
"""

import argparse
import math

from decision import DecisionConfig, ControlGains
from sim import VehicleState, Target, simulate


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start-x", type=float, default=-8.0)
    p.add_argument("--start-y", type=float, default=3.0)
    p.add_argument("--start-yaw", type=float, default=30.0, help="degrees")
    p.add_argument("--target-x", type=float, default=0.0)
    p.add_argument("--target-y", type=float, default=0.0)
    p.add_argument("--target-class", type=int, default=0, choices=[0, 1])
    p.add_argument("--hfov", type=float, default=60.0)
    p.add_argument("--standoff", type=float, default=2.0)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--dt", type=float, default=0.1)
    p.add_argument("--csv", default=None, help="optional path to write the trajectory")
    return p.parse_args()


def main():
    args = parse_args()
    config = DecisionConfig(
        target_class=args.target_class,
        hfov_deg=args.hfov,
        standoff_m=args.standoff,
        gains=ControlGains(),
    )
    vehicle = VehicleState(x=args.start_x, y=args.start_y,
                           yaw=math.radians(args.start_yaw))
    target = Target(x=args.target_x, y=args.target_y, class_id=args.target_class)

    traj = simulate(vehicle, target, config, steps=args.steps, dt=args.dt)

    print(f"{'t':>6} {'x':>7} {'y':>7} {'yaw':>7} {'action':>7} "
          f"{'bearing':>8} {'range':>7} {'vx':>6} {'yaw_rate':>8}")
    for r in traj[::max(1, len(traj) // 20)]:   # ~20 sampled rows
        print(f"{r.t:6.1f} {r.x:7.2f} {r.y:7.2f} {math.degrees(r.yaw):7.1f} "
              f"{r.action:>7} {r.bearing_deg:8.1f} {r.distance_m:7.2f} "
              f"{r.velocity_cmd[0]:6.2f} {r.velocity_cmd[2]:8.2f}")

    final = traj[-1]
    print("\n── convergence ──")
    print(f"final bearing : {final.bearing_deg:+.1f} deg (target: ~0)")
    print(f"final range   : {final.distance_m:.2f} m (standoff: {args.standoff})")
    tracked = sum(1 for r in traj if r.action == "track")
    print(f"frames tracked: {tracked}/{len(traj)}")

    if args.csv:
        with open(args.csv, "w") as f:
            f.write("t,x,y,yaw_deg,action,bearing_deg,range_m,vx,vy,yaw_rate\n")
            for r in traj:
                f.write(f"{r.t},{r.x},{r.y},{math.degrees(r.yaw)},{r.action},"
                        f"{r.bearing_deg},{r.distance_m},"
                        f"{r.velocity_cmd[0]},{r.velocity_cmd[1]},{r.velocity_cmd[2]}\n")
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
