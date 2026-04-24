import asyncio
import socket
import json
import time
import RPi.GPIO as GPIO  # أو أي library تستخدمها للـ GPIO
from mavsdk import System
from mavsdk.offboard import OffboardError, AttitudeRate

# ================== CONFIG ==================
UDP_PORT = 5005
ARM_SWITCH_PIN = 17  # GPIO pin للـ arm switch
DEADZONE = 0.15
MAX_PITCH_RATE = 30.0
MAX_YAW_RATE = 45.0
HOVER_THRUST = 0.75  # زوّدته من 0.6
FAILSAFE_TIMEOUT = 3.0
COMMAND_RATE = 0.05
# ============================================

# Setup GPIO for arm switch
GPIO.setmode(GPIO.BCM)
GPIO.setup(ARM_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def normalize(val):
    return max(-1.0, min(1.0, val))

def deadzone(v):
    return 0.0 if abs(v) < DEADZONE else v

async def wait_for_connection(drone):
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone connected!")
            return True
    return False

async def wait_for_arm_switch(drone):
    """Wait for hardware arm switch"""
    print("\n⏳ Waiting for ARM SWITCH...")
    print("   Flip the arm switch to arm the drone")
    
    while True:
        if GPIO.input(ARM_SWITCH_PIN) == GPIO.HIGH:
            print("✅ ARM SWITCH ACTIVATED!")
            
            # Try to arm
            try:
                await drone.action.arm()
                await asyncio.sleep(1)
                print("✅ ARMED!")
                return True
            except Exception as e:
                print(f"❌ Arming failed: {e}")
                await asyncio.sleep(0.5)
        
        await asyncio.sleep(0.1)

async def start_offboard(drone):
    print("\n🎮 Starting OFFBOARD mode...")
    
    try:
        await drone.offboard.set_attitude_rate(
            AttitudeRate(
                roll_deg_s=0.0,
                pitch_deg_s=0.0,
                yaw_deg_s=0.0,
                thrust_value=HOVER_THRUST
            )
        )
        
        await drone.offboard.start()
        print("✅ OFFBOARD mode active!")
        print(f"📊 Hover thrust: {HOVER_THRUST}")
        print(f"📊 UP=Forward, DOWN=Backward, LEFT=YawLeft, RIGHT=YawRight\n")
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
    last_hold_print = 0
    
    print("🎮 Waiting for joystick...\n")
    
    try:
        while True:
            # Check if arm switch is still ON
            if GPIO.input(ARM_SWITCH_PIN) == GPIO.LOW:
                print("\n🛑 ARM SWITCH OFF - Landing")
                break
            
            try:
                data, _ = sock.recvfrom(1024)
                joy = json.loads(data.decode())
                last_packet_time = time.time()
                
                x = deadzone(normalize((joy["x_normalized"] - 2000) / 2000))
                y = deadzone(normalize((joy["y_normalized"] - 2000) / 2000))
                
                pitch_rate = -y * MAX_PITCH_RATE
                yaw_rate = x * MAX_YAW_RATE
                
                current_time = time.time()
                if current_time - last_command_time >= COMMAND_RATE:
                    
                    if pitch_rate == 0 and yaw_rate == 0:
                        if current_time - last_hold_print > 1.0:
                            print("🟡 HOVERING")
                            last_hold_print = current_time
                        
                        await drone.offboard.set_attitude_rate(
                            AttitudeRate(
                                roll_deg_s=0.0,
                                pitch_deg_s=0.0,
                                yaw_deg_s=0.0,
                                thrust_value=HOVER_THRUST
                            )
                        )
                    else:
                        print(f"➡️  Pitch:{pitch_rate:+6.2f}°/s  Yaw:{yaw_rate:+6.2f}°/s")
                        
                        await drone.offboard.set_attitude_rate(
                            AttitudeRate(
                                roll_deg_s=0.0,
                                pitch_deg_s=pitch_rate,
                                yaw_deg_s=yaw_rate,
                                thrust_value=HOVER_THRUST
                            )
                        )
                    
                    last_command_time = current_time
                
            except socket.timeout:
                if time.time() - last_packet_time > FAILSAFE_TIMEOUT:
                    print(f"\n🛑 FAILSAFE - No joystick")
                    break
                
                current_time = time.time()
                if current_time - last_command_time >= COMMAND_RATE:
                    await drone.offboard.set_attitude_rate(
                        AttitudeRate(
                            roll_deg_s=0.0,
                            pitch_deg_s=0.0,
                            yaw_deg_s=0.0,
                            thrust_value=HOVER_THRUST
                        )
                    )
                    last_command_time = current_time
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"\n⚠️  Error: {e}")
                break
            
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n^C 🛑 User stop")
    finally:
        sock.close()

async def safe_shutdown(drone):
    print("\n🛬 Landing...")
    
    try:
        await drone.offboard.stop()
        print("✅ Offboard stopped")
    except:
        pass
    
    try:
        await drone.action.land()
        await asyncio.sleep(5)
    except:
        pass
    
    try:
        await drone.action.disarm()
        print("✅ Disarmed")
    except:
        pass

async def run():
    print("\n" + "="*60)
    print("🚁 DRONE CONTROL - CUSTOM RC")
    print("="*60)
    
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("\n📡 Connecting...")
    await drone.connect()
    
    if not await wait_for_connection(drone):
        return
    
    # Wait for hardware arm switch
    if not await wait_for_arm_switch(drone):
        return
    
    if not await start_offboard(drone):
        try:
            await drone.action.disarm()
        except:
            pass
        return
    
    await control_loop(drone)
    await safe_shutdown(drone)
    
    # Cleanup GPIO
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted")
        GPIO.cleanup()

