#!/usr/bin/env python3
import asyncio
import struct
import socket
import json
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw
from mavsdk.action import ActionError

UDP_PORT = 5656
UDP_PORT_STATUS = 5659
MAVSDK_PORT = 50051

print("\n" + "="*70)
print("🚁 DRONE CONTROL - POSITION HOLD + AUTO MODES")
print("="*70)

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("0.0.0.0", UDP_PORT))
udp_sock.settimeout(0.01)
print(f"📡 UDP Control: Port {UDP_PORT}")

status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
RASPBERRY_PI_IP = "192.168.100.1"
print(f"📤 UDP Status: → {RASPBERRY_PI_IP}:{UDP_PORT_STATUS}")

drone = System(mavsdk_server_address="localhost", port=MAVSDK_PORT)

def send_status(mode, message):
    status = {'mode': mode, 'message': message}
    data = json.dumps(status).encode('utf-8')
    status_sock.sendto(data, (RASPBERRY_PI_IP, UDP_PORT_STATUS))
    print(f"   📤 Sent to Flutter: {mode} - {message}")

async def auto_takeoff(drone, target_altitude=3.0):
    send_status('takeoff', f'Taking off to {target_altitude}m...')
    print(f"\n🛫 AUTO TAKEOFF to {target_altitude}m")
    
    try:
        await drone.action.set_takeoff_altitude(target_altitude)
        await drone.action.takeoff()
        
        print("   Climbing...")
        await asyncio.sleep(5)
        
        print(f"   ✅ Takeoff command sent")
        send_status('hover', f'Hovering at {target_altitude}m')
        return True
        
    except ActionError as e:
        print(f"   ❌ Takeoff failed: {e}")
        send_status('manual', 'Takeoff failed')
        return False

async def auto_land(drone):
    send_status('landing', 'Landing...')
    print("\n🛬 AUTO LANDING")
    
    try:
        await drone.action.land()
        
        print("   Descending...")
        await asyncio.sleep(5)
        
        print("   ✅ Landing command sent")
        send_status('manual', 'Landed')
        return True
        
    except ActionError as e:
        print(f"   ❌ Landing failed: {e}")
        send_status('manual', 'Landing failed')
        return False

