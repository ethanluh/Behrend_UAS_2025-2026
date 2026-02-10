import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected")
            break

    # AUX 4 = servo 12
    print("Setting AUX 4 to 1500 µs")
    await drone.action.set_servo(12, 1500)
    await asyncio.sleep(3)

    print("Setting AUX 4 to 1100 µs")
    await drone.action.set_servo(12, 1100)
    await asyncio.sleep(3)

    print("Setting AUX 4 to 1900 µs")
    await drone.action.set_servo(12, 1900)
    await asyncio.sleep(3)

    print("Stopping output")
    await drone.action.set_servo(12, 0)

asyncio.run(run())
