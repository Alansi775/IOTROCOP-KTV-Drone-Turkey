# IOTROCOP KTV Drone System - Turkey Branch

**Professional autonomous drone control system** developed by **IOTROCOP TECHNOLOGY** in collaboration with **KTV DRONE**, Turkey Branch.

## System Overview

Industrial-grade drone control platform featuring real-time video processing, GPS navigation, MAVSDK flight control integration, and Flutter-based ground control station. Optimized for fiber optic communication with low-latency telemetry and high-definition video streaming.

---

## Architecture

### Ground Control Station - Commander (Raspberry Pi 4)
High-performance ground control interface with embedded Flutter UI running on flutter-pi for direct hardware acceleration.

**Hardware:**
- Raspberry Pi 4 (4GB RAM)
- Fiber optic network interface
- Display output for real-time monitoring

**Software Stack:**
- Flutter (embedded UI via flutter-pi)
- Python microservices for video proxy
- UDP-based telemetry reception
- Real-time GPS visualization

**Key Features:**
- Live MJPEG video streaming with auto-reconnect
- Interactive GPS mapping (OpenStreetMap integration)
- Joystick telemetry display
- Connection status monitoring
- Manual keyboard control interface

---

### Onboard Computer - Drone (NVIDIA Jetson Xavier NX)
AI-capable onboard computer handling flight control, sensor fusion, and video encoding.

**Hardware:**
- NVIDIA Jetson Xavier NX
- IMX477 camera module
- Pixhawk Orange Cube flight controller
- Fiber optic communication module

**Software Stack:**
- MAVSDK (C++ flight controller interface)
- GStreamer (hardware-accelerated video encoding)
- Python control services
- GPS data aggregation

**Key Features:**
- MAVSDK server for Pixhawk communication
- Offboard flight mode control
- Hardware-accelerated H.264/MJPEG encoding
- GPS bridge with satellite tracking
- Automatic failsafe mechanisms

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
# Clone repository
git clone https://github.com/Alansi775/IOTROCOP-KTV-Drone-Turkey.git
cd IOTROCOP-KTV-Drone-Turkey/Commander

# Install service
sudo cp deployment/drone_app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable drone_app
sudo systemctl start drone_app
```

#### 2. Drone Setup

```bash
cd IOTROCOP-KTV-Drone-Turkey/Drone

# Install all services
sudo cp deployment/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mavsdk-server drone-control gps-bridge camera-stream
sudo systemctl start mavsdk-server drone-control gps-bridge camera-stream
```

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
| mavsdk-server | Flight controller interface | gRPC :50051 |
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
- **ttyACM0** - Pixhawk Orange Cube (921600 baud)

---

## Testing & Validation

### Manual Control Test
```bash
# On Commander
cd ~/microservices
python3 manual_joystick.py

# Keyboard controls:
# SPACE - ARM/DISARM toggle
# W/S   - Throttle increase/decrease
# A/D   - Roll left/right
# Q/E   - Pitch forward/backward
# ESC   - Exit
```

### GPS Validation (Simulated)
```bash
# On Drone
python3 /tmp/test_gps_istanbul.py
# Transmits fake GPS: Istanbul (41.0082°, 28.9784°)
# Verify on Commander GPS widget
```

### Service Health Check
```bash
# On Drone
sudo systemctl status mavsdk-server
sudo systemctl status drone-control
sudo systemctl status gps-bridge
sudo systemctl status camera-stream

# On Commander
sudo systemctl status drone_app
```

### Live Telemetry Monitoring
```bash
# Drone control logs
sudo journalctl -u drone-control -f

# GPS data logs
sudo journalctl -u gps-bridge -f

# Camera stream logs
sudo journalctl -u camera-stream -f

