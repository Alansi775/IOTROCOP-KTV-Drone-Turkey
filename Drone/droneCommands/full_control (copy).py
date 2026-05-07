import asyncio
import socket
import json
import struct
import time
from mavsdk import System
from mavsdk.offboard import OffboardError, AttitudeRate

# ================== CONFIG ==================
UDP_PORT = 5656
DEADZONE = 0.10
MAX_PITCH_RATE = 30.0
MAX_ROLL_RATE = 30.0
MIN_THRUST = 0.0
MAX_THRUST = 0.9
COMMAND_RATE = 0.05
FAILSAFE_TIMEOUT = 3.0
# ============================================

SWITCH_MANUAL_MODE_BIT = 9    # Bit 9 = Manual/Hold
SWITCH_ARM_BIT = 12           # Bit 12 = ARM/DISARM

def normalize(val, min_val=-100, max_val=100):
    normalized = (val - ((max_val + min_val) / 2)) / ((max_val - min_val) / 2)
    return max(-1.0, min(1.0, normalized))

def deadzone(v, threshold=DEADZONE):
    return 0.0 if abs(v) < threshold else v

def map_throttle(power_percent):
    power_percent = max(0.0, min(100.0, power_percent))
    thrust = MIN_THRUST + (power_percent / 100.0) * (MAX_THRUST - MIN_THRUST)
    return thrust

def parse_binary_packet(data):
    if len(data) != 17:
        return None
    
    try:
        unpacked = struct.unpack('<BhhhhhBBHBB', data)
        
        if unpacked[0] != 0xAA or unpacked[-1] != 0x55:
            return None
        
        packet = {
            'drone_x_norm': unpacked[1],
            'drone_y_norm': unpacked[2],
            'power_y_norm': unpacked[3],
            'comp_x_norm': unpacked[4],
            'comp_y_norm': unpacked[5],
            'pot1_percent': unpacked[6],
            'pot2_percent': unpacked[7],
            'switch_states': unpacked[8],
            'timestamp': time.time()
        }
        
        return packet
        
    except Exception as e:
        print(f"⚠️  Parse error: {e}")
        return None

def extract_switch_state(switch_states, bit_position):
    return (switch_states >> bit_position) & 1

async def wait_for_connection(drone):
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone connected!")
            return True
    return False

async def try_arm_once(drone):
    """محاولة ARM مرة واحدة - بالقوة!"""
    try:
        # Method 1: Normal arm
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ARMED!")
                return True
            break
        
    except:
        pass
    
    # Method 2: Force arm (لو فشل Normal)
    print("   Trying force arm...")
    try:
        # لا يوجد force arm في MAVSDK
        # لكن ممكن نبدأ OFFBOARD فوراً وهذا يسمح بالتسليح
        await drone.offboard.set_attitude_rate(
            AttitudeRate(0.0, 0.0, 0.0, 0.0)
        )
        await drone.offboard.start()
        await asyncio.sleep(0.5)
        
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print("✅ ARMED (force)!")
                return True
            break
    except Exception as e:
        print(f"❌ Force ARM failed: {e}")
    
    return False

async def try_start_offboard_once(drone):
    """محاولة بدء OFFBOARD مرة واحدة فقط"""
    try:
        await drone.offboard.set_attitude_rate(
            AttitudeRate(
                roll_deg_s=0.0,
                pitch_deg_s=0.0,
                yaw_deg_s=0.0,
                thrust_value=0.0
            )
        )
        
        await drone.offboard.start()
        print("✅ OFFBOARD active!")
        return True
        
    except OffboardError as e:
        print(f"❌ OFFBOARD failed: {e}")
        return False

