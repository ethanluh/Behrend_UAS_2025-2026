from pymavlink import mavutil
import time

# Initialize connection
master = mavutil.mavlink_connection("/dev/ttyACM0", baud=57600, autoreconnect=True)
master.wait_heartbeat()
print("Heartbeat received!")

def set_servo(value):
    """
    value: -1.0 to 1.0 (maps to 1000us - 2000us)
    param1: Value for Actuator 1
    param7: 0 (Direct Actuator Control)
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_ACTUATOR,
        0,          # confirmation
        value,      # param1: Actuator 1
        0, 0, 0, 0, 0, # param2-6: Actuators 2-6 (unused)
        0           # param7: Index (0 = first set of actuators)
    )

# PX4 usually requires arming to output PWM
print("Arming...")
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

# Sweep the servo
try:
    print("Sweeping Actuator...")
    for i in range(-10, 11):
        val = i / 10.0
        print(f"Setting to {val}")
        set_servo(val)
        time.sleep(0.5)
finally:
    print("Disarming...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)
