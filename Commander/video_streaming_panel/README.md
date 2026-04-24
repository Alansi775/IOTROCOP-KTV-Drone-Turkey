# Drone Video Streaming Panel

A real-time drone control and monitoring system built with Flutter, featuring live video streaming, GPS tracking, and telemetry visualization.

## System Architecture

### Hardware Components
- **Raspberry Pi 4** - Flutter UI and video proxy
- **NVIDIA Jetson Xavier NX** - Video processing and flight controller interface
- **Pixhawk Orange Cube** - Flight controller (via MAVSDK)
- **IMX477 Camera** - Video streaming via GStreamer
- **STM32 Joystick** - Remote control input
- **Fiber Optic Link** - High-speed communication (192.168.100.x network)

### Network Topology
Raspberry Pi (192.168.100.1)  <---Fiber--->  Nvidia Jetson (192.168.100.2)
|                                              |
Flutter UI                                   MAVSDK Server
Video Display                                Camera Stream
GPS Display                                  Drone Control
GPS Bridge

## Features

### Video Streaming
- Real-time MJPEG stream from IMX477 camera
- Auto-reconnect on connection loss
- Hardware-accelerated encoding via NVENC
- Proxy bridge for network isolation

### GPS Tracking
- Real-time GPS position display
- Satellite count and fix status
- Interactive map with OpenStreetMap tiles
- Automatic position centering
- Default location: Istanbul (41.0082, 28.9784)

### Drone Control
- MAVSDK-based flight controller interface
- ARM/DISARM controls
- Throttle, pitch, roll, yaw inputs
- Offboard flight mode support
- Failsafe auto-disarm (3-second timeout)

### Telemetry Display
- Connection status indicator
- Live joystick position feedback
- Switch state monitoring
- Sensor data visualization

## Installation

### Raspberry Pi Setup

#### Prerequisites
```bash
sudo apt update
sudo apt install -y flutter-pi git
```

#### Clone and Build
```bash
git clone https://github.com/Alansi775/DroneVideoStreamingPanel.git
cd DroneVideoStreamingPanel
flutter pub get
flutter build bundle
```

#### System Service
```bash
sudo cp deployment/drone_app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable drone_app
sudo systemctl start drone_app
```

### NVIDIA Jetson Setup

#### Install Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip gstreamer1.0-tools
pip3 install flask mavsdk --break-system-packages
```

#### Configure Services
```bash
# MAVSDK Server
sudo cp deployment/nvidia/mavsdk-server.service /etc/systemd/system/
sudo systemctl enable mavsdk-server

# Camera Stream
sudo cp deployment/nvidia/camera-stream.service /etc/systemd/system/
sudo systemctl enable camera-stream

# Drone Control
sudo cp deployment/nvidia/drone-control.service /etc/systemd/system/
sudo systemctl enable drone-control

# GPS Bridge
sudo cp deployment/nvidia/gps-bridge.service /etc/systemd/system/
sudo systemctl enable gps-bridge

sudo systemctl daemon-reload
```

## Configuration

### Network Settings
Edit configuration files to match your network:

**Raspberry Pi** (`~/microservices/rpi_bridge.py`):
```python
NVIDIA_IP = "192.168.100.2"
CAMERA_PORT = 5000
```

**NVIDIA Jetson** (`~/Desktop/droneCommands/gps_bridge.py`):
```python
RASPBERRY_IP = "192.168.100.1"
GPS_UDP_PORT = 5658
```

### Flight Controller
Update serial port in MAVSDK service:
```bash
sudo nano /etc/systemd/system/mavsdk-server.service
# ExecStart=/usr/local/bin/mavsdk_server -p 50051 serial:///dev/ttyACM0:921600
```

## Testing

### Manual Control Test
```bash
# On Raspberry Pi
cd ~/microservices
python3 manual_joystick.py

# Controls:
# SPACE - ARM/DISARM
# W/S   - Throttle UP/DOWN
# A/D   - Roll LEFT/RIGHT
# Q/E   - Pitch FORWARD/BACK
# ESC   - Quit
```

### GPS Test (Fake Location)
```bash
# On NVIDIA Jetson
python3 /tmp/test_gps_istanbul.py
# Sends fake GPS: Istanbul (41.0082, 28.9784)
```

### Service Status Check
```bash
# NVIDIA Jetson
sudo systemctl status mavsdk-server
sudo systemctl status drone-control
sudo systemctl status gps-bridge
sudo systemctl status camera-stream

# Raspberry Pi
sudo systemctl status drone_app
```

### Live Logs
```bash
# Drone Control
sudo journalctl -u drone-control.service -f

# GPS Data
sudo journalctl -u gps-bridge.service -f

# Flutter App
sudo journalctl -u drone_app -f
```

## Project Structure
DroneVideoStreamingPanel/
├── lib/
│   ├── main.dart
│   ├── screens/
│   │   ├── drone_control_page.dart
│   │   └── splash_screen.dart
│   ├── widgets/
│   │   ├── gps_widget.dart
│   │   ├── joystick.dart
│   │   ├── throttle_control.dart
│   │   └── simple_mjpeg_viewer.dart
│   └── services/
│       ├── gps_service.dart
│       └── udp_service.dart
├── assets/
│   └── icons/
├── deployment/
│   ├── drone_app.service
│   └── nvidia/
│       ├── mavsdk-server.service
│       ├── camera-stream.service
│       ├── drone-control.service
│       └── gps-bridge.service
└── README.md

## Communication Protocols

### UDP Ports
- **5656** - Drone control commands (Raspberry Pi to NVIDIA)
- **5657** - Joystick telemetry (NVIDIA to Raspberry Pi)
- **5658** - GPS data (NVIDIA to Raspberry Pi)

### HTTP Endpoints
- **8080** - Video proxy (Raspberry Pi)
- **5000** - Camera stream (NVIDIA)

### MAVSDK
- **50051** - gRPC server (localhost on NVIDIA)

## Troubleshooting

### Video Stream Issues
```bash
# Check camera detection
nvgstcapture-1.0 --help

# Test gstreamer pipeline
gst-launch-1.0 nvarguscamerasrc ! nvvidconv ! jpegenc ! fakesink

# Restart camera service
sudo systemctl restart camera-stream
```

### GPS Not Updating
```bash
# Check GPS service
sudo systemctl status gps-bridge

# Monitor UDP packets
nc -ul 5658

# Verify GPS data flow
sudo tcpdump -i any port 5658
```

### Flight Controller Connection
```bash
# Check serial port
ls -l /dev/ttyACM*

# Verify MAVSDK connection
sudo journalctl -u mavsdk-server -n 50
```

## Safety Notes

- Always test in a controlled environment
- Verify ARM/DISARM functionality before flight
- Monitor failsafe timeout (3 seconds)
- Keep manual override accessible
- Ensure GPS fix before outdoor flight

## Development

### Building for Development
```bash
flutter pub get
flutter build bundle --debug
```

### Hot Reload
Not supported on flutter-pi. Use systemctl restart for updates.

## License

This project is developed for educational and research purposes.

## Contributors

Alansi775

## Acknowledgments

- MAVSDK for flight controller interface
- flutter-pi for embedded Flutter runtime
- OpenStreetMap for map tiles

## Version History

### v1.0.0 (2026-04-24)
- Initial release
- Video streaming with auto-reconnect
- GPS tracking and mapping
- Manual control interface
- Automatic service startup
