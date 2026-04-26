# IOTROCOP KTV Drone System

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)
![Platform](https://img.shields.io/badge/platform-Jetson%20Xavier%20NX-76b900.svg)
![PX4](https://img.shields.io/badge/autopilot-PX4-purple.svg)

**Professional autonomous drone control system developed by IOTROCOP TECHNOLOGY in collaboration with KTV DRONE.**

Industrial-grade drone control platform featuring real-time video processing, GPS navigation,
MAVSDK flight control integration, and Flutter-based ground control station.
Optimized for fiber optic communication with low-latency telemetry and high-definition video streaming.

</div>

---

## Table of Contents

- [System Overview](#-system-overview)
- [PX4 Autopilot Integration](#-px4-autopilot-integration)
- [Network Topology](#-network-topology)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [System Services](#-system-services)
- [Communication Protocols](#-communication-protocols)
- [Testing & Validation](#-testing--validation)
- [Configuration](#-configuration)
- [Safety & Operations](#-safety--operations)
- [Technical Specifications](#-technical-specifications)

---

## System Overview

This system provides an industrial-grade drone control platform with the following capabilities:

-  **Real-time video processing** — MJPEG streaming via GStreamer + NVENC hardware encoding
-  **GPS navigation** — Live GPS tracking with UDP bridge
-  **MAVSDK flight control** — gRPC-based offboard control via PX4
-  **Flutter ground station** — Touch-friendly UI with joystick and telemetry
-  **Fiber optic link** — Low-latency, high-bandwidth communication between commander and drone

---

##  PX4 Autopilot Integration

This system uses **PX4 Autopilot firmware** running on the **Pixhawk Orange Cube** flight controller.

### Architecture

```
NVIDIA Jetson Xavier NX
        ↓
  MAVSDK Server (C++ library)
        ↓
   MAVLink Protocol
        ↓
Pixhawk Orange Cube
        ↓
  PX4 Autopilot Firmware
```

### Key Points

| Parameter        | Value                          |
|-----------------|-------------------------------|
| PX4 Version     | Stable release (on Pixhawk)   |
| Communication   | MAVLink via serial @ 921600 baud |
| Interface       | MAVSDK library (C++/Python)   |
| Firmware        | Official PX4 stable build     |
| Control Mode    | Offboard control via MAVSDK API |

> The **MAVSDK server** (`mavsdk-server.service`) acts as a bridge between Python control scripts and PX4 firmware, providing a clean gRPC API for flight control commands.

---

##  Network Topology

```
┌─────────────────────────┐                    ┌──────────────────────────┐
│  Commander (RPi 4)      │  Fiber Optic Link  │  Drone (Jetson Xavier)   │
│  192.168.100.1          │◄──────────────────►│  192.168.100.2           │
├─────────────────────────┤                    ├──────────────────────────┤
│ • Flutter UI Display    │                    │ • MAVSDK Server :50051   │
│ • Video Proxy    :8080  │                    │ • Camera Stream :5000    │
│ • GPS Listener   :5658  │                    │ • GPS Bridge    :5658    │
│ • Telemetry      :5657  │                    │ • Control Input :5656    │
└─────────────────────────┘                    └──────────────────────────┘
                                                          │
                                                          │ Serial
                                                          ▼
                                               ┌──────────────────────┐
                                               │  Pixhawk Orange Cube │
                                               │  /dev/ttyACM0:921600 │
                                               │  (PX4 Autopilot)     │
                                               └──────────────────────┘
```

---

##  Quick Start

### Prerequisites

**Commander (Raspberry Pi):**
- Raspberry Pi OS (64-bit)
- `flutter-pi` installed
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

##  Project Structure

```
IOTROCOP-KTV-Drone-Turkey/
│
├── README.md
│
├── Commander/                              # Ground Control Station
│   ├── README.md
│   ├── video_streaming_panel/              # Flutter UI
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
│   ├── microservices/
│   │   ├── rpi_bridge.py
│   │   └── manual_joystick.py
│   ├── start_drone.sh
│   └── deployment/
│       └── drone_app.service
│
└── Drone/                                  # Onboard Computer
    ├── README.md
    ├── droneCommands/
    │   ├── full_control.py
    │   ├── gps_bridge.py
    │   └── [additional scripts]
    ├── microservices/
    │   ├── jetson_pure_gst.py
    │   └── [camera variants]
    └── deployment/
        ├── mavsdk-server.service
        ├── drone-control.service
        ├── gps-bridge.service
        └── camera-stream.service
```

---

##  System Services

### Commander Services

| Service     | Description            | Port    |
|------------|------------------------|---------|
| `drone_app` | Flutter UI application | Display |
| `rpi_bridge`| Video proxy server     | 8080    |

### Drone Services

| Service          | Description                    | Port / Interface |
|-----------------|--------------------------------|-----------------|
| `mavsdk-server` | PX4 flight controller interface | gRPC :50051     |
| `drone-control` | Offboard flight control         | UDP :5656       |
| `gps-bridge`    | GPS data streaming              | UDP :5658       |
| `camera-stream` | Video encoding / streaming      | HTTP :5000      |

---

##  Communication Protocols

### UDP Ports

| Port | Direction              | Purpose               |
|------|------------------------|-----------------------|
| 5656 | Commander → Drone      | Drone control commands|
| 5657 | Drone → Commander      | Joystick telemetry    |
| 5658 | Drone → Commander      | GPS data stream       |

### HTTP Endpoints

| Port | Host      | Description                     |
|------|-----------|----------------------------------|
| 5000 | Drone     | Camera stream (GStreamer MJPEG)  |
| 8080 | Commander | Video proxy (Flask bridge)       |

### Serial Communication

| Device       | Baud Rate | Protocol |
|-------------|-----------|----------|
| `/dev/ttyACM0` | 921600  | MAVLink (Pixhawk Orange Cube) |

---

##  Testing & Validation

### Manual Control Test

```bash
# On Commander
cd ~/microservices
python3 manual_joystick.py
```

**Keyboard Controls:**

| Key     | Action              |
|---------|---------------------|
| `SPACE` | ARM / DISARM        |
| `W / S` | Throttle UP / DOWN  |
| `A / D` | Roll LEFT / RIGHT   |
| `Q / E` | Pitch FORWARD / BACK|

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

##  Configuration

### Network Settings

**Commander** (`~/microservices/rpi_bridge.py`):

```python
NVIDIA_IP    = "192.168.100.2"
CAMERA_PORT  = 5000
PROXY_PORT   = 8080
```

**Drone** (`~/Desktop/droneCommands/gps_bridge.py`):

```python
RASPBERRY_IP  = "192.168.100.1"
GPS_UDP_PORT  = 5658
```

---

##  Safety & Operations

### Pre-Flight Checklist

- [ ] All services running
- [ ] GPS fix confirmed (outdoor)
- [ ] ARM/DISARM tested
- [ ] Video stream verified
- [ ] Failsafe timeout checked

### Failsafe Mechanisms

-  **3-second timeout** — auto-disarm on lost connection
-  **GPS validation** — position lock required before flight
-  **Connection monitoring** — continuous link health checks
-  **Manual override** — available at all times

---

##  Technical Specifications

| Component        | Specification              |
|-----------------|---------------------------|
| Video Resolution | 640×480 @ 30fps           |
| Video Encoding   | MJPEG (NVENC hardware)    |
| GPS Update Rate  | 1 Hz                      |
| Control Latency  | < 50 ms                   |
| Failsafe Timeout | 3 seconds                 |
| Serial Baud Rate | 921600                    |
| MAVLink Protocol | v2                        |

---

##  License

**Proprietary** — IOTROCOP TECHNOLOGY & KTV DRONE. All rights reserved.

---

##  Version History

### v1.0.0 — 2026-04-24

- ✅ Initial production release
- ✅ PX4 integration via MAVSDK
- ✅ Video streaming with auto-reconnect
- ✅ GPS tracking and mapping
- ✅ Automatic service deployment

---

<div align="center">

**Status: Still Not Ready For Production**

Last Updated: 2026-04-24 · Maintained by **IOTROCOP TECHNOLOGY**

</div>
