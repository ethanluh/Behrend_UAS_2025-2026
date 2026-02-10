from pymavlink import mavutil
import time
import os

os.environ["MAVLINK_DIALECT"] = "common"

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

# MAIN 1 = servo 1
print("Arming sequence: 1000 µs for 5s")
set_servo(1, 1000)
time.sleep(5)

print("Throttle ramp: 1200 → 1400 µs")
set_servo(1, 1200)
time.sleep(3)
set_servo(1, 1400)
time.sleep(3)

print("Stop")
set_servo(1, 1000)
