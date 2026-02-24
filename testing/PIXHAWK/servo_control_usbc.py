import asyncio
from mavsdk import System

async def run():
    drone = await connect()
    await get_px4_version(drone)
    status = await check_pixhawk_status(drone)

    if (status == False):
        print("Arming...")
        await drone.action.arm()
        print("Armed")


async def connect():
    drone = System()
    print("Waiting for drone to connect...")
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")
    print("Connected")
    return drone

async def get_px4_version(drone):
    info = drone.info
    version = await info.get_version()
    product = await info.get_product()

    print(f"Flight SW Version: {version.flight_sw_major}.{version.flight_sw_minor}.{version.flight_sw_patch}")
    print(f"OS SW Version: {version.os_sw_major}.{version.os_sw_minor}.{version.os_sw_patch}")

async def check_pixhawk_status(drone):
    async for armed in drone.telemetry.armed():
        print("Armed: ", armed)
        break

    return armed

if __name__ == "__main__":
    asyncio.run(run())
