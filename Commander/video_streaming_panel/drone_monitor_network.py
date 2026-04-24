#!/usr/bin/env python3
"""
STM32 Drone Control System Monitor with Network Transmission + Flutter Bridge
ENHANCED VERSION - Individual Switch States with IDs
Monitors serial data and transmits to:
  1. Console (existing)
  2. Remote receiver via UDP (existing)
  3. Flutter UI via UDP Bridge (ENHANCED - with individual switch states)
"""

import serial
import serial.tools.list_ports
import struct
import sys
import time
import socket
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
import threading
from collections import deque

# ANSI Color codes
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
    NETWORK = '\033[38;5;201m'  # Magenta for network
    FLUTTER = '\033[38;5;105m'  # Purple for Flutter


@dataclass
class DronePacket:
    """STM32 binary packet structure - 17 bytes total"""
    start_byte: int      # Byte 0: 0xAA
    drone_x_norm: int    # Bytes 1-2: int16
    drone_y_norm: int    # Bytes 3-4: int16
    power_y_norm: int    # Bytes 5-6: int16
    comp_x_norm: int     # Bytes 7-8: int16
    comp_y_norm: int     # Bytes 9-10: int16
    pot1_percent: int    # Byte 11: uint8
    pot2_percent: int    # Byte 12: uint8
    switch_states: int   # Bytes 13-14: uint16
    checksum: int        # Byte 15: uint8
    end_byte: int        # Byte 16: 0x55

    @property
    def is_valid(self) -> bool:
        """Validate packet structure"""
        return self.start_byte == 0xAA and self.end_byte == 0x55

    def verify_checksum(self) -> bool:
        """Verify packet checksum - XOR of all data bytes"""
        data = struct.pack('<hhhhhBBH',
                          self.drone_x_norm,
                          self.drone_y_norm,
                          self.power_y_norm,
                          self.comp_x_norm,
                          self.comp_y_norm,
                          self.pot1_percent,
                          self.pot2_percent,
                          self.switch_states)

        calc_checksum = 0
        for byte in data:
            calc_checksum ^= byte

        return calc_checksum == self.checksum

    def get_individual_switches(self) -> dict:
        """
        16-bit switch_states değerini tek tek switch'lere ayır
        Her switch'e 0-15 arası ID atanır
        
        Returns:
            dict: {'switch_0': True/False, 'switch_1': True/False, ..., 'switch_15': True/False}
        
        Example:
            switch_states = 0b0000000000001001 (decimal 9)
            Returns: {
                'switch_0': True,   # bit 0 = 1
                'switch_1': False,  # bit 1 = 0
                'switch_2': False,  # bit 2 = 0
                'switch_3': True,   # bit 3 = 1
                ...
            }
        """
        switches = {}
        for i in range(16):
            # Her bit'i kontrol et (0'dan 15'e kadar)
            bit_value = (self.switch_states >> i) & 1
            switches[f'switch_{i}'] = bool(bit_value)
        return switches

    def get_switch_value(self, switch_id: int) -> bool:
        """
        Belirli bir switch'in değerini al
        
        Args:
            switch_id: 0-15 arası switch numarası
            
        Returns:
            bool: True (basılı) veya False (basılı değil)
            
        Raises:
            ValueError: switch_id 0-15 aralığında değilse
            
        Example:
            if packet.get_switch_value(0):
                print("Switch 0 basılı!")
        """
        if not 0 <= switch_id <= 15:
            raise ValueError(f"Switch ID 0-15 arasında olmalı, {switch_id} geldi")
        return bool((self.switch_states >> switch_id) & 1)

    def get_active_switches(self) -> list:
        """
        Aktif (basılı) olan switch'lerin ID listesini döndür
        
        Returns:
            list: Aktif switch ID'leri [0, 3, 7, ...]
            
        Example:
            active = packet.get_active_switches()
            print(f"Aktif switch'ler: {active}")  # [0, 3, 7]
        """
        active = []
        for i in range(16):
            if self.get_switch_value(i):
                active.append(i)
        return active

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON transmission"""
        return {
            'drone_x_norm': self.drone_x_norm,
            'drone_y_norm': self.drone_y_norm,
            'power_y_norm': self.power_y_norm,
            'comp_x_norm': self.comp_x_norm,
            'comp_y_norm': self.comp_y_norm,
            'pot1_percent': self.pot1_percent,
            'pot2_percent': self.pot2_percent,
            'switch_states_raw': self.switch_states,  # Ham değer (backward compatibility)
            'switches': self.get_individual_switches(),  # Ayrıştırılmış switch'ler
            'active_switches': self.get_active_switches(),  # Aktif switch ID listesi
            'timestamp': time.time()
        }


class FlutterBridge:
    """
    Real-time data bridge for Flutter UI - ENHANCED VERSION
    Publishes joystick + power + individual switch data via UDP
    Low-latency, high-frequency updates
    """

    def __init__(self, target_ip: str = "127.0.0.1", target_port: int = 5657):
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.enabled = True

        # Statistics
        self.packets_sent = 0
        self.bytes_sent = 0
        self.last_send_time = 0
        self.min_interval = 0.016  # ~60 Hz max (16ms between packets)
        self.errors = 0

        print(f"{Colors.FLUTTER}🎮 Flutter Bridge initialized (ENHANCED){Colors.RESET}")
        print(f"{Colors.FLUTTER}   Target: {target_ip}:{target_port} (UDP){Colors.RESET}")
        print(f"{Colors.FLUTTER}   Max Rate: ~60 Hz (low-latency mode){Colors.RESET}")
        print(f"{Colors.FLUTTER}   Features: Individual Switch States (0-15){Colors.RESET}")

    def publish_joystick_data(self, packet: DronePacket) -> bool:
        """
        Publish joystick + power + ENHANCED SWITCH data to Flutter
        Normalized values for direct UI consumption
        NOW INCLUDES: Individual switch states (0-15) as separate booleans
        """
        if not self.enabled:
            return False

        # Throttle to prevent flooding (60 Hz max)
        now = time.time()
        if now - self.last_send_time < self.min_interval:
            return False

        try:
            # Normalize helper (0-4000 → -1.0 to 1.0)
            def normalize(value):
                return round((value - 2000) / 2000.0, 3)

            # Get individual switch states
            individual_switches = packet.get_individual_switches()
            active_switches = packet.get_active_switches()

            # Flutter-friendly JSON format with ENHANCED switch data
            message = {
                'type': 'joystick_update',
                'timestamp': now,
                'data': {
                    # Left joystick (HAREKET)
                    'joystick_left': {
                        'x': normalize(packet.drone_x_norm),
                        'y': normalize(packet.drone_y_norm)
                    },
                    # Right joystick (YÖN)
                    'joystick_right': {
                        'x': normalize(packet.comp_x_norm),
                        'y': normalize(packet.comp_y_norm)
                    },
                    # Power/Throttle (0.0 to 1.0)
                    'power': round(packet.power_y_norm / 4000.0, 3),
                    # Extra sensors
                    'potentiometers': {
                        'pot1': packet.pot1_percent,
                        'pot2': packet.pot2_percent
                    },
                    # ENHANCED: Individual switches (switch_0 to switch_15)
                    'switches': individual_switches,
                    # Active switch IDs (for easy filtering)
                    'active_switches': active_switches,
                    # Also keep raw value for backward compatibility
                    'switches_raw': packet.switch_states
                }
            }

            # Compact JSON encoding
            json_data = json.dumps(message, separators=(',', ':')).encode('utf-8')
            self.socket.sendto(json_data, (self.target_ip, self.target_port))

            self.packets_sent += 1
            self.bytes_sent += len(json_data)
            self.last_send_time = now

            return True

        except Exception as e:
            self.errors += 1
            if self.errors % 100 == 1:  # Only print every 100th error
                print(f"{Colors.WARNING}⚠ Flutter Bridge error: {e}{Colors.RESET}")
            return False

    def get_stats(self) -> dict:
        """Get transmission statistics"""
        return {
            'packets_sent': self.packets_sent,
            'bytes_sent': self.bytes_sent,
            'max_rate_hz': round(1.0 / self.min_interval, 1) if self.min_interval > 0 else 0,
            'errors': self.errors
        }

    def close(self):
        """Close Flutter bridge"""
        self.socket.close()
        print(f"{Colors.FLUTTER}✓ Flutter Bridge closed{Colors.RESET}")


class NetworkTransmitter:
    """UDP network transmitter for drone data"""

    def __init__(self, target_ip: str = "192.168.100.2", target_port: int = 5656):
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Statistics
        self.packets_sent = 0
        self.bytes_sent = 0
        self.last_error = None

        print(f"{Colors.NETWORK}📡 Network Transmitter initialized{Colors.RESET}")
        print(f"{Colors.NETWORK}   Target: {target_ip}:{target_port}{Colors.RESET}")

    def send_binary_packet(self, packet: DronePacket) -> bool:
        """Send raw binary packet over network"""
        try:
            # Pack the packet as binary (17 bytes)
            data = struct.pack('<BhhhhhBBHBB',
                             packet.start_byte,
                             packet.drone_x_norm,
                             packet.drone_y_norm,
                             packet.power_y_norm,
                             packet.comp_x_norm,
                             packet.comp_y_norm,
                             packet.pot1_percent,
                             packet.pot2_percent,
                             packet.switch_states,
                             packet.checksum,
                             packet.end_byte)

            self.socket.sendto(data, (self.target_ip, self.target_port))
            self.packets_sent += 1
            self.bytes_sent += len(data)
            return True

        except Exception as e:
            self.last_error = str(e)
            return False

    def send_json_packet(self, packet: DronePacket) -> bool:
        """Send packet as JSON over network"""
        try:
            # Convert to JSON with message type
            message = {
                'type': 'binary_packet',
                'data': packet.to_dict()
            }

            json_data = json.dumps(message).encode('utf-8')
            self.socket.sendto(json_data, (self.target_ip, self.target_port))
            self.packets_sent += 1
            self.bytes_sent += len(json_data)
            return True

        except Exception as e:
            self.last_error = str(e)
            return False

    def send_ascii_message(self, message: str) -> bool:
        """Send ASCII debug message over network"""
        try:
            # Send as JSON
            packet = {
                'type': 'ascii_message',
                'data': {
                    'message': message,
                    'timestamp': time.time()
                }
            }

            json_data = json.dumps(packet).encode('utf-8')
            self.socket.sendto(json_data, (self.target_ip, self.target_port))
            return True

        except Exception as e:
            self.last_error = str(e)
            return False

    def get_stats(self) -> dict:
        """Get transmission statistics"""
        return {
            'packets_sent': self.packets_sent,
            'bytes_sent': self.bytes_sent,
            'last_error': self.last_error
        }

    def close(self):
        """Close network connection"""
        self.socket.close()


class DroneMonitor:
    """Main monitoring class with network transmission + Flutter bridge"""

    # Binary packet structure: 17 bytes total
    PACKET_FORMAT = '<BhhhhhBBHBB'
    PACKET_SIZE = 17
    START_BYTE = 0xAA
    END_BYTE = 0x55

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200,
                 enable_network: bool = True, target_ip: str = "192.168.100.2",
                 target_port: int = 5656,
                 enable_flutter: bool = True, flutter_ip: str = "127.0.0.1",
                 flutter_port: int = 5657):

        self.port = port if port else "/dev/ttyUSB0"
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.log_file = None

        # Network transmitter (EXISTING)
        self.enable_network = enable_network
        self.transmitter = None
        if enable_network:
            self.transmitter = NetworkTransmitter(target_ip, target_port)

        # Flutter Bridge (ENHANCED)
        self.enable_flutter = enable_flutter
        self.flutter_bridge = None
        if enable_flutter:
            self.flutter_bridge = FlutterBridge(flutter_ip, flutter_port)

        # Statistics
        self.stats = {
            'binary_packets': 0,
            'ascii_messages': 0,
            'errors': 0,
            'start_time': None
        }

        # Buffers
        self.packet_buffer = bytearray()
        self.line_buffer = ""

    def find_stm32_port(self) -> Optional[str]:
        """Auto-detect STM32 USB serial port (FTDI USB-UART)"""
        print(f"{Colors.OKCYAN}🔍 Searching for STM32 device...{Colors.RESET}")

        ports = serial.tools.list_ports.comports()

        # Priority 1: FTDI USB-UART
        ftdi_keywords = ['FTDI', 'FT232R', 'USB UART']
        stm32_keywords = ['STM32', 'STMicroelectronics', 'USB Serial', 'CDC']

        for port in ports:
            port_info = f"{port.device} - {port.description}"
            print(f"  Found: {port_info}")

            # Check for FTDI
            for keyword in ftdi_keywords:
                if keyword.lower() in port.description.lower():
                    print(f"{Colors.OKGREEN}✓ Detected FTDI USB-UART: {port.device}{Colors.RESET}")
                    return port.device

            # Check VID:PID for FTDI
            if port.vid == 0x0403 and port.pid == 0x6001:
                print(f"{Colors.OKGREEN}✓ Detected FTDI (VID:PID): {port.device}{Colors.RESET}")
                return port.device

            # Check for STM32
            for keyword in stm32_keywords:
                if keyword.lower() in port.description.lower():
                    print(f"{Colors.OKGREEN}✓ Detected STM32: {port.device}{Colors.RESET}")
                    return port.device

        if ports:
            print(f"{Colors.WARNING}⚠ Using first available: {ports[0].device}{Colors.RESET}")
            return ports[0].device

        return None

    def connect(self) -> bool:
        """Establish serial connection"""
        if self.port:
            try:
                print(f"{Colors.OKCYAN}🔌 Trying port: {self.port}{Colors.RESET}")
                self.serial_conn = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0
                )

                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()

                print(f"{Colors.OKGREEN}✓ Connected to {self.port} @ {self.baudrate} baud{Colors.RESET}")
                return True

            except Exception as e:
                print(f"{Colors.WARNING}⚠ Failed: {e}{Colors.RESET}")
                print(f"{Colors.OKCYAN}   Trying auto-detection...{Colors.RESET}")

        detected_port = self.find_stm32_port()
        if not detected_port:
            print(f"{Colors.FAIL}✗ No serial port found!{Colors.RESET}")
            return False

        self.port = detected_port

        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )

            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            print(f"{Colors.OKGREEN}✓ Connected to {self.port} @ {self.baudrate} baud{Colors.RESET}")
            return True

        except Exception as e:
            print(f"{Colors.FAIL}✗ Connection failed: {e}{Colors.RESET}")
            return False

    def setup_logging(self, log_dir: str = "logs"):
        """Setup file logging"""
        import os
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{log_dir}/drone_log_{timestamp}.txt"

        self.log_file = open(log_filename, 'w', encoding='utf-8')
        print(f"{Colors.OKCYAN}📝 Logging to: {log_filename}{Colors.RESET}")

    def log(self, message: str, console_only: bool = False):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"

        print(log_line)

        if self.log_file and not console_only:
            import re
            clean_line = re.sub(r'\033\[[0-9;]+m', '', log_line)
            self.log_file.write(clean_line + '\n')
            self.log_file.flush()

    def parse_binary_packet(self, data: bytes) -> Optional[DronePacket]:
        """Parse binary packet from STM32"""
        if len(data) != self.PACKET_SIZE:
            return None

        try:
            unpacked = struct.unpack(self.PACKET_FORMAT, data)
            packet = DronePacket(*unpacked)

            if not packet.is_valid:
                return None

            if not packet.verify_checksum():
                return None

            return packet

        except struct.error:
            return None

    def format_joystick_value(self, value: int) -> str:
        """Format normalized joystick value (0-4000) to percentage"""
        percent = ((value - 2000) / 2000.0) * 100.0
        return f"{percent:+6.1f}%"

    def format_switch_states(self, switch_bits: int) -> str:
        """Format switch states as binary"""
        return format(switch_bits, '016b')  # 16 bits

    def display_packet(self, packet: DronePacket):
        """Display parsed binary packet + transmit to all endpoints"""
        self.stats['binary_packets'] += 1

        # [EXISTING] Send over network
        if self.enable_network and self.transmitter:
            self.transmitter.send_json_packet(packet)
            self.transmitter.send_binary_packet(packet)

        # [ENHANCED] Send to Flutter Bridge with individual switch states
        if self.enable_flutter and self.flutter_bridge:
            self.flutter_bridge.publish_joystick_data(packet)

        # [ENHANCED] Get individual switch information
        switches = packet.get_individual_switches()
        active_switches = packet.get_active_switches()

        # [EXISTING] Format for console display
        drone_x = self.format_joystick_value(packet.drone_x_norm)
        drone_y = self.format_joystick_value(packet.drone_y_norm)
        power = (packet.power_y_norm / 4000.0) * 100.0
        comp_x = self.format_joystick_value(packet.comp_x_norm)
        comp_y = self.format_joystick_value(packet.comp_y_norm)

        # Show Flutter indicator if enabled
        flutter_icon = f"{Colors.FLUTTER}🎮{Colors.RESET}" if self.enable_flutter else ""
        network_icon = f"{Colors.NETWORK}📡{Colors.RESET}" if self.enable_network else ""

        output = f"{Colors.BOLD}[PACKET #{self.stats['binary_packets']}]{Colors.RESET} "
        output += f"{network_icon} {flutter_icon}\n"
        output += f"{Colors.JOYSTICK}  DRONE:{Colors.RESET} X={drone_x} Y={drone_y}  "
        output += f"{Colors.POWER}POWER:{Colors.RESET} {power:5.1f}%  "
        output += f"{Colors.JOYSTICK}COMP:{Colors.RESET} X={comp_x} Y={comp_y}\n"
        output += f"{Colors.POT}  POT1:{Colors.RESET} {packet.pot1_percent:3d}%  "
        output += f"{Colors.POT}POT2:{Colors.RESET} {packet.pot2_percent:3d}%\n"
        
        # [ENHANCED] Display individual switches
        output += f"{Colors.SWITCH}  SWITCHES:{Colors.RESET} "
        if active_switches:
            switch_labels = [f"SW{i}" for i in active_switches]
            output += f"{Colors.OKGREEN}{', '.join(switch_labels)}{Colors.RESET}"
        else:
            output += f"{Colors.WARNING}None Active{Colors.RESET}"
        
        # Binary representation (for debugging)
        output += f"  [{self.format_switch_states(packet.switch_states)}]"

        self.log(output, console_only=False)

    def process_ascii_line(self, line: str):
        """Process ASCII debug message"""
        line = line.strip()
        if not line:
            return

        self.stats['ascii_messages'] += 1

        # [EXISTING] Send over network
        if self.enable_network and self.transmitter:
            self.transmitter.send_ascii_message(line)

        # [EXISTING] Color code
        if '[DRONE_JOY]' in line:
            color = Colors.JOYSTICK
        elif '[POWER_JOY]' in line:
            color = Colors.POWER
        elif '[COMP_JOY]' in line:
            color = Colors.JOYSTICK
        elif '[POT' in line:
            color = Colors.POT
        elif 'POS_' in line or 'MOMENTARY' in line:
            color = Colors.SWITCH
        elif 'READY' in line or 'SYSTEM' in line:
            color = Colors.SYSTEM
        elif '===' in line:
            color = Colors.HEADER
        else:
            color = Colors.OKBLUE

        self.log(f"{color}{line}{Colors.RESET}")

    def read_serial_data(self):
        """Main serial reading loop with multi-endpoint transmission"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}  STM32 DRONE MONITOR v3.2 - ENHANCED SWITCH EDITION{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}\n")

        if self.enable_network:
            print(f"{Colors.NETWORK}📡 Network transmission: ENABLED{Colors.RESET}")
            print(f"{Colors.NETWORK}   Target: {self.transmitter.target_ip}:{self.transmitter.target_port}{Colors.RESET}")

        if self.enable_flutter:
            print(f"{Colors.FLUTTER}🎮 Flutter Bridge: ENABLED (ENHANCED){Colors.RESET}")
            print(f"{Colors.FLUTTER}   Target: {self.flutter_bridge.target_ip}:{self.flutter_bridge.target_port}{Colors.RESET}")
            print(f"{Colors.FLUTTER}   Individual Switch States: 0-15 with IDs{Colors.RESET}")

        print()

        self.stats['start_time'] = time.time()

        # State machine
        IN_ASCII = 0
        IN_BINARY = 1
        SEARCHING = 2

        state = SEARCHING
        consecutive_ascii = 0

        while self.running:
            try:
                if self.serial_conn.in_waiting > 0:
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting)

                    for byte in chunk:
                        # Binary packet start
                        if byte == self.START_BYTE:
                            if len(self.packet_buffer) > 0:
                                self.packet_buffer.clear()

                            self.packet_buffer.append(byte)
                            state = IN_BINARY
                            consecutive_ascii = 0

                        elif len(self.packet_buffer) > 0:
                            # Building binary packet
                            self.packet_buffer.append(byte)

                            if len(self.packet_buffer) == self.PACKET_SIZE:
                                if self.packet_buffer[-1] == self.END_BYTE:
                                    packet = self.parse_binary_packet(bytes(self.packet_buffer))
                                    if packet:
                                        self.display_packet(packet)
                                    else:
                                        self.stats['errors'] += 1
                                else:
                                    self.stats['errors'] += 1

                                self.packet_buffer.clear()
                                state = SEARCHING

                            elif len(self.packet_buffer) > self.PACKET_SIZE:
                                self.packet_buffer.clear()
                                state = SEARCHING
                                self.stats['errors'] += 1

                        else:
                            # ASCII character
                            try:
                                char = chr(byte)

                                if 32 <= byte <= 126 or byte in [9, 10, 13]:
                                    consecutive_ascii += 1
                                    state = IN_ASCII

                                    if char == '\n':
                                        if self.line_buffer.strip():
                                            self.process_ascii_line(self.line_buffer)
                                        self.line_buffer = ""
                                    elif char != '\r':
                                        self.line_buffer += char
                                else:
                                    if consecutive_ascii < 3:
                                        pass
                                    consecutive_ascii = 0

                            except:
                                pass

                else:
                    time.sleep(0.01)

            except serial.SerialException as e:
                self.log(f"{Colors.FAIL}✗ Serial error: {e}{Colors.RESET}")
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"{Colors.FAIL}✗ Error: {e}{Colors.RESET}")
                self.stats['errors'] += 1

    def print_statistics(self):
        """Print session statistics"""
        if self.stats['start_time']:
            duration = time.time() - self.stats['start_time']

            print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}SESSION STATISTICS:{Colors.RESET}")
            print(f"  Duration:        {duration:.1f} seconds")
            print(f"  Binary Packets:  {self.stats['binary_packets']}")
            print(f"  ASCII Messages:  {self.stats['ascii_messages']}")
            print(f"  Errors:          {self.stats['errors']}")
            if duration > 0:
                print(f"  Packet Rate:     {self.stats['binary_packets']/duration:.1f} pkt/sec")

            if self.enable_network and self.transmitter:
                net_stats = self.transmitter.get_stats()
                print(f"\n{Colors.NETWORK}NETWORK STATISTICS:{Colors.RESET}")
                print(f"  Packets Sent:    {net_stats['packets_sent']}")
                print(f"  Bytes Sent:      {net_stats['bytes_sent']}")
                if net_stats['last_error']:
                    print(f"  Last Error:      {net_stats['last_error']}")

            if self.enable_flutter and self.flutter_bridge:
                flutter_stats = self.flutter_bridge.get_stats()
                print(f"\n{Colors.FLUTTER}FLUTTER BRIDGE STATISTICS:{Colors.RESET}")
                print(f"  Packets Sent:    {flutter_stats['packets_sent']}")
                print(f"  Bytes Sent:      {flutter_stats['bytes_sent']}")
                print(f"  Max Rate:        {flutter_stats['max_rate_hz']} Hz")
                print(f"  Errors:          {flutter_stats['errors']}")

            print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.RESET}\n")

    def start(self):
        """Start monitoring"""
        if not self.connect():
            return

        self.setup_logging()
        self.running = True

        try:
            self.read_serial_data()
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}⚠ Interrupted by user{Colors.RESET}")
        finally:
            self.stop()

    def stop(self):
        """Stop monitoring and cleanup"""
        self.running = False

        self.print_statistics()

        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"{Colors.OKGREEN}✓ Serial closed{Colors.RESET}")

        if self.transmitter:
            self.transmitter.close()
            print(f"{Colors.OKGREEN}✓ Network closed{Colors.RESET}")

        if self.flutter_bridge:
            self.flutter_bridge.close()

        if self.log_file:
            self.log_file.close()
            print(f"{Colors.OKGREEN}✓ Log closed{Colors.RESET}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='STM32 Drone Monitor with Network + Enhanced Flutter Bridge (v3.2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                          # Auto-detect, all features enabled
  %(prog)s -p /dev/ttyUSB0                          # Specific port
  %(prog)s --no-network                             # Disable network (Flutter only)
  %(prog)s --no-flutter                             # Disable Flutter (Network only)
  %(prog)s --flutter-ip 192.168.100.2 --flutter-port 5657  # Custom Flutter target
  %(prog)s --target 192.168.100.3 --port 6666       # Custom network target

CHANGELOG v3.2:
  - Enhanced DronePacket class with individual switch parsing
  - get_individual_switches(): Returns dict with switch_0 to switch_15 (True/False)
  - get_switch_value(id): Get specific switch state by ID (0-15)
  - get_active_switches(): Returns list of active switch IDs
  - JSON output includes both 'switches' dict and 'active_switches' list
  - Console display shows active switches with IDs (SW0, SW3, etc.)
  - Full backward compatibility with 'switches_raw' field
        """
    )

    parser.add_argument('-p', '--port', help='Serial port (default: auto-detect)')
    parser.add_argument('-b', '--baudrate', type=int, default=115200, help='Baudrate (default: 115200)')

    # Network options
    parser.add_argument('--no-network', action='store_true', help='Disable network transmission')
    parser.add_argument('--target', default='192.168.100.2', help='Network target IP (default: 192.168.100.2)')
    parser.add_argument('--port-net', type=int, default=5656, help='Network target port (default: 5656)')

    # Flutter Bridge options
    parser.add_argument('--no-flutter', action='store_true', help='Disable Flutter bridge')
    parser.add_argument('--flutter-ip', default='127.0.0.1', help='Flutter target IP (default: 127.0.0.1)')
    parser.add_argument('--flutter-port', type=int, default=5657, help='Flutter target port (default: 5657)')

    args = parser.parse_args()

    # Banner
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   STM32 DRONE MONITOR v3.2 - ENHANCED SWITCH EDITION              ║")
    print("║   Serial Monitor + Network + Flutter Bridge (Individual Switches) ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    monitor = DroneMonitor(
        port=args.port,
        baudrate=args.baudrate,
        enable_network=not args.no_network,
        target_ip=args.target,
        target_port=args.port_net,
        enable_flutter=not args.no_flutter,
        flutter_ip=args.flutter_ip,
        flutter_port=args.flutter_port
    )

    try:
        monitor.start()
    except Exception as e:
        print(f"{Colors.FAIL}✗ Fatal error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()