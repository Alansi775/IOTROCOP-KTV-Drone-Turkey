#!/usr/bin/env python3
import asyncio
import socket
import json
from mavsdk import System

UDP_IP = "192.168.100.1"
UDP_PORT = 5658

async def gps_bridge():
    drone = System(mavsdk_server_address='localhost', port=50051)
    await drone.connect()
    
    print("⏳ Waiting for connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone connected!")
            break
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"🛰️ GPS Bridge Started → {UDP_IP}:{UDP_PORT}")
    
    print("Reading home position...")
    try:
        home = await asyncio.wait_for(
            drone.telemetry.home().__anext__(),
            timeout=5
        )
        print(f"✅ Home: {home.latitude_deg}, {home.longitude_deg}")
        
        while True:
            try:
                # GPS Info
                gps_info = await asyncio.wait_for(
                    drone.telemetry.gps_info().__anext__(),
                    timeout=2
                )
                
                # Heading from Attitude (Yaw)
                heading = 0.0
                try:
                    attitude = await asyncio.wait_for(
                        drone.telemetry.attitude_euler().__anext__(),
                        timeout=1
                    )
                    heading = attitude.yaw_deg
                    if heading < 0:
                        heading += 360
                except Exception as e:
                    pass
                
                packet = {
                    'latitude': home.latitude_deg,
                    'longitude': home.longitude_deg,
                    'altitude': home.absolute_altitude_m,
                    'satellites': gps_info.num_satellites,
                    'has_fix': (gps_info.fix_type.name in ['FIX_2D', 'FIX_3D', 'FIX_DGPS']),
                    'heading': heading
                }
                
                json_data = json.dumps(packet).encode('utf-8')
                sock.sendto(json_data, (UDP_IP, UDP_PORT))
                
                print(f"📡 Sats={packet['satellites']} | Heading={heading:.1f}°")
                
            except asyncio.TimeoutError:
                print("⚠️ GPS timeout")
            except Exception as e:
                print(f"⚠️ Error: {e}")
            
            await asyncio.sleep(1)
            
    except asyncio.TimeoutError:
        print("❌ No home position!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(gps_bridge())
    except KeyboardInterrupt:
        print("\n✅ Stopped")
