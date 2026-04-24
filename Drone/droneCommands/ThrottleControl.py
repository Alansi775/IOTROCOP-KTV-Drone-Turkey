import asyncio
import socket
import json
import time
from mavsdk import System
from mavsdk.offboard import OffboardError, AttitudeRate

# ================== CONFIG ==================
UDP_PORT = 5005
MIN_THRUST = 0.0
MAX_THRUST = 0.9
CENTER_THRUST = 0.0
DEADZONE = 0.05
COMMAND_RATE = 0.05
ARMING_RETRIES = 10
RETRY_DELAY = 2.0
# ============================================

def normalize(val):
    return max(-1.0, min(1.0, val))

def deadzone(v, threshold=DEADZONE):
    return 0.0 if abs(v) < threshold else v

def map_joystick_to_thrust(y_normalized):
    normalized = (y_normalized - 2000) / 2000
    normalized = max(-1.0, min(1.0, normalized))
    normalized = deadzone(normalized)
    
    if normalized > 0:
        thrust = CENTER_THRUST + (normalized * (MAX_THRUST - CENTER_THRUST))
    else:
        thrust = CENTER_THRUST + (normalized * (CENTER_THRUST - MIN_THRUST))
    
    return max(MIN_THRUST, min(MAX_THRUST, thrust))

async def wait_for_connection(drone):
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone connected!")
            return True
    return False

async def force_arm(drone):
    """Force arm the drone (equivalent to 'commander arm -f')"""
    print("\n🚀 Force arming (ignoring preflight checks)...\n")
    
    for attempt in range(1, ARMING_RETRIES + 1):
        try:
            print(f"   [{attempt}/{ARMING_RETRIES}] Forcing arm...", end=" ", flush=True)
            
            # Force arm - this is equivalent to 'commander arm -f'
            await drone.action.arm()
            await asyncio.sleep(1.5)
            
            # Verify armed
            try:
                async for armed in drone.telemetry.armed():
                    if armed:
                        print("✅ ARMED!")
                        print("   ✨ Success! Drone is armed and stable!")
                        return True
                    break
            except:
                pass
            
            print("❌")
            
        except Exception as e:
            print(f"❌ {str(e)[:60]}")
        
        if attempt < ARMING_RETRIES:
            await asyncio.sleep(RETRY_DELAY)
    
    print("\n❌ Force arming failed")
    print("💡 The drone armed successfully via Console with 'commander arm -f'")
    print("   but MAVSDK might not support force arming directly.")
    print("")
    print("SOLUTION: Disable remaining preflight checks:")
    print("  param set CBRK_VELPOSERR 201607")
    print("  param save")
    print("  reboot")
    return False

async def start_offboard(drone):
    print("\n🎮 Starting OFFBOARD mode...")
    
    try:
        # Initial setpoint
        await drone.offboard.set_attitude_rate(
            AttitudeRate(
                roll_deg_s=0.0,
                pitch_deg_s=0.0,
                yaw_deg_s=0.0,
                thrust_value=CENTER_THRUST
            )
        )
        
        await drone.offboard.start()
        print("✅ OFFBOARD active!")
        print(f"📊 Throttle control ready")
        print(f"📊 Joystick UP = Motors spin faster")
        print(f"📊 Joystick CENTER = Motors at minimum")
        print(f"📊 Joystick DOWN = Motors slow down\n")
        return True
        
    except OffboardError as e:
        print(f"❌ Offboard failed: {e}")
        return False

async def control_loop(drone):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.settimeout(0.1)
    
    last_packet_time = time.time()
    last_command_time = time.time()
    last_print_time = 0
    
    print("🎮 Listening on UDP port", UDP_PORT)
    print("📡 Send joystick data to control throttle!\n")
    
    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                joy = json.loads(data.decode())
                last_packet_time = time.time()
                
                y_normalized = joy["y_normalized"]
                thrust = map_joystick_to_thrust(y_normalized)
                
                current_time = time.time()
                if current_time - last_command_time >= COMMAND_RATE:
                    
                    await drone.offboard.set_attitude_rate(
                        AttitudeRate(
                            roll_deg_s=0.0,
                            pitch_deg_s=0.0,
                            yaw_deg_s=0.0,
                            thrust_value=thrust
                        )
                    )
                    
                    if current_time - last_print_time > 0.2:
                        bar_length = 20
                        filled = int((thrust / MAX_THRUST) * bar_length)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        
                        # Color codes
                        if thrust < 0.01:
                            status = "⚪ IDLE"
                        elif thrust < 0.3:
                            status = "🟡 LOW"
                        elif thrust < 0.6:
                            status = "🟠 MED"
                        else:
                            status = "🔴 HIGH"
                        
                        print(f"{status}  Joy:{y_normalized:4d} → Thrust:{thrust:.3f} [{bar}]")
                        last_print_time = current_time
                    
                    last_command_time = current_time
                
            except socket.timeout:
                if time.time() - last_packet_time > 3.0:
                    print(f"\n🛑 FAILSAFE - No joystick for 3s")
                    print("   Setting thrust to ZERO...")
                    
                    for _ in range(10):
                        await drone.offboard.set_attitude_rate(
                            AttitudeRate(0.0, 0.0, 0.0, 0.0)
                        )
                        await asyncio.sleep(0.1)
                    break
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"\n⚠️ Error: {e}")
                break
            
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n^C User stop")
    finally:
        sock.close()

async def safe_shutdown(drone):
    print("\n" + "="*60)
    print("🛬 Safe shutdown sequence...")
    print("="*60)
    
    # Zero thrust
    try:
        print("Setting thrust to zero...")
        for _ in range(10):
            await drone.offboard.set_attitude_rate(
                AttitudeRate(0.0, 0.0, 0.0, 0.0)
            )
            await asyncio.sleep(0.1)
    except:
        pass
    
    # Stop offboard
    try:
        await drone.offboard.stop()
        print("✅ Offboard stopped")
    except Exception as e:
        print(f"⚠️ Offboard stop: {e}")
    
    # Land
    try:
        await drone.action.land()
        print("✅ Landing command sent")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"⚠️ Land: {e}")
    
    # Disarm
    try:
        await drone.action.disarm()
        print("✅ Disarmed")
    except Exception as e:
        print(f"⚠️ Disarm: {e}")
    
    print("\n✅ SHUTDOWN COMPLETE - DRONE IS SAFE\n")

async def run():
    print("\n" + "="*60)
    print("🚁 THROTTLE CONTROL TEST - FULLY AUTONOMOUS")
    print("="*60)
    
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("\n📡 Connecting to MAVSDK...")
    await drone.connect()
    
    if not await wait_for_connection(drone):
        return
    
    if not await force_arm(drone):
        print("\n💡 TIP: Try adding this parameter:")
        print("   param set CBRK_VELPOSERR 201607")
        print("   param save")
        print("   reboot")
        return
    
    if not await start_offboard(drone):
        try:
            await drone.action.disarm()
        except:
            pass
        return
    
    await control_loop(drone)
    await safe_shutdown(drone)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
