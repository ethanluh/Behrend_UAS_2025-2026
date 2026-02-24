import asyncio
from mavsdk import System

async def reboot():
	drone = System()
	await drone.connect(system_address="serial:///dev/ttyACM0:57600")

	print(" -- Rebooting")
	await drone.action.reboot()
	print(" -- Done")

if __name__ == "__main__":
	asyncio.run(reboot());