async def main():
    print("📡 Connecting...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected!")
            break
    
    print("\n📡 Checking GPS...")
    try:
        gps_info = await asyncio.wait_for(
            drone.telemetry.gps_info().__anext__(),
            timeout=2
        )
        print(f"   Satellites: {gps_info.num_satellites}")
    except:
        print("   ⚠️ GPS timeout")
    
    print("\n" + "="*70)
    print("🎮 Controls:")
    print("   ARM Switch = Enable motors")
    print("   SW6 TOP    = ⚪ Manual control")
    print("   SW6 MID    = 🟢 AUTO TAKEOFF (3m)")
    print("   SW6 BOT    = 🟠 AUTO LAND")
    print("="*70 + "\n")
    
    armed = False
    offboard_active = False
    last_arm_switch = False
    last_sw6_mode = 'TOP'
    auto_mode_active = False
    
    north = 0.0
    east = 0.0
    down = 0.0
    yaw = 0.0
    
    while True:
        try:
            data, _ = udp_sock.recvfrom(1024)
            if len(data) == 19 and data[0] == 0xAA and data[18] == 0x55:
                u = struct.unpack("<BhhhhhhBBHBB", data)
                
                throttle_raw = u[3]
                pitch_raw = u[2]
                roll_raw = u[1]
                yaw_raw = u[4]
                switches = u[9]
                
                throttle = ((throttle_raw - 2000) / 2000.0)
                pitch = ((pitch_raw - 2000) / 2000.0)
                roll = ((roll_raw - 2000) / 2000.0)
                yaw_rate = ((yaw_raw - 2000) / 2000.0)
                
                # ARM switch (bit 12)
                arm_switch = bool(switches & (1 << 12))
                
                # SW6 detection
                sw6_raw = switches & 0x0F00
                if sw6_raw == 0x0600:
                    sw6_mode = 'TOP'
                elif sw6_raw == 0x0200:
                    sw6_mode = 'MID'
                elif sw6_raw == 0x0A00:
                    sw6_mode = 'BOT'
                else:
                    sw6_mode = last_sw6_mode
                
                # Debug (يمكن تعطيله بعدين)
                print(f"\rRAW: 0x{switches:04x} | SW6: {sw6_mode} | ARM: {'ON' if arm_switch else 'OFF'}", end="", flush=True)
                
                # ARM toggle
                if arm_switch != last_arm_switch:
                    if arm_switch:
                        print("\n\n🚀 ARM")
                        try:
                            await drone.action.arm()
                            await asyncio.sleep(1)
                            
                            is_armed = await asyncio.wait_for(
                                drone.telemetry.armed().__anext__(),
                                timeout=2
                            )
                            
                            if is_armed:
                                armed = True
                                print("✅ ARMED!\n")
                                send_status('armed', 'Armed')
                            else:
                                print("❌ ARM rejected (need GPS)\n")
                        except Exception as e:
                            print(f"❌ ARM error: {e}\n")
                    else:
                        print("\n\n🛑 DISARM")
                        if offboard_active:
                            await drone.offboard.stop()
                            offboard_active = False
                        if armed:
                            await drone.action.disarm()
                            armed = False
                            auto_mode_active = False
                            print("✅ Disarmed\n")
                            send_status('disarmed', 'Disarmed')
                            north = east = down = yaw = 0.0
                    
                    last_arm_switch = arm_switch
                
                # SW6 mode change (حتى بدون ARM للتجربة!)
                if sw6_mode != last_sw6_mode:
                    print(f"\n\n🎚️ SW6 Switch: {sw6_mode}")
                    
                    if sw6_mode == 'MID':
                        print("🟢 TAKEOFF MODE")
                        send_status('takeoff_ready', 'Takeoff mode - ARM to execute')
                        
                        if armed:
                            auto_mode_active = True
                            success = await auto_takeoff(drone, target_altitude=3.0)
                            if success:
                                await drone.offboard.set_position_ned(
                                    PositionNedYaw(0.0, 0.0, -3.0, 0.0)
                                )
                                await drone.offboard.start()
                                offboard_active = True
                                down = -3.0
                        else:
                            print("   ⚠️ ARM first to takeoff!")
                    
                    elif sw6_mode == 'BOT':
                        print("🟠 LANDING MODE")
                        send_status('landing_ready', 'Landing mode - ARM to execute')
                        
                        if armed:
                            auto_mode_active = True
                            if offboard_active:
                                await drone.offboard.stop()
                                offboard_active = False
                            await auto_land(drone)
                            auto_mode_active = False
                        else:
                            print("   ⚠️ ARM first to land!")
                    
                    elif sw6_mode == 'TOP':
                        print("⚪ MANUAL MODE")
                        auto_mode_active = False
                        send_status('manual', 'Manual control')
                        
                        if armed and not offboard_active:
                            await drone.offboard.set_position_ned(
                                PositionNedYaw(0.0, 0.0, 0.0, 0.0)
                            )
                            await drone.offboard.start()
                            offboard_active = True
                    
                    last_sw6_mode = sw6_mode
                    print()
                
                # Manual control
                if armed and offboard_active and sw6_mode == 'TOP' and not auto_mode_active:
                    down += -throttle * 0.02
                    north += pitch * 0.02
                    east += roll * 0.02
                    yaw += yaw_rate * 2
                    
                    down = max(-10, min(0, down))
                    north = max(-10, min(10, north))
                    east = max(-10, min(10, east))
                    yaw = yaw % 360
                    
                    await drone.offboard.set_position_ned(
                        PositionNedYaw(north, east, down, yaw)
                    )
        
        except socket.timeout:
            await asyncio.sleep(0.01)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutdown...")
            send_status('shutdown', 'Shutdown')
            if offboard_active:
                await drone.offboard.stop()
            if armed:
                await drone.action.disarm()
            break

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
