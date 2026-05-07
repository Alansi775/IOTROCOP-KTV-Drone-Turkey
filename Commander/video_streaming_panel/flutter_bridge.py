#!/usr/bin/env python3
"""
STM32 → Flutter Bridge (Fixed JSON Format)
"""
import serial
import struct
import socket
import json
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

NVIDIA_TARGET = ("192.168.100.2", 5656)
FLUTTER_TARGET = ("127.0.0.1", 5657)

PACKET_SIZE = 19
FMT = "<BhhhhhhBBHBB"

def parse_packet(data):
    if len(data) != 19 or data[0] != 0xAA or data[18] != 0x55:
        return None
    try:
        u = struct.unpack(FMT, data)
        return {
            'drone_x': u[1],
            'drone_y': u[2],
            'power_y': u[3],
            'spin_y': u[4],
            'comp_x': u[5],
            'comp_y': u[6],
            'pot1': u[7],
            'pot2': u[8],
            'switches': u[9]
        }
    except:
        return None

print("🎮 STM32 → Flutter Bridge (FIXED)\n")

ser = serial.Serial(PORT, BAUD, timeout=0.1)
time.sleep(0.5)  # Wait for serial to stabilize
ser.reset_input_buffer()

nvidia_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
flutter_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
buf = bytearray()

print(f"✅ Serial: {PORT}")
print(f"✅ NVIDIA: {NVIDIA_TARGET}")
print(f"✅ Flutter: {FLUTTER_TARGET}\n")

while True:
    try:
        chunk = ser.read(max(1, ser.in_waiting))
        if chunk:
            buf.extend(chunk)
        
        while len(buf) >= PACKET_SIZE:
            idx = buf.find(b'\xAA')
            if idx < 0:
                buf.clear()
                break
            if idx > 0:
                del buf[:idx]
            if len(buf) < PACKET_SIZE:
                break
            
            pkt = bytes(buf[:PACKET_SIZE])
            if pkt[18] != 0x55:
                del buf[0]
                continue
            
            data = parse_packet(pkt)
            if data:
                # Send binary to NVIDIA
                nvidia_sock.sendto(pkt, NVIDIA_TARGET)
                
                # Send CORRECT JSON to Flutter
                flutter_json = {
                    "type": "joystick_update",
                    "data": {
                        "joystick_left": {
                            "x": data['drone_x'] / 2000.0,  # normalize -1 to 1
                            "y": data['drone_y'] / 2000.0
                        },
                        "joystick_right": {
                            "x": data['comp_x'] / 2000.0,
                            "y": data['comp_y'] / 2000.0
                        },
                        "throttle": data['power_y'] / 4000.0,  # 0 to 1
                        "switches": data['switches'],
                        "pot1": data['pot1'],
                        "pot2": data['pot2']
                    }
                }
                
                flutter_sock.sendto(
                    json.dumps(flutter_json).encode('utf-8'),
                    FLUTTER_TARGET
                )
            
            del buf[:PACKET_SIZE]
        
        time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\n✅ Stopped\n")
        break
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(0.1)

ser.close()
nvidia_sock.close()
flutter_sock.close()
