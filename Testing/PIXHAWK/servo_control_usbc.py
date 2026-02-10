import os
os.environ["MAVLINK_DIALECT"] = "common"

from pymavlink import mavutil
import time

# Connect over USB
master = mavutil.mavlink_connection(
    "/dev/ttyACM0",
    baud=57600,
    autoreconnect=True
)

print("Waiting for heartbeat...")
master.wait_heartbeat(timeout=10)
print("Connected")

def set_servo(servo, pwm):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        servo, pwm,
        0, 0, 0, 0, 0
    )

# AUX 4 = servo 12
print("AUX 4 → 1500 µs")
set_servo(12, 1500)
time.sleep(3)

print("AUX 4 → 1100 µs")
set_servo(12, 1100)
time.sleep(3)

print("AUX 4 → 1900 µs")
set_servo(12, 1900)
time.sleep(3)

print("Stopping")
set_servo(12, 0)
