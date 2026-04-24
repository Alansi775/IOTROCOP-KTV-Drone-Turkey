# IOTROCOP KTV Drone System

**Professional autonomous drone control system** developed by **IOTROCOP TECHNOLOGY** in collaboration with **KTV DRONE**.

## System Overview

Industrial-grade drone control platform featuring real-time video processing, GPS navigation, MAVSDK flight control integration, and Flutter-based ground control station. Optimized for fiber optic communication with low-latency telemetry and high-definition video streaming.

---

## PX4 Autopilot Integration

This system uses **PX4 Autopilot** firmware running on the **Pixhawk Orange Cube** flight controller.

### Architecture
NVIDIA Jetson Xavier NX
↓
MAVSDK Server (C++ library)
↓
MAVLink Protocol
↓
Pixhawk Orange Cube
↓
PX4 Autopilot Firmware

### Key Points

- **PX4 Version:** Stable release (running on Pixhawk)
- **Communication:** MAVLink protocol via serial (921600 baud)
- **Interface:** MAVSDK library for C++/Python integration
- **No Custom Firmware:** Using official PX4 stable build
- **Control Mode:** Offboard control via MAVSDK API

The MAVSDK server (`mavsdk-server.service`) acts as a bridge between our Python control scripts and the PX4 firmware, providing a clean gRPC API for flight control commands.

---

## Network Topology
┌─────────────────────────┐                    ┌──────────────────────────┐
│  Commander (RPi 4)      │  Fiber Optic Link  │  Drone (Jetson Xavier)   │
│  192.168.100.1          │◄──────────────────►│  192.168.100.2           │
├─────────────────────────┤                    ├──────────────────────────┤
│ • Flutter UI Display    │                    │ • MAVSDK Server :50051   │
│ • Video Proxy :8080     │                    │ • Camera Stream :5000    │
│ • GPS Listener :5658    │                    │ • GPS Bridge :5658       │
│ • Telemetry :5657       │                    │ • Control Input :5656    │
└─────────────────────────┘                    └──────────────────────────┘
│
│ Serial
▼
┌──────────────────────┐
│  Pixhawk Orange Cube │
│  /dev/ttyACM0:921600 │
│  (PX4 Autopilot)     │
└──────────────────────┘

---

## Quick Start

### Prerequisites

**Commander (Raspberry Pi):**
- Raspberry Pi OS (64-bit)
- flutter-pi installed
- Python 3.7+

**Drone (NVIDIA Jetson):**
- JetPack 4.6+ (L4T 32.7.x)
- MAVSDK installed
- GStreamer with NVENC support
- Python 3.6+

### Installation

#### 1. Commander Setup

```bash
git clone https://github.com/Alansi775/IOTROCOP-KTV-Drone-Turkey.git
cd IOTROCOP-KTV-Drone-Turkey/Commander
sudo cp deployment/drone_app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable drone_app
sudo systemctl start drone_app
```

#### 2. Drone Setup

```bash
cd IOTROCOP-KTV-Drone-Turkey/Drone
sudo cp deployment/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mavsdk-server drone-control gps-bridge camera-stream
sudo systemctl start mavsdk-server drone-control gps-bridge camera-stream
```

---

## Project Structure
IOTROCOP-KTV-Drone-Turkey/
│
├── README.md
│
├── Commander/                         # Ground Control Station (Raspberry Pi 4)
│   ├── README.md
│   │
│   ├── video_streaming_panel/         # Flutter UI Application
│   │   ├── lib/
│   │   │   ├── main.dart
│   │   │   ├── screens/
│   │   │   │   ├── drone_control_page.dart
│   │   │   │   └── splash_screen.dart
│   │   │   ├── widgets/
│   │   │   │   ├── gps_widget.dart
│   │   │   │   ├── joystick.dart
│   │   │   │   ├── throttle_control.dart
│   │   │   │   └── simple_mjpeg_viewer.dart
│   │   │   └── services/
│   │   │       ├── gps_service.dart
│   │   │       └── udp_service.dart
│   │   ├── assets/
│   │   └── pubspec.yaml
│   │
│   ├── microservices/
│   │   ├── rpi_bridge.py              # Video proxy server
│   │   └── manual_joystick.py         # Manual keyboard control
│   │
│   ├── start_drone.sh                 # Startup script
│   │
│   └── deployment/
│       └── drone_app.service          # systemd service file
│
└── Drone/                             # Onboard Computer (NVIDIA Jetson Xavier NX)
├── README.md
│
├── droneCommands/
│   ├── full_control.py            # Main flight controller
│   ├── gps_bridge.py              # GPS UDP bridge
│   └── [additional scripts]
│
├── microservices/
│   ├── jetson_pure_gst.py         # GStreamer camera pipeline
│   └── [camera variants]
│
└── deployment/
├── mavsdk-server.service      # PX4 interface (MAVLink)
├── drone-control.service      # Offboard flight control
├── gps-bridge.service         # GPS data streaming
└── camera-stream.service      # Video encoding

