#!/usr/bin/env python3
import serial
import struct
import socket
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200
TARGET = ("192.168.100.2", 5656)

START_BYTE = 0xAA
END_BYTE = 0x55
PACKET_SIZE = 19
FMT = "<BhhhhhhBBHBB"

def calc_checksum(packet: bytes) -> int:
    checksum = 0
    for b in packet[1:17]:
        checksum ^= b
    return checksum

def parse_packet(packet: bytes):
    if len(packet) != PACKET_SIZE:
        return None
    if packet[0] != START_BYTE or packet[18] != END_BYTE:
        return None
    if packet[17] != calc_checksum(packet):
        return None
    
    unpacked = struct.unpack(FMT, packet)
    return {
        'drone_x_norm': unpacked[1],
        'drone_y_norm': unpacked[2],
        'power_y_norm': unpacked[3],
        'switch_states': unpacked[9]
    }

print("🎮 STM32 Binary Receiver")
print(f"Port: {PORT}")
print(f"Forwarding to: {TARGET}\n")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
        print("✅ Connected")
        buffer = bytearray()
        
        while True:
            if ser.in_waiting:
                incoming = ser.read(ser.in_waiting)
                buffer.extend(incoming)
            
            while len(buffer) >= PACKET_SIZE:
                start_index = buffer.find(bytes([START_BYTE]))
                
                if start_index < 0:
                    buffer.clear()
                    break
                
                if start_index > 0:
                    del buffer[:start_index]
                
                if len(buffer) < PACKET_SIZE:
                    break
                
                candidate = bytes(buffer[:PACKET_SIZE])
                
                if candidate[18] != END_BYTE:
                    del buffer[0]
                    continue
                
                data = parse_packet(candidate)
                
                if data:
                    sock.sendto(candidate, TARGET)
                    
                    arm = (data['switch_states'] >> 12) & 1
                    status = "🟢 ARM" if arm else "⚪ DIS"
                    
                    print(f"\r{status} | "
                          f"Thr:{data['power_y_norm']:4d} "
                          f"P:{data['drone_y_norm']:4d} "
                          f"R:{data['drone_x_norm']:4d}   ",
                          end='', flush=True)
                
                del buffer[:PACKET_SIZE]
            
            time.sleep(0.001)
    
    except (serial.SerialException, OSError) as e:
        print(f"\n⚠️  Error: {e}")
        print("🔄 Reconnecting in 2s...")
        time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n✅ Stopped\n")
        break
