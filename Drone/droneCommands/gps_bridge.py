import asyncio
import socket
import json
import time
from mavsdk import System

# ================== CONFIG ==================
RASPBERRY_IP = "192.168.100.1"
GPS_UDP_PORT = 5658
# ============================================

async def gps_bridge():
    """Bridge بين PX4 و Flutter"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    drone = System(mavsdk_server_address="localhost", port=50051)
    print("📡 Connecting to MAVSDK...")
    await drone.connect()
    
    print("⏳ Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone connected!")
            break
    
    print(f"🛰️ GPS Bridge active - Sending to {RASPBERRY_IP}:{GPS_UDP_PORT}")
    
    await send_gps_data(drone, sock)

async def send_gps_data(drone, sock):
    """أرسل GPS data كل ثانية"""
    
    while True:
        try:
            # البيانات الافتراضية
            gps_data = {
                'latitude': 0.0,
                'longitude': 0.0,
                'altitude': 0.0,
                'satellites': 0,
                'fix_type': 0,
                'has_fix': False,
                'timestamp': time.time()
            }
            
            # جلب position
            try:
                async for position in drone.telemetry.position():
                    gps_data['latitude'] = position.latitude_deg
                    gps_data['longitude'] = position.longitude_deg
                    gps_data['altitude'] = position.absolute_altitude_m
                    break
            except:
                pass
            
            # جلب GPS info
            try:
                async for gps_info in drone.telemetry.gps_info():
                    gps_data['satellites'] = gps_info.num_satellites
                    
                    # تحويل fix_type إلى int
                    if hasattr(gps_info.fix_type, 'value'):
                        gps_data['fix_type'] = int(gps_info.fix_type.value)
                    else:
                        gps_data['fix_type'] = int(gps_info.fix_type)
                    
                    gps_data['has_fix'] = gps_data['fix_type'] >= 3
                    break
            except Exception as e:
                print(f"GPS info error: {e}")
            
            # أرسل JSON
            packet = {
                'type': 'gps_update',
                'data': gps_data
            }
            
            json_data = json.dumps(packet).encode('utf-8')
            sock.sendto(json_data, (RASPBERRY_IP, GPS_UDP_PORT))
            
            # طباعة
            if gps_data['has_fix']:
                print(f"🛰️ GPS: {gps_data['satellites']} sats | "
                      f"{gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}")
            else:
                print(f"📡 GPS: {gps_data['satellites']} sats (no fix)")
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
        
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(gps_bridge())
    except KeyboardInterrupt:
        print("\n🛑 GPS Bridge stopped")