---

## System Services

### Commander Services

| Service | Description | Port |
|---------|-------------|------|
| drone_app | Flutter UI application | Display |
| rpi_bridge | Video proxy server | 8080 |

### Drone Services

| Service | Description | Port/Interface |
|---------|-------------|----------------|
| mavsdk-server | PX4 flight controller interface | gRPC :50051 |
| drone-control | Offboard flight control | UDP :5656 |
| gps-bridge | GPS data streaming | UDP :5658 |
| camera-stream | Video encoding/streaming | HTTP :5000 |

---

## Communication Protocols

### UDP Ports
- **5656** - Drone control commands (Commander → Drone)
- **5657** - Joystick telemetry (Drone → Commander)
- **5658** - GPS data stream (Drone → Commander)

### HTTP Endpoints
- **5000** - Camera stream (Drone, GStreamer MJPEG)
- **8080** - Video proxy (Commander, Flask bridge)

### Serial Communication
- **ttyACM0** - Pixhawk Orange Cube (921600 baud, MAVLink protocol)

---

## Testing & Validation

### Manual Control Test
```bash
# On Commander
cd ~/microservices
python3 manual_joystick.py

# Controls:
# SPACE - ARM/DISARM
# W/S   - Throttle UP/DOWN
# A/D   - Roll LEFT/RIGHT
# Q/E   - Pitch FORWARD/BACK
```

### GPS Test (Simulated)
```bash
# On Drone
python3 /tmp/test_gps_istanbul.py
```

### Service Health Check
```bash
# On Drone
sudo systemctl status mavsdk-server drone-control gps-bridge camera-stream

# On Commander
sudo systemctl status drone_app
```

---

## Configuration

### Network Settings

**Commander (`~/microservices/rpi_bridge.py`):**
```python
NVIDIA_IP = "192.168.100.2"
CAMERA_PORT = 5000
PROXY_PORT = 8080
```

**Drone (`~/Desktop/droneCommands/gps_bridge.py`):**
```python
RASPBERRY_IP = "192.168.100.1"
GPS_UDP_PORT = 5658
```

---

## Safety & Operations

### Pre-Flight Checklist
- [ ] All services running
- [ ] GPS fix confirmed (outdoor)
- [ ] ARM/DISARM tested
- [ ] Video stream verified
- [ ] Failsafe timeout checked

### Failsafe Mechanisms
- 3-second timeout auto-disarm
- GPS validation
- Connection monitoring
- Manual override available

---

## Technical Specifications

| Component | Specification |
|-----------|---------------|
| Video Resolution | 640x480 @ 30fps |
| Video Encoding | MJPEG (NVENC) |
| GPS Update Rate | 1Hz |
| Control Latency | <50ms |
| Failsafe Timeout | 3 seconds |

---

## License

Proprietary - IOTROCOP TECHNOLOGY & KTV DRONE

---

## Version History

### v1.0.0 (2026-04-24)
- Initial production release
- PX4 integration via MAVSDK
- Video streaming with auto-reconnect
- GPS tracking and mapping
- Automatic service deployment

---

**Status:** Production Ready ✅  
**Last Updated:** 2026-04-24  
**Maintained by:** IOTROCOP TECHNOLOGY
