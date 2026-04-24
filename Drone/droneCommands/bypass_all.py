import asyncio
from mavsdk import System

async def run():
    drone = System(mavsdk_server_address="localhost", port=50051)
    await drone.connect()
    
    print("⏳ Waiting...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("🔧 Bypassing ALL safety checks...")
    params = {
        "COM_ARM_WO_GPS": 1,
        "CBRK_USB_CHK": 197848,
        "CBRK_IO_SAFETY": 22027,
        "COM_PREARM_MODE": 0,
        "CBRK_VELPOSERR": 201607,
        "COM_ARM_MAG_ANG": 60,
        "COM_ARM_IMU_ACC": 1.0,
        "COM_ARM_IMU_GYR": 0.5
    }
    
    for param, value in params.items():
        try:
            if isinstance(value, int):
                await drone.param.set_param_int(param, value)
            else:
                await drone.param.set_param_float(param, value)
            print(f"✅ {param} = {value}")
        except:
            pass
    
    await asyncio.sleep(2)
    
    print("\n🚀 ARM ATTEMPT...")
    try:
        await drone.action.arm()
        print("✅ ✅ ✅ ARMED! ✅ ✅ ✅")
        await asyncio.sleep(5)
        await drone.action.disarm()
        print("✅ DISARMED")
    except Exception as e:
        print(f"❌ {e}")

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
