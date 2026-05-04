#!/usr/bin/env python3
"""
Custom Drone Remote Control - 2POS ARM EDITION
"""

import asyncio
import socket
import struct
import time
from mavsdk import System
from mavsdk.offboard import OffboardError, AttitudeRate

UDP_PORT = 5656
DEADZONE = 0.10
MAX_PITCH_RATE = 30.0
MAX_ROLL_RATE = 30.0
MIN_THRUST = 0.0
MAX_THRUST = 0.9
COMMAND_RATE = 0.02

class Colors:
    RESET = '\033[0m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'

def normalize(val, min_val=-100, max_val=100):
    normalized = (val - ((max_val + min_val) / 2)) / ((max_val - min_val) / 2)
    return max(-1.0, min(1.0, normalized))

def deadzone(v, threshold=DEADZONE):
    return 0.0 if abs(v) < threshold else v

def map_throttle(power_percent):
    power_percent = max(0.0, min(100.0, power_percent))
    return MIN_THRUST + (power_percent / 100.0) * (MAX_THRUST - MIN_THRUST)

def parse_binary_packet(data):
    if len(data) != 19:
        return None
    try:
        unpacked = struct.unpack('<BhhhhhhBBHBB', data)
        if unpacked[0] != 0xAA or unpacked[-1] != 0x55:
            return None
        
        return {
            'drone_x_norm': unpacked[1],
            'drone_y_norm': unpacked[2],
            'power_y_norm': unpacked[3],
            'switch_states': unpacked[9],
            'timestamp': time.time()
        }
    except:
        return None

async def wait_for_connection(drone):
    print(f"{Colors.OKCYAN}⏳ Waiting for drone...{Colors.RESET}")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"{Colors.OKGREEN}✅ Drone connected!{Colors.RESET}")
            return True
    return False

