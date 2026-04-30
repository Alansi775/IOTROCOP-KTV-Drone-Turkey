#!/usr/bin/env python3
"""
STM32F407 Drone Remote Binary Protocol Receiver
For IOTROCOP KTV Drone System
"""

import serial
import struct
import time
import json
import socket

# ============ CONFIGURATION ============
UART_PORT = "/dev/ttyUSB0"
UART_BAUD = 115200

# UDP forwarding to NVIDIA Jetson
NVIDIA_IP = "192.168.100.2"
NVIDIA_PORT = 5656

# Protocol constants
START_BYTE = 0xAA
END_BYTE = 0x55
PACKET_SIZE = 19
PACKET_FORMAT = "<BhhhhhhBBHBB"

# ============ FUNCTIONS ============

def calc_checksum(packet: bytes) -> int:
    checksum = 0
    for b in packet[1:17]:
        checksum ^= b
    return checksum


def is_bit_set(value: int, bit: int) -> int:
    return (value >> bit) & 0x01


def decode_3pos_switch(top: int, bot: int) -> str:
    if top == 1 and bot == 0:
        return "TOP"
    elif top == 0 and bot == 1:
        return "BOTTOM"
    elif top == 0 and bot == 0:
        return "MIDDLE"
    else:
        return "INVALID"


def parse_packet(packet: bytes):
    if len(packet) != PACKET_SIZE:
        return None
    
    if packet[0] != START_BYTE or packet[18] != END_BYTE:
        return None
    
    received_checksum = packet[17]
    calculated_checksum = calc_checksum(packet)
    if received_checksum != calculated_checksum:
        return None
    
    unpacked = struct.unpack(PACKET_FORMAT, packet)
    
    data = {
        "drone_x_norm": unpacked[1],
        "drone_y_norm": unpacked[2],
        "power_y_norm": unpacked[3],
        "spin_y_norm": unpacked[4],
        "comp_x_norm": unpacked[5],
        "comp_y_norm": unpacked[6],
        "pot1_percent": unpacked[7],
        "pot2_percent": unpacked[8],
        "switch_states": unpacked[9],
    }
    
    data["power_percent"] = (data["power_y_norm"] / 4000.0) * 100.0
    data["spin_percent"] = ((data["spin_y_norm"] - 2000) / 2000.0) * 100.0
    
    switches = data["switch_states"]
    data["switches"] = {
        "SW1": decode_3pos_switch(is_bit_set(switches, 0), is_bit_set(switches, 1)),
        "SW2": decode_3pos_switch(is_bit_set(switches, 2), is_bit_set(switches, 3)),
        "SW3": decode_3pos_switch(is_bit_set(switches, 4), is_bit_set(switches, 5)),
        "SW4": decode_3pos_switch(is_bit_set(switches, 6), is_bit_set(switches, 7)),
        "SW5": decode_3pos_switch(is_bit_set(switches, 9), is_bit_set(switches, 8)),
        "SW6": decode_3pos_switch(is_bit_set(switches, 10), is_bit_set(switches, 11)),
        "TWO_POS": is_bit_set(switches, 12),
        "MOMENTARY": is_bit_set(switches, 13),
    }
    
    return data


def format_joystick_packet(data: dict) -> dict:
    joystick_data = {
        "type": "joystick_update",
        "data": {
            "joystick_left": {
                "x": (data["drone_x_norm"] - 2000) / 2000.0,
                "y": (data["drone_y_norm"] - 2000) / 2000.0,
            },
            "joystick_right": {
                "x": (data["comp_x_norm"] - 2000) / 2000.0,
                "y": (data["comp_y_norm"] - 2000) / 2000.0,
            },
            "power": data["power_percent"] / 100.0,
            "potentiometers": {
                "pot1": data["pot1_percent"],
                "pot2": data["pot2_percent"],
            },
            "switches": data["switches"],
            "switches_raw": data["switch_states"],
        }
    }
    
    return joystick_data


def main():
    print("=" * 60)
    print("🎮 STM32 Joystick Receiver - IOTROCOP KTV Drone")
    print("=" * 60)
    print(f"📡 UART Port: {UART_PORT}")
    print(f"📡 Baudrate: {UART_BAUD}")
    print(f"📦 Packet Size: {PACKET_SIZE} bytes")
    print(f"🎯 Forwarding to: {NVIDIA_IP}:{NVIDIA_PORT}")
    print("=" * 60)
    
    try:
        ser = serial.Serial(
            port=UART_PORT,
            baudrate=UART_BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05
        )
        print("✅ UART opened successfully")
    except Exception as e:
        print(f"❌ Failed to open UART: {e}")
        print("\n💡 Try these ports:")
        print("   - /dev/serial0")
        print("   - /dev/ttyAMA0")
        print("   - /dev/ttyS0")
        return
    
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("✅ UDP socket ready")
    print()
    
    buffer = bytearray()
    packet_count = 0
    error_count = 0
    
    print("🔄 Listening for STM32 packets...")
    print()
    
    while True:
        try:
            incoming = ser.read(ser.in_waiting or 1)
            
            if incoming:
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
                    error_count += 1
                    continue
                
                data = parse_packet(candidate)
                
                if data is None:
                    del buffer[0]
                    error_count += 1
                    continue
                
                packet_count += 1
                
                if packet_count % 10 == 0:
                    print(
                        f"📊 DRONE X:{data['drone_x_norm']:4d} Y:{data['drone_y_norm']:4d} | "
                        f"POWER:{data['power_percent']:6.1f}% | "
                        f"SPIN:{data['spin_percent']:+6.1f}% | "
                        f"COMP X:{data['comp_x_norm']:4d} Y:{data['comp_y_norm']:4d} | "
                        f"POT1:{data['pot1_percent']:3d}% POT2:{data['pot2_percent']:3d}% | "
                        f"SW:0x{data['switch_states']:04X} | "
                        f"PKT:{packet_count} ERR:{error_count}"
                    )
                
                joystick_packet = format_joystick_packet(data)
                udp_data = json.dumps(joystick_packet).encode('utf-8')
                udp_sock.sendto(udp_data, (NVIDIA_IP, NVIDIA_PORT))
                
                del buffer[:PACKET_SIZE]
            
            time.sleep(0.001)
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            error_count += 1
            time.sleep(0.1)
    
    ser.close()
    udp_sock.close()
    print(f"\n📊 Total packets: {packet_count}")
    print(f"⚠️  Total errors: {error_count}")
    print("✅ Shutdown complete")


if __name__ == "__main__":
    main()
