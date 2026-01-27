import asyncio
import math
from mavsdk import System

def rad2deg(rad):
    return rad * 180.0 / math.pi

async def run():
    drone = System()
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Drone connected")
            break

    async def health_task():
        async for health in drone.telemetry.health():
            print(
                f"[HEALTH] "
                f"GPS: {health.is_global_position_ok} | "
                f"Home: {health.is_home_position_ok} | "
                f"IMU: {health.is_accelerometer_calibration_ok} | "
                f"Gyro: {health.is_gyrometer_calibration_ok} | "
                f"Mag: {health.is_magnetometer_calibration_ok}"
            )
            await asyncio.sleep(0.1)

    async def attitude_task():
        async for attitude in drone.telemetry.attitude_euler():
            print(
                f"[ATTITUDE ]"
                f"Roll: {attitude.roll_deg} | "
                f"Pitch: {attitude.pitch_deg} | "
                f"Yaw: {attitude.yaw_deg}"
            )
            await asyncio.sleep(0.1)

    await asyncio.gather(
        health_task(),
        attitude_task()
    )

if __name__ == "__main__":
    asyncio.run(run())