async def main_loop(drone, sock):
    """
    الحلقة الرئيسية - تشتغل طول الوقت
    تراقب الـ switches وتتفاعل معها
    """
    
    sock.settimeout(0.1)
    
    last_packet_time = time.time()
    last_command_time = time.time()
    last_print_time = 0
    
    # حالات النظام
    last_manual_mode_bit = 0
    last_arm_bit = 0
    is_armed = False
    is_offboard = False
    
    print("\n" + "="*70)
    print("🎮 SYSTEM ACTIVE - Monitoring switches...")
    print("="*70)
    print("\n📊 Waiting for switch inputs...\n")
    
    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                packet = parse_binary_packet(data)
                
                if not packet:
                    continue
                
                last_packet_time = time.time()
                
                # استخرج حالات الـ switches
                manual_mode_bit = extract_switch_state(packet['switch_states'], SWITCH_MANUAL_MODE_BIT)
                arm_bit = extract_switch_state(packet['switch_states'], SWITCH_ARM_BIT)
                
                # ==================== MANUAL MODE SWITCH ====================
                # اكتشف تغيير في Manual Mode switch
                if manual_mode_bit != last_manual_mode_bit:
                    if manual_mode_bit == 1:
                        print("\n🔧 Mode Switch → MANUAL MODE")
                        # حاول التغيير
                        try:
                            await drone.action.set_flight_mode("STABILIZED")
                            print("   Flight mode: STABILIZED")
                        except:
                            try:
                                await drone.action.set_flight_mode("MANUAL")
                                print("   Flight mode: MANUAL")
                            except:
                                print("   ⚠️  Mode change failed (will use OFFBOARD instead)")
                    else:
                        print("\n🔧 Mode Switch → HOLD MODE")
                        print("   Flight mode: HOLD")
                    
                    last_manual_mode_bit = manual_mode_bit
                
                # ==================== ARM SWITCH ====================
                # اكتشف تغيير في ARM switch
                if arm_bit != last_arm_bit:
                    if arm_bit == 1:
                        # ARM switch تم تفعيله
                        print("\n🚀 ARM Switch ON → Trying to ARM...")
                        
                        # محاولة واحدة فقط
                        is_armed = await try_arm_once(drone)
                        
                        if is_armed:
                            # بدء OFFBOARD
                            print("🎮 Starting OFFBOARD...")
                            is_offboard = await try_start_offboard_once(drone)
                            
                            if is_offboard:
                                print("\n📊 Controls:")
                                print("   Joystick 1: Pitch/Roll")
                                print("   Joystick 2: Throttle")
                                print("   ARM Switch OFF → DISARM\n")
                        else:
                            print("⚠️  Cannot start - drone not armed")
                            print("💡 Check: param set CBRK_VELPOSERR 201607\n")
                    
                    else:
                        # ARM switch تم إيقافه
                        print("\n🛑 ARM Switch OFF → DISARM")
                        
                        # إيقاف OFFBOARD
                        if is_offboard:
                            try:
                                # صفّر الـ thrust أولاً
                                for _ in range(10):
                                    await drone.offboard.set_attitude_rate(
                                        AttitudeRate(0.0, 0.0, 0.0, 0.0)
                                    )
                                    await asyncio.sleep(0.05)
                                
                                await drone.offboard.stop()
                                print("✅ OFFBOARD stopped")
                                is_offboard = False
                            except:
                                pass
                        
                        # فك التسليح
                        if is_armed:
                            try:
                                await drone.action.land()
                                await asyncio.sleep(2)
                                await drone.action.disarm()
                                print("✅ Disarmed")
                                is_armed = False
                            except:
                                pass
                        
                        print("📊 Waiting for commands...\n")
                    
                    last_arm_bit = arm_bit
                
                # ==================== CONTROL LOOP ====================
                # لو النظام armed و offboard، أرسل أوامر التحكم
                if is_armed and is_offboard:
                    # استخرج قيم الـ joysticks
                    drone_x_percent = (packet['drone_x_norm'] / 2000.0) * 100.0
                    drone_y_percent = (packet['drone_y_norm'] / 2000.0) * 100.0
                    power_percent = (packet['power_y_norm'] / 4000.0) * 100.0
                    
                    # طبّق deadzone
                    roll_normalized = deadzone(normalize(drone_x_percent))
                    pitch_normalized = deadzone(normalize(drone_y_percent))
                    
                    roll_rate = roll_normalized * MAX_ROLL_RATE
                    pitch_rate = -pitch_normalized * MAX_PITCH_RATE
                    
                    thrust = map_throttle(power_percent)
                    
                    # أرسل الأوامر
                    current_time = time.time()
                    if current_time - last_command_time >= COMMAND_RATE:
                        
                        await drone.offboard.set_attitude_rate(
                            AttitudeRate(
                                roll_deg_s=roll_rate,
                                pitch_deg_s=pitch_rate,
                                yaw_deg_s=0.0,
                                thrust_value=thrust
                            )
                        )
                        
                        # اطبع الحالة
                        if current_time - last_print_time > 0.3:
                            bar_length = 15
                            filled = int((thrust / MAX_THRUST) * bar_length)
                            bar = "█" * filled + "░" * (bar_length - filled)
                            
                            if thrust < 0.01:
                                status = "⚪"
                            elif thrust < 0.3:
                                status = "🟡"
                            elif thrust < 0.6:
                                status = "🟠"
                            else:
                                status = "🔴"
                            
                            print(f"{status} Thr:{power_percent:5.1f}% [{bar}] | "
                                  f"Pitch:{pitch_rate:+5.1f}°/s Roll:{roll_rate:+5.1f}°/s")
                            
                            last_print_time = current_time
                        
                        last_command_time = current_time
                
            except socket.timeout:
                # فحص failsafe
                if is_armed and (time.time() - last_packet_time > FAILSAFE_TIMEOUT):
                    print(f"\n🛑 FAILSAFE - No signal for {FAILSAFE_TIMEOUT}s!")
                    
                    # صفّر الـ thrust
                    if is_offboard:
                        for _ in range(10):
                            try:
                                await drone.offboard.set_attitude_rate(
                                    AttitudeRate(0.0, 0.0, 0.0, 0.0)
                                )
                            except:
                                pass
                            await asyncio.sleep(0.1)
                        
                        # أوقف offboard
                        try:
                            await drone.offboard.stop()
                            is_offboard = False
                        except:
                            pass
                    
                    # فك التسليح
                    try:
                        await drone.action.land()
                        await asyncio.sleep(2)
                        await drone.action.disarm()
                        is_armed = False
                        print("✅ Auto-disarmed")
                        print("📊 Waiting for commands...\n")
                    except:
                        pass
                
                continue
                
            except Exception as e:
                print(f"\n⚠️  Error: {e}")
                continue
            
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n^C Stopping...\n")
        
        # Cleanup
        if is_offboard:
            try:
                for _ in range(10):
                    await drone.offboard.set_attitude_rate(
                        AttitudeRate(0.0, 0.0, 0.0, 0.0)
                    )
                    await asyncio.sleep(0.05)
                await drone.offboard.stop()
                print("✅ OFFBOARD stopped")
            except:
                pass
        
        if is_armed:
            try:
                await drone.action.land()
                await asyncio.sleep(2)
                await drone.action.disarm()
                print("✅ Disarmed")
            except:
                pass
        
        print("\n✅ SHUTDOWN COMPLETE\n")

async def run():
    print("\n" + "="*70)
    print("🚁 CUSTOM DRONE REMOTE - CONTINUOUS MODE")
    print("="*70)
    
    # UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"\n📡 UDP: {UDP_PORT}")
    
    # MAVSDK
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 MAVSDK...")
    await drone.connect()
    
    if not await wait_for_connection(drone):
        sock.close()
        return
    
    # الحلقة الرئيسية - تشتغل طول الوقت
    await main_loop(drone, sock)
    
    sock.close()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
