import asyncio
from mavsdk import System

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    await drone.connect()
    
    async for state in drone.core.connection_state():
        if state.is_connected:
            break
    
    print("🔧 Disabling health check...")
    await drone.param.set_param_int("COM_ARM_HFLT_CHK", 0)
    print("✅ COM_ARM_HFLT_CHK = 0 (Disabled)")
    
    await asyncio.sleep(1)
    
    print("\n🚀 Attempting ARM...")
    await drone.action.arm()
    await asyncio.sleep(2)
    
    async for armed in drone.telemetry.armed():
        if armed:
            print("✅ ✅ ✅ ARMED! ✅ ✅ ✅")
        break
    
    await asyncio.sleep(3)
    await drone.action.disarm()
    print("✅ DISARMED")

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
