import asyncio
from mavsdk import System

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 Connecting to drone...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("🚀 Attempting FORCE ARM...")
    try:
        await drone.action.arm()
        print("✅ ARM SUCCESS!")
        await asyncio.sleep(3)
        
        print("🛑 Disarming...")
        await drone.action.disarm()
        print("✅ DISARM SUCCESS!")
    except Exception as e:
        print(f"❌ Error: {e}")
        # Try force arm
        print("🔧 Trying FORCE ARM...")
        try:
            await drone.action.arm_force()
            print("✅ FORCE ARM SUCCESS!")
            await asyncio.sleep(3)
            await drone.action.disarm()
            print("✅ DISARM SUCCESS!")
        except Exception as e2:
            print(f"❌ Force ARM failed: {e2}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
