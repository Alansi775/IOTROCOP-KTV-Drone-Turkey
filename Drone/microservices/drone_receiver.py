#!/usr/bin/env python3
"""
Drone Data Network Receiver
Receives and displays drone control data over UDP network
Runs on 192.168.100.2 (Jetson device)
"""

import socket
import json
import struct
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import threading

# ANSI Colors
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    JOYSTICK = '\033[38;5;51m'
    POWER = '\033[38;5;226m'
    POT = '\033[38;5;208m'
    SWITCH = '\033[38;5;141m'
    SYSTEM = '\033[38;5;46m'
    NETWORK = '\033[38;5;201m'


@dataclass
class DronePacket:
    """Drone data packet"""
    drone_x_norm: int
    drone_y_norm: int
    power_y_norm: int
    comp_x_norm: int
    comp_y_norm: int
    pot1_percent: int
    pot2_percent: int
    switch_states: int
    timestamp: float
    
    def format_joystick(self, value: int) -> str:
        """Format joystick value to percentage"""
        percent = ((value - 2000) / 2000.0) * 100.0
        return f"{percent:+6.1f}%"
    
    def format_power(self) -> str:
        """Format power value"""
        percent = (self.power_y_norm / 4000.0) * 100.0
        return f"{percent:5.1f}%"
    
    def format_switches(self) -> str:
        """Format switch states"""
        return format(self.switch_states, '014b')


