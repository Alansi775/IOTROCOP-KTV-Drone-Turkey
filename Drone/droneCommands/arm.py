# arm_disarm.py
import asyncio
from mavsdk import System

async def run():
    # اتأكد ان العنوان والport صحيح
    drone = System(mavsdk_server_address="localhost", port=50051)
    await drone.connect()

    print("Waiting for drone to be ready...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Drone discovered!")
            break
    
    print("Arming drone...")
    await drone.action.arm()
    await asyncio.sleep(3)  # خليها مسلحة 3 ثواني

    print("Disarming drone...")
    await drone.action.disarm()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(run())

