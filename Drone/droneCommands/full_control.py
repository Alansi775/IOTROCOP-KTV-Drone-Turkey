#!/usr/bin/env python3
"""
Custom Drone Remote Control - ENHANCED SWITCH EDITION
Compatible with drone_monitor_network_enhanced.py
Individual switch states (switch_0 to switch_15) support
"""

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

# ENHANCED: Switch ID'leri (0-15 arası)
SWITCH_MANUAL_MODE = 9     # Switch 9 = Manual/Hold Mode
SWITCH_ARM = 12            # Switch 12 = ARM/DISARM
SWITCH_EMERGENCY = 15      # Switch 15 = Emergency Stop (opsiyonel)

# ANSI Colors (drone_monitor ile uyumlu)
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    SWITCH = '\033[38;5;141m'

def normalize(val, min_val=-100, max_val=100):
    """Normalize value to -1.0 to 1.0 range"""
    normalized = (val - ((max_val + min_val) / 2)) / ((max_val - min_val) / 2)
    return max(-1.0, min(1.0, normalized))

def deadzone(v, threshold=DEADZONE):
    """Apply deadzone to prevent drift"""
    return 0.0 if abs(v) < threshold else v

def map_throttle(power_percent):
    """Map throttle percentage to thrust value"""
    power_percent = max(0.0, min(100.0, power_percent))
    thrust = MIN_THRUST + (power_percent / 100.0) * (MAX_THRUST - MIN_THRUST)
    return thrust

def parse_binary_packet(data):
    """
    Parse binary packet from STM32 (17 bytes)
    ENHANCED: Returns packet with individual switch parsing support
    """
    if len(data) != 17:
        return None
    
    try:
        unpacked = struct.unpack('<BhhhhhBBHBB', data)
        
        # Validate start/end bytes
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
            'switch_states_raw': unpacked[8],  # 16-bit raw value
            'timestamp': time.time()
        }
        
        # ENHANCED: Parse individual switches (0-15)
        packet['switches'] = get_individual_switches(packet['switch_states_raw'])
        packet['active_switches'] = get_active_switches(packet['switch_states_raw'])
        
        return packet
        
    except Exception as e:
        print(f"{Colors.FAIL}⚠️  Parse error: {e}{Colors.RESET}")
        return None

def get_individual_switches(switch_states):
    """
    Extract individual switch states from 16-bit value
    Returns: {'switch_0': True/False, ..., 'switch_15': True/False}
    """
    switches = {}
    for i in range(16):
        bit_value = (switch_states >> i) & 1
        switches[f'switch_{i}'] = bool(bit_value)
    return switches

def get_active_switches(switch_states):
    """
    Get list of active switch IDs
    Returns: [0, 3, 7, ...] (list of active switch indices)
    """
    active = []
    for i in range(16):
        if (switch_states >> i) & 1:
            active.append(i)
    return active

def get_switch_value(packet, switch_id):
    """
    Get specific switch state by ID (0-15)
    Args:
        packet: Parsed packet dictionary
        switch_id: Switch index (0-15)
    Returns: True (active) or False (inactive)
    """
    return packet['switches'].get(f'switch_{switch_id}', False)

def extract_switch_state(switch_states, bit_position):
    """Legacy function - kept for backward compatibility"""
    return (switch_states >> bit_position) & 1

async def wait_for_connection(drone):
    """Wait for drone connection"""
    print(f"{Colors.OKCYAN}⏳ Waiting for drone...{Colors.RESET}")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"{Colors.OKGREEN}✅ Drone connected!{Colors.RESET}")
            return True
    return False

async def try_arm_once(drone):
    """Attempt to ARM the drone once"""
    try:
        # Method 1: Normal arm
        await drone.action.arm()
        await asyncio.sleep(1)
        
        async for armed in drone.telemetry.armed():
            if armed:
                print(f"{Colors.OKGREEN}✅ ARMED!{Colors.RESET}")
                return True
            break
        
    except:
        pass
    
    # Method 2: Force arm via offboard
    print(f"{Colors.WARNING}   Trying force arm...{Colors.RESET}")
    try:
        await drone.offboard.set_attitude_rate(
            AttitudeRate(0.0, 0.0, 0.0, 0.0)
        )
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
        print(f"{Colors.FAIL}❌ Force ARM failed: {e}{Colors.RESET}")
    
    return False

async def try_start_offboard_once(drone):
    """Start OFFBOARD mode once"""
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
        print(f"{Colors.OKGREEN}✅ OFFBOARD active!{Colors.RESET}")
        return True
        
    except OffboardError as e:
        print(f"{Colors.FAIL}❌ OFFBOARD failed: {e}{Colors.RESET}")
        return False

def print_switch_status(packet):
    """Print current switch states (ENHANCED)"""
    active = packet['active_switches']
    if active:
        switch_labels = [f"SW{i}" for i in active]
        print(f"{Colors.SWITCH}🔘 Active Switches: {', '.join(switch_labels)}{Colors.RESET}")
    else:
        print(f"{Colors.WARNING}🔘 No Switches Active{Colors.RESET}")

