#!/usr/bin/env python3
import asyncio
from mavsdk import System
from mavsdk.offboard import AttitudeRate, OffboardError

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 Connecting...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!\n")
            break
    
    print("🚀 Method 1: Normal ARM...")
    try:
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ✅ ✅ ARMED! ✅ ✅ ✅\n")
                await asyncio.sleep(3)
                await drone.action.disarm()
                print("✅ DISARMED\n")
                return
            break
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n🔧 Method 2: Force ARM via Offboard...")
    try:
        # Set offboard with zero rates
        print("   Setting offboard mode...")
        await drone.offboard.set_attitude_rate(
            AttitudeRate(0.0, 0.0, 0.0, 0.0)
        )
        
        # Start offboard
        print("   Starting offboard...")
        await drone.offboard.start()
        await asyncio.sleep(0.5)
        
        # ARM
        print("   Arming...")
        await drone.action.arm()
        await asyncio.sleep(2)
        
        # Check
        async for armed in drone.telemetry.armed():
            if armed:
                print("\n✅ ✅ ✅ ARMED VIA OFFBOARD! ✅ ✅ ✅\n")
            else:
                print("\n❌ Still not armed\n")
            break
        
        # Wait
        await asyncio.sleep(5)
        
        # Zero thrust
        print("🛑 Stopping...")
        for _ in range(10):
            await drone.offboard.set_attitude_rate(
                AttitudeRate(0.0, 0.0, 0.0, 0.0)
            )
            await asyncio.sleep(0.05)
        
        # Stop offboard & disarm
        await drone.offboard.stop()
        await drone.action.disarm()
        print("✅ DISARMED\n")
        
    except OffboardError as e:
        print(f"\n❌ Offboard error: {e}\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
