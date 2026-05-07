import asyncio
from mavsdk import System

async def test():
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 Connecting...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("\n🧪 Testing telemetry methods:\n")
    
    # Test 1: position
    print("1️⃣ Testing position()...")
    try:
        async for pos in drone.telemetry.position():
            print(f"   Position: {pos.latitude_deg}, {pos.longitude_deg}")
            break
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: gps_info
    print("\n2️⃣ Testing gps_info()...")
    try:
        async for gps in drone.telemetry.gps_info():
            print(f"   GPS: {gps.num_satellites} sats, fix: {gps.fix_type}")
            break
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test())
