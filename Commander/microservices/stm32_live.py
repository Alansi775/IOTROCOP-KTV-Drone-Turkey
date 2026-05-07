#!/usr/bin/env python3
import serial
import struct
import sys

PORT = "/dev/ttyUSB0"
BAUD = 115200
PACKET_SIZE = 19
FMT = "<BhhhhhhBBHBB"

def calc_checksum(packet):
    return sum(packet[1:17]) & 0xFF ^ packet[1:17][0]

def parse(packet):
    if len(packet) != 19 or packet[0] != 0xAA or packet[18] != 0x55:
        return None
    try:
        u = struct.unpack(FMT, packet)
        sw = u[9]
        return {
            'dx': u[1], 'dy': u[2], 'pw': u[3], 'sp': u[4],
            'cx': u[5], 'cy': u[6], 'p1': u[7], 'p2': u[8],
            's1': ((sw>>0)&1, (sw>>1)&1), 's2': ((sw>>2)&1, (sw>>3)&1),
            's3': ((sw>>4)&1, (sw>>5)&1), 's4': ((sw>>6)&1, (sw>>7)&1),
            's5': ((sw>>9)&1, (sw>>8)&1), 's6': ((sw>>10)&1, (sw>>11)&1),
            '2p': (sw>>12)&1, 'mm': (sw>>13)&1, 'raw': sw
        }
    except:
        return None

def pos(t, b):
    if t and not b: return "TOP"
    if b and not t: return "BOT"
    if not t and not b: return "MID"
    return "INV"

ser = serial.Serial(PORT, BAUD, timeout=0.1)
buf = bytearray()

print("\033[2J\033[H")  # Clear screen
print("🎮 LIVE STM32 MONITOR - Press Ctrl+C to stop\n")

while True:
    try:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
        
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
            
            d = parse(pkt)
            if d:
                # Print at top of screen
                print("\033[H", end='')  # Move cursor to top
                print(f"┌─ JOYSTICKS ─────────────────────────────────┐")
                print(f"│ Drone  X:{d['dx']:5d} Y:{d['dy']:5d}               │")
                print(f"│ Power  Y:{d['pw']:5d}     Spin:{d['sp']:5d}       │")
                print(f"│ Comp   X:{d['cx']:5d} Y:{d['cy']:5d}               │")
                print(f"├─ POTS ──────────────────────────────────────┤")
                print(f"│ P1:{d['p1']:3d}%  P2:{d['p2']:3d}%                          │")
                print(f"├─ SWITCHES ──────────────────────────────────┤")
                print(f"│ S1:{pos(*d['s1'])} S2:{pos(*d['s2'])} S3:{pos(*d['s3'])} S4:{pos(*d['s4'])} │")
                print(f"│ S5:{pos(*d['s5'])} S6:{pos(*d['s6'])}                    │")
                print(f"│ 2POS:{d['2p']} MOM:{d['mm']}  RAW:0x{d['raw']:04X}           │")
                print(f"└─────────────────────────────────────────────┘")
                sys.stdout.flush()
            
            del buf[:PACKET_SIZE]
    
    except KeyboardInterrupt:
        print("\n\n✅ Stopped\n")
        break

ser.close()