# Commander UI logs
sudo journalctl -u drone_app -f
```

---

## Project Structure
IOTROCOP-KTV-Drone-Turkey/
│
├── README.md                          # This file
│
├── Commander/                         # Raspberry Pi Ground Station
│   ├── README.md                      # Commander documentation
│   ├── video_streaming_panel/         # Flutter UI application
│   │   ├── lib/
│   │   │   ├── main.dart
│   │   │   ├── screens/
│   │   │   ├── widgets/
│   │   │   └── services/
│   │   ├── assets/
│   │   └── pubspec.yaml
│   ├── microservices/
│   │   ├── rpi_bridge.py              # Video proxy server
│   │   └── manual_joystick.py         # Manual control interface
│   ├── start_drone.sh                 # Startup script
│   └── deployment/
│       └── drone_app.service          # systemd service
│
└── Drone/                             # NVIDIA Jetson Onboard Computer
├── README.md                      # Drone documentation
├── droneCommands/
│   ├── full_control.py            # Main flight controller
│   ├── gps_bridge.py              # GPS UDP bridge
│   └── [additional control scripts]
├── microservices/
│   ├── jetson_pure_gst.py         # GStreamer camera pipeline
│   └── [camera stream variants]
└── deployment/
├── mavsdk-server.service      # Flight controller interface
├── drone-control.service      # Offboard control
├── gps-bridge.service         # GPS streaming
└── camera-stream.service      # Video encoding

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

### Flight Controller Settings

Update serial port if needed:
```bash
sudo nano /etc/systemd/system/mavsdk-server.service
# ExecStart=/usr/local/bin/mavsdk_server -p 50051 serial:///dev/ttyACM0:921600
```

---

## Safety & Operations

### Pre-Flight Checklist
- [ ] Verify all services running (`systemctl status`)
- [ ] Confirm GPS fix (outdoor operation)
- [ ] Test ARM/DISARM functionality
- [ ] Verify video stream quality
- [ ] Check failsafe timeout (3 seconds)
- [ ] Ensure manual override available

### Failsafe Mechanisms
- **3-second timeout** - Automatic disarm if no commands received
- **GPS validation** - Position sanity checks before autonomous flight
- **Connection monitoring** - Visual indicator on Commander UI
- **Manual override** - Keyboard control available anytime

---

## Troubleshooting

### Video Stream Not Displaying

```bash
# On Drone - verify camera
nvgstcapture-1.0 --help

# Test GStreamer pipeline
gst-launch-1.0 nvarguscamerasrc ! nvvidconv ! jpegenc ! fakesink

# Restart camera service
sudo systemctl restart camera-stream
```

### GPS Not Updating

```bash
# Verify GPS service
sudo systemctl status gps-bridge

# Monitor UDP packets
nc -ul 5658

# Check network flow
sudo tcpdump -i any port 5658
```

### Flight Controller Connection Issues

```bash
# Verify serial port
ls -l /dev/ttyACM*

# Check MAVSDK logs
sudo journalctl -u mavsdk-server -n 100

# Verify baud rate
stty -F /dev/ttyACM0
```

---

## Development

### Building Commander UI
```bash
cd Commander/video_streaming_panel
flutter pub get
flutter build bundle
```

### Modifying Services
After editing service files:
```bash
sudo systemctl daemon-reload
sudo systemctl restart [service-name]
```

---

## Technical Specifications

| Component | Specification |
|-----------|---------------|
| Video Resolution | 640x480 @ 30fps (configurable) |
| Video Encoding | MJPEG (NVENC hardware acceleration) |
| GPS Update Rate | 1Hz |
| Control Latency | <50ms (fiber optic) |
| Failsafe Timeout | 3 seconds |
| Max Communication Range | Limited by fiber optic cable length |

---

## License

Proprietary - IOTROCOP TECHNOLOGY & KTV DRONE

---

## Contact & Support

**IOTROCOP TECHNOLOGY**  
Turkey Branch

For technical support or inquiries, contact the development team.

---

## Version History

### v1.0.0 (2026-04-24)
- Initial production release
- Video streaming with auto-reconnect
- GPS tracking and mapping
- MAVSDK flight control integration
- Automatic service deployment
- Comprehensive documentation

---

## Acknowledgments

- **MAVSDK** - Flight controller communication framework
- **flutter-pi** - Embedded Flutter runtime
- **OpenStreetMap** - GPS visualization tiles
- **GStreamer** - Video pipeline framework
- **NVIDIA** - Jetson platform and hardware acceleration

---

**Status:** Production Ready ✅  
**Last Updated:** 2026-04-24  
**Maintained by:** IOTROCOP TECHNOLOGY
