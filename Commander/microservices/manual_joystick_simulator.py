#!/usr/bin/env python3
"""
Manual joystick simulator - sends packets to Nvidia
Use keyboard to control drone
"""
import socket
import struct
import time
import sys
import termios
import tty

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET = ("192.168.100.2", 5656)

# Initial values
throttle = 2000  # 50% (center)
pitch = 2000     # center
roll = 2000      # center
armed = False

def send_packet():
    packet = struct.pack('<BhhhhhBBHBB',
        0xAA,
        roll,        # drone_x
        pitch,       # drone_y
        throttle,    # power
        2000, 2000,  # comp x,y
        50, 50,      # pots
        0b0001000000000000 if armed else 0,  # SW12 = ARM
        0x00,
        0x55
    )
    sock.sendto(packet, TARGET)

print("🎮 Manual Joystick Control")
print("="*50)
print("Controls:")
print("  W/S  - Throttle up/down")
print("  A/D  - Roll left/right")
print("  Q/E  - Pitch forward/back")
print("  SPACE - ARM/DISARM toggle")
print("  ESC  - Quit")
print("="*50)
print()

# Get terminal settings
old_settings = termios.tcgetattr(sys.stdin)
try:
    tty.setcbreak(sys.stdin.fileno())
    
    while True:
        send_packet()
        
        status = "🟢 ARMED" if armed else "⚪ DISARMED"
        print(f"\r{status} | Thr:{throttle:4d} Pitch:{pitch:4d} Roll:{roll:4d}   ", end='', flush=True)
        
        # Check for key press (non-blocking)
        import select
        if select.select([sys.stdin], [], [], 0.05)[0]:
            key = sys.stdin.read(1)
            
            if key == 'w':
                throttle = min(4000, throttle + 100)
            elif key == 's':
                throttle = max(0, throttle - 100)
            elif key == 'a':
                roll = max(0, roll - 100)
            elif key == 'd':
                roll = min(4000, roll + 100)
            elif key == 'q':
                pitch = max(0, pitch - 100)
            elif key == 'e':
                pitch = min(4000, pitch + 100)
            elif key == ' ':
                armed = not armed
                print(f"\n{'🟢 ARMED!' if armed else '⚪ DISARMED'}")
            elif key == '\x1b':  # ESC
                print("\n\n✅ Stopped\n")
                break

except KeyboardInterrupt:
    print("\n\n^C Stopped\n")
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    sock.close()
