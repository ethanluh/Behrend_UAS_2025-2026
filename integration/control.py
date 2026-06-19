"""MAVSDK control wrapper for the perception loop.

Reuses the connection and telemetry idioms already proven in
``testing/PIXHAWK/nano_pixhawk_usbc_connection.py`` and
``testing/PIXHAWK/servo_control_usbc.py``:

  * connect via ``serial:///dev/ttyACM0:57600`` and wait on
    ``drone.core.connection_state()``
  * read armed state via ``drone.telemetry.armed()``

SAFETY: this wrapper never arms the vehicle automatically. The operator arms
manually; the node only sends velocity setpoints while the SafetyGate permits
it. mavsdk is imported lazily so the module imports without it installed.
"""

import asyncio
import math

DEFAULT_ADDRESS = "serial:///dev/ttyACM0:57600"


class Controller:
    def __init__(self, address=DEFAULT_ADDRESS):
        self.address = address
        self.drone = None
        self._offboard_started = False
        self._armed = False
        self._armed_task = None

    async def connect(self):
        from mavsdk import System
        self.drone = System()
        await self.drone.connect(system_address=self.address)
        print(f"Waiting for drone to connect ({self.address})...")
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                print("Drone connected")
                break
        return self.drone

    async def read_armed_once(self):
        """Read the current armed state from a single telemetry sample."""
        async for armed in self.drone.telemetry.armed():
            self._armed = armed
            return armed
        return False

    def start_armed_watch(self):
        """Keep ``armed`` fresh from one long-lived subscription instead of
        re-subscribing every loop iteration."""
        if self._armed_task is None:
            self._armed_task = asyncio.create_task(self._watch_armed())

    async def _watch_armed(self):
        async for armed in self.drone.telemetry.armed():
            self._armed = armed

    @property
    def armed(self):
        """Latest cached armed state (updated by the watch task)."""
        return self._armed

    async def start_offboard(self):
        """Enter OFFBOARD mode with a zero setpoint. Requires the vehicle to be
        already armed (operator responsibility)."""
        from mavsdk.offboard import OffboardError, VelocityBodyYawspeed
        await self.drone.offboard.set_velocity_body(
            VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
        try:
            await self.drone.offboard.start()
            self._offboard_started = True
        except OffboardError as e:
            print(f"Offboard start failed: {e._result.result}")
            raise

    async def send_velocity(self, vx, vy, yaw_rate):
        """Send a body-frame velocity setpoint (forward, right, down=0, yaw).

        ``yaw_rate`` arrives in rad/s (decision.py convention); MAVSDK's
        VelocityBodyYawspeed expects the yaw component in deg/s, so convert here.
        """
        from mavsdk.offboard import VelocityBodyYawspeed
        await self.drone.offboard.set_velocity_body(
            VelocityBodyYawspeed(vx, vy, 0.0, math.degrees(yaw_rate)))

    async def hold(self):
        """Zero the velocity setpoint (stop moving, stay in offboard)."""
        from mavsdk.offboard import VelocityBodyYawspeed
        if self._offboard_started:
            await self.drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))

    async def stop(self):
        """Leave offboard mode, command a hold, and stop the armed watch."""
        if self._armed_task is not None:
            self._armed_task.cancel()
            self._armed_task = None
        if self._offboard_started:
            await self.drone.offboard.stop()
            self._offboard_started = False