async def try_arm(drone):
    try:
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print(f"{Colors.OKGREEN}✅ ARMED!{Colors.RESET}")
                return True
            break
    except:
        pass
    
    # Force arm via offboard
    print(f"{Colors.WARNING}   Force arm...{Colors.RESET}")
    try:
        await drone.offboard.set_attitude_rate(AttitudeRate(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
        await asyncio.sleep(0.5)
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print(f"{Colors.OKGREEN}✅ ARMED (force)!{Colors.RESET}")
                return True
            break
    except Exception as e:
        print(f"{Colors.FAIL}❌ ARM failed: {e}{Colors.RESET}")
    
    return False

async def try_start_offboard(drone):
    try:
        await drone.offboard.set_attitude_rate(AttitudeRate(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
        print(f"{Colors.OKGREEN}✅ OFFBOARD active!{Colors.RESET}")
        return True
    except OffboardError as e:
        print(f"{Colors.FAIL}❌ OFFBOARD failed: {e}{Colors.RESET}")
        return False

async def main_loop(drone, sock):
    sock.settimeout(0.1)
    
    last_packet_time = time.time()
    last_command_time = time.time()
    last_print_time = 0
    
    last_arm = 0
    is_armed = False
    is_offboard = False
    
    print("\n" + "="*70)
    print("🎮 READY - 2POS Switch = ARM/DISARM")
    print("="*70 + "\n")
    
    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                packet = parse_binary_packet(data)
                
                if not packet:
                    continue
                
                last_packet_time = time.time()
                
                # Extract 2POS switch (bit 12)
                arm = (packet['switch_states'] >> 12) & 1
                
                # ARM/DISARM on switch change
                if arm != last_arm:
                    if arm == 1:
                        # ARM
                        print(f"\n{Colors.WARNING}🚀 2POS ON → ARM{Colors.RESET}")
                        
                        is_armed = await try_arm(drone)
                        
                        if is_armed:
                            print(f"{Colors.OKCYAN}🎮 Starting OFFBOARD...{Colors.RESET}")
                            is_offboard = await try_start_offboard(drone)
                            
                            if is_offboard:
                                print(f"\n{Colors.OKGREEN}📊 Controls Active!{Colors.RESET}\n")
                    else:
                        # DISARM
                        print(f"\n{Colors.WARNING}🛑 2POS OFF → DISARM{Colors.RESET}")
                        
                        if is_offboard:
                            try:
                                for _ in range(10):
                                    await drone.offboard.set_attitude_rate(AttitudeRate(0.0, 0.0, 0.0, 0.0))
                                    await asyncio.sleep(0.05)
                                await drone.offboard.stop()
                                print(f"{Colors.OKGREEN}✅ OFFBOARD stopped{Colors.RESET}")
                                is_offboard = False
                            except:
                                pass
                        
                        if is_armed:
                            try:
                                await drone.action.land()
                                await asyncio.sleep(2)
                                await drone.action.disarm()
                                print(f"{Colors.OKGREEN}✅ Disarmed{Colors.RESET}\n")
                                is_armed = False
                            except:
                                pass
                    
                    last_arm = arm
                
                # Control loop
                if is_armed and is_offboard:
                    drone_x_percent = (packet['drone_x_norm'] / 2000.0) * 100.0
                    drone_y_percent = (packet['drone_y_norm'] / 2000.0) * 100.0
                    power_percent = (packet['power_y_norm'] / 4000.0) * 100.0
                    
                    roll_normalized = deadzone(normalize(drone_x_percent))
                    pitch_normalized = deadzone(normalize(drone_y_percent))
                    
                    roll_rate = roll_normalized * MAX_ROLL_RATE
                    pitch_rate = -pitch_normalized * MAX_PITCH_RATE
                    thrust = map_throttle(power_percent)
                    
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
                        
                        if current_time - last_print_time > 0.1:
                            bar_length = 15
                            filled = int((thrust / MAX_THRUST) * bar_length)
                            bar = "█" * filled + "░" * (bar_length - filled)
                            
                            status = "⚪" if thrust < 0.01 else "🟡" if thrust < 0.3 else "🟠" if thrust < 0.6 else "🔴"
                            
                            print(f"{status} Thr:{power_percent:5.1f}% [{bar}] | "
                                  f"Pitch:{pitch_rate:+5.1f}°/s Roll:{roll_rate:+5.1f}°/s")
                            
                            last_print_time = current_time
                        
                        last_command_time = current_time
            
            except socket.timeout:
                continue
            
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}^C Stopping...{Colors.RESET}\n")
        
        if is_offboard:
            try:
                for _ in range(10):
                    await drone.offboard.set_attitude_rate(AttitudeRate(0.0, 0.0, 0.0, 0.0))
                    await asyncio.sleep(0.05)
                await drone.offboard.stop()
                print(f"{Colors.OKGREEN}✅ OFFBOARD stopped{Colors.RESET}")
            except:
                pass
        
        if is_armed:
            try:
                await drone.action.land()
                await asyncio.sleep(2)
                await drone.action.disarm()
                print(f"{Colors.OKGREEN}✅ Disarmed{Colors.RESET}")
            except:
                pass
        
        print(f"\n{Colors.OKGREEN}✅ SHUTDOWN COMPLETE{Colors.RESET}\n")

async def run():
    print(f"\n{'='*70}")
    print(f"🚁 DRONE CONTROL - 2POS ARM EDITION")
    print(f"{'='*70}\n")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"{Colors.OKGREEN}📡 UDP Listening: Port {UDP_PORT}{Colors.RESET}")
    
    drone = System(mavsdk_server_address="localhost", port=50051)
    print(f"{Colors.OKCYAN}📡 MAVSDK Connecting...{Colors.RESET}")
    await drone.connect()
    
    while not await wait_for_connection(drone):
        print("Retrying connection...")
        await asyncio.sleep(2)
    
    await main_loop(drone, sock)
    sock.close()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Error: {e}{Colors.RESET}")
