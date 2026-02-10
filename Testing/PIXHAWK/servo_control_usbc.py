import asyncio
from mavsdk import System
from mavsdk.offboard import ActuatorControl, OffboardError

async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")

    async for state in drone.core.connection_state():
        if state.is_connected:
            break

    print("Connected")

    await drone.action.arm()

    # Actuator array: 8 channels
    # motor 1 → index 0
    actuators = [0.0] * 8
    actuators[0] = 0.5  # 50% throttle

    try:
        await drone.offboard.set_actuator_control(
            ActuatorControl(group=0, controls=actuators)
        )
        await drone.offboard.start()
        print("Actuator control started")

        await asyncio.sleep(3)

    except OffboardError as e:
        print(e)

    actuators[0] = 0.0
    await drone.offboard.set_actuator_control(
        ActuatorControl(group=0, controls=actuators)
    )

    await drone.action.disarm()

asyncio.run(run())