async def main_loop(drone, sock):
    """
    Main control loop - runs continuously
    Monitors switches and reacts to changes
    ENHANCED: Uses individual switch IDs
    """
    
    sock.settimeout(0.1)
    
    last_packet_time = time.time()
    last_command_time = time.time()
    last_print_time = 0
    
    # System states
    last_manual_mode = False
    last_arm = False
    last_emergency = False
    is_armed = False
    is_offboard = False
    
    print("\n" + "="*70)
    print("🎮 SYSTEM ACTIVE - Monitoring switches (ENHANCED MODE)")
    print("="*70)
    print(f"\n{Colors.SWITCH}📊 Switch Configuration:{Colors.RESET}")
    print(f"   Switch {SWITCH_MANUAL_MODE}: Manual/Hold Mode")
    print(f"   Switch {SWITCH_ARM}: ARM/DISARM")
    print(f"   Switch {SWITCH_EMERGENCY}: Emergency Stop")
    print(f"\n{Colors.OKCYAN}📡 Waiting for switch inputs...{Colors.RESET}\n")
    
    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                packet = parse_binary_packet(data)
                
                if not packet:
                    continue
                
                last_packet_time = time.time()
                
                # ENHANCED: Extract switch states using IDs
                manual_mode = get_switch_value(packet, SWITCH_MANUAL_MODE)
                arm = get_switch_value(packet, SWITCH_ARM)
                emergency = get_switch_value(packet, SWITCH_EMERGENCY)
                
                # ==================== EMERGENCY STOP ====================
                # Check emergency switch (highest priority)
                if emergency != last_emergency:
                    if emergency:
                        print(f"\n{Colors.FAIL}🚨 EMERGENCY STOP ACTIVATED!{Colors.RESET}")
                        
                        # Immediate shutdown
                        if is_offboard:
                            try:
                                for _ in range(5):
                                    await drone.offboard.set_attitude_rate(
                                        AttitudeRate(0.0, 0.0, 0.0, 0.0)
                                    )
                                    await asyncio.sleep(0.02)
                                await drone.offboard.stop()
                                is_offboard = False
                            except:
                                pass
                        
                        if is_armed:
                            try:
                                await drone.action.land()
                                await asyncio.sleep(1)
                                await drone.action.disarm()
                                is_armed = False
                                print(f"{Colors.OKGREEN}✅ Emergency disarmed{Colors.RESET}")
                            except:
                                pass
                    
                    last_emergency = emergency
                
                # Don't process other switches if emergency is active
                if emergency:
                    continue
                
                # ==================== MANUAL MODE SWITCH ====================
                if manual_mode != last_manual_mode:
                    if manual_mode:
                        print(f"\n{Colors.SWITCH}🔧 Switch {SWITCH_MANUAL_MODE} → MANUAL MODE{Colors.RESET}")
                        try:
                            await drone.action.set_flight_mode("STABILIZED")
                            print(f"{Colors.OKGREEN}   Flight mode: STABILIZED{Colors.RESET}")
                        except:
                            try:
                                await drone.action.set_flight_mode("MANUAL")
                                print(f"{Colors.OKGREEN}   Flight mode: MANUAL{Colors.RESET}")
                            except:
                                print(f"{Colors.WARNING}   ⚠️  Mode change failed (will use OFFBOARD){Colors.RESET}")
                    else:
                        print(f"\n{Colors.SWITCH}🔧 Switch {SWITCH_MANUAL_MODE} → HOLD MODE{Colors.RESET}")
                        print(f"{Colors.OKGREEN}   Flight mode: HOLD{Colors.RESET}")
                    
                    last_manual_mode = manual_mode
                
                # ==================== ARM SWITCH ====================
                if arm != last_arm:
                    if arm:
                        # ARM switch activated
                        print(f"\n{Colors.SWITCH}🚀 Switch {SWITCH_ARM} → ARM{Colors.RESET}")
                        print_switch_status(packet)
                        print(f"{Colors.OKCYAN}   Trying to ARM...{Colors.RESET}")
                        
                        # Try to arm once
                        is_armed = await try_arm_once(drone)
                        
                        if is_armed:
                            # Start OFFBOARD
                            print(f"{Colors.OKCYAN}🎮 Starting OFFBOARD...{Colors.RESET}")
                            is_offboard = await try_start_offboard_once(drone)
                            
                            if is_offboard:
                                print(f"\n{Colors.OKGREEN}📊 Controls Active:{Colors.RESET}")
                                print("   Joystick 1: Pitch/Roll")
                                print("   Joystick 2: Throttle")
                                print(f"   Switch {SWITCH_ARM} OFF → DISARM")
                                print(f"   Switch {SWITCH_EMERGENCY} → EMERGENCY STOP\n")
                        else:
                            print(f"{Colors.WARNING}⚠️  Cannot start - drone not armed{Colors.RESET}")
                            print(f"{Colors.OKCYAN}💡 Check: param set CBRK_VELPOSERR 201607{Colors.RESET}\n")
                    
                    else:
                        # ARM switch deactivated
                        print(f"\n{Colors.SWITCH}🛑 Switch {SWITCH_ARM} → DISARM{Colors.RESET}")
                        
                        # Stop OFFBOARD
                        if is_offboard:
                            try:
                                # Zero thrust first
                                for _ in range(10):
                                    await drone.offboard.set_attitude_rate(
                                        AttitudeRate(0.0, 0.0, 0.0, 0.0)
                                    )
                                    await asyncio.sleep(0.05)
                                
                                await drone.offboard.stop()
                                print(f"{Colors.OKGREEN}✅ OFFBOARD stopped{Colors.RESET}")
                                is_offboard = False
                            except:
                                pass
                        
                        # Disarm
                        if is_armed:
                            try:
                                await drone.action.land()
                                await asyncio.sleep(2)
                                await drone.action.disarm()
                                print(f"{Colors.OKGREEN}✅ Disarmed{Colors.RESET}")
                                is_armed = False
                            except:
                                pass
                        
                        print(f"{Colors.OKCYAN}📊 Waiting for commands...{Colors.RESET}\n")
                    
                    last_arm = arm
                
                # ==================== CONTROL LOOP ====================
                # Send control commands if armed and offboard
                if is_armed and is_offboard:
                    # Extract joystick values
                    drone_x_percent = (packet['drone_x_norm'] / 2000.0) * 100.0
                    drone_y_percent = (packet['drone_y_norm'] / 2000.0) * 100.0
                    power_percent = (packet['power_y_norm'] / 4000.0) * 100.0
                    
                    # Apply deadzone
                    roll_normalized = deadzone(normalize(drone_x_percent))
                    pitch_normalized = deadzone(normalize(drone_y_percent))
                    
                    roll_rate = roll_normalized * MAX_ROLL_RATE
                    pitch_rate = -pitch_normalized * MAX_PITCH_RATE
                    
                    thrust = map_throttle(power_percent)
                    
                    # Send commands
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
                        
                        # Print status
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
                            
                            # ENHANCED: Show active switches in status line
                            sw_status = f"[{','.join([f'SW{i}' for i in packet['active_switches']])}]" if packet['active_switches'] else "[None]"
                            
                            print(f"{status} Thr:{power_percent:5.1f}% [{bar}] | "
                                  f"Pitch:{pitch_rate:+5.1f}°/s Roll:{roll_rate:+5.1f}°/s | {sw_status}")
                            
                            last_print_time = current_time
                        
                        last_command_time = current_time
                
            except socket.timeout:
                # Check failsafe
                if is_armed and (time.time() - last_packet_time > FAILSAFE_TIMEOUT):
                    print(f"\n{Colors.FAIL}🛑 FAILSAFE - No signal for {FAILSAFE_TIMEOUT}s!{Colors.RESET}")
                    
                    # Zero thrust
                    if is_offboard:
                        for _ in range(10):
                            try:
                                await drone.offboard.set_attitude_rate(
                                    AttitudeRate(0.0, 0.0, 0.0, 0.0)
                                )
                            except:
                                pass
                            await asyncio.sleep(0.1)
                        
                        # Stop offboard
                        try:
                            await drone.offboard.stop()
                            is_offboard = False
                        except:
                            pass
                    
                    # Disarm
                    try:
                        await drone.action.land()
                        await asyncio.sleep(2)
                        await drone.action.disarm()
                        is_armed = False
                        print(f"{Colors.OKGREEN}✅ Auto-disarmed{Colors.RESET}")
                        print(f"{Colors.OKCYAN}📊 Waiting for commands...{Colors.RESET}\n")
                    except:
                        pass
                
                continue
                
            except Exception as e:
                print(f"\n{Colors.WARNING}⚠️  Error: {e}{Colors.RESET}")
                continue
            
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}^C Stopping...{Colors.RESET}\n")
        
        # Cleanup
        if is_offboard:
            try:
                for _ in range(10):
                    await drone.offboard.set_attitude_rate(
                        AttitudeRate(0.0, 0.0, 0.0, 0.0)
                    )
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
    """Main entry point"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}🚁 CUSTOM DRONE REMOTE - ENHANCED SWITCH EDITION{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
    
    # UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"\n{Colors.OKGREEN}📡 UDP Listening: Port {UDP_PORT}{Colors.RESET}")
    
    # MAVSDK
    drone = System(mavsdk_server_address="localhost", port=50051)
    print(f"{Colors.OKCYAN}📡 MAVSDK Connecting...{Colors.RESET}")
    await drone.connect()
    
    if not await wait_for_connection(drone):
        sock.close()
        return
    
    # Main loop - runs continuously
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