class DroneDataReceiver:
    """UDP receiver for drone control data"""
    
    def __init__(self, listen_ip: str = "0.0.0.0", listen_port: int = 5656):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.socket = None
        self.running = False
        
        # Statistics
        self.stats = {
            'binary_packets': 0,
            'json_packets': 0,
            'ascii_messages': 0,
            'total_bytes': 0,
            'errors': 0,
            'start_time': None,
            'last_packet_time': None
        }
        
        # Display settings
        self.verbose = True
        self.show_raw_binary = False
        
        # Latest data
        self.latest_packet: Optional[DronePacket] = None
    
    def setup_socket(self) -> bool:
        """Setup UDP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.listen_ip, self.listen_port))
            self.socket.settimeout(1.0)  # 1 second timeout
            
            print(f"{Colors.OKGREEN}✓ Socket bound to {self.listen_ip}:{self.listen_port}{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}✗ Socket setup failed: {e}{Colors.RESET}")
            return False
    
    def parse_binary_packet(self, data: bytes) -> Optional[DronePacket]:
        """Parse raw binary packet (17 bytes)"""
        if len(data) != 17:
            return None
        
        try:
            # Unpack: Start + 5*int16 + 2*uint8 + uint16 + checksum + end
            unpacked = struct.unpack('<BhhhhhBBHBB', data)
            
            # Verify start and end bytes
            if unpacked[0] != 0xAA or unpacked[-1] != 0x55:
                return None
            
            # Extract data fields
            packet = DronePacket(
                drone_x_norm=unpacked[1],
                drone_y_norm=unpacked[2],
                power_y_norm=unpacked[3],
                comp_x_norm=unpacked[4],
                comp_y_norm=unpacked[5],
                pot1_percent=unpacked[6],
                pot2_percent=unpacked[7],
                switch_states=unpacked[8],
                timestamp=time.time()
            )
            
            return packet
            
        except Exception as e:
            if self.verbose:
                print(f"{Colors.WARNING}⚠ Binary parse error: {e}{Colors.RESET}")
            return None
    
    def parse_json_packet(self, data: bytes) -> Optional[dict]:
        """Parse JSON packet"""
        try:
            message = json.loads(data.decode('utf-8'))
            return message
            
        except Exception as e:
            if self.verbose:
                print(f"{Colors.WARNING}⚠ JSON parse error: {e}{Colors.RESET}")
            return None
    
    def display_binary_packet(self, packet: DronePacket):
        """Display binary packet data"""
        self.stats['binary_packets'] += 1
        
        # Format values
        drone_x = packet.format_joystick(packet.drone_x_norm)
        drone_y = packet.format_joystick(packet.drone_y_norm)
        power = packet.format_power()
        comp_x = packet.format_joystick(packet.comp_x_norm)
        comp_y = packet.format_joystick(packet.comp_y_norm)
        switches = packet.format_switches()
        
        # Timestamp
        ts = datetime.fromtimestamp(packet.timestamp).strftime("%H:%M:%S.%f")[:-3]
        
        # Display
        output = f"[{ts}] {Colors.BOLD}PACKET #{self.stats['binary_packets']}{Colors.RESET}\n"
        output += f"  {Colors.JOYSTICK}DRONE:{Colors.RESET} X={drone_x} Y={drone_y}  "
        output += f"{Colors.POWER}POWER:{Colors.RESET} {power}  "
        output += f"{Colors.JOYSTICK}COMP:{Colors.RESET} X={comp_x} Y={comp_y}\n"
        output += f"  {Colors.POT}POT1:{Colors.RESET} {packet.pot1_percent:3d}%  "
        output += f"{Colors.POT}POT2:{Colors.RESET} {packet.pot2_percent:3d}%  "
        output += f"{Colors.SWITCH}SW:{Colors.RESET} {switches}"
        
        print(output)
    
    def display_json_message(self, message: dict):
        """Display JSON message"""
        msg_type = message.get('type', 'unknown')
        
        if msg_type == 'binary_packet':
            # Binary packet data in JSON format
            self.stats['json_packets'] += 1
            data = message.get('data', {})
            
            packet = DronePacket(
                drone_x_norm=data.get('drone_x_norm', 2000),
                drone_y_norm=data.get('drone_y_norm', 2000),
                power_y_norm=data.get('power_y_norm', 2000),
                comp_x_norm=data.get('comp_x_norm', 2000),
                comp_y_norm=data.get('comp_y_norm', 2000),
                pot1_percent=data.get('pot1_percent', 0),
                pot2_percent=data.get('pot2_percent', 0),
                switch_states=data.get('switch_states', 0),
                timestamp=data.get('timestamp', time.time())
            )
            
            self.latest_packet = packet
            # Don't display JSON packets if we're getting binary (avoid duplicates)
            
        elif msg_type == 'ascii_message':
            # ASCII debug message
            self.stats['ascii_messages'] += 1
            ascii_data = message.get('data', {})
            msg_text = ascii_data.get('message', '')
            
            ts = datetime.fromtimestamp(ascii_data.get('timestamp', time.time())).strftime("%H:%M:%S.%f")[:-3]
            
            # Color code
            if '[DRONE_JOY]' in msg_text:
                color = Colors.JOYSTICK
            elif '[POWER_JOY]' in msg_text:
                color = Colors.POWER
            elif '[COMP_JOY]' in msg_text:
                color = Colors.JOYSTICK
            elif '[POT' in msg_text:
                color = Colors.POT
            elif 'POS_' in msg_text or 'MOMENTARY' in msg_text:
                color = Colors.SWITCH
            else:
                color = Colors.OKBLUE
            
            print(f"[{ts}] {color}{msg_text}{Colors.RESET}")
    
    def receive_loop(self):
        """Main receive loop"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}  DRONE DATA RECEIVER - LISTENING{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}\n")
        print(f"{Colors.NETWORK}📡 Listening on {self.listen_ip}:{self.listen_port}{Colors.RESET}")
        print(f"{Colors.OKCYAN}   Waiting for data from 192.168.100.1...{Colors.RESET}\n")
        
        self.stats['start_time'] = time.time()
        
        while self.running:
            try:
                # Receive data with timeout
                data, addr = self.socket.recvfrom(4096)
                
                self.stats['total_bytes'] += len(data)
                self.stats['last_packet_time'] = time.time()
                
                # Try to parse as binary packet first (17 bytes)
                if len(data) == 17:
                    packet = self.parse_binary_packet(data)
                    if packet:
                        self.latest_packet = packet
                        self.display_binary_packet(packet)
                        continue
                
                # Try to parse as JSON
                message = self.parse_json_packet(data)
                if message:
                    self.display_json_message(message)
                else:
                    # Unknown format
                    self.stats['errors'] += 1
                    if self.verbose:
                        print(f"{Colors.WARNING}⚠ Unknown data format ({len(data)} bytes) from {addr}{Colors.RESET}")
                
            except socket.timeout:
                # No data received, continue
                continue
                
            except KeyboardInterrupt:
                break
                
            except Exception as e:
                self.stats['errors'] += 1
                print(f"{Colors.FAIL}✗ Error: {e}{Colors.RESET}")
    
    def print_statistics(self):
        """Print session statistics"""
        if self.stats['start_time']:
            duration = time.time() - self.stats['start_time']
            
            print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}SESSION STATISTICS:{Colors.RESET}")
            print(f"  Duration:        {duration:.1f} seconds")
            print(f"  Binary Packets:  {self.stats['binary_packets']}")
            print(f"  JSON Packets:    {self.stats['json_packets']}")
            print(f"  ASCII Messages:  {self.stats['ascii_messages']}")
            print(f"  Total Bytes:     {self.stats['total_bytes']}")
            print(f"  Errors:          {self.stats['errors']}")
            
            if duration > 0:
                total_packets = self.stats['binary_packets'] + self.stats['json_packets']
                print(f"  Packet Rate:     {total_packets/duration:.1f} pkt/sec")
                print(f"  Data Rate:       {self.stats['total_bytes']/duration:.0f} bytes/sec")
            
            if self.stats['last_packet_time']:
                elapsed = time.time() - self.stats['last_packet_time']
                print(f"  Last Packet:     {elapsed:.1f} seconds ago")
            
            print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}\n")
    
    def start(self):
        """Start receiver"""
        if not self.setup_socket():
            return False
        
        self.running = True
        
        try:
            self.receive_loop()
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠ Interrupted by user{Colors.RESET}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop receiver"""
        self.running = False
        
        self.print_statistics()
        
        if self.socket:
            self.socket.close()
            print(f"{Colors.OKGREEN}✓ Socket closed{Colors.RESET}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Drone Data Network Receiver (192.168.100.2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Listen on all interfaces, port 5656
  %(prog)s -p 6666                # Custom port
  %(prog)s --ip 192.168.100.2     # Specific interface
  %(prog)s --quiet                # Less verbose output
        """
    )
    
    parser.add_argument('--ip', default='0.0.0.0',
                       help='Listen IP address (default: 0.0.0.0 = all interfaces)')
    parser.add_argument('-p', '--port', type=int, default=5656,
                       help='Listen UDP port (default: 5656)')
    parser.add_argument('--quiet', action='store_true',
                       help='Quiet mode - less verbose')
    
    args = parser.parse_args()
    
    # Banner
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     DRONE DATA NETWORK RECEIVER v2.0                               ║")
    print("║     UDP Receiver for STM32 Drone Control Data                      ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    receiver = DroneDataReceiver(listen_ip=args.ip, listen_port=args.port)
    receiver.verbose = not args.quiet
    
    try:
        receiver.start()
    except Exception as e:
        print(f"{Colors.FAIL}✗ Fatal error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
