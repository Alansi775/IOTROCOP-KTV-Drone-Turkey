import asyncio
from mavsdk import System
from mavsdk.offboard import AttitudeRate, OffboardError

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    await drone.connect()
    
    print("⏳ Connecting...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("\n🚀 Method 1: Normal ARM...")
    try:
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ✅ ✅ ARMED! ✅ ✅ ✅")
                await asyncio.sleep(3)
                await drone.action.disarm()
                print("✅ DISARMED")
                return
            break
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n🔧 Method 2: Force ARM via Offboard...")
    try:
        # Set offboard mode with zero rates
        await drone.offboard.set_attitude_rate(
            AttitudeRate(0.0, 0.0, 0.0, 0.0)
        )
        
        # Start offboard
        print("   Starting offboard...")
        await drone.offboard.start()
        await asyncio.sleep(0.5)
        
        # Now ARM
        print("   Arming...")
        await drone.action.arm()
        await asyncio.sleep(2)
        
        # Check
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ✅ ✅ ARMED VIA OFFBOARD! ✅ ✅ ✅")
            else:
                print("❌ Still not armed")
            break
        
        await asyncio.sleep(3)
        
        # Disarm & stop offboard
        await drone.action.disarm()
        await drone.offboard.stop()
        print("✅ DISARMED & Offboard stopped")
        
    except OffboardError as e:
        print(f"❌ Offboard error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
