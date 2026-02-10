import asyncio
from mavsdk import System
from mavsdk.mavlink import MavlinkPassthrough
from pymavlink import mavutil

async def run():
    drone = System()
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected")
            break

    mavlink = MavlinkPassthrough(drone)

    print("Setting AUX 4 (servo 12) to 1500 µs")
    await mavlink.send_command_long(
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        param1=12,      # servo number (AUX 4)
        param2=1500,    # PWM
        param3=0,
        param4=0,
        param5=0,
        param6=0,
        param7=0,
    )

    await asyncio.sleep(3)

    print("Setting AUX 4 to 1100 µs")
    await mavlink.send_command_long(
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        param1=12,
        param2=1100,
        param3=0,
        param4=0,
        param5=0,
        param6=0,
        param7=0,
    )

    await asyncio.sleep(3)

    print("Setting AUX 4 to 1900 µs")
    await mavlink.send_command_long(
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        param1=12,
        param2=1900,
        param3=0,
        param4=0,
        param5=0,
        param6=0,
        param7=0,
    )

asyncio.run(run())
