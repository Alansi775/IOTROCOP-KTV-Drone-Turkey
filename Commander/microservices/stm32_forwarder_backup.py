#!/usr/bin/env python3
import serial
import struct
import socket
import json
import time

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.001)
nvidia_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
flutter_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
buf = bytearray()

NVIDIA_TARGET = ("192.168.100.2", 5656)
FLUTTER_TARGET = ("127.0.0.1", 5657)

print("🎮 STM32 → NVIDIA + Flutter (INVERTED)\n")

last_flutter_send = 0
FLUTTER_INTERVAL = 0.02

while True:
    try:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
        
        while len(buf) >= 19:
            idx = buf.find(b'\xAA')
            if idx < 0:
                buf.clear()
                break
            if idx > 0:
                del buf[:idx]
            if len(buf) < 19:
                break
            
            if buf[18] == 0x55:
                pkt = bytes(buf[:19])
                nvidia_sock.sendto(pkt, NVIDIA_TARGET)
                
                now = time.time()
                if now - last_flutter_send >= FLUTTER_INTERVAL:
                    try:
                        u = struct.unpack("<BhhhhhhBBHBB", pkt)
                        
                        switches_int = u[9]
                        switches_map = {}
                        for i in range(16):
                            switches_map[f'switch_{i}'] = bool(switches_int & (1 << i))
                        
                        # بدون عكس - مباشر
                        left_x = -((u[1] - 2000) / 2000.0)
                        left_y = -((u[2] - 2000) / 2000.0)
                        right_x = -((u[5] - 2000) / 2000.0)
                        right_y = -((u[6] - 2000) / 2000.0)
                        
                        flutter_json = {
                            "type": "joystick_update",
                            "data": {
                                "joystick_left": {
                                    "x": left_x,
                                    "y": left_y
                                },
                                "joystick_right": {
                                    "x": right_x,
                                    "y": right_y
                                },
                                "power": u[3] / 4000.0,
                                "potentiometers": {
                                    "pot1": u[7],
                                    "pot2": u[8]
                                },
                                "switches": switches_map
                            }
                        }
                        
                        flutter_sock.sendto(
                            json.dumps(flutter_json).encode('utf-8'),
                            FLUTTER_TARGET
                        )
                        last_flutter_send = now
                    except:
                        pass
            
            del buf[:19]
    
    except KeyboardInterrupt:
        print("\n✅ Stopped\n")
        break

ser.close()
nvidia_sock.close()
flutter_sock.close()
