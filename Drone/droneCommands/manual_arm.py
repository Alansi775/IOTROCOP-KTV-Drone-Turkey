import asyncio
from mavsdk import System

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    await drone.connect()
    
    print("⏳ Connecting...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("\n🔧 Setting Manual Mode...")
    try:
        # Set to Manual/Stabilized mode
        await drone.action.set_flight_mode("MANUAL")
        await asyncio.sleep(1)
        print("✅ Manual mode set")
    except:
        pass
    
    print("\n🚀 Attempting ARM...")
    try:
        await drone.action.arm()
        await asyncio.sleep(2)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ✅ ✅ ARMED! ✅ ✅ ✅")
            else:
                print("❌ Not armed")
            break
        
        await asyncio.sleep(3)
        
        print("\n🛑 Disarming...")
        await drone.action.disarm()
        print("✅ DISARMED")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
