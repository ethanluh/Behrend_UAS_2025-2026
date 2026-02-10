from pymavlink import mavutil
import time

# Connect to Pixhawk
mav = mavutil.mavlink_connection('/dev/ttyACM0', baud=57600)
mav.wait_heartbeat()

servo_channel = 8  # AUX4

# Sweep from 1000 -> 2000 -> 1000 μs
pwm = 1000
direction = 1

try:
    while True:
        mav.mav.command_long_send(
            mav.target_system,
            mav.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0,
            servo_channel,
            pwm,
            0,0,0,0,0
        )
        pwm += 20 * direction
        if pwm >= 2000:
            pwm = 2000
            direction = -1
        elif pwm <= 1000:
            pwm = 1000
            direction = 1
        time.sleep(0.05)
except KeyboardInterrupt:
    # Return to neutral
    mav.mav.command_long_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        servo_channel,
        1500,
        0,0,0,0,0
    )
    print("Stopped sweep, servo neutral")
