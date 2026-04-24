import asyncio
from mavsdk import System

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 Connecting...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    # Set parameters to bypass checks
    print("🔧 Setting parameters...")
    try:
        # Allow arming without GPS
        await drone.param.set_param_int("COM_ARM_WO_GPS", 1)
        print("✅ COM_ARM_WO_GPS = 1")
        
        # Disable preflight checks
        await drone.param.set_param_int("CBRK_USB_CHK", 197848)
        print("✅ CBRK_USB_CHK = 197848")
        
        await asyncio.sleep(1)
        
        print("🚀 Attempting ARM...")
        await drone.action.arm()
        print("✅ ✅ ✅ ARM SUCCESS! ✅ ✅ ✅")
        
        await asyncio.sleep(3)
        
        print("🛑 Disarming...")
        await drone.action.disarm()
        print("✅ DISARM SUCCESS!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
