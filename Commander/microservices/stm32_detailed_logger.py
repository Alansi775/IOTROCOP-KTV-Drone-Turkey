#!/usr/bin/env python3
"""
STM32 Detailed Logger - Shows ALL values
Use this to identify which switch/joystick is which
"""
import serial
import struct
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

START_BYTE = 0xAA
END_BYTE = 0x55
PACKET_SIZE = 19
FMT = "<BhhhhhhBBHBB"

def calc_checksum(packet: bytes) -> int:
    checksum = 0
    for b in packet[1:17]:
        checksum ^= b
    return checksum

def is_bit_set(value: int, bit: int) -> int:
    return (value >> bit) & 1

def decode_3pos(top: int, bot: int) -> str:
    if top == 1 and bot == 0:
        return "TOP"
    elif top == 0 and bot == 1:
        return "BOT"
    elif top == 0 and bot == 0:
        return "MID"
    else:
        return "INV"

def parse_packet(packet: bytes):
    if len(packet) != PACKET_SIZE:
        return None
    if packet[0] != START_BYTE or packet[18] != END_BYTE:
        return None
    if packet[17] != calc_checksum(packet):
        return None
    
    unpacked = struct.unpack(FMT, packet)
    
    return {
        'drone_x': unpacked[1],
        'drone_y': unpacked[2],
        'power_y': unpacked[3],
        'spin_y': unpacked[4],
        'comp_x': unpacked[5],
        'comp_y': unpacked[6],
        'pot1': unpacked[7],
        'pot2': unpacked[8],
        'switches': unpacked[9]
    }

print("="*80)
print("🎮 STM32 DETAILED LOGGER - Move controls to see which is which")
print("="*80)
print()

while True:
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            timeout=0.5
        )
        
        print(f"✅ Connected to {PORT}\n")
        buffer = bytearray()
        last_data = None
        
        while True:
            if ser.in_waiting:
                buffer.extend(ser.read(ser.in_waiting))
            
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
                
                if data and data != last_data:
                    switches = data['switches']
                    
                    # Decode switches
                    sw1 = decode_3pos(is_bit_set(switches, 0), is_bit_set(switches, 1))
                    sw2 = decode_3pos(is_bit_set(switches, 2), is_bit_set(switches, 3))
                    sw3 = decode_3pos(is_bit_set(switches, 4), is_bit_set(switches, 5))
                    sw4 = decode_3pos(is_bit_set(switches, 6), is_bit_set(switches, 7))
                    sw5 = decode_3pos(is_bit_set(switches, 9), is_bit_set(switches, 8))
                    sw6 = decode_3pos(is_bit_set(switches, 10), is_bit_set(switches, 11))
                    two_pos = is_bit_set(switches, 12)
                    momentary = is_bit_set(switches, 13)
                    
                    print(f"┌─ JOYSTICKS ─────────────────────────────────────────────────┐")
                    print(f"│ Drone   X:{data['drone_x']:5d}  Y:{data['drone_y']:5d}                      │")
                    print(f"│ Power   Y:{data['power_y']:5d}                                    │")
                    print(f"│ Spin    Y:{data['spin_y']:5d}                                    │")
                    print(f"│ Comp    X:{data['comp_x']:5d}  Y:{data['comp_y']:5d}                      │")
                    print(f"├─ POTENTIOMETERS ────────────────────────────────────────────┤")
                    print(f"│ POT1: {data['pot1']:3d}%    POT2: {data['pot2']:3d}%                              │")
                    print(f"├─ SWITCHES ──────────────────────────────────────────────────┤")
                    print(f"│ SW1:{sw1}  SW2:{sw2}  SW3:{sw3}  SW4:{sw4}  SW5:{sw5}  SW6:{sw6} │")
                    print(f"│ 2-POS: {two_pos}    MOMENTARY: {momentary}                                │")
                    print(f"│ RAW: 0x{switches:04X}                                             │")
                    print(f"└─────────────────────────────────────────────────────────────┘")
                    print()
                    
                    last_data = data
                
                del buffer[:PACKET_SIZE]
            
            time.sleep(0.01)
    
    except (serial.SerialException, OSError) as e:
        print(f"⚠️  {e}")
        print("🔄 Reconnecting in 2s...\n")
        time.sleep(2)
    except KeyboardInterrupt:
        print("\n✅ Stopped\n")
        break
