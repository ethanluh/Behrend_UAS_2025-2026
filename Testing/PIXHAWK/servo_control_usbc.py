import os
os.environ["MAVLINK_DIALECT"] = "common"

from pymavlink import mavutil
import time

master = mavutil.mavlink_connection("/dev/ttyACM0", baud=57600)
master.wait_heartbeat()
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

print("ESC arm: 1000 µs")
set_servo(12, 1000)
time.sleep(5)   # IMPORTANT
